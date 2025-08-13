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
    parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()
    
    print("🤖 TermAgent - LangGraph Agent System")
    if args.debug:
        print("🐛 DEBUG MODE ENABLED")
    if args.no_confirm:
        print("⏭️  NO-CONFIRM MODE ENABLED")
    print("=" * 40)
    print("This agent can:")
    print("  • Execute basic shell commands directly (ls, pwd, mkdir, rm, cp)")
    print("  • Handle git operations through shell commands")
    print("  • Handle file operations through shell commands")
    print("  • Handle Docker operations through shell commands")
    print("  • Detect and route Kubernetes commands to a specialized k8s agent")
    print("  • Edit files with vim or nano")
    print("  • Handle regular commands")
    print("  • Use MCP for agent communication")
    print("  • Show detailed debug information")
    print("  • Execute zsh-compatible shell commands")
    print("  • Navigate command history with ↑/↓ arrow keys")
    print("  • Search and manage command history")
    print()
    
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
    
    # Interactive mode
    print("Enter commands (or 'quit' to exit):")
    print("Special commands:")
    print("  history     - Show command history")
    print("  search <q>  - Search command history")
    print("  clear       - Clear command history")
    print("  stats       - Show history statistics")
    print("-" * 30)
    
    # Create input handler with command history
    input_handler = create_input_handler(debug=args.debug)
    
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
