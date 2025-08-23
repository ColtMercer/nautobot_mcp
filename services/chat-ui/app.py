"""Flask Chat UI for MCP tools."""

import json
import os
import time
import requests
from datetime import datetime
from typing import Any, Dict, List

import tempfile
import logging
from flask import Flask, render_template, request, jsonify, session, send_file, make_response
from dotenv import load_dotenv

from mcp_client import get_server_catalogs, invoke_tool_on_server, get_api_call_history, get_context_windows

def execute_tool_with_status(tool_name, args, server_name, start_time, round_num, tool_index, total_tools):
    """Execute a tool with detailed status logging and progress tracking."""
    import time
    logger.info(f"[STATUS] Starting tool execution: {tool_name} (Round {round_num}, Tool {tool_index}/{total_tools}) at {time.time() - start_time:.2f}s")
    
    # Log tool-specific details
    if tool_name == 'get_prefixes_by_location_enhanced':
        location_name = args.get('location_name', '')
        fmt = args.get('format', 'json')
        logger.info(f"[STATUS] Querying prefixes for location '{location_name}' in {fmt} format")
        api_result = invoke_tool_on_server(server_name, tool_name, args)
        logger.info(f"[STATUS] Prefix query completed for '{location_name}' - found {api_result.get('result', {}).get('count', 0)} prefixes")
        
    elif tool_name == 'get_devices_by_location':
        location_name = args.get('location_name', '')
        logger.info(f"[STATUS] Querying devices for location '{location_name}'")
        api_result = invoke_tool_on_server(server_name, tool_name, args)
        logger.info(f"[STATUS] Device query completed for '{location_name}' - found {api_result.get('result', {}).get('count', 0)} devices")
        
    elif tool_name == 'get_devices_by_location_and_role':
        location_name = args.get('location_name', '')
        role_name = args.get('role_name', '')
        logger.info(f"[STATUS] Querying devices for location '{location_name}' with role '{role_name}'")
        api_result = invoke_tool_on_server(server_name, tool_name, args)
        logger.info(f"[STATUS] Device+role query completed for '{location_name}'/'{role_name}' - found {api_result.get('result', {}).get('count', 0)} devices")
        
    elif tool_name == 'get_interfaces_by_device':
        device_name = args.get('device_name', '')
        logger.info(f"[STATUS] Querying interfaces for device '{device_name}'")
        api_result = invoke_tool_on_server(server_name, tool_name, args)
        logger.info(f"[STATUS] Interface query completed for '{device_name}' - found {api_result.get('result', {}).get('count', 0)} interfaces")
        
    elif tool_name == 'get_circuits_by_location':
        location_names = args.get('location_names', [])
        logger.info(f"[STATUS] Querying circuits for locations: {location_names}")
        
        api_result = invoke_tool_on_server(server_name, tool_name, args)
        
        logger.info(f"[STATUS] Circuit query completed for locations {location_names} - found {api_result.get('result', {}).get('count', 0)} circuits")
        
    else:
        logger.info(f"[STATUS] Executing unknown tool: {tool_name}")
        api_result = {"error": f"Unknown tool {tool_name}"}
    
    execution_time = time.time() - start_time
    logger.info(f"[STATUS] Tool '{tool_name}' completed in {execution_time:.2f}s (Round {round_num}, Tool {tool_index}/{total_tools})")
    
    return api_result

def discover_tools_from_mcp_server(server_name):
    """Dynamically discover tools from MCP server."""
    try:
        tools_response = requests.get(f"http://{server_name}:7001/tools", timeout=5)
        if tools_response.status_code == 200:
            mcp_tools = tools_response.json().get("tools", [])
            tools = []
            for tool in mcp_tools:
                # Convert MCP tool format to OpenAI function format
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"]
                    }
                }
                tools.append(openai_tool)
            logger.info(f"Discovered {len(tools)} tools from MCP server")
            return tools
        else:
            logger.warning(f"Failed to get tools from MCP server: {tools_response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error discovering tools from MCP server: {e}")
        return []

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
        logger.info(f"OpenAI API Key configured: {bool(os.environ.get('OPENAI_API_KEY'))}, OpenAI available: {OpenAI is not None}, use_openai: {use_openai}")
        assistant_response = None
        citations = []
        response_data = None
        
        if use_openai:
            logger.info(f"[TIMING] Starting OpenAI processing at {time.time() - start_time:.2f}s")
            client = OpenAI()
            model = os.environ.get('OPENAI_MODEL', os.environ.get('DEFAULT_MODEL', 'gpt-4o-mini'))
            system_prompt = (
                "You are a helpful general-purpose assistant with access to Nautobot network data tools. "
                "You can call multiple MCP tools in sequence to gather comprehensive information. "
                "IMPORTANT GUIDELINES: "
                "1. For complex questions, use multiple tools to gather different types of data (devices, prefixes, circuits, etc.) "
                "2. You can chain tool calls - use results from one tool to inform subsequent tool calls "
                "3. Always use conversation history to resolve pronouns and follow-ups "
                "4. If the user asks to reformat or export 'that' or 'those results', use the most recent relevant results "
                "5. Use markdown formatting for better readability with proper table syntax "
                "6. When analyzing network data, consider relationships between devices, prefixes, circuits, and locations "
                "7. For comprehensive analysis, gather data from multiple sources before providing insights "
                "8. You can chain tool calls - get devices first, then get their interfaces for detailed analysis "
                "9. Use exact location codes (e.g., 'BRCN', 'NYDC') - full names will fail "
                "Available tools: get_prefixes_by_location_enhanced, get_devices_by_location, get_devices_by_location_and_role, get_interfaces_by_device, get_circuits_by_location, get_locations, get_providers, get_circuits_by_provider"
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
            # Dynamically discover tools from MCP server
            tools = discover_tools_from_mcp_server(server_name)
            if not tools:
                logger.warning("No tools discovered from MCP server, using empty tools list")
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
            logger.info(f"OpenAI response - has tool calls: {bool(msg.tool_calls)}, content: {msg.content[:100] if msg.content else 'None'}")
            
            # Initialize assistant_response variable
            assistant_response = None
            citations = []
            
            if msg.tool_calls:
                messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
                logger.info(f"[TIMING] Processing {len(msg.tool_calls)} tool calls at {time.time() - start_time:.2f}s")
                
                # Enhanced multi-tool processing with chaining support
                tool_call_round = 1
                max_tool_rounds = 5  # Prevent infinite loops
                
                while msg.tool_calls and tool_call_round <= max_tool_rounds:
                    logger.info(f"[TIMING] Starting tool call round {tool_call_round} with {len(msg.tool_calls)} tools at {time.time() - start_time:.2f}s")
                    
                    # Process all tool calls in this round
                    for i, tc in enumerate(msg.tool_calls):
                        fn = tc.function
                        name = fn.name
                        logger.info(f"[TIMING] Round {tool_call_round}, Tool {i+1}/{len(msg.tool_calls)}: '{name}' at {time.time() - start_time:.2f}s")
                        
                        try:
                            args = json.loads(fn.arguments or '{}')
                        except Exception as e:
                            logger.error(f"Failed to parse arguments for tool {name}: {e}")
                            args = {}
                        
                        # Enhanced tool execution with detailed logging
                        api_result = execute_tool_with_status(name, args, server_name, start_time, tool_call_round, i+1, len(msg.tool_calls))
                        
                        # Store tool call and result for future reference
                        tool_result = api_result.get('result', api_result)
                        
                        persisted = {
                            "tool": name,
                            "args": args,
                            "result": tool_result,
                            "timestamp": datetime.now().isoformat(),
                            "round": tool_call_round,
                            "tool_index": i+1
                        }
                        tool_history.append(persisted)
                        citations.append({"tool": name, "args": args, "round": tool_call_round})
                        
                        # Add tool result to messages for this conversation turn
                        messages.append({
                            "role": "tool", 
                            "tool_call_id": tc.id, 
                            "content": json.dumps(tool_result)
                        })
                    
                    # Check if we need another round of tool calls
                    if tool_call_round < max_tool_rounds:
                        logger.info(f"[TIMING] Making follow-up OpenAI API call for round {tool_call_round} at {time.time() - start_time:.2f}s")
                        follow_up = client.chat.completions.create(
                            model=model, 
                            messages=messages,
                            tools=tools,
                            tool_choice="auto"
                        )
                        msg = follow_up.choices[0].message
                        logger.info(f"[TIMING] Follow-up OpenAI API call completed for round {tool_call_round} at {time.time() - start_time:.2f}s")
                        logger.info(f"Follow-up response - has tool calls: {bool(msg.tool_calls)}, content: {msg.content[:100] if msg.content else 'None'}")
                        
                        if msg.tool_calls:
                            messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
                            tool_call_round += 1
                        else:
                            # No more tool calls needed
                            assistant_response = msg.content or ""
                            break
                    else:
                        # Max rounds reached, get final response
                        logger.info(f"[TIMING] Max tool call rounds ({max_tool_rounds}) reached, getting final response at {time.time() - start_time:.2f}s")
                        final_response = client.chat.completions.create(model=model, messages=messages)
                        assistant_response = final_response.choices[0].message.content or ""
                        break
                
                # If we didn't get a response yet, get the final one
                if not assistant_response:
                    logger.info(f"[TIMING] Making final OpenAI API call at {time.time() - start_time:.2f}s")
                    final = client.chat.completions.create(model=model, messages=messages)
                    assistant_response = final.choices[0].message.content or ""
                    logger.info(f"[TIMING] Final OpenAI API call completed at {time.time() - start_time:.2f}s")
                
                logger.info(f"Multi-tool processing completed - final response: {assistant_response[:100] if assistant_response else 'None'}")
            else:
                # No tool calls made - use the assistant's direct response
                assistant_response = msg.content or "I don't have any specific tools to help with that request. Please try asking about network devices, prefixes, or locations using the available tools."
                citations = []
                logger.info(f"No tool calls - using direct response: {assistant_response[:100] if assistant_response else 'None'}")
        
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
        
        # Ensure assistant_response is not None
        if assistant_response is None:
            if not use_openai:
                assistant_response = "OpenAI is not configured. Please set the OPENAI_API_KEY environment variable to use this chat interface."
                logger.warning("OpenAI not configured, using fallback message")
            else:
                assistant_response = "I apologize, but I encountered an issue processing your request. Please try again."
                logger.warning("assistant_response was None, using fallback message")
        
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
                "text": (msg.get("text") or "")[:200] + "..." if len(msg.get("text") or "") > 200 else (msg.get("text") or ""),
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
