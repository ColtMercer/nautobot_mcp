"""Streamlit Chat UI for MCP tools."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st
from dotenv import load_dotenv

from mcp_client import get_server_catalogs, invoke_tool_on_server
from exporters import export_json, export_markdown

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="MCP Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "selected_servers" not in st.session_state:
    st.session_state.selected_servers = []


def main():
    """Main application."""
    st.title("🤖 MCP Chat")
    st.markdown("Chat with MCP tools and export conversations")
    
    # Sidebar for server selection and tool catalogs
    with st.sidebar:
        st.header("MCP Servers")
        
        # Get server catalogs
        catalogs = get_server_catalogs()
        
        # Server selection
        available_servers = list(catalogs.keys())
        selected_servers = st.multiselect(
            "Select servers",
            options=available_servers,
            default=available_servers,
            key="server_selector"
        )
        
        # Display tool catalogs for selected servers
        for server_name in selected_servers:
            catalog = catalogs.get(server_name, {})
            
            if "error" in catalog:
                st.error(f"**{server_name}**: {catalog['error']}")
            else:
                st.subheader(server_name)
                
                tools = catalog.get("tools", [])
                if tools:
                    for tool in tools:
                        with st.expander(f"🔧 {tool['name']}"):
                            st.write(f"**Description:** {tool.get('description', 'No description')}")
                            
                            if "input_schema" in tool:
                                st.write("**Input Schema:**")
                                st.json(tool["input_schema"])
                            
                            if "output_schema" in tool:
                                st.write("**Output Schema:**")
                                st.json(tool["output_schema"])
                else:
                    st.info("No tools available")
    
    # Main chat area
    st.header("Chat")
    
    # Display chat history
    for i, turn in enumerate(st.session_state.chat_history):
        with st.chat_message(turn["role"]):
            st.markdown(turn["text"])
            
            # Show tool calls if any
            citations = turn.get("citations", [])
            if citations:
                st.write("**Tool Calls:**")
                for j, citation in enumerate(citations):
                    with st.expander(f"🔧 {citation.get('tool', 'Unknown Tool')}"):
                        st.write(f"**Tool:** {citation.get('tool', 'Unknown')}")
                        
                        if "args" in citation:
                            st.write("**Arguments:**")
                            st.json(citation["args"])
                        
                        if "result_count" in citation:
                            st.write(f"**Results:** {citation['result_count']} items")
                        
                        if "result_summary" in citation:
                            st.write(f"**Summary:** {citation['result_summary']}")
                        
                        if "error" in citation:
                            st.error(f"**Error:** {citation['error']}")
    
    # Chat input
    if prompt := st.chat_input("Ask something (e.g., 'What prefixes exist at HQ-Dallas?')"):
        # Add user message to history
        user_turn = {
            "role": "user",
            "text": prompt,
            "timestamp": datetime.now().isoformat()
        }
        st.session_state.chat_history.append(user_turn)
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process with LLM chat tool
        if selected_servers:
            # Use the first selected server for LLM chat
            server_name = selected_servers[0]
            
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
                st.session_state.chat_history.append(assistant_turn)
                
                # Display assistant response
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
                    
                    # Show tool calls
                    if citations:
                        st.write("**Tool Calls:**")
                        for j, citation in enumerate(citations):
                            with st.expander(f"🔧 {citation.get('tool', 'Unknown Tool')}"):
                                st.write(f"**Tool:** {citation.get('tool', 'Unknown')}")
                                
                                if "args" in citation:
                                    st.write("**Arguments:**")
                                    st.json(citation["args"])
                                
                                if "result_count" in citation:
                                    st.write(f"**Results:** {citation['result_count']} items")
                                
                                if "result_summary" in citation:
                                    st.write(f"**Summary:** {citation['result_summary']}")
                                
                                if "error" in citation:
                                    st.error(f"**Error:** {citation['error']}")
                
            except Exception as e:
                error_response = f"Error processing request: {str(e)}"
                st.error(error_response)
                
                # Add error to history
                error_turn = {
                    "role": "assistant",
                    "text": error_response,
                    "citations": [],
                    "timestamp": datetime.now().isoformat()
                }
                st.session_state.chat_history.append(error_turn)
        else:
            st.warning("Please select at least one MCP server")
    
    # Export controls
    st.header("Export")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Export JSON"):
            if st.session_state.chat_history:
                try:
                    filepath = export_json(st.session_state.chat_history)
                    st.success(f"✅ Exported to {filepath}")
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
            else:
                st.warning("No chat history to export")
    
    with col2:
        if st.button("📝 Export Markdown"):
            if st.session_state.chat_history:
                try:
                    filepath = export_markdown(st.session_state.chat_history)
                    st.success(f"✅ Exported to {filepath}")
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
            else:
                st.warning("No chat history to export")
    
    with col3:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Show chat statistics
    if st.session_state.chat_history:
        st.header("Statistics")
        
        total_turns = len(st.session_state.chat_history)
        user_turns = len([t for t in st.session_state.chat_history if t["role"] == "user"])
        assistant_turns = len([t for t in st.session_state.chat_history if t["role"] == "assistant"])
        total_tool_calls = sum(len(t.get("citations", [])) for t in st.session_state.chat_history)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Turns", total_turns)
        col2.metric("User Messages", user_turns)
        col3.metric("Assistant Responses", assistant_turns)
        col4.metric("Tool Calls", total_tool_calls)


if __name__ == "__main__":
    main()
