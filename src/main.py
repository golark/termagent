import argparse
from typing import Dict

from src import __version__
from src.model import call_anthropic, ContextWindowExceededError
from src.shell import is_shell_command, execute_shell_command, get_shell_aliases, resolve_alias, setup_readline, save_command_history, add_to_history, get_input
from src.utils.debug import dbg_messages
from src.utils.config import Config
from src.utils.message_cache import add_to_message_cache, initialize_messages, dump_message_cache, should_replay


def process_command(command: str, aliases: Dict[str, str], config: Config) -> str:
    command = resolve_alias(command, aliases)

    if command.lower() == "config":
        config.display()
        return ""

    if is_shell_command(command):
        output, return_code = execute_shell_command(command)
        return output

    tool_use_command = should_replay(command)
    if tool_use_command:
        output, return_code = execute_shell_command(tool_use_command)
        return output
        
    try:
        final_message, messages = call_anthropic(command, config=config)
        add_to_message_cache(command, messages)
        dbg_messages(command, messages)
        print(final_message)
        return messages
    except ContextWindowExceededError as e:
        # Context window exceeded - the error is already handled in call_anthropic
        # but we need to handle it here to prevent the program from crashing
        warning_msg = f"⚠️  {str(e)}"
        print(warning_msg)


def main():
    """Main entry point for TermAgent."""
    parser = argparse.ArgumentParser(
        prog="termagent",
        description="An AI-powered terminal assistant"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    parser.parse_args()
    
    config = Config.from_file()
    initialize_messages()
    setup_readline()
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
                    process_command(user_input, aliases, config)
                else:
                    print("Please enter a message for TermAgent")
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
    finally:
        save_command_history()
        dump_message_cache()


if __name__ == "__main__":
    main()
