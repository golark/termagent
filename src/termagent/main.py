#!/usr/bin/env python3
"""
TermAgent - A LangGraph-based agent system with router and git agent via MCP.
"""

import sys
import os
import argparse
from pprint import pprint
from .termagent_graph import create_agent_graph, process_command, process_command_with_cwd
from .input_handler import create_input_handler


def display_agent_state(result, debug: bool, no_confirm: bool):
    """Display the current agent state in a readable format."""
    if result is not None:
        # Display task breakdown information if available
        task_breakdown = result.get('task_breakdown')
        current_step = result.get('current_step')
        total_steps = result.get('total_steps')
        routed_to = result.get('routed_to')
        
        if task_breakdown:
            print("📋 Task Breakdown Information:")
            print("-" * 40)
            print(f"🎯 Total Steps: {total_steps}")
            print(f"📍 Current Step: {current_step}")
            print(f"🔄 Routed To: {routed_to}")
            print()
            print("📝 Task Steps:")
            for step_info in task_breakdown:
                step_num = step_info.get('step', '?')
                description = step_info.get('description', 'No description')
                command = step_info.get('command', 'No command')
                print(f"  [{step_num}] {description}")
                print(f"     Command: {command}")
            print("-" * 40)
            print()
        
        # Display messages
        messages = result.get('messages', [])
        if messages:
            print("📋 Current Agent State Messages:")
            print("-" * 40)
            for i, msg in enumerate(messages, 1):
                msg_type = msg.__class__.__name__
                if msg_type == 'HumanMessage':
                    print(msg.pretty_repr())
                elif msg_type == 'AIMessage':
                    print(msg.pretty_repr())
                else:
                    print(f"📝 {i}. {msg_type}:")
                    print(f"   Content: {getattr(msg, 'content', str(msg))}")
                print()
        else:
            print("📝 No messages in current state")
    else:
        print("📝 No commands executed yet")
        print(f"🛡️ Debug Mode: {debug}")
        print(f"⏭️  No-Confirm Mode: {no_confirm}")
    print("-" * 30)


def main():
    """Main entry point for the TermAgent application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="TermAgent - LangGraph Agent System")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--oneshot", type=str, help="Execute a single command and exit")
    parser.add_argument("--file", type=str, help="Execute commands from a file (one command per line)")
    parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()
    
    print("🤖 TermAgent - LangGraph Agent System")
    if args.debug:
        print("🐛 DEBUG MODE ENABLED")
    if args.no_confirm:
        print("⏭️  NO-CONFIRM MODE ENABLED")
    
    # Create the agent graph
    print("Initializing agent system...")
    graph = create_agent_graph(debug=args.debug, no_confirm=args.no_confirm)
    print("✅ Agent system ready!")
    print()
    
    # Oneshot mode
    if args.oneshot:
        print(f"🎯 ONESHOT MODE: {args.oneshot}")
        print("-" * 30)
        
        try:
            # Process the command
            if args.debug:
                print(f"\n🔄 Processing: {args.oneshot}")
            result = process_command_with_cwd(args.oneshot, graph, os.getcwd(), debug=args.debug, no_confirm=args.no_confirm)
            
            # Display the result
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
            
            print("-" * 30)
            print("✅ Oneshot command completed. Exiting...")
            return
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            if args.debug:
                import traceback
                traceback.print_exc()
            print("-" * 30)
            sys.exit(1)
    
    # File mode
    if args.file:
        print(f"📁 FILE MODE: {args.file}")
        print("-" * 30)
        
        try:
            # Check if file exists
            if not os.path.exists(args.file):
                print(f"❌ Error: File '{args.file}' does not exist")
                sys.exit(1)
            
            # Read commands from file
            with open(args.file, 'r') as f:
                commands = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not commands:
                print("⚠️  No commands found in file (empty file or all lines are comments/empty)")
                return
            
            print(f"📋 Found {len(commands)} commands to execute")
            if args.debug:
                for i, cmd in enumerate(commands, 1):
                    print(f"  {i:2d}: {cmd}")
            print("-" * 30)
            
            # Track working directory across commands
            current_cwd = os.getcwd()
            
            # Execute each command
            for i, command in enumerate(commands, 1):
                print(f"\n🔄 [{i}/{len(commands)}] Executing: {command}")
                if args.debug:
                    print(f"📍 Current working directory: {current_cwd}")
                
                try:
                    # Process the command
                    result = process_command_with_cwd(command, graph, current_cwd, debug=args.debug, no_confirm=args.no_confirm)
                    
                    # Update working directory from result
                    new_cwd = result.get("current_working_directory")
                    if new_cwd and new_cwd != current_cwd:
                        current_cwd = new_cwd
                        if args.debug:
                            print(f"📍 Working directory updated to: {current_cwd}")
                    
                    # Display the result
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
                    print(f"❌ Error executing command '{command}': {str(e)}")
                    if args.debug:
                        import traceback
                        traceback.print_exc()
                    continue
                
                print("-" * 30)
            
            print(f"\n✅ File processing completed. {len(commands)} commands processed.")
            print(f"📍 Final working directory: {current_cwd}")
            return
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            if args.debug:
                import traceback
                traceback.print_exc()
            print("-" * 30)
            sys.exit(1)
    
    
    # Create input handler with command history
    input_handler = create_input_handler(debug=args.debug)
    
    # Track working directory across commands
    current_working_directory = os.getcwd()
    
    # Initialize result for state tracking
    result = None
    
    while True:
        try:
            # Get user input with history navigation
            command = input_handler.get_input("> ").strip()
            
            if not command:
                continue
            
            # Handle special commands
            if command.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            elif command.lower() in ['history', 'h']:
                # Show command history
                print("📚 Command History:")
                history = input_handler.history.get_history()
                for i, cmd in enumerate(history[-10:], 1):  # Show last 10 commands
                    print(f"  {i}. {cmd}")
                print()
                continue
            elif command.lower() in ['breakdowns', 'bd']:
                # Show saved task breakdowns
                from termagent import display_saved_task_breakdowns
                display_saved_task_breakdowns()
                continue
            elif command.lower() in ['state', 's']:
                # Show current agent state
                display_agent_state(result, args.debug, args.no_confirm)
                continue
            
            # Process the command with current working directory
            if args.debug:
                print(f"\n🔄 Processing: {command}")
                print(f"📍 Current working directory: {current_working_directory}")
            
            result = process_command_with_cwd(command, graph, current_working_directory, debug=args.debug, no_confirm=args.no_confirm)
            
            # Update working directory from result
            new_cwd = result.get("current_working_directory")
            if new_cwd and new_cwd != current_working_directory:
                current_working_directory = new_cwd
                if args.debug:
                    print(f"📍 Working directory updated to: {current_working_directory}")
            
            # Display the result
            messages = result.get("messages", [])
            ai_messages = [msg for msg in messages if hasattr(msg, 'content') and 
                          msg.__class__.__name__ == 'AIMessage']
            
            if ai_messages:
                response = ai_messages[-1].content
                print(response)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            if args.debug:
                import traceback
                traceback.print_exc()
            print("-" * 30)


if __name__ == "__main__":
    main()
