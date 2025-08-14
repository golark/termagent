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
from typing import List, Optional, Callable, Any
from pathlib import Path

try:
    import pyaudio
    import numpy as np
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("⚠️  Voice input not available: Install speechrecognition and pyaudio for voice commands")


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
    """Handles voice input using speech recognition."""
    
    def __init__(self, debug: bool = False):
        """Initialize voice input handler.
        
        Args:
            debug: Enable debug mode
        """
        self.debug = debug
        self.is_listening = False
        self.audio_thread = None
        self.recognizer = None
        
        if not SPEECH_RECOGNITION_AVAILABLE:
            self._debug_print("Voice input not available - missing dependencies")
            return
        
        self._setup_voice_recognition()
    
    def _debug_print(self, message: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"voice_handler: {message}")
    
    def _setup_voice_recognition(self):
        """Set up speech recognition components."""
        try:
            # Initialize speech recognizer
            self._debug_print("Initializing speech recognition")
            self.recognizer = sr.Recognizer()
            
            # Configure recognition settings
            self.recognizer.energy_threshold = 4000  # Adjust based on your microphone
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            
            self._debug_print("Speech recognition initialized successfully")
            
        except Exception as e:
            self._debug_print(f"Failed to initialize speech recognition: {e}")
    
    def start_listening(self, callback: Callable[[str], None]):
        """Start listening for voice input in a background thread.
        
        Args:
            callback: Function to call when voice input is detected
        """
        if not self.recognizer:
            self._debug_print("Speech recognition not available")
            return
        
        if self.is_listening:
            self._debug_print("Already listening")
            return
        
        self.is_listening = True
        self.audio_thread = threading.Thread(target=self._listen_loop, args=(callback,))
        self.audio_thread.daemon = True
        self.audio_thread.start()
        self._debug_print("Started listening for voice input")
    
    def stop_listening(self):
        """Stop listening for voice input."""
        self.is_listening = False
        self._debug_print("Stopped listening for voice input")
    
    def _listen_loop(self, callback: Callable[[str], None]):
        """Main listening loop for voice input."""
        try:
            with sr.Microphone() as source:
                self._debug_print("Using microphone as audio source")
                
                # Adjust for ambient noise
                self._debug_print("Adjusting for ambient noise... Please wait...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self._debug_print("Ambient noise adjustment complete")
                
                while self.is_listening:
                    try:
                        self._debug_print("Listening for speech...")
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=10)
                        
                        if not self.is_listening:
                            break
                        
                        self._debug_print("Speech detected, processing...")
                        
                        # Use Google's speech recognition (free, requires internet)
                        try:
                            text = self.recognizer.recognize_google(audio)
                            if text and self.is_listening:
                                self._debug_print(f"Recognized: {text}")
                                callback(text)
                        except sr.UnknownValueError:
                            self._debug_print("Speech was unintelligible")
                        except sr.RequestError as e:
                            self._debug_print(f"Could not request results from speech recognition service: {e}")
                        except Exception as e:
                            self._debug_print(f"Error during speech recognition: {e}")
                    
                    except sr.WaitTimeoutError:
                        # No speech detected, continue listening
                        continue
                    except Exception as e:
                        self._debug_print(f"Error in listening loop: {e}")
                        break
                        
        except Exception as e:
            self._debug_print(f"Error setting up microphone: {e}")
        finally:
            self.is_listening = False
            self._debug_print("Listening loop ended")
    
    def is_available(self) -> bool:
        """Check if voice input is available.
        
        Returns:
            True if voice input is available, False otherwise
        """
        return SPEECH_RECOGNITION_AVAILABLE and self.recognizer is not None
    
    def get_status(self) -> str:
        """Get the status of voice input.
        
        Returns:
            Status string describing voice input availability
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            return "Voice input not available - missing dependencies"
        elif not self.recognizer:
            return "Voice input not available - recognition not initialized"
        elif self.is_listening:
            return "Voice input active - listening for commands"
        else:
            return "Voice input ready - press 'v' to activate"


class InputHandler:
    """Handles user input with command history navigation and voice input."""
    
    def __init__(self, history_file: Optional[str] = None, debug: bool = False, command_processor: Optional[Callable[[str], Any]] = None):
        """Initialize input handler.
        
        Args:
            history_file: Path to history file
            debug: Enable debug mode
            command_processor: Optional callback function to process commands
        """
        self.debug = debug
        self.history = CommandHistory(history_file)
        self.voice_handler = VoiceInputHandler(debug=debug)
        self.voice_active = False
        self.command_processor = command_processor
        self._setup_input_handling()
    
    def _setup_input_handling(self):
        """Set up input handling and display help."""
        if self.debug:
            print("🔧 Input handler initialized with command history navigation")
            print("   Use ↑/↓ arrow keys to navigate command history")
            print("   Use Ctrl+R to search history (if supported)")
            if self.voice_handler.is_available():
                print("   Use 'v' to toggle voice input mode")
                print(f"   Voice status: {self.voice_handler.get_status()}")
            else:
                print("   Voice input not available")
    
    def set_command_processor(self, processor: Callable[[str], Any]):
        """Set the command processor callback.
        
        Args:
            processor: Function to process commands
        """
        self.command_processor = processor
    
    def get_input(self, prompt: str = "> ") -> str:
        """Get user input with command history support and voice input.
        
        Args:
            prompt: Input prompt to display
            
        Returns:
            User input string
        """
        try:
            # Check for voice input activation
            if self.voice_handler.is_available() and not self.voice_active:
                # Use input() with prompt to keep cursor on same line
                user_input = input(f"💬 {prompt} (press 'v' for voice input)").strip()
            else:
                # Use input() with prompt to keep cursor on same line
                user_input = input(prompt).strip()
            
            # Handle voice input toggle
            if user_input.lower() == 'v' and self.voice_handler.is_available():
                self._toggle_voice_input()
                return ""
            
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
        
        # Process the voice command through the router if processor is available
        if self.command_processor and text.strip():
            try:
                if self.debug:
                    print(f"🔄 Processing voice command through router: {text}")
                result = self.command_processor(text.strip())
                
                # Display the result if it's available
                if result and hasattr(result, 'get'):
                    messages = result.get("messages", [])
                    ai_messages = [msg for msg in messages if hasattr(msg, 'content') and 
                                  msg.__class__.__name__ == 'AIMessage']
                    
                    if ai_messages:
                        response = ai_messages[-1].content
                        print(response)
                    
                    # Show routing information
                    routed_to = result.get("routed_to")
                    if routed_to:
                        print(f"📍 Routed to: {routed_to}")
                        
            except Exception as e:
                print(f"❌ Error processing voice command: {str(e)}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
        
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
            print("1. Install speechrecognition and pyaudio: pip install speechrecognition pyaudio")
            print("2. Ensure you have a working microphone")
            print("3. Internet connection required for Google Speech Recognition")


def create_input_handler(history_file: Optional[str] = None, debug: bool = False, command_processor: Optional[Callable[[str], Any]] = None) -> InputHandler:
    """Create and configure an input handler.
    
    Args:
        history_file: Path to history file
        debug: Enable debug mode
        command_processor: Optional callback function to process commands
        
    Returns:
        Configured InputHandler instance
    """
    return InputHandler(history_file, debug, command_processor)
