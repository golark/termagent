from typing import Dict, Any, List, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from termagent.agents.router_agent import RouterAgent
from termagent.agents.git_agent import GitAgent
from termagent.agents.file_agent import FileAgent
from termagent.agents.k8s_agent import K8sAgent
from termagent.agents.docker_agent import DockerAgent


class AgentState(TypedDict):
    """State for the agent system."""
    messages: List[BaseMessage]
    routed_to: str | None
    last_command: str | None
    git_result: str | None
    file_result: str | None
    k8s_result: str | None
    docker_result: str | None
    error: str | None
    # Task breakdown fields
    task_breakdown: List[Dict[str, str]] | None
    current_step: int | None
    total_steps: int | None


def create_agent_graph(debug: bool = False, no_confirm: bool = False) -> StateGraph:
    """Create the main agent graph with router, git agent, and file agent."""
    
    # Initialize agents
    router_agent = RouterAgent(debug=debug, no_confirm=no_confirm)
    git_agent = GitAgent(debug=debug, no_confirm=no_confirm)
    file_agent = FileAgent(debug=debug, no_confirm=no_confirm)
    k8s_agent = K8sAgent(debug=debug, no_confirm=no_confirm)
    docker_agent = DockerAgent(debug=debug, no_confirm=no_confirm)
    
    # Create the state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router_agent.process)
    workflow.add_node("git_agent", git_agent.process)
    workflow.add_node("file_agent", file_agent.process)
    workflow.add_node("k8s_agent", k8s_agent.process)
    workflow.add_node("docker_agent", docker_agent.process)
    workflow.add_node("handle_regular", handle_regular_command)
    workflow.add_node("handle_task_breakdown", handle_task_breakdown)
    
    # Add conditional edges from router
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "git_agent": "git_agent",
            "file_agent": "file_agent",
            "k8s_agent": "k8s_agent",
            "docker_agent": "docker_agent",
            "handle_regular": "handle_regular",
            "handle_task_breakdown": "handle_task_breakdown",
            END: END
        }
    )
    
    # Add edges to END
    workflow.add_edge("git_agent", END)
    workflow.add_edge("file_agent", END)
    workflow.add_edge("k8s_agent", END)
    workflow.add_edge("docker_agent", END)
    workflow.add_edge("handle_regular", END)
    workflow.add_edge("handle_task_breakdown", END)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    return workflow.compile()


def route_decision(state: AgentState) -> str:
    """Decide which node to route to based on the state."""
    # Check if we're in the middle of a task breakdown
    if state.get("task_breakdown") and state.get("current_step", 0) < state.get("total_steps", 0):
        # Continue with task breakdown
        return "handle_task_breakdown"
    
    # Regular routing logic
    if state.get("routed_to") == "git_agent":
        return "git_agent"
    elif state.get("routed_to") == "file_agent":
        return "file_agent"
    elif state.get("routed_to") == "k8s_agent":
        return "k8s_agent"
    elif state.get("routed_to") == "docker_agent":
        return "docker_agent"
    elif state.get("routed_to") == "regular_command":
        return "handle_regular"
    elif state.get("routed_to") == "task_breakdown":
        return "handle_task_breakdown"
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


def handle_task_breakdown(state: AgentState) -> AgentState:
    """Handle task breakdown and execute all steps in sequence."""
    messages = state.get("messages", [])
    task_breakdown = state.get("task_breakdown", [])
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if not task_breakdown or current_step >= total_steps:
        messages.append(AIMessage(content="✅ Task breakdown completed or no steps remaining."))
        return {
            **state,
            "messages": messages,
            "routed_to": "regular_command"
        }
    
    # Execute all remaining steps in sequence
    results = []
    for i in range(current_step, total_steps):
        step_info = task_breakdown[i]
        step_num = step_info["step"]
        description = step_info["description"]
        agent = step_info["agent"]
        command = step_info["command"]
        
        # Create step execution message
        step_message = f"🚀 Executing Step {step_num}: {description}\n"
        step_message += f"   Agent: {agent}\n"
        step_message += f"   Command: {command}\n"
        step_message += f"   Progress: {i + 1}/{total_steps}"
        
        messages.append(AIMessage(content=step_message))
        
        # Execute the command based on the agent type
        if agent == "git_agent":
            # For git commands, we'll simulate execution
            result = f"✅ Git command executed: {command}"
        elif agent == "file_agent":
            # For file operations, we'll simulate execution
            result = f"✅ File operation executed: {command}"
        elif agent == "k8s_agent":
            # For k8s commands, we'll simulate execution
            result = f"✅ K8s command executed: {command}"
        elif agent == "docker_agent":
            # For Docker commands, we'll simulate execution
            result = f"✅ Docker command executed: {command}"
        else:
            # For regular commands, we'll simulate execution
            result = f"✅ Command executed: {command}"
        
        results.append(f"Step {step_num}: {result}")
        messages.append(AIMessage(content=result))
    
    # Add completion message
    completion_message = f"🎉 All {total_steps} steps completed successfully!\n\n"
    completion_message += "Summary:\n"
    for result in results:
        completion_message += f"  {result}\n"
    
    messages.append(AIMessage(content=completion_message))
    
    # Mark task breakdown as complete
    return {
        **state,
        "messages": messages,
        "routed_to": "regular_command",
        "task_breakdown": None,
        "current_step": None,
        "total_steps": None
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
        k8s_result=None,
        docker_result=None,
        error=None,
        task_breakdown=None,
        current_step=None,
        total_steps=None
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
