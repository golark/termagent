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


def setup_readline() -> None:
    # Set up tab completion
    readline.set_completer(tab_completer)
    readline.parse_and_bind('tab: complete')
    
    # Enable readline history
    readline.parse_and_bind(r'"\e[A": history-search-backward')
    readline.parse_and_bind(r'"\e[B": history-search-forward')
    readline.parse_and_bind(r'"\e[C": forward-char')
    readline.parse_and_bind(r'"\e[D": backward-char')

    # Create .termagent directory if it doesn't exist
    history_file = get_history_file_path()
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    
    # Load existing history
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass


def update_rlcompleter_with_local_files() -> None:
    """Update tab completion with local files and folders from current directory."""
    # This function is now a no-op since we use the tab_completer function
    # which dynamically reads the current directory
    pass


def save_comand_history() -> None:
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
    """Get user input with history navigation and tab completion support."""
    import readline
    import sys
    import os
    
    if 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    
    # Set up tab completion
    readline.set_completer(tab_completer)
    
    # Set up custom key bindings
    readline.parse_and_bind('tab: complete')
    readline.parse_and_bind('set editing-mode emacs')
    
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        raise


def tab_completer(text: str, state: int) -> str:
    """Tab completion function for commands and file paths."""
    import os
    import glob
    
    
    # Get the current line
    line = readline.get_line_buffer()
    
    # Split the line into words
    words = line.split()
    
    if not words:
        # No words yet, suggest common commands
        commands = ['ls', 'cd', 'pwd', 'cat', 'grep', 'find', 'mkdir', 'rm', 'cp', 'mv']
        matches = [cmd for cmd in commands if cmd.startswith(text)]
        return matches[state] if state < len(matches) else None
    
    # If we're completing the first word (command)
    if len(words) == 1 and not line.endswith(' '):
        commands = ['ls', 'cd', 'pwd', 'cat', 'grep', 'find', 'mkdir', 'rm', 'cp', 'mv', 'python', 'git', 'docker']
        matches = [cmd for cmd in commands if cmd.startswith(text)]
        return matches[state] if state < len(matches) else None
    
    # If we're completing a file path
    if len(words) > 0:
        # Get the last word (which might be a file path)
        last_word = words[-1]
        
        # Commands that typically work with files
        file_commands = ['cat', 'ls', 'cd', 'rm', 'cp', 'mv', 'grep', 'find', 'chmod', 'chown']
        

        # If it looks like a file path or the command works with files
        if ('/' in last_word or last_word.startswith('.') or 
            (len(words) > 0 and words[0] in file_commands)):
            # File path completion
            dirname = os.path.dirname(last_word)
            basename = os.path.basename(last_word)
            
            if not dirname:
                dirname = '.'
            
            try:
                # Get all files in the directory
                files = os.listdir(dirname)
                # Filter files that start with the basename
                matches = []
                for f in files:
                    if f.startswith(basename):
                        full_path = os.path.join(dirname, f)
                        if os.path.isdir(full_path):
                            matches.append(f + '/')
                        else:
                            matches.append(f)
                
                return matches[state] if state < len(matches) else None
            except (OSError, PermissionError):
                return None
        else:
            # Command argument completion
            commands = ['ls', 'cd', 'pwd', 'cat', 'grep', 'find', 'mkdir', 'rm', 'cp', 'mv']
            matches = [cmd for cmd in commands if cmd.startswith(text)]
            return matches[state] if state < len(matches) else None
    
    return None
