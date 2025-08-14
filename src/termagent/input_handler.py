#!/usr/bin/env python3
"""
Input handler for TermAgent with command history navigation and voice input.
Provides up/down arrow key navigation through command history and voice command recognition.
"""

import os
import readline
import atexit
import threading
import time
from typing import List, Optional, Callable
from pathlib import Path

try:
    import pyaudio
    import numpy as np
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("⚠️  Voice input not available: Install vosk and pyaudio for voice commands")


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


class VoiceInputHandler:
    """Handles voice input using Vosk speech recognition."""
    
    def __init__(self, model_path: Optional[str] = None, debug: bool = False):
        """Initialize voice input handler.
        
        Args:
            model_path: Path to Vosk model (defaults to ~/.termagent/models/vosk-model-small-en-us)
            debug: Enable debug mode
        """
        self.debug = debug
        self.is_listening = False
        self.audio_thread = None
        self.recognizer = None
        self.audio_stream = None
        self.audio = None
        self.model = None
        
        if not VOSK_AVAILABLE:
            self._debug_print("Voice input not available - missing dependencies")
            return
        
        # Set up model path
        if model_path is None:
            model_dir = Path.home() / ".termagent" / "models"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = str(model_dir / "vosk-model-small-en-us")
        
        self.model_path = model_path
        self._setup_voice_recognition()
    
    def _debug_print(self, message: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"voice_handler: {message}")
    
    def _setup_voice_recognition(self):
        """Set up Vosk model and audio components."""
        try:
            # Check if model exists
            if not os.path.exists(self.model_path):
                self._debug_print(f"Model not found at {self.model_path}")
                self._debug_print("Download a Vosk model from https://alphacephei.com/vosk/models")
                return
            
            # Load Vosk model
            self._debug_print(f"Loading Vosk model from {self.model_path}")
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, 16000)
            
            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()
            self._debug_print("Voice recognition initialized successfully")
            
        except Exception as e:
            self._debug_print(f"Failed to initialize voice recognition: {e}")
            self.model = None
    
    def start_listening(self, callback: Callable[[str], None]):
        """Start listening for voice input in a background thread.
        
        Args:
            callback: Function to call when voice input is detected
        """
        if not self.model or self.is_listening:
            return
        
        self.is_listening = True
        self.audio_thread = threading.Thread(target=self._listen_loop, args=(callback,), daemon=True)
        self.audio_thread.start()
        self._debug_print("Started listening for voice input")
    
    def stop_listening(self):
        """Stop listening for voice input."""
        self.is_listening = False
        if self.audio_thread:
            self.audio_thread.join(timeout=1.0)
        self._cleanup_audio()
        self._debug_print("Stopped listening for voice input")
    
    def _listen_loop(self, callback: Callable[[str], None]):
        """Main listening loop for voice input."""
        try:
            # Open audio stream
            self.audio_stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8192
            )
            
            self._debug_print("Audio stream opened, listening...")
            
            while self.is_listening:
                try:
                    # Read audio data
                    data = self.audio_stream.read(8192, exception_on_overflow=False)
                    
                    if self.recognizer.AcceptWaveform(data):
                        # Process the recognized speech
                        result = self.recognizer.Result()
                        import json
                        result_dict = json.loads(result)
                        
                        if result_dict.get('text', '').strip():
                            text = result_dict['text'].strip()
                            self._debug_print(f"Recognized: {text}")
                            
                            # Call the callback with the recognized text
                            callback(text)
                            
                except Exception as e:
                    self._debug_print(f"Error in audio processing: {e}")
                    break
                    
        except Exception as e:
            self._debug_print(f"Error in listening loop: {e}")
        finally:
            self._cleanup_audio()
    
    def _cleanup_audio(self):
        """Clean up audio resources."""
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except:
                pass
            self.audio_stream = None
    
    def is_available(self) -> bool:
        """Check if voice input is available.
        
        Returns:
            True if voice input is available, False otherwise
        """
        return VOSK_AVAILABLE and self.model is not None
    
    def get_status(self) -> str:
        """Get the status of voice input.
        
        Returns:
            Status string describing voice input availability
        """
        if not VOSK_AVAILABLE:
            return "Voice input not available - missing dependencies"
        elif not self.model:
            return "Voice input not available - model not loaded"
        elif self.is_listening:
            return "Voice input active - listening for commands"
        else:
            return "Voice input ready - press 'v' to activate"


class InputHandler:
    """Handles user input with command history navigation and voice input."""
    
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
            # Get input from user with prompt
            user_input = input(prompt).strip()
            
            # Add to history if not empty
            if user_input:
                self.history.add_command(user_input)
            
            return user_input
            
        except EOFError:
            # Handle Ctrl+D
            return "quit"
        except KeyboardInterrupt:
            # Handle Ctrl+C
            print("\n⏹️  Input cancelled")
            return ""
    
    def _toggle_voice_input(self):
        """Toggle voice input on/off."""
        if not self.voice_handler.is_available():
            print("❌ Voice input not available")
            return
        
        if self.voice_active:
            self.voice_handler.stop_listening()
            self.voice_active = False
            print("🔇 Voice input deactivated")
        else:
            print("🎤 Voice input activated - speak your command")
            print("   Press 'v' again to deactivate")
            self.voice_handler.start_listening(self._on_voice_command)
            self.voice_active = True
    
    def _on_voice_command(self, text: str):
        """Handle voice command recognition.
        
        Args:
            text: Recognized voice command text
        """
        if self.debug:
            print(f"🎤 Voice command recognized: {text}")
        
        # Add to history
        self.history.add_command(text)
        
        # Display the command
        print(f"🎤 Voice command: {text}")
        
        # Stop listening after command is received
        self.voice_handler.stop_listening()
        self.voice_active = False
    
    def get_voice_status(self) -> str:
        """Get the current voice input status.
        
        Returns:
            Status string describing voice input
        """
        return self.voice_handler.get_status()
    
    def is_voice_available(self) -> bool:
        """Check if voice input is available.
        
        Returns:
            True if voice input is available, False otherwise
        """
        return self.voice_handler.is_available()
    
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
    
    def show_voice_status(self):
        """Display voice input status."""
        print("🎤 Voice Input Status:")
        print("-" * 30)
        print(f"Available: {'✅ Yes' if self.is_voice_available() else '❌ No'}")
        print(f"Status: {self.get_voice_status()}")
        if self.voice_active:
            print("Active: ✅ Listening for commands")
        else:
            print("Active: 🔇 Not listening")
        print("-" * 30)
        if self.is_voice_available():
            print("Usage: Press 'v' during input to toggle voice mode")
            print("       Speak your command clearly when voice mode is active")
        else:
            print("To enable voice input:")
            print("1. Install vosk and pyaudio: pip install vosk pyaudio")
            print("2. Download a Vosk model from https://alphacephei.com/vosk/models")
            print("3. Extract to ~/.termagent/models/")


def create_input_handler(history_file: Optional[str] = None, debug: bool = False) -> InputHandler:
    """Create and configure an input handler.
    
    Args:
        history_file: Path to history file
        debug: Enable debug mode
        
    Returns:
        Configured InputHandler instance
    """
    return InputHandler(history_file, debug)
