#!/usr/bin/env python3
"""
Test script to demonstrate GPT-4o query handling in TermAgent.
"""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from termagent.termagent_graph import create_agent_graph, process_command

def test_gpt4o_queries():
    """Test various types of queries to see GPT-4o in action."""
    
    print("🧠 Testing GPT-4o Query Handling in TermAgent")
    print("=" * 60)
    
    # Check if OpenAI API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key to test GPT-4o functionality")
        return
    
    # Create the agent graph with debug enabled
    print("🔄 Creating agent graph...")
    graph = create_agent_graph(debug=True, no_confirm=True)
    print("✅ Agent graph created successfully!")
    
    # Test queries of varying complexity
    test_queries = [
        # Simple queries (should use GPT-3.5-turbo)
        "what files are in this directory?",
        "how many python files are here?",
        "show git status",
        
        # Complex queries (should use GPT-4o)
        "how would you recommend organizing this project structure for better maintainability?",
        "what are the pros and cons of using Docker vs virtual environments for this Python project?",
        "analyze the current git workflow and suggest improvements for team collaboration",
        "what would happen if we refactor the agent system to use a different architecture?",
        "compare different approaches to handling shell commands and recommend the best strategy",
        "explain why the current routing system works this way and what alternatives exist"
    ]
    
    print(f"\n📋 Testing {len(test_queries)} queries...")
    print("-" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 [{i}/{len(test_queries)}] Testing: {query}")
        print("-" * 40)
        
        try:
            # Process the query
            result = process_command(query, graph, debug=True, no_confirm=True)
            
            # Display the result
            messages = result.get("messages", [])
            ai_messages = [msg for msg in messages if hasattr(msg, 'content') and 
                          msg.__class__.__name__ == 'AIMessage']
            
            if ai_messages:
                # Show the last AI message (the response)
                response = ai_messages[-1].content
                print(f"🤖 Response:\n{response}")
            
            # Show routing information
            routed_to = result.get("routed_to")
            if routed_to:
                print(f"📍 Routed to: {routed_to}")
            
            # Show query complexity information
            query_complexity = result.get("query_complexity")
            should_use_gpt4o = result.get("should_use_gpt4o")
            is_complex_query = result.get("is_complex_query")
            
            if query_complexity:
                print(f"🧠 Complexity Score: {query_complexity.get('complexity_score', 'Unknown')}")
                print(f"🧠 Requires GPT-4o: {should_use_gpt4o}")
                print(f"🔍 Detected as Complex: {is_complex_query}")
            
        except Exception as e:
            print(f"❌ Error processing query: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("-" * 40)
    
    print(f"\n✅ Testing completed! {len(test_queries)} queries processed.")
    print("\n💡 Key Features Demonstrated:")
    print("• Automatic query complexity detection")
    print("• GPT-4o usage for complex reasoning tasks")
    print("• GPT-3.5-turbo for simple queries")
    print("• Step-by-step guidance for complex queries")
    print("• Context-aware analysis using workspace information")

if __name__ == "__main__":
    test_gpt4o_queries()
