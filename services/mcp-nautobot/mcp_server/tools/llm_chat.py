"""LLM chat tool that can call other MCP tools and emit citations."""

import json
import os
import re
from typing import Any, Dict, List, Tuple

import structlog

from .prefixes import get_prefixes_by_location

logger = structlog.get_logger(__name__)

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


def extract_location_name(message: str) -> str:
    """Extract location name from user message using simple heuristics."""
    message_lower = message.lower()
    
    # Common location names to look for (including common typos)
    known_locations = [
        "hq-dallas", "lab-austin", "hq-london", "hq-sydney",
        "branch office 1", "branch office 2", "branch office 3", "branch ofice 3",  # Handle typo
        "data center 1", "data center 2", "campus a", "campus b"
    ]
    
    # First, try to find known location names in the message
    for location in known_locations:
        if location in message_lower:
            # Find the actual case from the original message
            location_pattern = re.compile(re.escape(location), re.IGNORECASE)
            match = location_pattern.search(message)
            if match:
                return match.group(0)
    
    # If no known location found, try to extract using patterns
    # Look for patterns like "at [location]" or "in [location]" or "for [location]"
    patterns = [
        r'(?:at|in|for)\s+([A-Za-z0-9\-\s]+?)(?:\s|$|\.|\?)',  # Multi-word locations
        r'(?:site|office|branch|location)\s+([A-Za-z0-9\-\s]+?)(?:\s|$|\.|\?)',  # After location keywords
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, message, re.IGNORECASE)
        for match in matches:
            location_name = match.strip()
            # Avoid extracting common non-location words
            if location_name.lower() not in ['prefixes', 'prefix', 'what', 'show', 'find', 'me', 'the', 'location']:
                return location_name
    
    # Default location if none found
    return "HQ-Dallas"


def llm_chat(message: str, conversation_history: List[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """LLM assistant that can call other MCP tools and records citations.
    
    This tool is designed to be used by an LLM that has access to the full MCP tool catalog.
    The LLM should decide which tools to call based on the user's message and conversation history.
    
    Args:
        message: The user's message
        conversation_history: List of previous conversation turns for context
        
    Returns:
        Dictionary with answer and citations
    """
    logger.info("Processing LLM chat message", message=message[:100] + "..." if len(message) > 100 else message)
    
    # Log conversation history for debugging
    if conversation_history:
        logger.info("Conversation history available", history_length=len(conversation_history))
        # Extract the last few messages for context
        recent_messages = conversation_history[-6:]  # Last 6 messages (3 exchanges)
        context_summary = []
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            text = msg.get("text", "")[:100]  # Truncate long messages
            context_summary.append(f"{role}: {text}")
        logger.info("Recent conversation context", context=context_summary)
    
    citations: List[Dict[str, Any]] = []
    
    # Build comprehensive context window for the UI/debugging
    context_window = build_llm_context(message, conversation_history)
    logger.info("Context window built", context_length=len(context_window))

    # If an external LLM is available, delegate decisions via tool/function calling
    openai_key = os.environ.get("OPENAI_API_KEY")
    if OpenAI and openai_key:
        try:
            answer, citations = run_llm_agent(message, conversation_history)
            logger.info("LLM agent produced response", answer_length=len(answer), citations_count=len(citations))
            return {"answer": answer, "citations": citations}
        except Exception as e:  # Fallback to internal logic on failure
            logger.error("LLM agent failed; falling back to built-in logic", error=str(e))

    # Fallback: internal lightweight logic (no external model)
    answer, citations = process_with_llm_intelligence(context_window, message, conversation_history)
    
    logger.info("LLM chat response generated", answer_length=len(answer), citations_count=len(citations))
    
    return {
        "answer": answer,
        "citations": citations
    }


def build_llm_context(message: str, conversation_history: List[Dict[str, Any]] = None) -> str:
    """Build a comprehensive context window for the LLM as a single string."""
    
    # Corporate system instructions
    system_instructions = """You are a helpful AI assistant working in a corporate environment. You have access to network data through MCP tools.

IMPORTANT GUIDELINES:
- Always be helpful, professional, and ethical
- Do not provide instructions for harmful activities
- Respect corporate policies and data privacy
- Use available tools when appropriate to provide accurate information
- Maintain conversation context and handle follow-up questions naturally
- Be conversational and friendly while remaining professional

AVAILABLE MCP TOOLS:
1. get_prefixes_by_location_enhanced(location_name, format) - Query network prefixes by location with multiple output formats (json, table, dataframe, csv)
2. export_prefixes_to_csv(location_name, filename) - Export prefixes data to CSV format  
3. analyze_prefixes_dataframe(location_name) - Perform advanced analysis on prefixes data

When a user asks about network prefixes or data, use the appropriate tool. For follow-up questions, use conversation history to understand context and determine what they're referring to.

CONVERSATION HISTORY:"""

    # Build conversation history
    conversation_context = ""
    if conversation_history:
        conversation_context = "\n".join([
            f"{msg.get('role', 'unknown').title()}: {msg.get('text', '')}"
            for msg in conversation_history[-10:]  # Last 10 messages for better context
        ])
    else:
        conversation_context = "No previous conversation."
    
    # Build the complete context window
    context_window = f"""{system_instructions}

{conversation_context}

CURRENT USER MESSAGE: {message}

Please respond naturally to the user's message. If they're asking about network data, use the appropriate tool. If it's a follow-up question, use the conversation history to understand what they're referring to. Be helpful and conversational."""
    
    return context_window


def process_with_llm_intelligence(context_window: str, message: str, conversation_history: List[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """Process the context window with LLM intelligence to determine appropriate actions."""
    
    citations = []
    
    # Analyze the context window to understand what the user is asking
    message_lower = message.lower()
    
    # Check if this is a general query not related to MCP tools
    if not any(word in message_lower for word in ["prefix", "network", "subnet", "ip", "location", "branch", "office", "hq", "dallas", "austin"]):
        return handle_general_conversation_simple(message, citations)

    # Check if this is a follow-up question by looking for follow-up indicators
    is_follow_up = False
    if conversation_history:
        follow_up_indicators = ["it", "them", "those", "this", "that", "the", "show", "give", "get", "as", "in", "can you", "please", "format", "put", "make", "provide"]
        is_follow_up = any(word in message_lower for word in follow_up_indicators)

    # If it's a follow-up question, analyze the conversation history to understand context
    if is_follow_up and conversation_history:
        # Look for network-related context in the conversation history
        history_text = " ".join([msg.get("text", "") for msg in conversation_history])
        if "prefix" in history_text.lower() or "network" in history_text.lower() or "branch office" in history_text.lower():
            # This is a follow-up about network data
            return handle_network_follow_up(context_window, message, conversation_history, citations)

    # Check if this is a network-related query
    if any(word in message_lower for word in ["prefix", "network", "subnet", "ip"]) and any(word in message_lower for word in ["location", "branch", "office", "hq", "dallas", "austin"]):
        return handle_network_query(context_window, message, conversation_history, citations)

    # Check if this is a help request
    if any(word in message_lower for word in ["help", "what can you do", "capabilities"]):
        return handle_help_request_simple(citations)

    # Default to general conversation
    return handle_general_conversation_simple(message, citations)


def run_llm_agent(message: str, conversation_history: List[Dict[str, Any]] | None) -> Tuple[str, List[Dict[str, Any]]]:
    """Use an external LLM with function-calling to decide when to call tools.

    - Answers general questions directly (e.g., "What is OSPF?")
    - When appropriate, the model issues tool calls which we execute and feed back
    - Returns the model's final message and a list of citations (tool invocations)
    """
    assert OpenAI is not None, "OpenAI client not available"
    client = OpenAI()

    system_instructions = (
        "You are a helpful general-purpose assistant in a corporate environment. "
        "You can also call tools to access Nautobot network data when helpful. "
        "Use tools only when needed; otherwise answer normally. "
        "Maintain conversation context and respond clearly."
    )

    # Convert our history into OpenAI chat format
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_instructions}]
    if conversation_history:
        for turn in conversation_history[-25:]:
            role = turn.get("role", "user")
            text = turn.get("text", "")
            if role not in ("user", "assistant"):
                role = "user"
            messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": message})

    # Declare available functions for the model
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_prefixes_by_location",
                "description": "Query Nautobot for network prefixes by a location name. Supports multiple output formats.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location_name": {"type": "string", "description": "The location name, e.g., 'Branch Office 3'"},
                        "format": {
                            "type": "string",
                            "description": "Desired output format",
                            "enum": ["json", "table", "dataframe", "csv"],
                            "default": "json",
                        },
                    },
                    "required": ["location_name"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "export_prefixes_to_csv",
                "description": "Export prefixes for a location to a CSV file and return metadata about the export.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location_name": {"type": "string"},
                        "filename": {"type": "string", "description": "Optional filename to use"},
                    },
                    "required": ["location_name"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_prefixes_dataframe",
                "description": "Perform analysis on prefixes for a location and return summary statistics.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location_name": {"type": "string"},
                    },
                    "required": ["location_name"],
                    "additionalProperties": False,
                },
            },
        },
    ]

    model = os.environ.get("OPENAI_MODEL", os.environ.get("DEFAULT_MODEL", "gpt-4o-mini"))

    first = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    choice = first.choices[0]
    msg = choice.message
    citations: List[Dict[str, Any]] = []

    if msg.tool_calls:
        # Execute tool calls and provide results back to the model
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})

        for tool_call in msg.tool_calls:
            fn = tool_call.function
            name = fn.name
            try:
                args = json.loads(fn.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            # Route to local Python functions
            if name == "get_prefixes_by_location":
                location_name = args.get("location_name", "")
                fmt = args.get("format", "json")
                result = get_prefixes_by_location(location_name, format=fmt)
            elif name == "export_prefixes_to_csv":
                from .prefixes import export_prefixes_to_csv  # local import to avoid cycles
                location_name = args.get("location_name", "")
                filename = args.get("filename")
                result = export_prefixes_to_csv(location_name, filename)
            elif name == "analyze_prefixes_dataframe":
                from .prefixes import analyze_prefixes_dataframe  # local import to avoid cycles
                location_name = args.get("location_name", "")
                result = analyze_prefixes_dataframe(location_name)
            else:
                result = {"error": f"Unknown tool: {name}"}

            # Record citation
            citations.append({
                "tool": name,
                "args": args,
                "result_count": result.get("count") if isinstance(result, dict) else None,
                "result_summary": result.get("message") if isinstance(result, dict) else None,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

        second = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        final = second.choices[0].message
        return final.content or "", citations

    # No tools needed; answer directly
    return msg.content or "", citations


def handle_network_follow_up(context_window: str, message: str, conversation_history: List[Dict[str, Any]], citations: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Handle follow-up questions about network data."""
    
    # Extract location from conversation history
    location_name = None
    for msg in reversed(conversation_history):
        if msg.get("role") == "user":
            location_name = extract_location_name(msg.get("text", ""))
            if location_name and location_name not in ["HQ-Dallas", "a", "to", "in", "as", "the", "data", "format", "table", "csv", "export"]:
                break
    
    if not location_name:
        location_name = "Branch Office 3"  # Default fallback
    
    # Determine format based on user request
    format_type = "json"  # default
    if any(word in message.lower() for word in ["table", "as table", "show table"]):
        format_type = "table"
    elif any(word in message.lower() for word in ["csv", "export", "download", "file"]):
        format_type = "csv"
    elif any(word in message.lower() for word in ["dataframe", "analysis", "analyze"]):
        format_type = "dataframe"
    else:
        # Default to table for "show me" type requests
        if any(word in message.lower() for word in ["show", "give", "get", "provide"]):
            format_type = "table"
    
    try:
        # Call the appropriate tool
        result = get_prefixes_by_location(location_name, format=format_type)
        
        # Record the citation
        citations.append({
            "tool": "get_prefixes_by_location_enhanced",
            "args": {"location_name": location_name, "format": format_type},
            "result_count": result.get("count", 0),
            "result_summary": result.get("message", "Query completed")
        })
        
        # Generate response based on format
        if result.get("success") and result.get("data"):
            if format_type == "json":
                prefixes = result["data"]
                prefix_list = [p["prefix"] for p in prefixes[:5]]
                answer = f"Found {len(prefixes)} prefixes at {location_name}. "
                if len(prefixes) <= 5:
                    answer += f"All prefixes: {', '.join(prefix_list)}"
                else:
                    answer += f"First 5 prefixes: {', '.join(prefix_list)}... (and {len(prefixes) - 5} more)"
                
                if result.get("summary"):
                    summary = result["summary"]
                    answer += f"\n\n📊 Summary: {summary['total_prefixes']} prefixes with {summary['total_hosts']} total hosts"
            
            elif format_type == "table":
                answer = f"📋 **Prefixes Table for {location_name}**\n\n"
                answer += "Here's a formatted table of the prefixes:\n\n"
                answer += result["data"]
            
            elif format_type == "dataframe":
                answer = f"📊 **Data Analysis for {location_name}**\n\n"
                if result.get("analysis"):
                    analysis = result["analysis"]
                    answer += f"• **Total Hosts**: {analysis['total_hosts']:,}\n"
                    answer += f"• **Average Subnet**: /{analysis['average_subnet']:.1f}\n"
                    answer += f"• **Largest Subnet**: /{analysis['largest_subnet']}\n"
                    answer += f"• **Smallest Subnet**: /{analysis['smallest_subnet']}\n"
                answer += f"\nFound {result.get('count', 0)} prefixes with detailed analysis."
            
            elif format_type == "csv":
                answer = f"📥 **CSV Export for {location_name}**\n\n"
                answer += f"CSV data has been generated for {location_name}.\n"
                answer += f"Filename: {result.get('filename', 'prefixes.csv')}\n\n"
                answer += "The CSV contains the following columns:\n"
                answer += "• Prefix, Network, Subnet, Total Hosts, Status, Description, Locations\n\n"
                answer += "You can download this data for further analysis in Excel or other tools."
            
            # Add helpful format options
            answer += f"\n\n💡 **Other Format Options**:\n"
            answer += f"• Ask for 'table format' to see a formatted table\n"
            answer += f"• Ask for 'CSV export' to download the data\n"
            answer += f"• Ask for 'data analysis' to get statistical insights\n"
            
        else:
            answer = result.get("message", f"No prefixes found at {location_name}.")
            
    except Exception as e:
        logger.error("Failed to get prefixes", location=location_name, error=str(e))
        answer = f"Sorry, I encountered an error while looking up prefixes for {location_name}: {e}"
        citations.append({
            "tool": "get_prefixes_by_location_enhanced",
            "args": {"location_name": location_name, "format": format_type},
            "error": str(e)
        })
    
    return answer, citations


def handle_network_query(context_window: str, message: str, conversation_history: List[Dict[str, Any]], citations: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Handle network-related queries."""
    return handle_prefix_query({"user_message": message, "conversation_history": " ".join([msg.get("text", "") for msg in conversation_history or []])}, citations)


def handle_general_conversation_simple(message: str, citations: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Handle general conversation with simple responses."""
    
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
        answer = """Hello! I'm an AI assistant that can help you with various tasks, particularly network information and data analysis.

I have access to Nautobot network data and can help you with:
• Network prefix information and analysis
• Data formatting and export options
• General questions about network infrastructure
• And much more!

What would you like to work on today?"""
    
    elif any(word in message_lower for word in ["how are you", "how do you do", "are you ok"]):
        answer = """I'm doing well, thank you for asking! I'm ready to help you with whatever you need.

I'm particularly good at working with network data and can help you analyze, format, and export information from Nautobot. What can I assist you with today?"""
    
    elif any(word in message_lower for word in ["thanks", "thank you", "appreciate"]):
        answer = """You're very welcome! I'm happy to help. 

Is there anything else you'd like to know or work on? I'm here to assist with network data analysis, formatting, or any other questions you might have."""
    
    elif any(word in message_lower for word in ["bye", "goodbye", "see you", "later"]):
        answer = """Goodbye! It was great working with you. Feel free to come back anytime if you need help with network data analysis or any other tasks. Have a wonderful day!"""
    
    else:
        answer = """I'm an AI assistant that can help you with various tasks, particularly network information and data analysis.

I have access to Nautobot network data and can help you with:
• Network prefix information and analysis
• Data formatting and export options  
• General questions about network infrastructure
• And much more!

What would you like to work on today? You can ask me about specific network locations, request data in different formats, or just chat about whatever's on your mind!"""
    
    return answer, citations


def handle_help_request_simple(citations: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Handle help requests with comprehensive information."""
    
    answer = """I can help you with Nautobot network information! Here are some things I can do:

1. **Find prefixes by location**: Ask me "What prefixes exist at HQ-Dallas?" or "Show me prefixes at Branch Office 3"

2. **Multiple format options**:
   • **JSON format** (default): "What prefixes are at Branch Office 3?"
   • **Table format**: "Show me prefixes at Branch Office 3 as a table"
   • **CSV export**: "Export prefixes from Branch Office 3 to CSV"
   • **Data analysis**: "Analyze prefixes at Branch Office 3"

3. **Follow-up questions**: I maintain conversation context, so you can ask follow-up questions like:
   • "Show me that as a table"
   • "Export that to CSV"
   • "Analyze that data"

4. **Network information**: I can query Nautobot for network data and provide insights

Just ask me about prefixes at a specific location and I'll look it up for you!"""
    
    return answer, citations





def handle_prefix_query(context: Dict[str, Any], citations: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Handle prefix-related queries with intelligent context understanding."""
    
    message = context["user_message"]
    conversation_history = context.get("conversation_history", "")
    
    # Extract location with fallback to conversation history
    location_name = extract_location_name(message)
    
    # If no location found and we have conversation history, look for it there
    invalid_locations = ["HQ-Dallas", "a", "to", "in", "as", "the", "data", "format", "table", "csv", "export"]
    if not location_name or location_name in invalid_locations:
        if conversation_history:
            # Look for location in recent conversation
            for line in conversation_history.split('\n'):
                if 'user:' in line.lower():
                    historical_location = extract_location_name(line)
                    if historical_location and historical_location not in invalid_locations:
                        location_name = historical_location
                        break
    
    # Determine format based on user request
    format_type = "json"  # default
    if any(word in message.lower() for word in ["table", "as table", "show table"]):
        format_type = "table"
    elif any(word in message.lower() for word in ["csv", "export", "download", "file"]):
        format_type = "csv"
    elif any(word in message.lower() for word in ["dataframe", "analysis", "analyze"]):
        format_type = "dataframe"
    
    # Handle follow-up questions
    if any(word in message.lower() for word in ["it", "them", "those", "this", "that", "the", "show", "give", "get", "as", "in"]):
        # Override format based on follow-up request
        if any(word in message.lower() for word in ["table", "as table", "show table"]):
            format_type = "table"
        elif any(word in message.lower() for word in ["csv", "export", "download", "file"]):
            format_type = "csv"
        elif any(word in message.lower() for word in ["dataframe", "analysis", "analyze"]):
            format_type = "dataframe"
        else:
            # Default to table for "show me" type requests
            if any(word in message.lower() for word in ["show", "give", "get"]):
                format_type = "table"
    
    try:
        # Call the appropriate tool
        result = get_prefixes_by_location(location_name, format=format_type)
        
        # Record the citation
        citations.append({
            "tool": "get_prefixes_by_location_enhanced",
            "args": {"location_name": location_name, "format": format_type},
            "result_count": result.get("count", 0),
            "result_summary": result.get("message", "Query completed")
        })
        
        # Generate intelligent response
        if result.get("success") and result.get("data"):
            if format_type == "json":
                prefixes = result["data"]
                prefix_list = [p["prefix"] for p in prefixes[:5]]
                answer = f"Found {len(prefixes)} prefixes at {location_name}. "
                if len(prefixes) <= 5:
                    answer += f"All prefixes: {', '.join(prefix_list)}"
                else:
                    answer += f"First 5 prefixes: {', '.join(prefix_list)}... (and {len(prefixes) - 5} more)"
                
                if result.get("summary"):
                    summary = result["summary"]
                    answer += f"\n\n📊 Summary: {summary['total_prefixes']} prefixes with {summary['total_hosts']} total hosts"
            
            elif format_type == "table":
                answer = f"📋 **Prefixes Table for {location_name}**\n\n"
                answer += "Here's a formatted table of the prefixes:\n\n"
                answer += result["data"]
            
            elif format_type == "dataframe":
                answer = f"📊 **Data Analysis for {location_name}**\n\n"
                if result.get("analysis"):
                    analysis = result["analysis"]
                    answer += f"• **Total Hosts**: {analysis['total_hosts']:,}\n"
                    answer += f"• **Average Subnet**: /{analysis['average_subnet']:.1f}\n"
                    answer += f"• **Largest Subnet**: /{analysis['largest_subnet']}\n"
                    answer += f"• **Smallest Subnet**: /{analysis['smallest_subnet']}\n"
                answer += f"\nFound {result.get('count', 0)} prefixes with detailed analysis."
            
            elif format_type == "csv":
                answer = f"📥 **CSV Export for {location_name}**\n\n"
                answer += f"CSV data has been generated for {location_name}.\n"
                answer += f"Filename: {result.get('filename', 'prefixes.csv')}\n\n"
                answer += "The CSV contains the following columns:\n"
                answer += "• Prefix, Network, Subnet, Total Hosts, Status, Description, Locations\n\n"
                answer += "You can download this data for further analysis in Excel or other tools."
            
            # Add helpful format options
            answer += f"\n\n💡 **Other Format Options**:\n"
            answer += f"• Ask for 'table format' to see a formatted table\n"
            answer += f"• Ask for 'CSV export' to download the data\n"
            answer += f"• Ask for 'data analysis' to get statistical insights\n"
            
        else:
            answer = result.get("message", f"No prefixes found at {location_name}.")
            
    except Exception as e:
        logger.error("Failed to get prefixes", location=location_name, error=str(e))
        answer = f"Sorry, I encountered an error while looking up prefixes for {location_name}: {e}"
        citations.append({
            "tool": "get_prefixes_by_location_enhanced",
            "args": {"location_name": location_name, "format": format_type},
            "error": str(e)
        })
    
    return answer, citations


def handle_help_request(context: Dict[str, Any], citations: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Handle help requests with comprehensive information."""
    
    answer = """I can help you with Nautobot network information! Here are some things I can do:

1. **Find prefixes by location**: Ask me "What prefixes exist at HQ-Dallas?" or "Show me prefixes at Branch Office 3"

2. **Multiple format options**:
   • **JSON format** (default): "What prefixes are at Branch Office 3?"
   • **Table format**: "Show me prefixes at Branch Office 3 as a table"
   • **CSV export**: "Export prefixes from Branch Office 3 to CSV"
   • **Data analysis**: "Analyze prefixes at Branch Office 3"

3. **Follow-up questions**: I maintain conversation context, so you can ask follow-up questions like:
   • "Show me that as a table"
   • "Export that to CSV"
   • "Analyze that data"

4. **Network information**: I can query Nautobot for network data and provide insights

Just ask me about prefixes at a specific location and I'll look it up for you!"""
    
    return answer, citations


def handle_general_conversation(context: Dict[str, Any], citations: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Handle general conversation with helpful guidance."""
    
    message = context["user_message"].lower()
    
    # More natural and flexible responses based on the message content
    if any(word in message for word in ["hello", "hi", "hey", "greetings"]):
        answer = """Hello! I'm an AI assistant that can help you with various tasks, particularly network information and data analysis.

I have access to Nautobot network data and can help you with:
• Network prefix information and analysis
• Data formatting and export options
• General questions about network infrastructure
• And much more!

What would you like to work on today?"""
    
    elif any(word in message for word in ["how are you", "how do you do", "are you ok"]):
        answer = """I'm doing well, thank you for asking! I'm ready to help you with whatever you need.

I'm particularly good at working with network data and can help you analyze, format, and export information from Nautobot. What can I assist you with today?"""
    
    elif any(word in message for word in ["thanks", "thank you", "appreciate"]):
        answer = """You're very welcome! I'm happy to help. 

Is there anything else you'd like to know or work on? I'm here to assist with network data analysis, formatting, or any other questions you might have."""
    
    elif any(word in message for word in ["bye", "goodbye", "see you", "later"]):
        answer = """Goodbye! It was great working with you. Feel free to come back anytime if you need help with network data analysis or any other tasks. Have a wonderful day!"""
    
    else:
        answer = """I'm an AI assistant that can help you with various tasks, particularly network information and data analysis.

I have access to Nautobot network data and can help you with:
• Network prefix information and analysis
• Data formatting and export options  
• General questions about network infrastructure
• And much more!

What would you like to work on today? You can ask me about specific network locations, request data in different formats, or just chat about whatever's on your mind!"""
    
    return answer, citations
