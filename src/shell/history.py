"""Command history management for shell input."""

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
        if command.strip() and (not self.history or self.history[-1] != command):
            self.history.append(command)
            if len(self.history) > self.max_history:
                self.history.pop(0)
            self.current_index = len(self.history)
    
    def get_previous(self) -> Optional[str]:
        """Get the previous command in history."""
        if self.current_index > 0:
            self.current_index -= 1
            return self.history[self.current_index]
        return None
    
    def get_next(self) -> Optional[str]:
        """Get the next command in history."""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return self.history[self.current_index]
        elif self.current_index == len(self.history) - 1:
            self.current_index += 1
            return ""  # Return empty string for "future" position
        return None
    
    def get_all_history(self) -> List[str]:
        """Get all history as a list."""
        return self.history.copy()
    
    def clear_history(self) -> None:
        """Clear all history."""
        self.history.clear()
        self.current_index = 0
    
    def search_history(self, query: str) -> List[str]:
        """Search history for commands containing the query."""
        return [cmd for cmd in self.history if query.lower() in cmd.lower()]


def get_history_file_path() -> str:
    """Get the path to the history file in home directory."""
    home_dir = os.path.expanduser('~')
    return os.path.join(home_dir, '.termagent', 'history')


def save_command_history() -> None:
    """Save history to file."""
    try:
        history_file = get_history_file_path()
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        readline.write_history_file(history_file)
    except Exception:
        pass  # Ignore errors when saving history


def load_command_history() -> None:
    """Load history from file."""
    try:
        history_file = get_history_file_path()
        if os.path.exists(history_file):
            readline.read_history_file(history_file)
    except Exception:
        pass  # Ignore errors when loading history


# Global history instance
command_history = CommandHistory()


def add_to_history(command: str) -> None:
    """Add command to history."""
    command_history.add_command(command)
    readline.add_history(command)
