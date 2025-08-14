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
    # Configuration fields
    debug: bool | None
    no_confirm: bool | None
    # Working directory tracking
    current_working_directory: str | None


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
    
    # Check if this query should use GPT-4o for complex analysis
    should_use_gpt4o = state.get("should_use_gpt4o", False)
    query_complexity = state.get("query_complexity", {})
    
    if should_use_gpt4o:
        # Use GPT-4o for complex shell queries
        if state.get("debug", False):
            print("fileagent: 🧠 Using GPT-4o for complex shell query analysis")
        
        # Get directory context for better analysis
        try:
            import os
            current_dir = state.get("current_working_directory", os.getcwd())
            from termagent.directory_context import get_directory_context, get_relevant_files_context
            
            directory_context = get_directory_context(current_dir, max_depth=2, max_files_per_dir=15)
            relevant_files = get_relevant_files_context(current_dir)
            
            context_info = f"""📁 CURRENT WORKSPACE CONTEXT:
{directory_context}

{relevant_files}

"""
        except Exception as e:
            context_info = f"⚠️  Could not get directory context: {e}\n\n"
        
        # Use GPT-4o to analyze the query and provide comprehensive guidance
        try:
            from termagent.agents.base_agent import BaseAgent
            base_agent = BaseAgent("shell_query_analyzer", debug=state.get("debug", False))
            
            if base_agent._initialize_llm("gpt-4o"):
                # Create system prompt for shell query analysis
                system_prompt = f"""You are an expert shell command analyst using GPT-4o. Given a user query about files, directories, Docker, or system information, provide comprehensive analysis and step-by-step guidance.

{context_info}

Your task is to:
1. Understand what the user is asking about
2. Analyze the current workspace context
3. Provide the most appropriate shell command(s) to answer their query
4. Explain why this command is the best choice
5. Provide alternative approaches if relevant
6. Consider edge cases and potential issues
7. Suggest follow-up commands if helpful

IMPORTANT GUIDELINES:
- Be specific and actionable
- Consider the current directory and file structure
- Suggest the most efficient and reliable commands
- Explain the reasoning behind your recommendations
- Consider multiple ways to answer the query
- Be helpful and informative
- Focus on practical, executable solutions

For each recommendation, provide:
- The specific shell command to use
- Why this command is appropriate
- What the expected output will be
- Any potential issues or considerations
- Alternative approaches if relevant

Return your response in a clear, structured format that helps the user understand how to answer their query effectively."""

                # Create messages for LLM
                llm_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this shell-related query and provide guidance: {query}"}
                ]
                
                # Get response from GPT-4o
                llm_response = base_agent.llm.invoke(llm_messages)
                analysis_content = llm_response.content.strip()
                
                # Create comprehensive response
                analysis_response = f"🧠 GPT-4o Shell Query Analysis Complete!\n\n"
                analysis_response += f"🔍 Query: {query}\n"
                analysis_response += f"📋 Type: Shell Query\n"
                analysis_response += f"🧠 Complexity: {query_complexity.get('complexity_score', 'Unknown')} score\n\n"
                analysis_response += f"📋 Analysis:\n{analysis_content}\n\n"
                analysis_response += "💡 You can now follow these recommendations, or ask me to execute specific commands for you."
                
                messages.append(AIMessage(content=analysis_response))
                
                return {
                    **state,
                    "messages": messages
                }
                
        except Exception as e:
            if state.get("debug", False):
                print(f"fileagent: ⚠️ GPT-4o analysis failed: {e}, falling back to standard approach")
    
    # Standard approach for simple queries or when GPT-4o is not available
    # Use LLM to determine the appropriate command for the query
    command, description, response_type = _analyze_query_with_llm(query)
    
    # Check if the command is valid
    if not command or command.strip() == "":
        # No specific command needed - this is an analysis query
        response = f"🔍 Query: {query}\n"
        response += f"📋 Type: Analysis Query\n"
        response += f"💡 Description: {description}\n\n"
        response += "This query requires analysis rather than a specific shell command. "
        response += "Consider rephrasing it as a more specific question about files, directories, or system information."
        
        messages.append(AIMessage(content=response))
        
        return {
            **state,
            "messages": messages
        }
    
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
    
    # Check if this is an analysis query that doesn't need a shell command
    analysis_indicators = [
        'how would you recommend', 'what are the pros and cons', 'analyze', 'compare',
        'what would happen if', 'explain why', 'describe how', 'recommend',
        'suggest', 'best practices', 'alternatives', 'considerations'
    ]
    
    query_lower = query.lower()
    is_analysis_query = any(indicator in query_lower for indicator in analysis_indicators)
    
    if is_analysis_query:
        # This is an analysis query that doesn't need a specific shell command
        return "", f"Analysis query requiring high-level reasoning", "analysis"
    
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
            # LLM is not available, return a simple fallback
            return query, f"Executing query: {query}", "generic"
            
    except Exception as e:
        # LLM failed, return a simple fallback
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
    
    # Import the shell command detector from its own module
    import os
    from termagent.shell_commands import ShellCommandDetector
    
    # Create detector instance
    detector = ShellCommandDetector(debug=state.get("debug", False), no_confirm=state.get("no_confirm", False))
    
    # Execute the command directly
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


def handle_query(state: AgentState) -> AgentState:
    """Handle general queries using GPT-4o to determine multiple steps to answer them."""
    messages = state.get("messages", [])
    query = state.get("last_command", "Unknown query")
    query_type = state.get("query_type", "general_query")
    
    # Create initial response indicating we're using GPT-4o for analysis
    response = f"🔍 Query: {query}\n"
    response += f"📋 Type: {query_type}\n\n"
    response += "🧠 Using GPT-4o to analyze this query and provide a step-by-step approach..."
    messages.append(AIMessage(content=response))
    
    # Use GPT-4o to analyze the query and provide multiple actionable steps
    try:
        from termagent.agents.base_agent import BaseAgent
        base_agent = BaseAgent("query_analyzer", debug=state.get("debug", False))
        
        # Initialize with GPT-4o specifically for complex query analysis
        if base_agent._initialize_llm("gpt-4o"):
            if state.get("debug", False):
                print("query_analyzer | 🧠 Using GPT-4o for multi-step query analysis")
            
            # Get directory context for better analysis
            try:
                import os
                current_dir = state.get("current_working_directory", os.getcwd())
                from termagent.directory_context import get_directory_context, get_relevant_files_context
                
                directory_context = get_directory_context(current_dir, max_depth=2, max_files_per_dir=15)
                relevant_files = get_relevant_files_context(current_dir)
                
                context_info = f"""📁 CURRENT WORKSPACE CONTEXT:
{directory_context}

{relevant_files}

"""
            except Exception as e:
                context_info = f"⚠️  Could not get directory context: {e}\n\n"
            
            # Create system prompt for multi-step query analysis
            system_prompt = f"""You are an expert query analyzer using GPT-4o. Given a user query, analyze it and provide a structured, multi-step approach to answer it effectively.

{context_info}

Your task is to:
1. Understand what the user is asking
2. Break down the query into 3-7 logical, actionable steps
3. Provide specific guidance for each step
4. Suggest relevant commands, tools, or approaches when appropriate
5. Consider the current workspace context
6. Provide explanations for why certain approaches are chosen

IMPORTANT REQUIREMENTS:
- Break down the query into MULTIPLE actionable steps (3-7 steps)
- Each step must be specific and actionable
- Provide clear guidance on what to do at each step
- Suggest specific commands or tools when relevant
- Consider the current workspace structure
- Be helpful and informative
- Focus on practical, executable solutions

STEP STRUCTURE:
For each step, provide:
1. Step number and title
2. Clear description of what to do
3. Specific commands or tools to use (if applicable)
4. Expected outcome or what to look for
5. Any considerations or warnings

Return your response in a clear, structured format with numbered steps that the user can follow sequentially.

Example format:
Step 1: [Title]
Description: [What to do]
Commands: [Specific commands if applicable]
Expected Outcome: [What you should see/achieve]

Step 2: [Title]
Description: [What to do]
Commands: [Specific commands if applicable]
Expected Outcome: [What you should see/achieve]

[Continue for all steps...]"""

            # Create messages for LLM
            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this query and provide multiple actionable steps to answer it: {query}"}
            ]
            
            # Get response from GPT-4o
            llm_response = base_agent.llm.invoke(llm_messages)
            analysis_content = llm_response.content.strip()
            
            # Create comprehensive response with multi-step guidance
            analysis_response = f"🧠 GPT-4o Multi-Step Analysis Complete!\n\n"
            analysis_response += f"📋 Query: {query}\n"
            analysis_response += f"🔍 Type: {query_type}\n\n"
            analysis_response += f"📋 Multi-Step Approach:\n{analysis_content}\n\n"
            analysis_response += "💡 Follow these steps sequentially to answer your query. "
            analysis_response += "Each step builds on the previous one to provide a comprehensive solution."
            
            messages.append(AIMessage(content=analysis_response))
            
        else:
            # Fallback if GPT-4o is not available
            fallback_response = f"⚠️ GPT-4o not available for multi-step query analysis\n\n"
            fallback_response += f"🔍 Query: {query}\n"
            fallback_response += f"📋 Type: {query_type}\n\n"
            fallback_response += "This query doesn't fit into a specific agent category. "
            fallback_response += "You can try rephrasing it as a more specific question or command.\n\n"
            fallback_response += "Examples:\n"
            fallback_response += "• For K8s: 'how many pods are running?' or 'get all deployments'\n"
            fallback_response += "• For Docker: 'how many containers are running?' or 'list all images'\n"
            fallback_response += "• For Git: 'what branch am I on?' or 'show git status'\n"
            fallback_response += "• For files: 'what files are in this directory?' or 'ls -la'"
            
            messages.append(AIMessage(content=fallback_response))
            
    except Exception as e:
        # Error handling
        error_response = f"❌ Error during GPT-4o multi-step query analysis: {str(e)}\n\n"
        error_response += f"🔍 Query: {query}\n"
        error_response += f"📋 Type: {query_type}\n\n"
        error_response += "This query doesn't fit into a specific agent category. "
        error_response += "You can try rephrasing it as a more specific question or command.\n\n"
        error_response += "Examples:\n"
        error_response += "• For K8s: 'how many pods are running?' or 'get all deployments'\n"
        error_response += "• For Docker: 'how many containers are running?' or 'list all images'\n"
        error_response += "• For Git: 'what branch am I on?' or 'show git status'\n"
        error_response += "• For files: 'what files are in this directory?' or 'ls -la'"
        
        messages.append(AIMessage(content=error_response))
    
    return {
        **state,
        "messages": messages
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
        agent = step_info["agent"]
        command = step_info["description"]
        
        # Create step execution message
        step_message = f"🚀 Executing Step {step_num}: {description}\n"
        step_message += f"   Agent: {agent}\n"
        step_message += f"   Progress: {i + 1}/{total_steps}"
        
        messages.append(AIMessage(content=step_message))
        
        # Execute the command (all commands are now shell commands)
        step_success = False
        step_attempts = 0
        max_attempts = 3  # Allow up to 3 attempts per step
        
        while not step_success and step_attempts < max_attempts:
            step_attempts += 1
            
            if step_attempts > 1:
                retry_message = f"🔄 Retry Attempt {step_attempts} for Step {step_num}..."
                messages.append(AIMessage(content=retry_message))
            
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
                    step_success = True
                else:
                    # Command failed - ask LLM for alternatives/fixes
                    if step_attempts == 1:  # Only ask LLM on first failure
                        alternative_command = _get_llm_alternative_for_failed_step(
                            step_num, description, command, process_result.stderr.strip(), 
                            state.get("debug", False)
                        )
                        
                        if alternative_command and alternative_command != command:
                            # Update the command for retry
                            command = alternative_command
                            step_info["command"] = alternative_command
                            task_breakdown[i] = step_info
                            
                            alt_message = f"🔄 LLM suggested alternative approach for Step {step_num}:\n"
                            alt_message += f"   New command: {alternative_command}"
                            messages.append(AIMessage(content=alt_message))
                    
                    result = f"❌ Command failed: {command}"
                    if process_result.stderr.strip():
                        result += f"\nError: {process_result.stderr.strip()}"
                        
            except subprocess.TimeoutExpired:
                result = f"⏰ Command timed out: {command}"
                # Ask LLM for timeout alternatives
                if step_attempts == 1:
                    timeout_alternative = _get_llm_timeout_alternative(
                        step_num, description, command, state.get("debug", False)
                    )
                    if timeout_alternative and timeout_alternative != command:
                        command = timeout_alternative
                        step_info["command"] = timeout_alternative
                        task_breakdown[i] = step_info
                        
                        alt_message = f"🔄 LLM suggested timeout alternative for Step {step_num}:\n"
                        alt_message += f"   New command: {timeout_alternative}"
                        messages.append(AIMessage(content=alt_message))
                        
            except Exception as e:
                result = f"❌ Command execution error: {command}\nError: {str(e)}"
                # Ask LLM for error alternatives
                if step_attempts == 1:
                    error_alternative = _get_llm_error_alternative(
                        step_num, description, command, str(e), state.get("debug", False)
                    )
                    if error_alternative and error_alternative != command:
                        command = error_alternative
                        step_info["command"] = alternative_command
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
        messages.append(AIMessage(content=result))
    
    # Add completion message with success/failure summary
    success_count = len([r for r in results if "✅" in r])
    failure_count = len(failed_steps)
    
    if failure_count == 0:
        completion_message = "🎉 All steps completed successfully!\n\n"
        completion_message += "Summary:\n"
        for result in results:
            completion_message += f"  {result}\n"
    else:
        completion_message = f"⚠️ Task completed with {success_count} successful and {failure_count} failed steps.\n\n"
        completion_message += "Summary:\n"
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
    return {
        **state,
        "messages": messages,
        "routed_to": "shell_command",
        "task_breakdown": None,
        "current_step": None,
        "total_steps": None
    }


def process_command(command: str, graph, debug: bool = False, no_confirm: bool = False) -> Dict[str, Any]:
    """Process a command through the agent graph."""
    # Create initial state
    import os
    initial_state = AgentState(
        messages=[HumanMessage(content=command)],
        routed_to=None,
        last_command=None,
        error=None,
        task_breakdown=None,
        current_step=None,
        total_steps=None,
        is_query=None,
        query_type=None,
        debug=debug,
        no_confirm=no_confirm,
        current_working_directory=os.getcwd()
    )
    
    # Run the graph with config
    config = {"configurable": {"thread_id": "default"}}
    result = graph.invoke(initial_state, config=config)
    
    return result


def process_command_with_cwd(command: str, graph, current_working_directory: str, debug: bool = False, no_confirm: bool = False) -> Dict[str, Any]:
    """Process a command through the agent graph with a specific working directory."""
    # Create initial state with the provided working directory
    initial_state = AgentState(
        messages=[HumanMessage(content=command)],
        routed_to=None,
        last_command=None,
        error=None,
        task_breakdown=None,
        current_step=None,
        total_steps=None,
        is_query=None,
        query_type=None,
        debug=debug,
        no_confirm=no_confirm,
        current_working_directory=current_working_directory
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
