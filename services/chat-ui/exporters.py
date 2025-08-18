"""Export functionality for chat transcripts."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List


def export_json(chat_history: List[Dict[str, Any]], filename: str = None) -> str:
    """Export chat history to JSON format.
    
    Args:
        chat_history: List of chat turns
        filename: Optional filename, defaults to timestamped name
        
    Returns:
        Path to the exported file
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_{timestamp}.json"
    
    # Ensure exports directory exists
    os.makedirs("exports", exist_ok=True)
    filepath = os.path.join("exports", filename)
    
    # Prepare export data
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "total_turns": len(chat_history),
        "turns": []
    }
    
    for i, turn in enumerate(chat_history):
        turn_data = {
            "turn_number": i + 1,
            "timestamp": turn.get("timestamp", datetime.now().isoformat()),
            "role": turn["role"],
            "text": turn["text"],
            "tool_calls": turn.get("citations", [])
        }
        export_data["turns"].append(turn_data)
    
    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    return filepath


def export_markdown(chat_history: List[Dict[str, Any]], filename: str = None) -> str:
    """Export chat history to Markdown format.
    
    Args:
        chat_history: List of chat turns
        filename: Optional filename, defaults to timestamped name
        
    Returns:
        Path to the exported file
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_{timestamp}.md"
    
    # Ensure exports directory exists
    os.makedirs("exports", exist_ok=True)
    filepath = os.path.join("exports", filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        # Write header
        f.write("# Chat Transcript\n\n")
        f.write(f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Turns:** {len(chat_history)}\n\n")
        f.write("---\n\n")
        
        # Write each turn
        for i, turn in enumerate(chat_history):
            role = turn["role"].upper()
            text = turn["text"]
            
            f.write(f"## Turn {i + 1}: {role}\n\n")
            f.write(f"{text}\n\n")
            
            # Write tool calls if any
            citations = turn.get("citations", [])
            if citations:
                f.write("### Tool Calls\n\n")
                for j, citation in enumerate(citations):
                    f.write(f"**Tool {j + 1}:** {citation.get('tool', 'Unknown')}\n\n")
                    
                    if "args" in citation:
                        f.write("**Arguments:**\n")
                        f.write("```json\n")
                        f.write(json.dumps(citation["args"], indent=2))
                        f.write("\n```\n\n")
                    
                    if "result_count" in citation:
                        f.write(f"**Results:** {citation['result_count']} items\n\n")
                    
                    if "result_summary" in citation:
                        f.write(f"**Summary:** {citation['result_summary']}\n\n")
                    
                    if "error" in citation:
                        f.write(f"**Error:** {citation['error']}\n\n")
                
                f.write("---\n\n")
            else:
                f.write("---\n\n")
    
    return filepath
