#!/usr/bin/env python3
"""
Input handler for TermAgent with command history navigation.
Provides up/down arrow key navigation through command history.
"""

import os
import readline
import atexit
from typing import List, Optional
from pathlib import Path


class CommandHistory:
    """Manages command history with file persistence and navigation."""
    
    def __init__(self, history_file: Optional[str] = None, max_history: int = 1000):
        """Initialize command history.
        
        Args:
            history_file: Path to history file (defaults to ~/.termagent/history)
            max_history: Maximum number of commands to keep in history
        """
        self.max_history = max_history
        
        # Set up history file
        if history_file is None:
            history_dir = Path.home() / ".termagent"
            history_dir.mkdir(exist_ok=True)
            history_file = str(history_dir / "history")
        
        self.history_file = history_file
        self._setup_readline()
        self._load_history()
        
        # Register cleanup on exit
        atexit.register(self._save_history)
    
    def _setup_readline(self):
        """Set up readline for command history navigation."""
        try:
            # Configure readline
            readline.set_history_length(self.max_history)
            
            # Set up tab completion (basic)
            readline.parse_and_bind('tab: complete')
            
            # Set up history file
            readline.read_history_file(self.history_file)
            
            # Configure input mode for better arrow key handling
            if hasattr(readline, 'set_auto_history'):
                readline.set_auto_history(True)
                
        except (FileNotFoundError, OSError):
            # History file doesn't exist yet, that's fine
            pass
        except Exception as e:
            # Fallback if readline setup fails
            print(f"⚠️  Warning: Could not set up readline: {e}")
    
    def _load_history(self):
        """Load command history from file."""
        try:
            if os.path.exists(self.history_file):
                readline.read_history_file(self.history_file)
        except Exception as e:
            print(f"⚠️  Warning: Could not load history: {e}")
    
    def _save_history(self):
        """Save command history to file."""
        try:
            readline.write_history_file(self.history_file)
        except Exception as e:
            print(f"⚠️  Warning: Could not save history: {e}")
    
    def add_command(self, command: str):
        """Add a command to history.
        
        Args:
            command: The command to add to history
        """
        if command.strip() and not command.startswith('#'):
            # Add to readline history
            readline.add_history(command.strip())
            
            # Trim history if it exceeds max size
            current_length = readline.get_current_history_length()
            if current_length > self.max_history:
                # Remove oldest entries
                for _ in range(current_length - self.max_history):
                    readline.remove_history_item(0)
    
    def get_history(self) -> List[str]:
        """Get the current command history.
        
        Returns:
            List of commands in history
        """
        try:
            return [readline.get_history_item(i) for i in range(1, readline.get_current_history_length() + 1)]
        except Exception:
            return []
    
    def search_history(self, query: str) -> List[str]:
        """Search command history for commands matching a query.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching commands
        """
        history = self.get_history()
        query_lower = query.lower()
        return [cmd for cmd in history if query_lower in cmd.lower()]
    
    def clear_history(self):
        """Clear the command history."""
        try:
            readline.clear_history()
        except Exception as e:
            print(f"⚠️  Warning: Could not clear history: {e}")
    
    def get_history_stats(self) -> dict:
        """Get statistics about the command history.
        
        Returns:
            Dictionary with history statistics
        """
        try:
            total_commands = readline.get_current_history_length()
            history = self.get_history()
            
            return {
                'total_commands': total_commands,
                'unique_commands': len(set(history)),
                'history_file': self.history_file,
                'max_history': self.max_history
            }
        except Exception:
            return {
                'total_commands': 0,
                'unique_commands': 0,
                'history_file': self.history_file,
                'max_history': self.max_history
            }


class InputHandler:
    """Handles user input with command history navigation."""
    
    def __init__(self, history_file: Optional[str] = None, debug: bool = False):
        """Initialize input handler.
        
        Args:
            history_file: Path to history file
            debug: Enable debug mode
        """
        self.debug = debug
        self.history = CommandHistory(history_file)
        self._setup_input_handling()
    
    def _setup_input_handling(self):
        """Set up input handling and display help."""
        if self.debug:
            print("🔧 Input handler initialized with command history navigation")
            print("   Use ↑/↓ arrow keys to navigate command history")
            print("   Use Ctrl+R to search history (if supported)")
    
    def get_input(self, prompt: str = "> ") -> str:
        """Get user input with command history support.
        
        Args:
            prompt: Input prompt to display
            
        Returns:
            User input string
        """
        try:
            # Get input from user
            user_input = input(prompt).strip()
            
            # Add to history if not empty
            if user_input:
                self.history.add_command(user_input)
                if self.debug:
                    print(f"📝 Added to history: {user_input}")
            
            return user_input
            
        except EOFError:
            # Handle Ctrl+D
            return "quit"
        except KeyboardInterrupt:
            # Handle Ctrl+C
            print("\n⏹️  Input cancelled")
            return ""
    
    def show_history(self, limit: int = 20):
        """Display recent command history.
        
        Args:
            limit: Maximum number of commands to show
        """
        history = self.history.get_history()
        if not history:
            print("📚 No command history yet")
            return
        
        print(f"📚 Recent commands (showing last {min(limit, len(history))}):")
        print("-" * 50)
        
        # Show recent commands with line numbers
        for i, cmd in enumerate(history[-limit:], 1):
            print(f"{i:3d}: {cmd}")
        
        print("-" * 50)
        stats = self.history.get_history_stats()
        print(f"Total commands in history: {stats['total_commands']}")
    
    def search_history(self, query: str):
        """Search command history.
        
        Args:
            query: Search query
        """
        if not query.strip():
            print("🔍 Please provide a search query")
            return
        
        matches = self.history.search_history(query)
        if not matches:
            print(f"🔍 No commands found matching: {query}")
            return
        
        print(f"🔍 Found {len(matches)} commands matching '{query}':")
        print("-" * 50)
        
        for i, cmd in enumerate(matches, 1):
            print(f"{i:3d}: {cmd}")
        
        print("-" * 50)
    
    def clear_history(self):
        """Clear command history."""
        self.history.clear_history()
        print("🗑️  Command history cleared")
    
    def get_history_stats(self):
        """Display history statistics."""
        stats = self.history.get_history_stats()
        print("📊 Command History Statistics:")
        print("-" * 30)
        print(f"Total commands: {stats['total_commands']}")
        print(f"Unique commands: {stats['unique_commands']}")
        print(f"History file: {stats['history_file']}")
        print(f"Max history size: {stats['max_history']}")


def create_input_handler(history_file: Optional[str] = None, debug: bool = False) -> InputHandler:
    """Create and configure an input handler.
    
    Args:
        history_file: Path to history file
        debug: Enable debug mode
        
    Returns:
        Configured InputHandler instance
    """
    return InputHandler(history_file, debug)
