"""Simple command history module with up/down arrow navigation."""

import readline
import os
from typing import List, Optional


class CommandHistory:
    """Simple command history manager."""
    
    def __init__(self, max_history: int = 1000):
        """Initialize command history with maximum size."""
        self.max_history = max_history
        self.history: List[str] = []
        self.current_index = 0
        
    def add_command(self, command: str) -> None:
        """Add a command to history."""
        if command.strip() and (not self.history or command != self.history[-1]):
            self.history.append(command.strip())
            if len(self.history) > self.max_history:
                self.history.pop(0)
        self.current_index = len(self.history)
    
    def get_previous(self) -> Optional[str]:
        """Get previous command in history."""
        if self.current_index > 0:
            self.current_index -= 1
            return self.history[self.current_index]
        return None
    
    def get_next(self) -> Optional[str]:
        """Get next command in history."""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return self.history[self.current_index]
        elif self.current_index == len(self.history) - 1:
            self.current_index = len(self.history)
            return ""
        return None
    
    def get_current(self) -> Optional[str]:
        """Get current command in history."""
        if 0 <= self.current_index < len(self.history):
            return self.history[self.current_index]
        return ""
    
    def reset_index(self) -> None:
        """Reset history index to end."""
        self.current_index = len(self.history)


# Global history instance
command_history = CommandHistory()


def get_history_file_path() -> str:
    """Get the path to the history file in home directory."""
    home_dir = os.path.expanduser('~')
    return os.path.join(home_dir, '.termagent', 'history')


def setup_readline_history() -> None:
    """Setup readline for history navigation."""
    # Enable readline history
    readline.parse_and_bind('"\e[A": history-search-backward')
    readline.parse_and_bind('"\e[B": history-search-forward')
    readline.parse_and_bind('"\e[C": forward-char')
    readline.parse_and_bind('"\e[D": backward-char')
    
    # Set up tab completion (basic)
    readline.set_completer_delims(' \t\n')
    
    # Create .termagent directory if it doesn't exist
    history_file = get_history_file_path()
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    
    # Load existing history
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass


def save_history() -> None:
    """Save history to file."""
    try:
        history_file = get_history_file_path()
        readline.write_history_file(history_file)
    except Exception:
        pass


def add_to_history(command: str) -> None:
    """Add command to history."""
    command_history.add_command(command)
    readline.add_history(command)


def get_input(prompt: str = "> ") -> str:
    """Get user input with history navigation support."""
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        raise
