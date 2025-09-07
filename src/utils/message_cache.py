import json
import os
from typing import Dict, List, Any


def get_messages_file_path() -> str:
    """Get the path to the messages file in home directory."""
    home_dir = os.path.expanduser('~')
    return os.path.join(home_dir, '.termagent', 'messages.json')


def load_messages() -> Dict[str, List[Dict[str, Any]]]:
    """Load saved messages from file."""
    messages_file = get_messages_file_path()
    try:
        with open(messages_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _serialize_content(content: Any) -> Any:
    """Convert Anthropic API objects to JSON-serializable format."""
    if hasattr(content, '__dict__'):
        # Handle Anthropic API objects like TextBlock, ToolUse, etc.
        return {
            'type': getattr(content, 'type', 'unknown'),
            'text': getattr(content, 'text', ''),
            'id': getattr(content, 'id', ''),
            'name': getattr(content, 'name', ''),
            'input': getattr(content, 'input', {})
        }
    elif isinstance(content, list):
        return [_serialize_content(item) for item in content]
    elif isinstance(content, dict):
        return {key: _serialize_content(value) for key, value in content.items()}
    else:
        return content


def save_messages(command: str, messages: List[Dict[str, Any]]) -> None:
    """Add successful messages to storage and save to file."""
    # Check if messages contain any errors
    has_error = any(msg.get("role") == "error" for msg in messages)
    
    if not has_error:
        # Serialize messages to make them JSON-compatible
        serialized_messages = []
        for msg in messages:
            serialized_msg = {
                'role': msg.get('role'),
                'content': _serialize_content(msg.get('content'))
            }
            serialized_messages.append(serialized_msg)
        
        # Load existing messages, add new ones, and save
        messages_dict = load_messages()
        messages_dict[command] = serialized_messages
        
        # Save directly to file
        messages_file = get_messages_file_path()
        os.makedirs(os.path.dirname(messages_file), exist_ok=True)
        
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages_dict, f, indent=2, ensure_ascii=False)


def get_messages_for_command(command: str) -> List[Dict[str, Any]]:
    """Get saved messages for a specific command."""
    messages_dict = load_messages()
    return messages_dict.get(command, [])
