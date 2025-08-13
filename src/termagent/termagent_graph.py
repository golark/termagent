from typing import Dict, Any, List, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from termagent.agents.router_agent import RouterAgent


class AgentState(TypedDict):
    """State for the agent system."""
    messages: List[BaseMessage]
    routed_to: str | None
    last_command: str | None
    error: str | None
    # Task breakdown fields
    task_breakdown: List[Dict[str, str]] | None
    current_step: int | None
    total_steps: int | None
    # Query handling fields
    is_query: bool | None
    query_type: str | None


def create_agent_graph(debug: bool = False, no_confirm: bool = False) -> StateGraph:
    """Create the main agent graph with router and shell command handling."""
    
    # Initialize agents
    router_agent = RouterAgent(debug=debug, no_confirm=no_confirm)
    
    # Create the state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router_agent.process)
    workflow.add_node("handle_shell", handle_shell_command)
    workflow.add_node("handle_task_breakdown", handle_task_breakdown)
    workflow.add_node("handle_direct_execution", handle_direct_execution)
    workflow.add_node("handle_query", handle_query)
    
    # Add conditional edges from router
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "handle_shell": "handle_shell",
            "handle_task_breakdown": "handle_task_breakdown",
            "handle_direct_execution": "handle_direct_execution",
            "handle_query": "handle_query",
            END: END
        }
    )
    
    # Add edges to END
    workflow.add_edge("handle_shell", END)
    workflow.add_edge("handle_task_breakdown", END)
    workflow.add_edge("handle_direct_execution", END)
    workflow.add_edge("handle_query", END)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    return workflow.compile()


def route_decision(state: AgentState) -> str:
    """Decide which node to route to based on the state."""
    # Check if we're in the middle of a task breakdown
    if state.get("task_breakdown") and state.get("current_step", 0) < state.get("total_steps", 0):
        # Continue with task breakdown
        return "handle_task_breakdown"
    
    # Check if this is a query that needs special handling
    if state.get("is_query"):
        query_type = state.get("query_type", "general_query")
        
        # Route queries to appropriate agents
        if query_type == 'shell_query':
            return "handle_shell"
        else:
            return "handle_query"
    
    # Regular routing logic
    if state.get("routed_to") == "shell_command":
        return "handle_shell"
    elif state.get("routed_to") == "task_breakdown":
        return "handle_task_breakdown"
    elif state.get("routed_to") == "handle_direct_execution":
        return "handle_direct_execution"
    else:
        return END


def handle_shell_command(state: AgentState) -> AgentState:
    """Handle shell commands and file-related queries."""
    messages = state.get("messages", [])
    
    # Get the last command
    last_command = state.get("last_command", "Unknown command")
    is_query = state.get("is_query", False)
    query_type = state.get("query_type", "")
    
    if is_query and query_type == "shell_query":
        # This is a file-related query, handle it intelligently
        return _handle_shell_query(state, last_command)
    else:
        # Regular shell command
        messages.append(AIMessage(
            content=f"Handled shell command: {last_command}. This command was not a git command."
        ))
        
        return {
            **state,
            "messages": messages
        }


def _handle_shell_query(state: AgentState, query: str) -> AgentState:
    """Handle file and Docker queries by converting them to appropriate shell commands."""
    messages = state.get("messages", [])
    
    # Use LLM to determine the appropriate command for the query
    command, description, response_type = _analyze_query_with_llm(query)
    
    # Create response message
    response = f"🔍 Query: {query}\n"
    response += f"📋 Converting to: {command}\n"
    response += f"💡 Description: {description}\n\n"
    
    # Execute the command
    try:
        import subprocess
        import shlex
        
        # Check if command contains shell operators that require shell=True
        shell_operators = ['|', '>', '<', '>>', '<<', '&&', '||', ';', '(', ')', '`', '$(']
        needs_shell = any(op in command for op in shell_operators)
        
        if needs_shell:
            # Use shell=True for commands with operators
            process_result = subprocess.run(
                command,
                shell=True,
                executable="/bin/zsh",
                capture_output=True,
                text=True,
                timeout=30
            )
        else:
            # Use shlex.split for simple commands without operators
            args = shlex.split(command)
            process_result = subprocess.run(
                args, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
        
        if process_result.returncode == 0:
            output = process_result.stdout.strip() if process_result.stdout.strip() else "✅ Command executed successfully"
            
            # Generate natural language response based on query type and output
            natural_response = _generate_natural_response(query, response_type, output, command)
            response += f"✅ Result:\n{natural_response}"
            
            # Add raw output for reference (in smaller text)
            if output and output != "✅ Command executed successfully":
                response += f"\n\n📊 Raw output:\n```\n{output}\n```"
        else:
            error_msg = process_result.stderr.strip() if process_result.stderr.strip() else "Command failed with no error output"
            response += f"❌ Error:\n{error_msg}"
            
    except subprocess.TimeoutExpired:
        response += f"⏰ Command timed out: {command}"
    except FileNotFoundError:
        response += f"❌ Command not found: {command}"
    except Exception as e:
        response += f"❌ Command execution error: {command}\nError: {str(e)}"
    
    messages.append(AIMessage(content=response))
    
    return {
        **state,
        "messages": messages
    }


def _analyze_query_with_llm(query: str) -> tuple[str, str, str]:
    """Use LLM to analyze a query and determine the appropriate command, description, and response type."""
    
    # System prompt for query analysis
    system_prompt = """You are a shell command expert. Given a user query, determine the most appropriate shell command to answer it.

Analyze the query and return a JSON response with:
1. "command": The shell command to execute
2. "description": A brief description of what the command does
3. "response_type": The type of response expected (count, list, status, info, etc.)

IMPORTANT:
- Return ONLY valid JSON
- Commands must work in zsh shell
- Use zsh-compatible syntax
- For counting queries, use commands that output numbers
- For listing queries, use commands that show details
- For status queries, use commands that show current state

Examples:
Query: "how many python files?"
Response: {"command": "ls *.py | wc -l", "description": "Counting Python files in current directory", "response_type": "count"}

Query: "what git branch am I on?"
Response: {"command": "git branch --show-current", "description": "Showing current git branch", "response_type": "info"}

Query: "show running containers"
Response: {"command": "docker ps", "description": "Listing running Docker containers", "response_type": "list"}

Analyze this query:"""

    try:
        # Try to use LLM if available
        from termagent.agents.base_agent import BaseAgent
        base_agent = BaseAgent("temp", debug=False)
        
        if base_agent._initialize_llm():
            # Create messages for LLM
            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            response = base_agent.llm.invoke(llm_messages)
            content = response.content.strip()
            
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON content between ```json and ``` markers
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object in the content
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content
            
            result = json.loads(json_str)
            return result["command"], result["description"], result["response_type"]
            
        else:
            # Fallback to basic pattern matching if LLM is not available
            return _fallback_query_analysis(query)
            
    except Exception as e:
        # Fallback to basic pattern matching if LLM fails
        return _fallback_query_analysis(query)


def _fallback_query_analysis(query: str) -> tuple[str, str, str]:
    """Fallback method to analyze queries when LLM is not available."""
    query_lower = query.lower()
    
    # Basic pattern matching as fallback
    if 'python' in query_lower and ('file' in query_lower or 'count' in query_lower):
        return "ls *.py | wc -l", "Counting Python files in current directory", "count"
    elif 'file' in query_lower and ('count' in query_lower or 'how many' in query_lower):
        return "ls -1 | wc -l", "Counting files in current directory", "count"
    elif 'git' in query_lower and ('status' in query_lower or 'state' in query_lower):
        return "git status", "Showing git repository status", "status"
    elif 'git' in query_lower and 'branch' in query_lower:
        return "git branch -a", "Listing all git branches", "list"
    elif 'docker' in query_lower and 'container' in query_lower:
        return "docker ps -a", "Showing Docker containers", "list"
    elif 'docker' in query_lower and 'image' in query_lower:
        return "docker images", "Listing Docker images", "list"
    else:
        # Generic fallback
        return query, f"Executing query: {query}", "generic"


def _generate_natural_response(query: str, response_type: str, output: str, command: str) -> str:
    """Generate a natural language response based on the query type and command output."""
    
    if response_type == "count":
        try:
            # Extract the count number from output
            count = int(output.strip())
            if 'python' in query.lower():
                return f"There are {count} Python files in this directory."
            elif 'docker' in query.lower() and 'image' in query.lower():
                return f"There are {count} Docker images available."
            elif 'file' in query.lower():
                return f"There are {count} files in this directory."
            else:
                return f"The count is {count}."
        except (ValueError, AttributeError):
            return f"The result is: {output}"
    
    elif response_type == "list":
        if 'file' in query.lower():
            # Count files from ls output
            lines = output.strip().split('\n')
            file_count = len([line for line in lines if line.strip() and not line.startswith('total')])
            return f"There are {file_count} files in this directory:\n{output}"
        else:
            return f"Here are the items:\n{output}"
    
    elif response_type == "status":
        if 'git' in query.lower():
            return "Here's the current git status:\n" + output
        else:
            return f"Here's the current status:\n{output}"
    
    elif response_type == "info":
        if 'git' in query.lower() and 'branch' in query.lower():
            return "You are currently on the git branch: " + output
        else:
            return f"Here's the information:\n{output}"
    
    elif response_type == "docker_containers":
        lines = output.strip().split('\n')
        if len(lines) <= 1:  # Only header or empty
            return "There are no Docker containers running."
        else:
            container_count = len(lines) - 1  # Subtract header line
            if 'running' in query.lower():
                return f"There are {container_count} Docker containers running."
            else:
                return f"There are {container_count} Docker containers (including stopped ones)."
    
    elif response_type == "docker_images":
        lines = output.strip().split('\n')
        if len(lines) <= 1:  # Only header or empty
            return "There are no Docker images available."
        else:
            image_count = len(lines) - 1  # Subtract header line
            return f"There are {image_count} Docker images available."
    
    elif response_type == "directory":
        # Extract current directory and file count
        lines = output.strip().split('\n')
        if lines:
            current_dir = lines[0].strip()
            file_count = len([line for line in lines[1:] if line.strip() and not line.startswith('total')])
            return f"You are currently in {current_dir} and there are {file_count} files/directories here."
        else:
            return f"Current directory information:\n{output}"
    
    elif response_type == "git_status":
        return "Here's the current git status:\n" + output
    
    elif response_type == "git_branches":
        return "Here are all git branches:\n" + output
    
    elif response_type == "git_commits":
        return "Here are the recent git commits:\n" + output
    
    elif response_type == "git_remotes":
        return "Here are the git remote repositories:\n" + output
    
    elif response_type == "git_current_branch":
        return "You are currently on the git branch: " + output
    
    else:
        # Generic response
        return f"Here's the result:\n{output}"


def handle_direct_execution(state: AgentState) -> AgentState:
    """Handle direct execution of known shell commands."""
    messages = state.get("messages", [])
    last_command = state.get("last_command", "Unknown command")
    
    # Import the shell command detector from router agent
    from termagent.agents.router_agent import ShellCommandDetector
    
    # Create detector instance
    detector = ShellCommandDetector(debug=state.get("debug", False), no_confirm=state.get("no_confirm", False))
    
    # Execute the command directly
    success, output, return_code = detector.execute_command(last_command)
    
    if success:
        result_message = f"✅ Command executed successfully: {last_command}\n"
        if output and output != "✅ Command executed successfully":
            result_message += f"Output:\n{output}"
    else:
        result_message = f"❌ Command execution failed: {last_command}\n"
        if output:
            result_message += f"Error: {output}"
    
    messages.append(AIMessage(content=result_message))
    
    return {
        **state,
        "messages": messages
    }


def handle_query(state: AgentState) -> AgentState:
    """Handle general queries that don't fit into specific agent categories."""
    messages = state.get("messages", [])
    query = state.get("last_command", "Unknown query")
    query_type = state.get("query_type", "general_query")
    
    # Create response for general queries
    response = f"🔍 Query: {query}\n"
    response += f"📋 Type: {query_type}\n\n"
    response += "This query doesn't fit into a specific agent category. "
    response += "You can try rephrasing it as a more specific question or command.\n\n"
    response += "Examples:\n"
    response += "• For K8s: 'how many pods are running?' or 'get all deployments'\n"
    response += "• For Docker: 'how many containers are running?' or 'list all images'\n"
    response += "• For Git: 'what branch am I on?' or 'show git status'\n"
    response += "• For files: 'what files are in this directory?' or 'ls -la'"
    
    messages.append(AIMessage(content=response))
    
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
            "routed_to": "shell_command"
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
        
        # Execute the command (all commands are now shell commands)
        try:
            import subprocess
            import shlex
            
            # Check if command contains shell operators that require shell=True
            shell_operators = ['|', '>', '<', '>>', '<<', '&&', '||', ';', '(', ')', '`', '$(']
            needs_shell = any(op in command for op in shell_operators)
            
            if needs_shell:
                # Use shell=True for commands with operators
                process_result = subprocess.run(
                    command,
                    shell=True,
                    executable="/bin/zsh",
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            else:
                # Use shlex.split for simple commands without operators
                args = shlex.split(command)
                process_result = subprocess.run(
                    args, 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
            
            if process_result.returncode == 0:
                result = f"✅ Command executed: {command}"
                if process_result.stdout.strip():
                    result += f"\nOutput: {process_result.stdout.strip()}"
            else:
                result = f"❌ Command failed: {command}"
                if process_result.stderr.strip():
                    result += f"\nError: {process_result.stderr.strip()}"
                    
        except subprocess.TimeoutExpired:
            result = f"⏰ Command timed out: {command}"
        except Exception as e:
            result = f"❌ Command execution error: {command}\nError: {str(e)}"
        
        results.append(f"Step {step_num}: {result}")
        messages.append(AIMessage(content=result))
    
    # Add completion message with success/failure summary
    success_count = len([r for r in results if "✅" in r])
    failure_count = len([r for r in results if "❌" in r])
    
    if failure_count == 0:
        completion_message = f"🎉 All {total_steps} steps completed successfully!\n\n"
        completion_message += "Summary:\n"
        for result in results:
            completion_message += f"  {result}\n"
    else:
        completion_message = f"⚠️ Task completed with {success_count} successful and {failure_count} failed steps.\n\n"
        completion_message += "Summary:\n"
        for result in results:
            completion_message += f"  {result}\n"
        
        # Provide helpful suggestions for failed steps
        completion_message += "\n💡 Suggestions:\n"
        if any("docker" in r.lower() for r in results if "❌" in r):
            completion_message += "• For Docker errors, check if the container name exists: `docker ps -a`\n"
            completion_message += "• Verify container is running: `docker ps`\n"
        if any("git" in r.lower() for r in results if "❌" in r):
            completion_message += "• For Git errors, check repository status: `git status`\n"
            completion_message += "• Verify you're in a git repository: `git rev-parse --git-dir`\n"
    
    messages.append(AIMessage(content=completion_message))
    
    # Mark task breakdown as complete
    return {
        **state,
        "messages": messages,
        "routed_to": "shell_command",
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
        k8s_result=None,
        error=None,
        task_breakdown=None,
        current_step=None,
        total_steps=None,
        is_query=None,
        query_type=None
    )
    
    # Run the graph with config
    config = {"configurable": {"thread_id": "default"}}
    result = graph.invoke(initial_state, config=config)
    
    return result





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
