#!/usr/bin/env python3
"""
TermAgent - A LangGraph-based agent system with router and git agent via MCP.
"""

import sys
from termagent_graph import create_agent_graph, process_command


def main():
    """Main entry point for the TermAgent application."""
    print("🤖 TermAgent - LangGraph Agent System")
    print("=" * 40)
    print("This agent can:")
    print("  • Detect and route git commands to a specialized git agent")
    print("  • Handle regular commands")
    print("  • Use MCP for agent communication")
    print()
    
    # Create the agent graph
    print("Initializing agent system...")
    graph = create_agent_graph()
    print("✅ Agent system ready!")
    print()
    
    # Interactive mode
    print("Enter commands (or 'quit' to exit):")
    print("-" * 30)
    
    while True:
        try:
            # Get user input
            command = input("termagent> ").strip()
            
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
                print(f"🤖 Response: {response}")
            
            # Show routing information
            routed_to = result.get("routed_to")
            if routed_to:
                print(f"📍 Routed to: {routed_to}")
            
            print("-" * 30)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("-" * 30)


if __name__ == "__main__":
    main()
