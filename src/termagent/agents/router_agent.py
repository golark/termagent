import re
import subprocess
import shlex
import os
from typing import Dict, Any, List, Tuple, Optional
from langchain_core.messages import HumanMessage, AIMessage
from termagent.agents.base_agent import BaseAgent
from termagent.agents.shell_tool import ShellTool
from termagent.directory_context import get_directory_context, get_relevant_files_context

class RouterAgent(BaseAgent):
    """Router agent that breaks down tasks into steps."""
    
    def __init__(self, debug: bool = False, no_confirm: bool = False, llm_model: str = "gpt-3.5-turbo"):
        super().__init__("router_agent", debug, no_confirm)
        
        self.shell_tool = ShellTool(debug=debug, no_confirm=no_confirm)
        
        self._initialize_llm(llm_model)
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if there are messages to process."""
        messages = state.get("messages", [])
        if not messages:
            self._debug_print("No messages in state")
            return False
        
        # Get the latest user message
        latest_message = messages[-1]
        if isinstance(latest_message, HumanMessage):
            self._debug_print(f"Found user message to process")
            return True
        
        return False
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Break down tasks into steps."""
        messages = state.get("messages", [])
        latest_message = messages[-1]
        
        if isinstance(latest_message, HumanMessage):
            content = latest_message.content
            
            return self._break_down_task(state, content)
        
        self._debug_print("No HumanMessage found, returning current state")
        return state
    
    def _break_down_task(self, state: Dict[str, Any], task: str) -> Dict[str, Any]:
        # step 1 - Check if this is a known shell command that should be executed directly
        if self.shell_tool.is_shell_command(task):
            self._debug_print(f"Routing to direct shell execution")
            return self._create_direct_execution_state(state, task)
       
        # step 2 - Check if we have a successful task breakdown in history
        successful_breakdowns = state.get("successful_task_breakdowns", [])
        if successful_breakdowns:
            historical_breakdown = self._search_task_breakdown_cache(task, successful_breakdowns)
            if historical_breakdown:
                return self._create_task_breakdown_state(state, task, historical_breakdown)
       
        # Step 3 - Use LLM for intelligent task breakdown with shell tool integration
        breakdown = self._llm_task_breakdown_with_shell_tool(task)
        if breakdown:
            return self._create_task_breakdown_state(state, task, breakdown)

        self._debug_print("Unable to handle this command. No breakdown or direct execution available.")
        messages = state.get("messages", [])
        messages.append(AIMessage(content="❌ Sorry, I cannot handle this command."))
        return {**state, "messages": messages}

    def _llm_task_breakdown_with_shell_tool(self, task: str) -> List[Dict[str, str]]:
        """Enhanced LLM task breakdown that uses shell tool for discovery and validation."""
        # Get directory context for the LLM
        try:
            current_dir = os.getcwd()
            directory_context = get_directory_context(current_dir, max_depth=2, max_files_per_dir=15)
            relevant_files = get_relevant_files_context(current_dir)
            
            # Use shell tool to gather additional context
            shell_context = self._gather_shell_context()
            
            context_info = f"""📁 CURRENT WORKSPACE CONTEXT:
{directory_context}

{relevant_files}

🔧 SYSTEM CONTEXT:
{shell_context}

"""
        except Exception as e:
            context_info = f"⚠️  Could not get directory context: {e}\n\n"

        system_prompt = f"""You are a task analysis expert with access to shell tools. Your job is to break down a given task into the absolute MINIMAL number of logical steps.

{context_info}

RULES:
1. Use the FEWEST possible steps — combine actions when they can be done in a single command.
2. Each step must be ACTIONABLE (something a user can execute directly).
3. Avoid unnecessary "discovery" or exploratory steps unless required by the task.
4. If specific names/identifiers are given, use them directly (no guessing).
5. Reference actual files/directories from the provided workspace context when relevant.
6. When the output of one command is used in the next, prefer a single step with pipes (|).
7. When independent commands can be executed together, prefer a one-liner with `&&`.
8. Only separate steps if they are true sequential dependencies that cannot be merged.
9. Before returning the breakdown, perform a META-CHECK:  
   - Verify that no two steps can be combined into a one-liner with `|` or `&&`.  
   - Verify that each step is absolutely necessary.  
   - If possible, reduce the total number of steps further.
10. Use the shell tool context to validate your suggestions and ensure they're appropriate for the current system.

OUTPUT FORMAT:
Return the breakdown as a JSON array of objects.  
Each object must have:
- `"step"`: sequential number starting at 1  
- `"description"`: clear explanation of the action  
- `"command"`: the exact command to run  

EXAMPLES:

Task: "stop docker container nginxx"  
Breakdown: [
  {{
    "step": 1,
    "description": "Stop the Docker container named nginxx",
    "command": "docker stop nginxx"
  }}
]

Task: "create a new git branch called feature-x"  
Breakdown: [
  {{
    "step": 1,
    "description": "Create and switch to new git branch feature-x",
    "command": "git checkout -b feature-x"
  }}
]

Task: "check how many python files are in this directory"  
Breakdown: [
  {{
    "step": 1,
    "description": "Count Python files in current directory",
    "command": "ls *.py | wc -l"
  }}
]

Task: "what is the largest file in directory?"  
Breakdown: [
  {{
    "step": 1,
    "description": "List files by size and return the largest one",
    "command": "ls -lS | head -n 1"
  }}
]"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Break down this task: {task}"}
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Try to extract JSON from the response
            import json
            # Look for JSON content between ```json and ``` markers
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON array in the content
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content
            
            breakdown = json.loads(json_str)
            
            # Validate the breakdown using shell tool
            validated_breakdown = self._validate_breakdown_with_shell_tool(breakdown, task)
            
            self._debug_print(f"LLM breakdown successful: {len(validated_breakdown)} steps")
            return validated_breakdown
            
        except Exception as e:
            self._debug_print(f"LLM breakdown failed: {e}")
            return []
    
    def _search_task_breakdown_cache(self, task: str, cache: List[Dict[str, Any]]) -> Optional[List[Dict[str, str]]]:
        if not cache:
            return None
        
        task_lower = task.lower().strip()
        
        # First, try exact command matches
        for breakdown in cache:
            command = breakdown.get("command", "").lower().strip()
            if command == task_lower:
                self._debug_print(f"Found exact command match in cache: {command}")
                return breakdown.get("task_breakdown")
               
        return None

    def _create_task_breakdown_state(self, state: Dict[str, Any], task: str, breakdown: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create state with task breakdown information."""
        messages = state.get("messages", [])
        
        # Create breakdown message
        breakdown_text = f"📋 Task Breakdown for: {task}\n\n"
        
        # Add summary of what will be accomplished
        if len(breakdown) == 1:
            breakdown_text += f"🎯 This task will be completed in 1 step:\n\n"
        else:
            breakdown_text += f"🎯 This task will be completed in {len(breakdown)} steps:\n\n"
        
        for step_info in breakdown:
            breakdown_text += f"[{step_info['step']}] -- {step_info['description']}\n"
            breakdown_text += f"  Command: {step_info['command']}\n\n"
        
        messages.append(AIMessage(content=breakdown_text))
        
        # Debug output: Print task steps
        if self.debug:
            self._debug_print(f"📋 Task Breakdown for: {task}")
            for step_info in breakdown:
                self._debug_print(f"  [{step_info['step']}] -- {step_info['description']}")
                self._debug_print(f"    Command: {step_info['command']}")
            self._debug_print(f"Total steps: {len(breakdown)}")
        
        # Add breakdown to state
        return {
            **state,
            "messages": messages,
            "routed_to": "task_breakdown",
            "last_command": task,
            "task_breakdown": breakdown,
            "current_step": 0,
            "total_steps": len(breakdown)
        }
    
    def _create_direct_execution_state(self, state: Dict[str, Any], task: str) -> Dict[str, Any]:
        """Create state for direct shell command execution."""
        messages = state.get("messages", [])
        
        # Create message indicating direct execution
        execution_text = f"⚡ Direct execution: {task}\n"
        execution_text += "This is a known shell command that will be executed directly."
        messages.append(AIMessage(content=execution_text))
        
        # Add to state
        return {
            **state,
            "messages": messages,
            "routed_to": "handle_direct_execution",
            "last_command": task
        }
    
    def _gather_shell_context(self) -> str:
        """Gather system context using shell tool for better LLM decision making."""
        context_parts = []
        
        try:
            # Get basic system info
            sys_info = self.shell_tool.get_system_info()
            if sys_info["success"]:
                info = sys_info["system_info"]
                context_parts.append(f"OS: {info.get('os', 'unknown')}")
                context_parts.append(f"User: {info.get('user', 'unknown')}")
                context_parts.append(f"Shell: {info.get('shell', 'unknown')}")
            
            # Get current working directory
            cwd = self.shell_tool.get_working_directory()
            context_parts.append(f"Current Directory: {cwd}")
            
            # Check if we're in a git repository
            git_check = self.shell_tool.execute("git rev-parse --git-dir 2>/dev/null || echo 'not_git'")
            if git_check["success"] and "not_git" not in git_check["output"]:
                context_parts.append("Git Repository: Yes")
                # Get git status
                git_status = self.shell_tool.execute("git status --porcelain")
                if git_status["success"]:
                    context_parts.append(f"Git Status: {git_status['output'] or 'clean'}")
            else:
                context_parts.append("Git Repository: No")
            
            # Check if we're in a Python project
            pyproject_check = self.shell_tool.check_file_exists("pyproject.toml")
            if pyproject_check["success"] and "exists" in pyproject_check["output"]:
                context_parts.append("Python Project: Yes (pyproject.toml found)")
            
            # Check for common development files
            for file in ["package.json", "requirements.txt", "Makefile", "Dockerfile"]:
                exists_check = self.shell_tool.check_file_exists(file)
                if exists_check["success"] and "exists" in exists_check["output"]:
                    context_parts.append(f"Development File: {file}")
            
        except Exception as e:
            self._debug_print(f"Error gathering shell context: {e}")
            context_parts.append(f"Context gathering error: {e}")
        
        return "\n".join(context_parts)
    
    def _validate_breakdown_with_shell_tool(self, breakdown: List[Dict[str, str]], original_task: str) -> List[Dict[str, str]]:
        """Validate the LLM breakdown using shell tool to ensure commands are appropriate."""
        if not breakdown:
            return breakdown
        
        validated_breakdown = []
        
        for step in breakdown:
            command = step.get("command", "")
            if not command:
                continue
            
            # Validate command safety
            safety_check = self.shell_tool.validate_command(command)
            if not safety_check["safe"]:
                self._debug_print(f"Command safety check failed: {command}")
                # Try to get a safer alternative from LLM
                safer_command = self._get_safer_alternative(command, step.get("description", ""))
                if safer_command:
                    step["command"] = safer_command
                    self._debug_print(f"Replaced with safer command: {safer_command}")
            
            # Check if command is appropriate for current context
            context_check = self._validate_command_context(command, step.get("description", ""))
            if not context_check["valid"]:
                self._debug_print(f"Context validation failed: {command}")
                # Try to get a more appropriate alternative
                better_command = self._get_context_appropriate_alternative(command, step.get("description", ""), context_check["issues"])
                if better_command:
                    step["command"] = better_command
                    self._debug_print(f"Replaced with context-appropriate command: {better_command}")
            
            validated_breakdown.append(step)
        
        return validated_breakdown
    
    def _get_safer_alternative(self, dangerous_command: str, description: str) -> str:
        """Get a safer alternative command from LLM."""
        try:
            system_prompt = """You are a command safety expert. Given a potentially dangerous command, suggest a safer alternative.

Your task is to:
1. Identify why the command is dangerous
2. Suggest a safer alternative that accomplishes the same goal
3. Ensure the alternative is safe and appropriate

IMPORTANT:
- Return ONLY the safer command, nothing else
- Make sure the command is valid and safe
- Consider the original description when suggesting alternatives
- If no safe alternative exists, return an empty string"""

            user_message = f"""Dangerous Command: {dangerous_command}
Description: {description}

Suggest a safer alternative:"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = self.llm.invoke(messages)
            alternative = response.content.strip()
            
            # Clean up the response
            if alternative and alternative != dangerous_command:
                alternative = alternative.replace('```', '').replace('`', '').strip()
                return alternative
            
        except Exception as e:
            self._debug_print(f"Error getting safer alternative: {e}")
        
        return ""
    
    def _validate_command_context(self, command: str, description: str) -> Dict[str, Any]:
        """Validate if a command is appropriate for the current context."""
        issues = []
        
        try:
            # Check if we're trying to use git commands outside a git repo
            if command.startswith("git ") and not self._is_in_git_repo():
                issues.append("Git command used outside git repository")
            
            # Check if we're trying to use docker commands without docker
            if command.startswith("docker ") and not self._has_docker():
                issues.append("Docker command used without docker available")
            
            # Check if we're trying to access files that don't exist
            file_paths = self._extract_file_paths(command)
            for path in file_paths:
                if not self.shell_tool.check_file_exists(path)["success"]:
                    issues.append(f"File/directory not found: {path}")
            
        except Exception as e:
            issues.append(f"Validation error: {e}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _is_in_git_repo(self) -> bool:
        """Check if we're in a git repository."""
        try:
            result = self.shell_tool.execute("git rev-parse --git-dir 2>/dev/null")
            return result["success"] and "not_git" not in result["output"]
        except:
            return False
    
    def _has_docker(self) -> bool:
        """Check if docker is available."""
        try:
            result = self.shell_tool.execute("docker --version")
            return result["success"]
        except:
            return False
    
    def _extract_file_paths(self, command: str) -> List[str]:
        """Extract potential file paths from a command."""
        # Simple extraction - could be enhanced with more sophisticated parsing
        paths = []
        parts = command.split()
        
        for part in parts:
            if part.startswith("./") or part.startswith("/") or (not part.startswith("-") and "." in part):
                # Remove quotes and common command suffixes
                clean_part = part.strip("'\"")
                if clean_part and not clean_part.startswith("-"):
                    paths.append(clean_part)
        
        return paths
    
    def _get_context_appropriate_alternative(self, command: str, description: str, issues: List[str]) -> str:
        """Get a context-appropriate alternative command from LLM."""
        try:
            system_prompt = """You are a command context expert. Given a command that's inappropriate for the current context, suggest a better alternative.

Your task is to:
1. Understand why the command is inappropriate
2. Suggest an alternative that works in the current context
3. Ensure the alternative accomplishes the same goal

IMPORTANT:
- Return ONLY the better command, nothing else
- Make sure the command is valid and appropriate for the context
- Consider the original description when suggesting alternatives
- If no better alternative exists, return an empty string"""

            issues_text = "\n".join([f"- {issue}" for issue in issues])
            user_message = f"""Inappropriate Command: {command}
Description: {description}
Context Issues:
{issues_text}

Suggest a context-appropriate alternative:"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = self.llm.invoke(messages)
            alternative = response.content.strip()
            
            # Clean up the response
            if alternative and alternative != command:
                alternative = alternative.replace('```', '').replace('`', '').strip()
                return alternative
            
        except Exception as e:
            self._debug_print(f"Error getting context-appropriate alternative: {e}")
        
        return ""