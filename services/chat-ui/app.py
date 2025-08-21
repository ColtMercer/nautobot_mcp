"""Flask Chat UI for MCP tools."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

import os
import tempfile
import logging
from flask import Flask, render_template, request, jsonify, session, send_file, make_response
from dotenv import load_dotenv

from mcp_client import get_server_catalogs, invoke_tool_on_server, get_api_call_history, get_context_windows

try:
    from openai import OpenAI  # Optional: only used if OPENAI_API_KEY is set
except Exception:
    OpenAI = None

from exporters import export_json, export_markdown

logger = logging.getLogger(__name__)

# MongoDB setup
from pymongo import MongoClient
from bson import ObjectId
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB = os.environ.get('MONGO_DB', 'nautobot_mcp')
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB]
conversations_col = mongo_db.get_collection('conversations')

load_dotenv()

app = Flask(__name__)
app.secret_key = 'nautobot-mcp-chat-secret-key'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour


@app.route('/')
def index():
    """Main chat interface."""
    # Get server catalogs
    catalogs = get_server_catalogs()
    
    # Get or create session ID from request
    session_id = request.cookies.get('session_id')
    if not session_id:
        # Create a new session
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
    
    # Get or create conversation for this session
    conv_doc = conversations_col.find_one({'session_id': session_id})
    if not conv_doc:
        # Create a new conversation document for this session
        conv = {
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'messages': [],
            'tools': []
        }
        inserted = conversations_col.insert_one(conv)
        conv_doc = conv
    
    # Load conversation data
    chat_history = conv_doc.get('messages', [])
    tool_history = conv_doc.get('tools', [])
    
    response = make_response(render_template('index.html', 
                         catalogs=catalogs,
                         chat_history=chat_history,
                         context_history=[]))
    
    # Set session cookie
    response.set_cookie('session_id', session_id, max_age=3600)  # 1 hour
    
    return response


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests."""
    import time
    start_time = time.time()
    
    data = request.get_json()
    prompt = data.get('message', '')
    selected_servers = data.get('selected_servers', [])
    
    if not prompt or not selected_servers:
        return jsonify({'error': 'Message and server selection required'})
    
    # Get session ID from request
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session ID found'})
    
    # Get conversation for this session
    conv_doc = conversations_col.find_one({'session_id': session_id})
    if not conv_doc:
        return jsonify({'error': 'No conversation found for session'})
    
    # Load conversation data
    chat_history = conv_doc.get('messages', [])
    tool_history = conv_doc.get('tools', [])
    
    # Add user message to history
    user_turn = {
        "role": "user",
        "text": prompt,
        "timestamp": datetime.now().isoformat()
    }
    
    # Add user message to history
    chat_history.append(user_turn)
    
    # Process with LLM chat tool
    server_name = selected_servers[0]  # Use first selected server
    
    try:
        # Prepare conversation history for context
        conversation_history = chat_history[-25:]  # Use more history for better follow-ups
        
        # If OpenAI is configured, use it as a general-purpose LLM with function-calling to MCP tools
        use_openai = bool(os.environ.get('OPENAI_API_KEY')) and OpenAI is not None
        assistant_response = None
        citations = []
        response_data = None
        
        if use_openai:
            logger.info(f"[TIMING] Starting OpenAI processing at {time.time() - start_time:.2f}s")
            client = OpenAI()
            model = os.environ.get('OPENAI_MODEL', os.environ.get('DEFAULT_MODEL', 'gpt-4o-mini'))
            system_prompt = (
                "You are a helpful general-purpose assistant. "
                "You can call MCP tools to retrieve Nautobot data when appropriate. "
                "Answer normally unless a tool is needed. "
                "Always use conversation history to resolve pronouns and follow-ups. "
                "If the user asks to reformat or export 'that' or 'those results', use the most recent relevant results from the conversation without asking them to paste it again. "
                "IMPORTANT: Use markdown formatting for better readability. When presenting data in tables, use proper markdown table syntax. "
                "For example: | Column1 | Column2 | Column3 | |---------|---------|---------| | Data1 | Data2 | Data3 |"
            )
            # Build conversation history for OpenAI function calling
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add recent conversation history (last 5 turns to avoid context overflow)
            recent_history = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
            
            for turn in recent_history:
                role = turn.get("role", "user")
                text = turn.get("text", "")
                
                # Skip error messages
                if role == "assistant" and text.startswith("Error processing request:"):
                    continue
                
                # Add user messages directly
                if role == "user":
                    messages.append({"role": "user", "content": text})
                    continue
                
                # For assistant messages, check if they had tool calls
                if role == "assistant" and turn.get("citations"):
                    # Find the corresponding tool result
                    citations = turn.get("citations", [])
                    if len(citations) == 1:  # Simple case: one tool call
                        citation = citations[0]
                        tool_name = citation.get("tool")
                        tool_args = citation.get("args", {})
                        
                        # Find the tool result
                        tool_result = None
                        for tool_entry in tool_history:
                            if (tool_entry.get('tool') == tool_name and 
                                tool_entry.get('args') == tool_args):
                                tool_result = tool_entry.get('result', {})
                                break
                        
                        if tool_result:
                            # Add assistant message with tool call
                            tool_call_id = f"call_{tool_name[:15]}_{abs(hash(json.dumps(tool_args, sort_keys=True))) % 1000:03d}"
                            messages.append({
                                "role": "assistant",
                                "content": text,
                                "tool_calls": [{
                                    "id": tool_call_id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": json.dumps(tool_args)
                                    }
                                }]
                            })
                            
                            # Add tool response
                            messages.append({
                                "role": "tool",
                                "content": json.dumps(tool_result),
                                "tool_call_id": tool_call_id
                            })
                        else:
                            # No tool result found, add as regular assistant message
                            messages.append({"role": "assistant", "content": text})
                    else:
                        # Multiple tool calls - add as regular assistant message for now
                        messages.append({"role": "assistant", "content": text})
                else:
                    # Regular assistant message without tool calls
                    messages.append({"role": "assistant", "content": text})
            
            logger.info(f"Built conversation history with {len(messages)} messages, including {len([m for m in messages if m['role'] == 'tool'])} tool results")
            
            # Debug: Log what we're sending to OpenAI
            debug_messages = []
            for msg in messages:
                debug_msg = {
                    "role": msg["role"],
                    "content_length": len(msg.get("content", ""))
                }
                if msg["role"] == "tool":
                    debug_msg["tool_call_id"] = msg.get("tool_call_id", "unknown")
                debug_messages.append(debug_msg)
            logger.info(f"Messages being sent to OpenAI: {json.dumps(debug_messages, indent=2)}")
            
            # Debug: Log session state
            logger.info(f"Session state - chat_history: {len(session.get('chat_history', []))} messages, tool_history: {len(session.get('tool_history', []))} tools")
            if session.get('tool_history'):
                logger.info(f"Recent tool history: {[t.get('tool') for t in session.get('tool_history', [])[-3:]]}")
            
            messages.append({"role": "user", "content": prompt})
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_prefixes_by_location_enhanced",
                        "description": "Query prefixes by location with optional output format.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location_name": {"type": "string"},
                                "format": {"type": "string", "enum": ["json", "table", "dataframe", "csv"], "default": "json"}
                            },
                            "required": ["location_name"],
                            "additionalProperties": False
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_devices_by_location",
                        "description": "Query devices by location.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location_name": {"type": "string"}
                            },
                            "required": ["location_name"],
                            "additionalProperties": False
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_devices_by_location_and_role",
                        "description": "Query devices by location and role.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location_name": {"type": "string"},
                                "role_name": {"type": "string"}
                            },
                            "required": ["location_name", "role_name"],
                            "additionalProperties": False
                        }
                    }
                }
            ]
            logger.info(f"[TIMING] Making first OpenAI API call at {time.time() - start_time:.2f}s")
            first = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            logger.info(f"[TIMING] First OpenAI API call completed at {time.time() - start_time:.2f}s")
            choice = first.choices[0]
            msg = choice.message
            if msg.tool_calls:
                messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
                logger.info(f"[TIMING] Processing {len(msg.tool_calls)} tool calls at {time.time() - start_time:.2f}s")
                for tc in msg.tool_calls:
                    fn = tc.function
                    name = fn.name
                    logger.info(f"[TIMING] Invoking tool '{name}' at {time.time() - start_time:.2f}s")
                    try:
                        args = json.loads(fn.arguments or '{}')
                    except Exception:
                        args = {}
                    
                    if name == 'get_prefixes_by_location_enhanced':
                        location_name = args.get('location_name', '')
                        fmt = args.get('format', 'json')
                        logger.info(f"[TIMING] Calling MCP tool 'get_prefixes_by_location_enhanced' for location '{location_name}' at {time.time() - start_time:.2f}s")
                        api_result = invoke_tool_on_server(
                            server_name,
                            'get_prefixes_by_location_enhanced',
                            {"location_name": location_name, "format": fmt}
                        )
                        logger.info(f"[TIMING] MCP tool 'get_prefixes_by_location_enhanced' completed at {time.time() - start_time:.2f}s")
                    elif name == 'get_devices_by_location':
                        location_name = args.get('location_name', '')
                        logger.info(f"[TIMING] Calling MCP tool 'get_devices_by_location' for location '{location_name}' at {time.time() - start_time:.2f}s")
                        api_result = invoke_tool_on_server(
                            server_name,
                            'get_devices_by_location',
                            {"location_name": location_name}
                        )
                        logger.info(f"[TIMING] MCP tool 'get_devices_by_location' completed at {time.time() - start_time:.2f}s")
                    elif name == 'get_devices_by_location_and_role':
                        location_name = args.get('location_name', '')
                        role_name = args.get('role_name', '')
                        logger.info(f"[TIMING] Calling MCP tool 'get_devices_by_location_and_role' for location '{location_name}', role '{role_name}' at {time.time() - start_time:.2f}s")
                        api_result = invoke_tool_on_server(
                            server_name,
                            'get_devices_by_location_and_role',
                            {"location_name": location_name, "role_name": role_name}
                        )
                        logger.info(f"[TIMING] MCP tool 'get_devices_by_location_and_role' completed at {time.time() - start_time:.2f}s")
                    else:
                        api_result = {"error": f"Unknown tool {name}"}
                    
                    # Store tool call and result for future reference
                    tool_result = api_result.get('result', api_result)
                    persisted = {
                        "tool": name,
                        "args": args,
                        "result": tool_result,
                        "timestamp": datetime.now().isoformat()
                    }
                    tool_history.append(persisted)
                    citations.append({"tool": name, "args": args})
                    
                    # Add tool result to messages for this conversation turn
                    messages.append({
                        "role": "tool", 
                        "tool_call_id": tc.id, 
                        "content": json.dumps(tool_result)
                    })
                logger.info(f"[TIMING] Making second OpenAI API call at {time.time() - start_time:.2f}s")
                second = client.chat.completions.create(model=model, messages=messages)
                logger.info(f"[TIMING] Second OpenAI API call completed at {time.time() - start_time:.2f}s")
                assistant_response = second.choices[0].message.content or ""
            else:
                assistant_response = msg.content or ""
        else:
            logger.info(f"[TIMING] Using MCP llm_chat tool at {time.time() - start_time:.2f}s")
            result = invoke_tool_on_server(
                server_name,
                "llm_chat",
                {
                    "message": prompt,
                    "conversation_history": conversation_history
                }
            )
            logger.info(f"[TIMING] MCP llm_chat tool completed at {time.time() - start_time:.2f}s")
            if "error" in result:
                assistant_response = f"Error: {result['error']}"
            else:
                tool_result = result.get("result", {})
                assistant_response = tool_result.get("answer", "No response")
                citations = tool_result.get("citations", [])
        
        # Check if the LLM requested any specific format and prepare response data
        response_data = None
        if citations:
            for citation in citations:
                if citation.get("tool") == "get_prefixes_by_location_enhanced":
                    format_type = citation.get("args", {}).get("format", "json")
                    # Only make additional API calls if the LLM specifically requested a different format
                    if format_type in ["csv", "table", "dataframe"]:
                        # Find the tool result from our history to avoid redundant API calls
                        location_name = citation.get("args", {}).get("location_name", "")
                        for tool_entry in tool_history:
                            if (tool_entry.get('tool') == 'get_prefixes_by_location_enhanced' and 
                                tool_entry.get('args', {}).get('location_name') == location_name):
                                # Use the existing result instead of making a new API call
                                tool_result = tool_entry.get('result', {})
                                if format_type == "csv" and tool_result.get("success"):
                                    response_data = {
                                        "format": "csv",
                                        "data": tool_result.get("data", []),
                                        "message": "Data available for CSV export"
                                    }
                                elif format_type == "table" and tool_result.get("success"):
                                    response_data = {
                                        "format": "table", 
                                        "data": tool_result.get("data", [])
                                    }
                                elif format_type == "dataframe" and tool_result.get("success"):
                                    response_data = {
                                        "format": "dataframe",
                                        "analysis": tool_result.get("summary", {})
                                    }
                                break
                        break
        
        # Add assistant response to history
        assistant_turn = {
            "role": "assistant",
            "text": assistant_response,
            "citations": citations,
            "timestamp": datetime.now().isoformat()
        }
        chat_history.append(assistant_turn)
        
        # Persist conversation data to MongoDB
        try:
            conversations_col.update_one(
                {'session_id': session_id}, 
                {
                    '$set': {
                        'messages': chat_history,
                        'tools': tool_history
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to persist conversation data: {e}")
        
        total_time = time.time() - start_time
        logger.info(f"[TIMING] Total request completed in {total_time:.2f}s")
        
        return jsonify({
            'success': True,
            'response': assistant_response,
            'citations': citations,
            'data': response_data,
            'chat_history': chat_history,
            'context_history': [],
            'timing': {
                'total_time': total_time
            }
        })
        
    except Exception as e:
        error_response = f"Error processing request: {str(e)}"
        
        # Add error to history
        error_turn = {
            "role": "assistant",
            "text": error_response,
            "citations": [],
            "timestamp": datetime.now().isoformat()
        }
        chat_history.append(error_turn)
        
        # Persist error to MongoDB
        try:
            conversations_col.update_one(
                {'session_id': session_id}, 
                {
                    '$set': {
                        'messages': chat_history,
                        'tools': tool_history
                    }
                }
            )
        except Exception as persist_error:
            logger.error(f"Failed to persist error: {persist_error}")
        
        total_time = time.time() - start_time
        logger.info(f"[TIMING] Request failed after {total_time:.2f}s")
        
        return jsonify({
            'success': False,
            'error': error_response,
            'chat_history': chat_history,
            'context_history': [],
            'timing': {
                'total_time': total_time
            }
        })


@app.route('/api/export/<format>')
def export(format):
    """Export chat history."""
    # Get session ID from request
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'success': False, 'error': 'No session ID found'})
    
    # Get conversation for this session
    conv_doc = conversations_col.find_one({'session_id': session_id})
    if not conv_doc:
        return jsonify({'success': False, 'error': 'No conversation found for session'})
    
    chat_history = conv_doc.get('messages', [])
    
    if format == 'json':
        try:
            filepath = export_json(chat_history)
            return jsonify({'success': True, 'filepath': filepath})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    elif format == 'markdown':
        try:
            filepath = export_markdown(chat_history)
            return jsonify({'success': True, 'filepath': filepath})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    else:
        return jsonify({'success': False, 'error': 'Invalid export format'})


@app.route('/api/clear')
def clear_chat():
    """Clear chat history and start a new conversation."""
    # Get session ID from request
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'success': False, 'error': 'No session ID found'})
    
    # Archive the current conversation before clearing
    conv_doc = conversations_col.find_one({'session_id': session_id})
    if conv_doc and conv_doc.get('messages'):
        # Create archive entry
        archive_entry = {
            'session_id': session_id,
            'archived_at': datetime.now().isoformat(),
            'messages': conv_doc.get('messages', []),
            'tools': conv_doc.get('tools', []),
            'title': _generate_conversation_title(conv_doc.get('messages', [])),
            'message_count': len(conv_doc.get('messages', [])),
            'first_message': conv_doc.get('messages', [{}])[0].get('text', '') if conv_doc.get('messages') else ''
        }
        mongo_db.get_collection('conversation_archives').insert_one(archive_entry)
    
    # Clear conversation data
    conversations_col.update_one(
        {'session_id': session_id}, 
        {
            '$set': {
                'messages': [],
                'tools': [],
                'updated_at': datetime.now().isoformat()
            }
        }
    )
    
    return jsonify({'success': True})


def _generate_conversation_title(messages):
    """Generate a title for the conversation based on the first user message."""
    if not messages:
        return "Empty Conversation"
    
    # Find the first user message
    for msg in messages:
        if msg.get('role') == 'user':
            text = msg.get('text', '')
            # Truncate to reasonable length
            if len(text) > 50:
                text = text[:47] + "..."
            return text
    
    return "Conversation"


@app.route('/api/chat-history', methods=['GET'])
def get_chat_history():
    """Get archived conversation history."""
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session ID found'})
    
    # Get archived conversations for this session
    archives = list(mongo_db.get_collection('conversation_archives').find(
        {'session_id': session_id},
        {
            'archived_at': 1,
            'title': 1,
            'message_count': 1,
            'first_message': 1,
            '_id': 1
        }
    ).sort('archived_at', -1).limit(20))  # Last 20 conversations
    
    # Convert ObjectId to string for JSON serialization
    for archive in archives:
        archive['_id'] = str(archive['_id'])
    
    return jsonify({'archives': archives})


@app.route('/api/chat-history/<archive_id>', methods=['GET'])
def get_archived_conversation(archive_id):
    """Get a specific archived conversation."""
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session ID found'})
    
    try:
        # Convert string to ObjectId
        obj_id = ObjectId(archive_id)
        
        # Get the archived conversation
        archive = mongo_db.get_collection('conversation_archives').find_one({
            '_id': obj_id,
            'session_id': session_id
        })
        
        if not archive:
            return jsonify({'error': 'Archive not found'})
        
        # Convert ObjectId to string
        archive['_id'] = str(archive['_id'])
        
        return jsonify({'archive': archive})
    except Exception as e:
        return jsonify({'error': f'Invalid archive ID: {str(e)}'})


@app.route('/api/chat-history/<archive_id>', methods=['DELETE'])
def delete_archived_conversation(archive_id):
    """Delete an archived conversation."""
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session ID found'})
    
    try:
        # Convert string to ObjectId
        obj_id = ObjectId(archive_id)
        
        # Delete the archived conversation
        result = mongo_db.get_collection('conversation_archives').delete_one({
            '_id': obj_id,
            'session_id': session_id
        })
        
        if result.deleted_count == 0:
            return jsonify({'error': 'Archive not found'})
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'Invalid archive ID: {str(e)}'})


@app.route('/api/new-chat', methods=['GET'])
def new_chat():
    """Start a new chat conversation."""
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session ID found'})
    
    # Archive current conversation if it has messages
    conv_doc = conversations_col.find_one({'session_id': session_id})
    if conv_doc and conv_doc.get('messages'):
        archive_entry = {
            'session_id': session_id,
            'archived_at': datetime.now().isoformat(),
            'messages': conv_doc.get('messages', []),
            'tools': conv_doc.get('tools', []),
            'title': _generate_conversation_title(conv_doc.get('messages', [])),
            'message_count': len(conv_doc.get('messages', [])),
            'first_message': conv_doc.get('messages', [{}])[0].get('text', '') if conv_doc.get('messages') else ''
        }
        mongo_db.get_collection('conversation_archives').insert_one(archive_entry)
    
    # Create new conversation
    new_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
    new_conv = {
        'session_id': new_session_id,
        'created_at': datetime.now().isoformat(),
        'messages': [],
        'tools': []
    }
    conversations_col.insert_one(new_conv)
    
    response = jsonify({'success': True, 'new_session_id': new_session_id})
    response.set_cookie('session_id', new_session_id, max_age=3600)
    return response


@app.route('/api/context')
def get_context():
    """Get current context windows and conversation history."""
    context_windows = get_context_windows()
    
    # Get session ID from request
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session ID found'})
    
    # Get conversation for this session
    conv_doc = conversations_col.find_one({'session_id': session_id})
    if not conv_doc:
        return jsonify({'error': 'No conversation found for session'})
    
    chat_history = conv_doc.get('messages', [])
    tool_history = conv_doc.get('tools', [])
    
    # Build a more detailed context for display
    detailed_context = {
        'context_windows': context_windows,
        'chat_history': chat_history,
        'context_history': [],
        'tool_history': tool_history,
        'recent_tools': tool_history[-5:] if tool_history else [],  # Last 5 tool calls
        'conversation_summary': [
            {
                "role": msg.get("role", "unknown"),
                "text": msg.get("text", "")[:200] + "..." if len(msg.get("text", "")) > 200 else msg.get("text", ""),
                "citations": msg.get("citations", [])
            }
            for msg in chat_history[-10:]  # Last 10 messages
        ]
    }
    
    return jsonify(detailed_context)


@app.route('/api/history')
def get_history():
    """Get API call history."""
    api_history = get_api_call_history()
    return jsonify(api_history)


@app.route('/api/debug')
def debug_session():
    """Debug endpoint to see session state."""
    try:
        # Get session ID from request
        session_id = request.cookies.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session ID found'})
        
        # Get conversation for this session
        conv_doc = conversations_col.find_one({'session_id': session_id})
        if not conv_doc:
            return jsonify({'error': 'No conversation found for session'})
        
        # Build the conversation history that would be sent to OpenAI
        conversation_history = conv_doc.get('messages', [])[-5:]
        messages = []
        
        for turn in conversation_history:
            role = turn.get("role", "user")
            text = turn.get("text", "")
            
            # Skip error messages
            if role == "assistant" and text.startswith("Error processing request:"):
                continue
            
            # Add user messages directly
            if role == "user":
                messages.append({"role": "user", "content": text})
                continue
            
            # For assistant messages, check if they had tool calls
            if role == "assistant" and turn.get("citations"):
                # Find the corresponding tool result
                citations = turn.get("citations", [])
                if len(citations) == 1:  # Simple case: one tool call
                    citation = citations[0]
                    tool_name = citation.get("tool")
                    tool_args = citation.get("args", {})
                    
                    # Find the tool result
                    tool_result = None
                    for tool_entry in conv_doc.get('tools', []):
                        if (tool_entry.get('tool') == tool_name and 
                            tool_entry.get('args') == tool_args):
                            tool_result = tool_entry.get('result', {})
                            break
                    
                    if tool_result:
                        # Add assistant message with tool call
                        tool_call_id = f"call_{tool_name[:15]}_{abs(hash(json.dumps(tool_args, sort_keys=True))) % 1000:03d}"
                        messages.append({
                            "role": "assistant",
                            "content": text,
                            "tool_calls": [{
                                "id": tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": json.dumps(tool_args)
                                }
                            }]
                        })
                        
                        # Add tool response
                        messages.append({
                            "role": "tool",
                            "content": json.dumps(tool_result),
                            "tool_call_id": tool_call_id
                        })
                    else:
                        # No tool result found, add as regular assistant message
                        messages.append({"role": "assistant", "content": text})
                else:
                    # Multiple tool calls - add as regular assistant message for now
                    messages.append({"role": "assistant", "content": text})
            else:
                # Regular assistant message without tool calls
                messages.append({"role": "assistant", "content": text})
        
        debug_info = {
            'session_id': session_id,
            'chat_history_length': len(conv_doc.get('messages', [])),
            'tool_history_length': len(conv_doc.get('tools', [])),
            'mongo_conv_messages': len(conv_doc.get('messages', [])),
            'mongo_conv_tools': len(conv_doc.get('tools', [])),
            'recent_tool_history': conv_doc.get('tools', [])[-3:],
            'conversation_messages': messages,
            'chat_history': conv_doc.get('messages', [])[-5:]  # Last 5 messages
        }
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/export/csv/<filename>')
def download_csv(filename):
    """Download CSV file."""
    try:
        # Extract location name from filename (handle timestamped filenames)
        # Example: prefixes_branch_office_3_20250819_055826.csv -> Branch Office 3
        if filename.startswith('prefixes_'):
            # Remove 'prefixes_' prefix and '.csv' suffix
            name_part = filename[9:].replace('.csv', '')
            
            # Split by underscores and handle timestamp
            parts = name_part.split('_')
            
            # Find where the timestamp starts (YYYYMMDD pattern)
            location_parts = []
            for part in parts:
                if len(part) == 8 and part.isdigit():  # Timestamp found
                    break
                location_parts.append(part)
            
            # Reconstruct location name
            location_name = ' '.join(location_parts).title()
        else:
            location_name = filename.replace('.csv', '').replace('_', ' ')
        
        # Get CSV data from MCP server
        result = invoke_tool_on_server("nautobot", "export_prefixes_to_csv", {
            "location_name": location_name,
            "filename": filename
        })
        
        if result.get("success") and result.get("data"):
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(result["data"])
                temp_path = f.name
            
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='text/csv'
            )
        else:
            return jsonify({"error": "Failed to generate CSV"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8501, debug=True)
