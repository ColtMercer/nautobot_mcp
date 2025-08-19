"""Flask Chat UI for MCP tools."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

from mcp_client import get_server_catalogs, invoke_tool_on_server, get_api_call_history, get_context_windows
from exporters import export_json, export_markdown

load_dotenv()

app = Flask(__name__)
app.secret_key = 'nautobot-mcp-chat-secret-key'


@app.route('/')
def index():
    """Main chat interface."""
    # Get server catalogs
    catalogs = get_server_catalogs()
    
    # Initialize session state if not exists
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    if 'context_history' not in session:
        session['context_history'] = []
    
    return render_template('index.html', 
                         catalogs=catalogs,
                         chat_history=session.get('chat_history', []),
                         context_history=session.get('context_history', []))


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests."""
    data = request.get_json()
    prompt = data.get('message', '')
    selected_servers = data.get('selected_servers', [])
    
    if not prompt or not selected_servers:
        return jsonify({'error': 'Message and server selection required'})
    
    # Initialize session state if not exists
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    if 'context_history' not in session:
        session['context_history'] = []
    
    # Add user message to history
    user_turn = {
        "role": "user",
        "text": prompt,
        "timestamp": datetime.now().isoformat()
    }
    
    session['chat_history'].append(user_turn)
    
    # Process with LLM chat tool
    server_name = selected_servers[0]  # Use first selected server
    
    try:
        result = invoke_tool_on_server(
            server_name,
            "llm_chat",
            {"message": prompt}
        )
        
        if "error" in result:
            assistant_response = f"Error: {result['error']}"
            citations = []
        else:
            tool_result = result.get("result", {})
            assistant_response = tool_result.get("answer", "No response")
            citations = tool_result.get("citations", [])
        
        # Add assistant response to history
        assistant_turn = {
            "role": "assistant",
            "text": assistant_response,
            "citations": citations,
            "timestamp": datetime.now().isoformat()
        }
        session['chat_history'].append(assistant_turn)
        
        # Update context history with full context
        context_windows = get_context_windows()
        if context_windows:
            full_context = {
                "timestamp": datetime.now().isoformat(),
                "user_prompt": prompt,
                "tool_metadata": context_windows,
                "full_context": {
                    "user_message": prompt,
                    "available_tools": context_windows,
                    "conversation_history": session['chat_history'][-10:]  # Last 10 messages
                }
            }
            session['context_history'].append(full_context)
        
        return jsonify({
            'success': True,
            'response': assistant_response,
            'citations': citations,
            'chat_history': session['chat_history'],
            'context_history': session['context_history']
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
        session['chat_history'].append(error_turn)
        
        return jsonify({
            'success': False,
            'error': error_response,
            'chat_history': session['chat_history']
        })


@app.route('/api/export/<format>')
def export(format):
    """Export chat history."""
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    if format == 'json':
        try:
            filepath = export_json(session.get('chat_history', []))
            return jsonify({'success': True, 'filepath': filepath})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    elif format == 'markdown':
        try:
            filepath = export_markdown(session.get('chat_history', []))
            return jsonify({'success': True, 'filepath': filepath})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    else:
        return jsonify({'success': False, 'error': 'Invalid export format'})


@app.route('/api/clear')
def clear_chat():
    """Clear chat history."""
    session['chat_history'] = []
    session['context_history'] = []
    return jsonify({'success': True})


@app.route('/api/context')
def get_context():
    """Get current context windows."""
    context_windows = get_context_windows()
    return jsonify(context_windows)


@app.route('/api/history')
def get_history():
    """Get API call history."""
    api_history = get_api_call_history()
    return jsonify(api_history)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8501, debug=True)
