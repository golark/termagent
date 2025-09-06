import os
import sys
from model import call_anthropic
from shell import is_shell_command, execute_shell_command


def process_command(command: str) -> str:
    # Check if it's a shell command and execute directly
    if is_shell_command(command):
        output, return_code = execute_shell_command(command)
        return output
    
    # Otherwise, process through AI
    response = call_anthropic(command)
    print(f"{response}")

    return response


def main():
    
    while True:
        try:
            # Get user input
            user_input = input("> ").strip()
            
            # Check for exit command
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
            
            if user_input:
                process_command(user_input)
            else:
                print("Please enter a message for Forq")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()
