#!/usr/bin/env python3
"""
TermAgent - A LangGraph-based agent system with router and git agent via MCP.
"""

import sys
import os
import argparse
from .termagent_graph import create_agent_graph, process_command, process_command_with_cwd
from .input_handler import create_input_handler


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
    
    # Interactive mode
    print("Enter commands (or 'quit' to exit):")
    print("Special commands:")
    print("  history     - Show command history")
    print("  search <q>  - Search command history")
    print("  clear       - Clear command history")
    print("  voice       - Enable voice input mode")
    print("  Note: Voice commands are automatically processed through the router")
    print("-" * 30)
    
    # Set up command processor for voice commands
    def process_voice_command(command: str):
        """Process voice commands through the router."""
        try:
            return process_command_with_cwd(command, graph, current_working_directory, debug=args.debug, no_confirm=args.no_confirm)
        except Exception as e:
            print(f"❌ Error processing voice command: {str(e)}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return None
    
    # Create input handler with command history and command processor
    input_handler = create_input_handler(debug=args.debug, command_processor=process_voice_command)
    
    # Track working directory across commands
    current_working_directory = os.getcwd()
    
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
            elif command.lower() == 'history':
                input_handler.show_history()
                continue
            elif command.lower() == 'clear':
                input_handler.clear_history()
                continue
            elif command.lower() == 'stats':
                input_handler.get_history_stats()
                continue
            elif command.lower() == 'voice':
                if input_handler.is_voice_available():
                    print("🎤 Activating voice input mode...")
                    input_handler._toggle_voice_input()
                else:
                    print("❌ Voice input not available")
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
