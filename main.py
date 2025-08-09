#!/usr/bin/env python3
"""
TermAgent - A LangGraph-based agent system with router and git agent via MCP.
"""

import sys
import argparse
from termagent_graph import create_agent_graph, process_command


def main():
    """Main entry point for the TermAgent application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="TermAgent - LangGraph Agent System")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--oneshot", type=str, help="Execute a single command and exit")
    args = parser.parse_args()
    
    print("🤖 TermAgent - LangGraph Agent System")
    if args.debug:
        print("🐛 DEBUG MODE ENABLED")
    print("=" * 40)
    print("This agent can:")
    print("  • Detect and route git commands to a specialized git agent")
    print("  • Handle regular commands")
    print("  • Use MCP for agent communication")
    if args.debug:
        print("  • Show detailed debug information")
    print()
    
    # Create the agent graph
    print("Initializing agent system...")
    graph = create_agent_graph(debug=args.debug)
    print("✅ Agent system ready!")
    print()
    
    # Oneshot mode
    if args.oneshot:
        print(f"🎯 ONESHOT MODE: {args.oneshot}")
        print("-" * 30)
        
        try:
            # Process the command
            print(f"\n🔄 Processing: {args.oneshot}")
            result = process_command(args.oneshot, graph)
            
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
    print("-" * 30)
    
    while True:
        try:
            # Get user input
            command = input("> ").strip()
            
            if not command:
                continue
            
            if command.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            # Process the command
            print(f"\n🔄 Processing: {command}")
            result = process_command(command, graph)
            
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
