import os
import sys
from model import call_anthropic, should_replay
from shell import is_shell_command, execute_shell_command, get_shell_aliases, resolve_alias, setup_readline_history, save_comand_history, add_to_history, get_input
from typing import Dict
from utils.message_cache import search_message_cache

from utils.message_cache import add_to_message_cache, initialize_messages, dump_message_cache


def process_command(command: str, aliases: Dict[str, str]) -> str:
    command = resolve_alias(command, aliases)

    if is_shell_command(command):
        output, return_code = execute_shell_command(command)
        return output

    # if command is in message cache then use the message cache
    messages = search_message_cache(command)
    can_replay = should_replay(command)
    print(f"replay: {can_replay}")

    final_message, messages = call_anthropic(command)
    add_to_message_cache(command, messages)
    
    print(final_message)

    return messages


def main():
    initialize_messages()
    
    setup_readline_history()
    aliases = get_shell_aliases()
    
    try:
        while True:
            try:
                user_input = get_input("> ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("Goodbye!")
                    break
                
                if user_input:
                    add_to_history(user_input)
                    process_command(user_input, aliases)
                else:
                    print("Please enter a message for TermAgent")
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
    finally:
        save_comand_history()
        dump_message_cache()


if __name__ == "__main__":
    main()
