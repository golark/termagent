import os
import sys
from typing import Any, List, Dict
import json



def dbg(*args, **kwargs) -> None:
    if is_debug_mode():
        print("DEBUG |", *args, **kwargs)


def dbg_messages(command: str, messages: List[Dict[str, Any]]) -> None:
    if is_debug_mode():
        dbg_file_path = get_dbg_file_path()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(dbg_file_path), exist_ok=True)
        
        # Load existing debug messages or start with empty dict
        debug_messages = {}
        if os.path.exists(dbg_file_path):
            with open(dbg_file_path, 'r') as f:
                debug_messages = json.load(f)

        from utils.message_cache import serialize_messages
        debug_messages[command] = serialize_messages(messages)
        with open(dbg_file_path, 'w') as f:
            json.dump(debug_messages, f, indent=2)


def is_debug_mode() -> bool:
    if os.getenv('TERMAGENT_DEBUG', '').lower() in ('true', '1', 'yes', 'on'):
        return True
    if '--debug' in sys.argv or '-d' in sys.argv:
        return True
    
    return False

def get_dbg_file_path() -> str:
    home_dir = os.path.expanduser('~')
    return os.path.join(home_dir, '.termagent', 'debug.json')
