from model import call_anthropic, ContextWindowExceededError
from shell import is_shell_command, execute_shell_command, get_shell_aliases, resolve_alias, setup_readline, save_command_history, add_to_history, get_input
from typing import Dict
from utils.debug import dbg_messages
from utils.config import Config
from utils.message_cache import add_to_message_cache, initialize_messages, dump_message_cache, should_replay
from utils.rules import add_rule, remove_rule, list_rules


def process_command(command: str, aliases: Dict[str, str], config: Config) -> str:
    command = resolve_alias(command, aliases)

    if command.lower() == "config":
        config.display()
        return ""
    
    # Handle rules commands
    if command.lower() == "rules":
        rules = list_rules()
        if not rules:
            print("No rules defined. Use 'rule add <text>' to add a rule.")
        else:
            print("\n📋 User-Defined Rules:")
            for rule in rules:
                if rule.get('description'):
                    print(f"  {rule['id']}. {rule['rule']} ({rule['description']})")
                else:
                    print(f"  {rule['id']}. {rule['rule']}")
            print()
        return ""
    
    if command.lower().startswith("rule add "):
        rule_text = command[9:].strip()
        if rule_text:
            rule_id = add_rule(rule_text)
            print(f"✓ Added rule #{rule_id}: {rule_text}")
            print("⚠️  Restart TermAgent for rules to take effect.")
        else:
            print("Error: Please provide rule text. Usage: rule add <text>")
        return ""
    
    if command.lower().startswith("rule remove "):
        try:
            rule_id = int(command[12:].strip())
            if remove_rule(rule_id):
                print(f"✓ Removed rule #{rule_id}")
                print("⚠️  Restart TermAgent for rules to take effect.")
            else:
                print(f"Error: Rule #{rule_id} not found")
        except ValueError:
            print("Error: Please provide a valid rule ID. Usage: rule remove <id>")
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
