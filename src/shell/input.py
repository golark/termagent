"""Shell input handling with readline support and tab completion."""

import readline
import os
from typing import Optional

from .completions import tab_completer
from .history import get_history_file_path, save_command_history, load_command_history


def setup_readline() -> None:
    readline.set_completer(tab_completer)
    readline.parse_and_bind('tab: complete')
    
    readline.parse_and_bind(r'"\e[A": history-search-backward')
    readline.parse_and_bind(r'"\e[B": history-search-forward')
    readline.parse_and_bind(r'"\e[C": forward-char')
    readline.parse_and_bind(r'"\e[D": backward-char')

    history_file = get_history_file_path()
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    
    load_command_history()


def get_input(prompt: str = "> ") -> str:
    """Get user input with history navigation and tab completion support."""
    import readline
    import sys
    import os
    
    if 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    
    readline.set_completer(tab_completer)
    readline.parse_and_bind('tab: complete')
    readline.parse_and_bind('set editing-mode emacs')
    
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        raise
