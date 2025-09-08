import json
import os
from typing import Dict, List, Any

# Global variable to store messages dictionary in memory
_messages_dict: Dict[str, List[Dict[str, Any]]] = None


def get_messages_file_path() -> str:
    """Get the path to the messages file in home directory."""
    home_dir = os.path.expanduser('~')
    return os.path.join(home_dir, '.termagent', 'messages.json')


def initialize_messages() -> None:
    """Initialize the messages dictionary from file at startup."""
    global _messages_dict
    if _messages_dict is None:
        messages_file = get_messages_file_path()
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                _messages_dict = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _messages_dict = {}


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

def search_message_cache(command: str) -> List[Dict[str, Any]]:
    global _messages_dict
    initialize_messages()
    return _messages_dict.get(command, [])

def add_to_message_cache(command: str, messages: List[Dict[str, Any]]) -> None:
    global _messages_dict
    initialize_messages()
    
    has_error = any(msg.get("role") == "error" for msg in messages)
    
    if not has_error:
        _messages_dict[command] = messages


def dump_message_cache() -> None:
    """Save the in-memory messages dictionary to file with proper serialization."""
    global _messages_dict
    
    if _messages_dict is not None:
        # Serialize all messages before saving
        serialized_messages_dict = {}
        for command, messages in _messages_dict.items():
            serialized_messages = []
            for msg in messages:
                serialized_msg = {
                    'role': msg.get('role'),
                    'content': _serialize_content(msg.get('content'))
                }
                serialized_messages.append(serialized_msg)
            serialized_messages_dict[command] = serialized_messages
        
        messages_file = get_messages_file_path()
        os.makedirs(os.path.dirname(messages_file), exist_ok=True)
        
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(serialized_messages_dict, f, indent=2, ensure_ascii=False)


def search_message_cache(command: str) -> List[Dict[str, Any]]:
    """Search for messages in the cache for a given command."""
    global _messages_dict
    
    # Initialize messages if not already done
    initialize_messages()
    
    return _messages_dict.get(command, [])


def get_command_messages(command: str) -> List[Dict[str, Any]]:
    """Get messages for a specific command from the cache."""
    global _messages_dict
    
    # Initialize messages if not already done
    initialize_messages()
    
    return _messages_dict.get(command, [])
