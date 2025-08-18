from typing import Dict, Any, List, TypedDict
import os
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
    # Configuration fields
    debug: bool | None
    no_confirm: bool | None
    # Working directory tracking
    current_working_directory: str | None
    # Task breakdown history for successful executions
    successful_task_breakdowns: List[Dict[str, Any]] | None


def _debug_print(message: str, debug: bool = False):
    """Print debug message if debug mode is enabled."""
    if debug:
        print(f"termagent | {message}")


def save_successful_task_breakdowns(breakdowns: List[Dict[str, Any]], file_path: str = None) -> bool:
    """Save successful task breakdowns to a JSON file for persistence."""
    try:
        import json
        import os
        from pathlib import Path
        
        if file_path is None:
            # Default to ~/.termagent/task_breakdowns.json
            history_dir = Path.home() / ".termagent"
            history_dir.mkdir(exist_ok=True)
            file_path = str(history_dir / "task_breakdowns.json")
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(breakdowns, f, indent=2)
        
        return True
    except Exception as e:
        print(f"❌ Error saving task breakdowns: {e}")
        return False


def load_successful_task_breakdowns(file_path: str = None) -> List[Dict[str, Any]]:
    """Load successful task breakdowns from a JSON file."""
    try:
        import json
        from pathlib import Path
        
        if file_path is None:
            # Default to ~/.termagent/task_breakdowns.json
            history_dir = Path.home() / ".termagent"
            file_path = str(history_dir / "task_breakdowns.json")
        
        if not os.path.exists(file_path):
            return []
        
        with open(file_path, 'r') as f:
            breakdowns = json.load(f)
        
        return breakdowns
    except Exception as e:
        print(f"❌ Error loading task breakdowns: {e}")
        return []


def display_saved_task_breakdowns(file_path: str = None) -> None:
    """Display all saved successful task breakdowns."""
    breakdowns = load_successful_task_breakdowns(file_path)
    
    if not breakdowns:
        print("📋 No saved task breakdowns found.")
        return
    
    print(f"📋 Found {len(breakdowns)} saved successful task breakdowns:\n")
    
    for i, breakdown in enumerate(breakdowns, 1):
        command = breakdown.get("command", "unknown")
        timestamp = breakdown.get("timestamp", "unknown")
        working_dir = breakdown.get("working_directory", "unknown")
        task_steps = breakdown.get("task_breakdown", [])
        
        print(f"{i}. Command: {command}")
        print(f"   📅 Timestamp: {timestamp}")
        print(f"   📁 Working Directory: {working_dir}")
        print(f"   📝 Steps: {len(task_steps)}")
        
        for step in task_steps:
            step_num = step.get("step", "?")
            description = step.get("description", "No description")
            agent = step.get("agent", "unknown")
            command = step.get("command", "No command")
            print(f"      Step {step_num}: {description}")
            print(f"         Agent: {agent}")
            print(f"         Command: {command}")
        
        print()


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
    
    # Add conditional edges from router
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
        "handle_shell": "handle_shell",
        "handle_task_breakdown": "handle_task_breakdown",
        "handle_direct_execution": "handle_direct_execution",
        END: END
        }
    )
    
    # Add edges to END
    workflow.add_edge("handle_shell", END)
    workflow.add_edge("handle_task_breakdown", END)
    workflow.add_edge("handle_direct_execution", END)
    
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

    # Regular shell command
    messages.append(AIMessage(
        content=f"Handled shell command: {last_command}"
    ))
    
    return {
        **state,
        "messages": messages
    }


def handle_direct_execution(state: AgentState) -> AgentState:
    """Handle direct execution of known shell commands."""
    messages = state.get("messages", [])
    last_command = state.get("last_command", "Unknown command")
    
    # Import the shell command detector from its own module
    import os
    from termagent.shell_commands import ShellCommandHandler
    
    # Create detector instance
    detector = ShellCommandHandler(debug=state.get("debug", False), no_confirm=state.get("no_confirm", False))
    
    # Shell commands execute directly without confirmation
    
    # Execute the command
    current_cwd = state.get("current_working_directory", os.getcwd())
    success, output, return_code, new_cwd = detector.execute_command(last_command, current_cwd)
    
    if success:
        result_message = f"✅"
        if output:
            result_message += f"\n{output}"
    else:
        result_message = f"❌ Command execution failed: {last_command}\n"
        if output:
            result_message += f"Error: {output}"
    
    messages.append(AIMessage(content=result_message))
    
    return {
        **state,
        "messages": messages,
        "current_working_directory": new_cwd
    }


def handle_task_breakdown(state: AgentState) -> AgentState:
    """Handle task breakdown and execute all steps in sequence with intelligent failure recovery."""
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
    
    # Execute all remaining steps in sequence with intelligent failure recovery
    results = []
    failed_steps = []
    
    for i in range(current_step, total_steps):
        step_info = task_breakdown[i]
        step_num = step_info["step"]
        description = step_info["description"]
        command = step_info["command"]  # Use the command field, not description
        
        # Create step execution message
        step_message = f"🚀 Executing Step {step_num}: {description}\n"
        step_message += f"   Command: {command}\n"
        step_message += f"   Progress: {i + 1}/{total_steps}"
        
        messages.append(AIMessage(content=step_message))
        
        step_success = False
        step_attempts = 0
        max_attempts = 3  # Allow up to 3 attempts per step
        
        while not step_success and step_attempts < max_attempts:
            step_attempts += 1
            
            if step_attempts > 1:
                retry_message = f"🔄 Retry Attempt {step_attempts} for Step {step_num}..."
                messages.append(AIMessage(content=retry_message))
            
            try:
                # Import and create ShellCommandDetector
                from termagent.shell_commands import ShellCommandHandler
                detector = ShellCommandHandler(
                    debug=state.get("debug", False), 
                    no_confirm=state.get("no_confirm", False)
                )
                
                # Check if confirmation is needed for task breakdown steps
                if not state.get("no_confirm", False):
                    print(f"> {command}  (↵ to confirm) ", end="")
                    
                    try:
                        response = input().strip().lower()
                        if response in ['n', 'no', 'cancel', 'skip']:
                            result = f"❌ Step {step_num} cancelled: {command}"
                            messages.append(AIMessage(content=result))
                            # When step is cancelled, break out of the loop and return to main prompt
                            break
                    except KeyboardInterrupt:
                        print("\n❌ Step cancelled")
                        result = f"❌ Step {step_num} cancelled: {command}"
                        messages.append(AIMessage(content=result))
                        # When step is cancelled, break out of the loop and return to main prompt
                        break
                
                _debug_print(f"🔍 Step {step_num} - Executing command: {command}", state.get("debug", False))
                
                # Execute command using ShellCommandDetector
                current_cwd = state.get("current_working_directory", os.getcwd())
                success, output, return_code, new_cwd = detector.execute_command(command, current_cwd)
                
                # Update working directory if it changed
                if new_cwd and new_cwd != current_cwd:
                    state["current_working_directory"] = new_cwd

                if success:
                    result = f"✅ Command executed: {command}"
                    if output and output != "✅ Command executed successfully":
                        result += f"\nOutput: {output}"
                    
                    # Use LLM to reflect on the step execution and decide whether to proceed
                    _debug_print(f"🔍 Step {step_num} - Using LLM reflection to analyze output", state.get("debug", False))
                    reflection = _reflect_on_step_execution(
                        step_num, description, command, output, success, 
                        state.get("debug", False)
                    )
                    
                    # Add reflection message
                    reflection_message = f"🧠 Step {step_num} Reflection:\n"
                    reflection_message += f"   Decision: {'✅ Proceed' if reflection['should_proceed'] else '❌ Stop'}\n"
                    reflection_message += f"   Reasoning: {reflection['reasoning']}\n"
                    if reflection['adjustments_needed']:
                        reflection_message += f"   Adjustments: {reflection['adjustments_needed']}\n"
                    if reflection.get('alternative_commands'):
                        reflection_message += f"   Alternative Commands:\n"
                        for alt_cmd in reflection['alternative_commands']:
                            reflection_message += f"     • {alt_cmd}\n"
                    reflection_message += f"   Confidence: {reflection['confidence']}"
                    messages.append(AIMessage(content=reflection_message))
                    
                    # Check if we should proceed based on reflection
                    if not reflection['should_proceed']:
                        # Check if this was an alternative command that succeeded but didn't achieve the goal
                        if step_attempts > 1 and reflection.get('alternative_commands'):
                            # This was an alternative command - try other alternatives we haven't tried yet
                            tried_alternatives = step_info.get('tried_alternatives', [])
                            if not tried_alternatives:
                                tried_alternatives = []
                            
                            # Add current command to tried alternatives
                            if command not in tried_alternatives:
                                tried_alternatives.append(command)
                            
                            # Find untried alternatives
                            untried_alternatives = [alt for alt in reflection['alternative_commands'] if alt not in tried_alternatives]
                            
                            if untried_alternatives:
                                # Try the next untried alternative
                                next_alternative = untried_alternatives[0]
                                _debug_print(f"🔄 Step {step_num} - Alternative succeeded but didn't achieve goal, trying next alternative: {next_alternative}", state.get("debug", False))
                                
                                # Update the command for retry
                                command = next_alternative
                                step_info["command"] = next_alternative
                                step_info["tried_alternatives"] = tried_alternatives
                                task_breakdown[i] = step_info
                                
                                alt_message = f"🔄 Alternative command succeeded but didn't achieve goal. Trying next alternative for Step {step_num}:\n"
                                alt_message += f"   Next alternative: {next_alternative}"
                                messages.append(AIMessage(content=alt_message))
                                
                                # Continue with the retry loop
                                continue
                            else:
                                # All alternatives tried, now try the original command as last resort
                                original_command = step_info.get('original_command', command)
                                if original_command != command and original_command not in tried_alternatives:
                                    _debug_print(f"🔄 Step {step_num} - All alternatives tried, trying original command as last resort: {original_command}", state.get("debug", False))
                                    
                                    # Reset to original command
                                    command = original_command
                                    step_info["command"] = original_command
                                    step_info["tried_alternatives"] = tried_alternatives
                                    task_breakdown[i] = step_info
                                    
                                    alt_message = f"🔄 All alternatives tried. Trying original command as last resort for Step {step_num}:\n"
                                    alt_message += f"   Original command: {original_command}"
                                    messages.append(AIMessage(content=alt_message))
                                    
                                    # Continue with the retry loop
                                    continue
                        
                        # No alternatives or original command retry, stop execution
                        stop_message = f"🛑 Stopping task breakdown at step {step_num} based on LLM reflection.\n"
                        stop_message += f"Reason: {reflection['reasoning']}"
                        messages.append(AIMessage(content=stop_message))
                        
                        # Return to main prompt
                        return {
                            **state,
                            "messages": messages,
                            "routed_to": "shell_command",
                            "task_breakdown": None,
                            "current_step": None,
                            "total_steps": None
                        }
                    
                    step_success = True
                else:
                    # Command failed - ask LLM for alternatives/fixes
                    if step_attempts == 1: # Only ask LLM on first failure
                        alternative_command = _get_llm_alternative_for_failed_step(
                            step_num, description, command, output, 
                            state.get("debug", False)
                        )
                        
                        if alternative_command and alternative_command != command:
                            # Store the original command before trying alternative
                            if 'original_command' not in step_info:
                                step_info["original_command"] = command
                            
                            # Initialize tried alternatives tracking
                            if 'tried_alternatives' not in step_info:
                                step_info["tried_alternatives"] = []
                            
                            # Add current command to tried alternatives
                            if command not in step_info["tried_alternatives"]:
                                step_info["tried_alternatives"].append(command)
                            
                            # Update the command for retry
                            command = alternative_command
                            step_info["command"] = alternative_command
                            task_breakdown[i] = step_info
                            
                            alt_message = f"🔄 LLM suggested alternative approach for Step {step_num}:\n"
                            alt_message += f"   New command: {alternative_command}"
                            messages.append(AIMessage(content=alt_message))
                    
                    result = f"❌ Command failed: {command}"
                    if output:
                        result += f"\nError: {output}"
                    
                    # Use LLM to reflect on the failed step execution
                    _debug_print(f"🔍 Step {step_num} - Using LLM reflection to analyze failed step", state.get("debug", False))
                    reflection = _reflect_on_step_execution(
                        step_num, description, command, output, success, 
                        state.get("debug", False)
                    )
                    
                    # Add reflection message for failed step
                    reflection_message = f"🧠 Step {step_num} Reflection (Failed):\n"
                    reflection_message += f"   Decision: {'✅ Proceed' if reflection['should_proceed'] else '❌ Stop'}\n"
                    reflection_message += f"   Reasoning: {reflection['reasoning']}\n"
                    if reflection['adjustments_needed']:
                        reflection_message += f"   Adjustments: {reflection['adjustments_needed']}\n"
                    if reflection.get('alternative_commands'):
                        reflection_message += f"   Alternative Commands:\n"
                        for alt_cmd in reflection['alternative_commands']:
                            reflection_message += f"   • {alt_cmd}\n"
                    reflection_message += f"   Confidence: {reflection['confidence']}"
                    messages.append(AIMessage(content=reflection_message))
                    
                    # Check if we should stop based on reflection even for failed steps
                    if not reflection['should_proceed']:
                        # Check if we have alternative commands to try
                        if reflection.get('alternative_commands') and step_attempts < max_attempts:
                            # Try the first alternative command
                            alternative_command = reflection['alternative_commands'][0]
                            _debug_print(f"🔄 Step {step_num} - Trying reflection-suggested alternative: {alternative_command}", state.get("debug", False))
                            
                            # Store the original command before trying alternative
                            if 'original_command' not in step_info:
                                step_info["original_command"] = command
                            
                            # Initialize tried alternatives tracking
                            if 'tried_alternatives' not in step_info:
                                step_info["tried_alternatives"] = []
                            
                            # Add current command to tried alternatives
                            if command not in step_info["tried_alternatives"]:
                                step_info["tried_alternatives"].append(command)
                            
                            # Update the command for retry
                            command = alternative_command
                            step_info["command"] = alternative_command
                            task_breakdown[i] = step_info
                            
                            alt_message = f"🔄 LLM reflection suggested alternative for Step {step_num}:\n"
                            alt_message += f"   New command: {alternative_command}"
                            messages.append(AIMessage(content=alt_message))
                            
                            # Continue with the retry loop instead of stopping
                            continue
                        else:
                            # No alternatives or max attempts reached, stop execution
                            stop_message = f"🛑 Stopping task breakdown at step {step_num} based on LLM reflection of failed step.\n"
                            stop_message += f"Reason: {reflection['reasoning']}"
                            if reflection.get('alternative_commands'):
                                stop_message += f"\n\n💡 Alternative commands were suggested but max attempts reached."
                            messages.append(AIMessage(content=stop_message))
                            
                            # Return to main prompt
                            return {
                                **state,
                                "messages": messages,
                                "routed_to": "shell_command",
                                "task_breakdown": None,
                                "current_step": None,
                                "total_steps": None
                            }
                        
            except Exception as e:
                result = f"❌ Command execution error: {command}\nError: {str(e)}"
                
                # Use LLM to reflect on the execution error
                _debug_print(f"🔍 Step {step_num} - Using LLM reflection to analyze execution error", state.get("debug", False))
                reflection = _reflect_on_step_execution(
                    step_num, description, command, f"Execution error: {str(e)}", False, 
                    state.get("debug", False)
                )
                
                # Add reflection message for execution error
                reflection_message = f"🧠 Step {step_num} Reflection (Execution Error):\n"
                reflection_message += f"   Decision: {'✅ Proceed' if reflection['should_proceed'] else '❌ Stop'}\n"
                reflection_message += f"   Reasoning: {reflection['reasoning']}\n"
                if reflection['adjustments_needed']:
                    reflection_message += f"   Adjustments: {reflection['adjustments_needed']}\n"
                if reflection.get('alternative_commands'):
                    reflection_message += f"   Alternative Commands:\n"
                    for alt_cmd in reflection['alternative_commands']:
                        reflection_message += f"   • {alt_cmd}\n"
                reflection_message += f"   Confidence: {reflection['confidence']}"
                messages.append(AIMessage(content=reflection_message))
                
                # Check if we should stop based on reflection
                if not reflection['should_proceed']:
                    # Check if we have alternative commands to try
                    if reflection.get('alternative_commands') and step_attempts < max_attempts:
                        # Try the first alternative command
                        alternative_command = reflection['alternative_commands'][0]
                        _debug_print(f"🔍 Step {step_num} - Trying reflection-suggested alternative for execution error: {alternative_command}", state.get("debug", False))
                        
                        # Store the original command before trying alternative
                        if 'original_command' not in step_info:
                            step_info["original_command"] = command
                        
                        # Initialize tried alternatives tracking
                        if 'tried_alternatives' not in step_info:
                            step_info["tried_alternatives"] = []
                        
                        # Add current command to tried alternatives
                        if command not in step_info["tried_alternatives"]:
                            step_info["tried_alternatives"].append(command)
                        
                        # Update the command for retry
                        command = alternative_command
                        step_info["command"] = alternative_command
                        task_breakdown[i] = step_info
                        
                        alt_message = f"🔄 LLM reflection suggested alternative for Step {step_num} execution error:\n"
                        alt_message += f"   New command: {alternative_command}"
                        messages.append(AIMessage(content=alt_message))
                        
                        # Continue with the retry loop instead of stopping
                        continue
                    else:
                        # No alternatives or max attempts reached, stop execution
                        stop_message = f"🛑 Stopping task breakdown at step {step_num} based on LLM reflection of execution error.\n"
                        stop_message += f"Reason: {reflection['reasoning']}"
                        if reflection.get('alternative_commands'):
                            stop_message += f"\n\n💡 Alternative commands were suggested but max attempts reached."
                        messages.append(AIMessage(content=stop_message))
                        
                        # Return to main prompt
                        return {
                            **state,
                            "messages": messages,
                            "routed_to": "shell_command",
                            "task_breakdown": None,
                            "current_step": None,
                            "total_steps": None
                        }
                
                # Ask LLM for error alternatives
                if step_attempts == 1:
                    error_alternative = _get_llm_error_alternative(
                        step_num, description, command, str(e), state.get("debug", False)
                    )
                    if error_alternative and error_alternative != command:
                        # Store the original command before trying alternative
                        if 'original_command' not in step_info:
                            step_info["original_command"] = command
                        
                        # Initialize tried alternatives tracking
                        if 'tried_alternatives' not in step_info:
                            step_info["tried_alternatives"] = []
                        
                        # Add current command to tried alternatives
                        if command not in step_info["tried_alternatives"]:
                            step_info["tried_alternatives"].append(command)
                        
                        command = error_alternative
                        step_info["command"] = error_alternative
                        task_breakdown[i] = step_info
                        
                        alt_message = f"🔄 LLM suggested error alternative for Step {step_num}:\n"
                        alt_message += f"   New command: {error_alternative}"
                        messages.append(AIMessage(content=alt_message))
            
            if not step_success and step_attempts >= max_attempts:
                failed_steps.append({
                    "step": step_num,
                    "description": description,
                    "command": command,
                    "attempts": step_attempts,
                    "final_error": result
                })
        
        results.append(f"Step {step_num}: {result}")
        
        # Check if the step was cancelled (loop was broken)
        if "cancelled" in result:
            # Task breakdown was cancelled, return to main prompt
            cancellation_message = f"🔄 Task breakdown cancelled at step {step_num}. Returning to main prompt."
            messages.append(AIMessage(content=cancellation_message))
            
            return {
                **state,
                "messages": messages,
                "routed_to": "shell_command",
                "task_breakdown": None,
                "current_step": None,
                "total_steps": None
            }
    

    # Add completion message with success/failure summary
    success_count = len([r for r in results if "✅" in r])
    failure_count = len(failed_steps)
    
    if failure_count == 0:
        completion_message = ""
        for result in results:
            completion_message += f"  {result}\n"
    else:
        completion_message = f"⚠️ Task completed with {success_count} successful and {failure_count} failed steps.\n\n"
        completion_message += ""
        for result in results:
            completion_message += f"  {result}\n"
        
        # Provide detailed failure analysis and suggestions
        completion_message += f"\n🔍 Failed Steps Analysis:\n"
        for failed_step in failed_steps:
            completion_message += f"  Step {failed_step['step']}: {failed_step['description']}\n"
            completion_message += f"    Attempts: {failed_step['attempts']}\n"
            completion_message += f"    Final Error: {failed_step['final_error']}\n"
        
        # Ask LLM for overall recovery suggestions
        recovery_suggestions = _get_llm_recovery_suggestions(
            failed_steps, task_breakdown, state.get("debug", False)
        )
        
        if recovery_suggestions:
            completion_message += f"\n🧠 LLM Recovery Suggestions:\n{recovery_suggestions}\n"
        
        # Provide helpful suggestions for failed steps
        completion_message += "\n💡 Manual Recovery Suggestions:\n"
        if any("docker" in r.lower() for r in results if "❌" in r):
            completion_message += "• For Docker errors, check if the container name exists: `docker ps -a`\n"
            completion_message += "• Verify container is running: `docker ps`\n"
        if any("git" in r.lower() for r in results if "❌" in r):
            completion_message += "• For Git errors, check repository status: `git status`\n"
            completion_message += "• Verify you're in a git repository: `git rev-parse --git-dir`\n"
    
    messages.append(AIMessage(content=completion_message))
    
    # Mark task breakdown as complete
    # Save successful task breakdowns for future reference
    successful_task_breakdowns = state.get("successful_task_breakdowns", [])
    if failure_count == 0:
        # Save successful task breakdown with the original command
        original_command = state.get("last_command", "unknown")
        
        # Check if this command already exists in successful breakdowns
        existing_breakdown = None
        for breakdown in successful_task_breakdowns:
            if breakdown.get("command", "").lower().strip() == original_command.lower().strip():
                existing_breakdown = breakdown
                break
        
        if existing_breakdown:
            # Update the existing breakdown with the new timestamp
            existing_breakdown["task_breakdown"] = task_breakdown
            existing_breakdown["timestamp"] = __import__("datetime").datetime.now().isoformat()
            existing_breakdown["working_directory"] = state.get("current_working_directory", "unknown")
        else:
            # Add new breakdown
            successful_breakdown = {
                "command": original_command,
                "task_breakdown": task_breakdown,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
                "working_directory": state.get("current_working_directory", "unknown")
            }
            successful_task_breakdowns.append(successful_breakdown)
        
        # Save to disk for persistence
        save_successful_task_breakdowns(successful_task_breakdowns)
    
    return {
        **state,
        "messages": messages,
        "routed_to": "shell_command",
        "task_breakdown": None,
        "current_step": None,
        "total_steps": None,
        "successful_task_breakdowns": successful_task_breakdowns
    }


def process_command(command: str, graph, debug: bool = False, no_confirm: bool = False) -> Dict[str, Any]:
    """Process a command through the agent graph."""
    # Create initial state
    import os
    # Load existing successful task breakdowns
    existing_breakdowns = load_successful_task_breakdowns()
    
    initial_state = AgentState(
        messages=[HumanMessage(content=command)],
        routed_to=None,
        last_command=command,
        error=None,
        task_breakdown=None,
        current_step=None,
        total_steps=None,
        is_query=None,
        debug=debug,
        no_confirm=no_confirm,
        current_working_directory=os.getcwd(),
        successful_task_breakdowns=existing_breakdowns
    )
    
    # Run the graph with config
    config = {"configurable": {"thread_id": "default"}}
    result = graph.invoke(initial_state, config=config)
    
    return result


def process_command_with_cwd(command: str, graph, current_working_directory: str, debug: bool = False, no_confirm: bool = False) -> Dict[str, Any]:
    """Process a command through the agent graph with a specific working directory."""
    # Create initial state with the provided working directory
    # Load existing successful task breakdowns
    existing_breakdowns = load_successful_task_breakdowns()
    
    initial_state = AgentState(
        messages=[HumanMessage(content=command)],
        routed_to=None,
        last_command=command,
        error=None,
        task_breakdown=None,
        current_step=None,
        total_steps=None,
        is_query=None,
        debug=debug,
        no_confirm=no_confirm,
        current_working_directory=current_working_directory,
        successful_task_breakdowns=existing_breakdowns
    )
    
    # Run the graph with config
    config = {"configurable": {"thread_id": "default"}}
    result = graph.invoke(initial_state, config=config)
    
    return result


def _get_llm_alternative_for_failed_step(step_num: int, description: str, command: str, error_output: str, debug: bool = False) -> str:
    """Ask LLM for an alternative approach when a step fails."""
    try:
        from termagent.agents.base_agent import BaseAgent
        base_agent = BaseAgent("failure_recovery", debug=debug)
        
        if base_agent._initialize_llm("gpt-4o"):
            _debug_print("failure_recovery | 🧠 Using GPT-4o for step failure recovery", debug)
            
            system_prompt = """You are an expert at troubleshooting failed shell commands and suggesting alternatives. Given a failed step, provide a better approach.

Your task is to:
1. Analyze why the command failed
2. Suggest an alternative command or approach
3. Consider common issues and their solutions
4. Provide a more robust alternative

IMPORTANT:
- Return ONLY the alternative command, nothing else
- Make sure the command is valid and safe
- Consider the error message when suggesting alternatives
- If no good alternative exists, return an empty string

Examples:
Failed: "docker stop nonexistent_container"
Error: "Error response from daemon: No such container: nonexistent_container"
Alternative: "docker ps -a | grep container_name"

Failed: "git checkout nonexistent_branch"
Error: "error: pathspec 'nonexistent_branch' did not match any file(s) known to git"
Alternative: "git branch -a | grep branch_name"

Failed: "ls /nonexistent/path"
Error: "No such file or directory"
Alternative: "find . -name 'filename' -type f" """

            user_message = f"""Step {step_num}: {description}
Failed Command: {command}
Error Output: {error_output}

Suggest an alternative command or approach:"""

            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = base_agent.llm.invoke(llm_messages)
            alternative = response.content.strip()
            
            # Clean up the response
            if alternative and alternative != command:
                # Remove any markdown formatting or extra text
                alternative = alternative.replace('```', '').replace('`', '').strip()
                if alternative.startswith('Alternative: '):
                    alternative = alternative[13:].strip()
                
                _debug_print(f"failure_recovery | Suggested alternative: {alternative}", debug)
                
                return alternative
            
    except Exception as e:
        _debug_print(f"failure_recovery | Error getting LLM alternative: {e}", debug)
    
    return ""


def _get_llm_error_alternative(step_num: int, description: str, command: str, error: str, debug: bool = False) -> str:
    """Ask LLM for an alternative approach when a step encounters an execution error."""
    try:
        from termagent.agents.base_agent import BaseAgent
        base_agent = BaseAgent("error_recovery", debug=debug)
        
        if base_agent._initialize_llm("gpt-4o"):
            _debug_print("error_recovery | 🧠 Using GPT-4o for execution error recovery", debug)
            
            system_prompt = """You are an expert at handling command execution errors and suggesting alternatives. Given a failed step, provide a better approach.

Your task is to:
1. Analyze the execution error
2. Suggest an alternative command or approach
3. Consider system compatibility and permissions
4. Provide a more robust solution

IMPORTANT:
- Return ONLY the alternative command, nothing else
- Make sure the command is valid and safe
- Consider the error type when suggesting alternatives
- If no good alternative exists, return an empty string

Examples:
Error: "Permission denied"
Alternative: "sudo command" or "chmod +x file"

Error: "Command not found"
Alternative: "which command" or "locate command"

Error: "File not found"
Alternative: "find . -name filename" or "ls -la | grep filename" """

            user_message = f"""Step {step_num}: {description}
Failed Command: {command}
Execution Error: {error}

Suggest an alternative command:"""

            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = base_agent.llm.invoke(llm_messages)
            alternative = response.content.strip()
            
            # Clean up the response
            if alternative and alternative != command:
                alternative = alternative.replace('```', '').replace('`', '').strip()
                if alternative.startswith('Alternative: '):
                    alternative = alternative[13:].strip()
                
                _debug_print(f"error_recovery | Suggested error alternative: {alternative}", debug)
                
                return alternative
            
    except Exception as e:
        _debug_print(f"error_recovery | Error getting LLM error alternative: {e}", debug)
    
    return ""


def _get_llm_recovery_suggestions(failed_steps: list, task_breakdown: list, debug: bool = False) -> str:
    """Ask LLM for overall recovery suggestions when multiple steps fail."""
    try:
        from termagent.agents.base_agent import BaseAgent
        base_agent = BaseAgent("recovery_advisor", debug=debug)
        
        if base_agent._initialize_llm("gpt-4o"):
            _debug_print("recovery_advisor | 🧠 Using GPT-4o for overall recovery suggestions", debug)
            
            system_prompt = """You are an expert at analyzing failed task breakdowns and providing recovery strategies. Given a list of failed steps, suggest overall recovery approaches.

Your task is to:
1. Analyze the pattern of failures
2. Identify common root causes
3. Suggest recovery strategies
4. Provide alternative approaches to complete the task

IMPORTANT:
- Be specific and actionable
- Consider the relationships between failed steps
- Suggest both immediate fixes and long-term solutions
- Focus on practical, executable advice

Provide your suggestions in a clear, structured format."""

            # Create a summary of failed steps
            failed_summary = "\n".join([
                f"Step {step['step']}: {step['description']} (Error: {step['final_error']})"
                for step in failed_steps
            ])
            
            # Create a summary of the overall task
            task_summary = "\n".join([
                f"Step {step['step']}: {step['description']}"
                for step in task_breakdown
            ])
            
            user_message = f"""Task Breakdown:
{task_summary}

Failed Steps:
{failed_summary}

Provide overall recovery suggestions and alternative approaches:"""

            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = base_agent.llm.invoke(llm_messages)
            suggestions = response.content.strip()
            
            _debug_print(f"recovery_advisor | Generated recovery suggestions", debug)
            
            return suggestions
            
    except Exception as e:
        _debug_print(f"recovery_advisor | Error getting LLM recovery suggestions: {e}", debug)
    
    return ""


def _reflect_on_step_execution(step_num: int, description: str, command: str, output: str, success: bool, debug: bool = False) -> Dict[str, Any]:
    """Use LLM to reflect on the output of a shell execution and decide whether to proceed."""
    try:
        from termagent.agents.base_agent import BaseAgent
        base_agent = BaseAgent("step_reflection", debug=debug)
        
        if base_agent._initialize_llm("gpt-4o"):
            _debug_print(f"step_reflection | 🧠 Using GPT-4o for step {step_num} reflection", debug)
            
            system_prompt = """You are an expert at analyzing shell command execution results and deciding whether to proceed with the next step.

Your task is to:
1. Analyze the command output and execution result
2. Determine if the step was successful
3. Decide whether to proceed to the next step
4. Provide reasoning for your decision
5. Suggest any necessary adjustments or alternative approaches

IMPORTANT:
- Return a JSON response with the following structure:
{
  "should_proceed": true/false,
  "reasoning": "explanation of your decision",
  "adjustments_needed": "any suggested changes or fixes",
  "alternative_commands": ["command1", "command2"],
  "confidence": "high/medium/low"
}

- Consider error messages, exit codes, and unexpected output
- Be conservative - if there's uncertainty, recommend stopping
- Focus on whether the step achieved its intended goal
- ALWAYS suggest alternative commands when execution fails
- Provide specific, actionable alternatives that could resolve the issue
- Only suggest stopping if alternatives are unlikely to work or would be dangerous
- Prefer suggesting alternatives over stopping when there are reasonable solutions"""

            user_message = f"""Step {step_num}: {description}
Command: {command}
Success: {success}
Output: {output}

Analyze this step execution and decide whether to proceed.

IMPORTANT: If the step failed (Success: False), you MUST suggest alternative commands that could resolve the issue. These should be specific, actionable commands that address the root cause of the failure."""

            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = base_agent.llm.invoke(llm_messages)
            reflection_content = response.content.strip()
            
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON content between ```json and ``` markers
            json_match = re.search(r'```json\s*(.*?)\s*```', reflection_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object in the content
                json_match = re.search(r'\{.*\}', reflection_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # Fallback to parsing the entire content
                    json_str = reflection_content
            
            try:
                reflection = json.loads(json_str)
                _debug_print(f"step_reflection | Step {step_num} reflection successful", debug)
                return reflection
            except json.JSONDecodeError:
                _debug_print(f"step_reflection | Failed to parse JSON for step {step_num}, using fallback", debug)
                # Fallback response
                return {
                    "should_proceed": success,  # Default to proceeding if successful
                    "reasoning": "LLM reflection failed, defaulting to success-based decision",
                    "adjustments_needed": "",
                    "alternative_commands": [],
                    "confidence": "low"
                }
            
    except Exception as e:
        _debug_print(f"step_reflection | Error getting LLM reflection for step {step_num}: {e}", debug)
        # Fallback response
        return {
            "should_proceed": success,  # Default to proceeding if successful
            "reasoning": "Reflection failed due to error, defaulting to success-based decision",
            "adjustments_needed": "",
            "alternative_commands": [],
            "confidence": "low"
        }


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
