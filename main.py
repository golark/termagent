#!/usr/bin/env python3
"""
Simple REPL loop that echoes messages back to the user.
"""

def main():
    print("Simple REPL - Type 'exit' to quit")
    
    while True:
        try:
            # Get user input
            user_input = input("> ").strip()
            
            # Check for exit command
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
            
            # Echo the message back
            if user_input:
                print(f"Echo: {user_input}")
            else:
                print("Echo: (empty input)")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()
