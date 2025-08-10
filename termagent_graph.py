from typing import Dict, Any, List, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents.router_agent import RouterAgent
from agents.git_agent import GitAgent
from agents.file_agent import FileAgent


class AgentState(TypedDict):
    """State for the agent system."""
    messages: List[BaseMessage]
    routed_to: str | None
    last_command: str | None
    git_result: str | None
    file_result: str | None
    error: str | None


def create_agent_graph(debug: bool = False, no_confirm: bool = False) -> StateGraph:
    """Create the main agent graph with router, git agent, and file agent."""
    
    # Initialize agents
    router_agent = RouterAgent(debug=debug, no_confirm=no_confirm)
    git_agent = GitAgent(debug=debug, no_confirm=no_confirm)
    file_agent = FileAgent(debug=debug, no_confirm=no_confirm)
    
    # Create the state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router_agent.process)
    workflow.add_node("git_agent", git_agent.process)
    workflow.add_node("file_agent", file_agent.process)
    workflow.add_node("handle_regular", handle_regular_command)
    
    # Add conditional edges from router
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "git_agent": "git_agent",
            "file_agent": "file_agent",
            "handle_regular": "handle_regular",
            END: END
        }
    )
    
    # Add edges to END
    workflow.add_edge("git_agent", END)
    workflow.add_edge("file_agent", END)
    workflow.add_edge("handle_regular", END)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    return workflow.compile()


def route_decision(state: AgentState) -> str:
    """Decide which node to route to based on the state."""
    if state.get("routed_to") == "git_agent":
        return "git_agent"
    elif state.get("routed_to") == "file_agent":
        return "file_agent"
    elif state.get("routed_to") == "regular_command":
        return "handle_regular"
    else:
        return END


def handle_regular_command(state: AgentState) -> AgentState:
    """Handle regular (non-git) commands."""
    messages = state.get("messages", [])
    
    # Get the last command
    last_command = state.get("last_command", "Unknown command")
    
    # Add a response for regular commands
    messages.append(AIMessage(
        content=f"Handled regular command: {last_command}. This command was not a git command."
    ))
    
    return {
        **state,
        "messages": messages
    }


def process_command(command: str, graph) -> Dict[str, Any]:
    """Process a command through the agent graph."""
    # Create initial state
    initial_state = AgentState(
        messages=[HumanMessage(content=command)],
        routed_to=None,
        last_command=None,
        git_result=None,
        file_result=None,
        error=None
    )
    
    # Run the graph with config
    config = {"configurable": {"thread_id": "default"}}
    result = graph.invoke(initial_state, config=config)
    
    return result


# Alternative implementation that uses should_handle
def create_agent_graph_with_should_handle() -> StateGraph:
    """Create the main agent graph with should_handle-based routing."""
    
    # Initialize agents
    router_agent = RouterAgent()
    git_agent = GitAgent()
    
    # Create the state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router_agent.process)
    workflow.add_node("git_agent", git_agent.process)
    workflow.add_node("handle_regular", handle_regular_command)
    
    # Add conditional edges from router using should_handle
    workflow.add_conditional_edges(
        "router",
        route_decision_with_should_handle,
        {
            "git_agent": "git_agent",
            "handle_regular": "handle_regular",
            END: END
        }
    )
    
    # Add edges to END
    workflow.add_edge("git_agent", END)
    workflow.add_edge("handle_regular", END)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    return workflow.compile()


def route_decision_with_should_handle(state: AgentState) -> str:
    """Decide which node to route to based on should_handle methods."""
    router_agent = RouterAgent()
    git_agent = GitAgent()
    
    # Check if git agent should handle this
    if git_agent.should_handle(state):
        return "git_agent"
    # Check if router should handle this (for regular commands)
    elif router_agent.should_handle(state):
        return "handle_regular"
    else:
        return END


if __name__ == "__main__":
    # Create the graph
    graph = create_agent_graph()
    
    # Test with some commands
    test_commands = [
        "git status",
        "git add .",
        "git commit -m 'test commit'",
        "ls -la",
        "echo 'hello world'"
    ]
    
    print("Testing agent system...")
    print("=" * 50)
    
    for command in test_commands:
        print(f"\nProcessing command: {command}")
        result = process_command(command, graph)
        
        # Print the last AI message
        messages = result.get("messages", [])
        ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
        
        if ai_messages:
            print(f"Response: {ai_messages[-1].content}")
        
        # Print routing information
        routed_to = result.get("routed_to")
        if routed_to:
            print(f"Routed to: {routed_to}")
        
        print("-" * 30)
