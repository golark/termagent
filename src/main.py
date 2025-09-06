import os
import sys
from model import call_anthropic
from shell import is_shell_command, execute_shell_command
from history import setup_readline_history, save_history, add_to_history, get_input


def process_command(command: str) -> str:

    if is_shell_command(command):
        output, return_code = execute_shell_command(command)
        return output
    
    response = call_anthropic(command)
    print(f"{response}")

    return response


def main():
    # Setup history navigation
    setup_readline_history()
    
    try:
        while True:
            try:
                user_input = get_input("> ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("Goodbye!")
                    break
                
                if user_input:
                    add_to_history(user_input)
                    process_command(user_input)
                else:
                    print("Please enter a message for Forq")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except EOFError:
                print("\nGoodbye!")
                break
    finally:
        # Save history on exit
        save_history()

if __name__ == "__main__":
    main()
