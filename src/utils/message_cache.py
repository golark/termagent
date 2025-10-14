import json
import os
from typing import Dict, List, Any

# Global variable to store messages dictionary in memory
_messages_dict: Dict[str, List[Dict[str, Any]]] = None


def get_messages_file_path() -> str:
    home_dir = os.path.expanduser('~')
    return os.path.join(home_dir, '.termagent', 'messages.json')


def initialize_messages() -> None:
    global _messages_dict
    if _messages_dict is None:
        messages_file = get_messages_file_path()
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                _messages_dict = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _messages_dict = {}


def _serialize_content(content: Any) -> Any:
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

def add_to_message_cache(command: str, messages: List[Dict[str, Any]]) -> None:
    global _messages_dict
    initialize_messages()
    
    has_error = any(msg.get("role") == "error" for msg in messages)
    
    if not has_error:
        _messages_dict[command] = messages


def serialize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    serialized = []
    for msg in messages:
        serialized.append({
            'role': msg.get('role'),
            'content': _serialize_content(msg.get('content'))
        })
    return serialized

def dump_message_cache() -> None:
    global _messages_dict
    
    if _messages_dict is not None:
        serialized_messages_dict = {command: serialize_messages(messages) for command, messages in _messages_dict.items()}
       
        messages_file = get_messages_file_path()
        os.makedirs(os.path.dirname(messages_file), exist_ok=True)
        
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(serialized_messages_dict, f, indent=2, ensure_ascii=False)


def get_command_messages(command: str) -> List[Dict[str, Any]]:
    global _messages_dict
    initialize_messages()
    
    return _messages_dict.get(command, [])


def should_replay(command: str) -> bool:
    messages = get_command_messages(command)

    if not messages:
        return None
    tool_use_idx = None
    for i, m in enumerate(messages):
        if not m['role'] == 'assistant':
            continue
        if not isinstance(m['content'], list):
            continue
        for k, content in enumerate(m['content']):
            # Handle both serialized dict and Anthropic API objects
            if hasattr(content, 'type'):
                # Anthropic API object (TextBlock, ToolUse, etc.)
                content_type = content.type
            elif isinstance(content, dict):
                # Serialized content
                content_type = content.get('type')
            else:
                continue
                
            if content_type == 'tool_use':
                tool_use_idx = (i, k)
                break

    if not tool_use_idx:
        return False 

    # check if there is any assistant message after tool_use
    for i in range(tool_use_idx[0] + 1, len(messages)):
        if messages[i]['role'] == 'assistant' and messages[i]['content']:
            return False

    i, k = tool_use_idx
    content = messages[i]['content'][k]
    
    # Handle both serialized dict and Anthropic API objects
    if hasattr(content, 'input'):
        # Anthropic API object (ToolUseBlock)
        tool_input = content.input
    elif isinstance(content, dict):
        # Serialized content
        tool_input = content.get('input', {})
    else:
        return None
    
    # Return command if it exists (for bash tool)
    return tool_input.get('command') if tool_input else None
