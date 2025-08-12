import os
import subprocess
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage
from termagent.agents.base_agent import BaseAgent
import re

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class FileAgent(BaseAgent):
    """Agent for handling file operations using natural language."""
    
    def __init__(self, debug: bool = False, llm_model: str = "gpt-3.5-turbo", no_confirm: bool = False):
        super().__init__("file_agent", debug, no_confirm)
        self._initialize_llm(llm_model)
        
        # Planning prompt for minimal file operations
        self.planning_prompt = """Create a minimal, concise file operation plan with only essential steps.

IMPORTANT: Keep steps minimal and focused. Only include necessary actions.

Format: One action per line, starting with:
- Execute: for commands to run
- Action: for specific actions

Keep each line short and direct. Focus only on the core file operation.

Example format:
Execute: ls -la
Action: Create backup directory
Execute: cp source.txt backup/

CRITICAL: Be minimal. Only include essential steps needed to complete the task.

Now create a minimal plan for this task:"""
        
        # Common file operation patterns and their direct commands
        self.common_patterns = {
            r'^list\s+files?$': 'ls',
            r'^list\s+contents?$': 'ls',
            r'^show\s+files?$': 'ls',
            r'^show\s+contents?$': 'ls',
            r'^what\s+files?$': 'ls',
            r'^what\s+contents?$': 'ls',
            r'^dir$': 'ls',
            r'^ls$': 'ls',
            r'^pwd$': 'pwd',
            r'^current\s+directory$': 'pwd',
            r'^show\s+current\s+directory$': 'pwd',
            r'^where\s+am\s+i$': 'pwd',
            r'^working\s+directory$': 'pwd',
            r'^create\s+file\s+([a-zA-Z0-9._-]+)$': 'touch',
            r'^make\s+file\s+([a-zA-Z0-9._-]+)$': 'touch',
            r'^new\s+file\s+([a-zA-Z0-9._-]+)$': 'touch',
            r'^create\s+directory\s+(.+)$': 'mkdir',
            r'^make\s+directory\s+(.+)$': 'mkdir',
            r'^new\s+directory\s+(.+)$': 'mkdir',
            r'^mkdir\s+(.+)$': 'mkdir',
            r'^remove\s+file\s+(.+)$': 'rm',
            r'^delete\s+file\s+(.+)$': 'rm',
            r'^rm\s+(.+)$': 'rm',
            r'^remove\s+directory\s+(.+)$': 'rmdir',
            r'^delete\s+directory\s+(.+)$': 'rmdir',
            r'^rmdir\s+(.+)$': 'rmdir',
            r'^copy\s+(.+)\s+to\s+(.+)$': 'cp',
            r'^cp\s+(.+)\s+(.+)$': 'cp',
            r'^move\s+(.+)\s+to\s+(.+)$': 'mv',
            r'^mv\s+(.+)\s+(.+)$': 'mv',
            r'^rename\s+(.+)\s+to\s+(.+)$': 'mv',
            r'^find\s+(.+)$': 'find',
            r'^search\s+for\s+(.+)$': 'find',
            r'^grep\s+(.+)$': 'grep',
            r'^search\s+in\s+(.+)$': 'grep',
            # Common variations
            r'^show\s+python\s+files$': 'find . -name "*.py"',
            r'^find\s+python\s+files$': 'find . -name "*.py"',
            r'^list\s+python\s+files$': 'find . -name "*.py"',
            r'^show\s+text\s+files$': 'find . -name "*.txt"',
            r'^find\s+text\s+files$': 'find . -name "*.txt"',
            r'^list\s+text\s+files$': 'find . -name "*.txt"',
            r'^show\s+hidden\s+files$': 'ls -la',
            r'^list\s+hidden\s+files$': 'ls -la',
            r'^show\s+all\s+files$': 'ls -la',
            r'^list\s+all\s+files$': 'ls -la',
            # File editing patterns
            r'^edit\s+([a-zA-Z0-9._/-]+)$': 'vim',
            r'^vim\s+([a-zA-Z0-9._/-]+)$': 'vim',
            r'^nano\s+([a-zA-Z0-9._/-]+)$': 'nano',
            r'^open\s+([a-zA-Z0-9._/-]+)$': 'vim',
            r'^edit\s+file\s+([a-zA-Z0-9._/-]+)$': 'vim',
            r'^open\s+file\s+([a-zA-Z0-9._/-]+)$': 'vim',
            r'^edit\s+([a-zA-Z0-9._/-]+)\s+with\s+vim$': 'vim',
            r'^edit\s+([a-zA-Z0-9._/-]+)\s+with\s+nano$': 'nano',
        }
        
        # Compile patterns for efficient matching
        self.compiled_patterns = {re.compile(pattern, re.IGNORECASE): command 
                                 for pattern, command in self.common_patterns.items()}
        
        # System prompt for LLM fallback
        self.system_prompt = """You are a file operation assistant. Convert natural language file operations to zsh-compatible shell commands.
                
        Examples:
        - "list files" → "ls"
        - "create a new file called test.txt" → "touch test.txt"
        - "move file.txt to backup/" → "mv file.txt backup/"
        - "copy source.txt to destination.txt" → "cp source.txt destination.txt"
        - "delete old_file.txt" → "rm old_file.txt"
        - "find all .txt files" → "find . -name '*.txt'"
        - "search for 'hello' in files" → "grep -r 'hello' ."
        - "count files in directory" → "ls -1 | wc -l"
        - "list only directories" → "ls -d */"
        - "show file sizes" → "ls -lh"
        - "edit file.txt" → "vim file.txt"
        - "open file.txt with vim" → "vim file.txt"
        - "edit file.txt with nano" → "nano file.txt"
        - "open file.txt" → "vim file.txt"
        
        ZSH COMPATIBILITY NOTES:
        - Use single quotes for file paths with spaces: 'file with spaces.txt'
        - Use double quotes for variables: "echo $HOME"
        - Escape special characters properly: echo "Hello $USER"
        - Use zsh-compatible globbing: ls *.txt, not ls "*.txt"
        
        Return only the shell command, nothing else."""
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this agent should handle the current input."""
        should_handle = state.get("routed_to") == "file_agent"
        return should_handle
    
    
    def _create_task_plan(self, task: str) -> str:
        """Create a detailed plan for complex file operations."""
        try:
            # Use LLM to create a structured plan
            plan_prompt = f"Task: {task}\n\n{self.planning_prompt}"
            plan = self._convert_natural_language(task, self.planning_prompt)
            
            if not plan:
                return "⚠️ Failed to create plan - proceeding with direct execution"
            
            return plan
            
        except Exception as e:
            self._debug_print(f"Error creating plan: {str(e)}")
            return f"⚠️ Plan creation failed: {str(e)} - proceeding with direct execution"
    
    def _execute_planned_tasks(self, plan: str, original_task: str) -> str:
        """Execute file operations according to the created plan."""
        
        # Parse the plan and execute step by step
        lines = plan.split('\n')
        results = []
        step_count = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
                
            # Look for actionable items (minimal format)
            if any(marker in line.lower() for marker in ['action:', 'execute:']):
                step_count += 1
                
                # Extract the command from the line
                command = self._extract_command_from_plan_line(line)
                if command:
                    try:
                        result = self._execute_shell_command(command)
                        self._debug_print(f"{step_count} | Command: {command} | result: {result}")
                        results.append(f"Step {step_count}: ✅ {result}")
                    except Exception as e:
                        error_msg = f"Command failed: {str(e)}"
                        self._debug_print(error_msg)
                        results.append(f"Step {step_count}: ❌ Failed - {str(e)}")
                else:
                    # For non-command lines, just note them
                    self._debug_print(f"No command to execute for step {step_count}: {line}")
                    results.append(f"Step {step_count}: ℹ️ {line}")
        
        if not results:
            return f"⚠️ No actionable steps found in plan. Original task: {original_task}"
        
        return "\n".join(results)
    
    def _extract_command_from_plan_line(self, line: str) -> str:
        """Extract shell command from a plan line."""
        # Remove common markers
        markers = ['Action:', 'Execute:']
        cleaned_line = line
        
        for marker in markers:
            if marker.lower() in line.lower():
                # Find the position of the marker and extract everything after it
                marker_pos = line.lower().find(marker.lower())
                if marker_pos != -1:
                    cleaned_line = line[marker_pos + len(marker):].strip()
                    break
        
        # If the cleaned line contains a shell command, extract it
        if cleaned_line:
            # Look for common shell commands
            shell_commands = ['ls', 'pwd', 'touch', 'mkdir', 'rm', 'rmdir', 'cp', 'mv', 'find', 'grep', 'vim', 'nano', 'cat', 'head', 'tail', 'wc', 'du', 'df']
            
            for cmd in shell_commands:
                if cmd in cleaned_line:
                    # Extract the command and its arguments
                    cmd_start = cleaned_line.find(cmd)
                    if cmd_start != -1:
                        command_part = cleaned_line[cmd_start:].strip()
                        # Clean up any extra text after the command
                        if ' ' in command_part:
                            # Find the end of the command (before any explanatory text)
                            parts = command_part.split(' ')
                            if len(parts) >= 1:
                                return ' '.join(parts)
                        else:
                            return command_part
            
            # If no specific command found, return the cleaned line as potential command
            return cleaned_line
        
        return ""
    
    def _normalize_plan(self, plan: str) -> str:
        """Normalize the plan to ensure proper line breaks."""
        # If the plan is all on one line, try to split it intelligently
        if '\n' not in plan or plan.count('\n') < 2:
            self._debug_print("Plan appears to be on one line, attempting to normalize...")
            
            # Split by common markers
            markers = ['Action:', 'Execute:']
            normalized_lines = []
            
            for marker in markers:
                if marker in plan:
                    # Split by this marker and keep the marker
                    parts = plan.split(marker)
                    for i, part in enumerate(parts):
                        if i == 0:  # First part doesn't have the marker
                            if part.strip():
                                normalized_lines.append(part.strip())
                        else:  # Subsequent parts have the marker
                            if part.strip():
                                normalized_lines.append(f"{marker}{part.strip()}")
            
            if normalized_lines:
                return '\n'.join(normalized_lines)
        
        return plan
    
    def _validate_plan(self, plan: str) -> bool:
        """Validate that the plan contains actionable steps."""
        if not plan:
            return False
        
        lines = plan.split('\n')
        actionable_lines = 0
        
        for line in lines:
            line = line.strip()
            if line and any(marker in line.lower() for marker in ['action:', 'execute:']):
                actionable_lines += 1
        
        return actionable_lines >= 1
    
    def _format_plan_for_display(self, plan: str) -> str:
        """Format the plan for better display to the user."""
        if not plan:
            return "No plan available"
        
        lines = plan.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Format different types of lines
            if line.lower().startswith('action:'):
                formatted_lines.append(f"⚡ {line}")
            elif line.lower().startswith('execute:'):
                formatted_lines.append(f"🚀 {line}")
            else:
                formatted_lines.append(f"ℹ️ {line}")
        
        return '\n'.join(formatted_lines)
    
    def _parse_common_pattern(self, natural_language: str) -> tuple[str, list]:
        """Parse natural language input using common patterns and return command and arguments."""
        for pattern, command in self.compiled_patterns.items():
            match = pattern.match(natural_language.strip())
            if match:
                args = [arg.strip() for arg in match.groups() if arg and arg.strip()]
                self._debug_print(f"Pattern match | {natural_language} -> {command} args:{args}")
                
                # For complex queries, prefer LLM over simple pattern matching
                if command == 'find' and len(args) > 0 and len(args[0]) > 20:
                    self._debug_print(f" Complex find query detected, using LLM instead")
                    return "", []
                if command == 'grep' and len(args) > 0 and len(args[0]) > 20:
                    self._debug_print(f" Complex grep query detected, using LLM instead")
                    return "", []
                
                return command, args
        
        return "", []
    
    def _build_command(self, command: str, args: list) -> str:
        """Build the actual shell command from parsed components."""
        if not command:
            return ""
        
        if command in ['ls', 'pwd']:
            return command
        elif command == 'touch' and args:
            # Ensure proper quoting for zsh compatibility
            return f"touch '{args[0]}'"
        elif command == 'mkdir' and args:
            return f"mkdir -p '{args[0]}'"
        elif command == 'rm' and args:
            return f"rm '{args[0]}'"
        elif command == 'rmdir' and args:
            return f"rmdir '{args[0]}'"
        elif command == 'cp' and len(args) >= 2:
            return f"cp '{args[0]}' '{args[1]}'"
        elif command == 'mv' and len(args) >= 2:
            return f"mv '{args[0]}' '{args[1]}'"
        elif command == 'find' and args:
            return f"find . -name '{args[0]}'"
        elif command == 'grep' and args:
            return f"grep -r '{args[0]}' ."
        elif command == 'vim' and args:
            return f"vim '{args[0]}'"
        elif command == 'nano' and args:
            return f"nano '{args[0]}'"
        else:
            return command
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process file operations with planning for all tasks."""
        command = state.get("last_command", "")
        self._debug_print(f" Processing command: {command}")
        
        if not command:
            return state
        
        try:
            plan = self._create_task_plan(command)
            
            plan = self._normalize_plan(plan)
            self._debug_print(f"plan: {plan}")
            
            # Validate the plan
            if not self._validate_plan(plan):
                self._debug_print(" Plan validation failed - falling back to direct execution")
                # Fall back to direct execution if plan is invalid
                parsed_command, args = self._parse_common_pattern(command)
                if parsed_command:
                    shell_command = self._build_command(parsed_command, args)
                else:
                    shell_command = self._convert_natural_language(command, self.system_prompt)
                
                if shell_command:
                    if not self._confirm_operation_execution(shell_command, "operation"):
                        return self._add_message(state, f"Operation cancelled: {shell_command}", "cancelled")
                    
                    result = self._execute_shell_command(shell_command)
                    state = self._add_message(state, result, "success", file_result=result)
                    
                    # Check if we should continue with task breakdown
                    if state.get("task_breakdown"):
                        return self._continue_task_breakdown(state)
                    
                    return state
                else:
                    return self._add_message(state, "❌ Failed to convert command", "error")
            
            # Format the plan for better display
            formatted_plan = self._format_plan_for_display(plan)
            
            # Show the plan to the user
            plan_message = f"📋 **Execution Plan for: {command}**\n\n{formatted_plan}\n\nProceed with plan execution?"
            state = self._add_message(state, plan_message, "info")
            
            # Ask for confirmation to execute the plan
            if not self._confirm_operation_execution(f"Execute planned file operations for: {command}", "plan"):
                return self._add_message(state, f"⏹️ Plan execution cancelled for: {command}", "cancelled")
            
            # Execute the planned tasks
            result = self._execute_planned_tasks(plan, command)
            state = self._add_message(state, result, "success", file_result=result)
            
            # Check if we should continue with task breakdown
            if state.get("task_breakdown"):
                return self._continue_task_breakdown(state)
            
            return state
            
        except Exception as e:
            if self.debug:
                self._debug_print(f" Error in process: {str(e)}")
            return self._add_message(state, f"❌ File operation failed: {str(e)}", "error")
    

    
    def _convert_natural_language_to_operation(self, natural_language: str) -> str:
        """Convert natural language to file operation using LLM."""
        return self._convert_natural_language(natural_language, self.system_prompt)
    

    
    def _execute_file_operation(self, operation: str) -> str:
        """Execute a shell command for file operations."""
        try:
            # Execute the command using subprocess
            result = subprocess.run(
                operation,
                shell=True,
                capture_output=True,
                text=True,
                cwd="."
            )
            
            if result.returncode == 0:
                output = result.stdout.strip() if result.stdout.strip() else "Command executed successfully"
                return output
            else:
                error_msg = result.stderr.strip() if result.stderr.strip() else "Unknown error"
                if self.debug:
                    self._debug_print(f"Command failed, error: {error_msg[:100]}...")
                return f"Error: {error_msg}"
                
        except Exception as e:
            error_msg = f"Failed to execute shell command: {str(e)}"
            if self.debug:
                self._debug_print(f"Exception during execution: {str(e)}")
            return error_msg
    

    

    

    

    

    

    
