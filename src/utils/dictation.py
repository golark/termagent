"""Mac dictation input support for TermAgent."""

import subprocess
import tempfile
import os
from typing import Optional


def is_dictation_available() -> bool:
    """Check if Mac dictation is available."""
    try:
        # Check if we're on macOS
        result = subprocess.run(['uname'], capture_output=True, text=True)
        if result.stdout.strip() != 'Darwin':
            return False
        
        # Check if dictation is enabled in system preferences
        # This is a simple check - in practice, we'll just try to use it
        return True
    except Exception:
        return False


def get_dictation_input(prompt: str = "🎤 Speak your command: ") -> Optional[str]:
    """Get input using Mac's built-in dictation."""
    if not is_dictation_available():
        print("Dictation not available on this system")
        return None
    
    print(prompt)
    print("Press Enter when ready to start dictation, then speak your command...")
    
    try:
        # Wait for user to press Enter to start dictation
        input()
        
        # Use AppleScript to trigger dictation
        applescript = '''
        tell application "System Events"
            activate
            key code 145 using {command down} -- Trigger dictation
        end tell
        '''
        
        # Execute the AppleScript
        subprocess.run(['osascript', '-e', applescript], check=True)
        
        print("Dictation started. Speak your command, then press Enter when done...")
        
        # Wait for user to finish dictation and press Enter
        dictation_result = input()
        
        return dictation_result.strip() if dictation_result else None
        
    except subprocess.CalledProcessError:
        print("Failed to start dictation. Make sure dictation is enabled in System Preferences.")
        return None
    except KeyboardInterrupt:
        print("\nDictation cancelled.")
        return None
    except Exception as e:
        print(f"Error with dictation: {e}")
        return None


def get_input_with_dictation_option(prompt: str = "> ") -> str:
    """Get input with option to use dictation or keyboard."""
    print("Type your command or press 'd' + Enter for dictation mode")
    
    while True:
        user_input = input(prompt).strip()
        
        if user_input.lower() == 'd':
            dictation_input = get_dictation_input()
            if dictation_input:
                print(f"You said: {dictation_input}")
                return dictation_input
            else:
                print("Dictation failed, please try typing instead.")
                continue
        elif user_input:
            return user_input
        else:
            print("Please enter a command or press 'd' for dictation mode")
