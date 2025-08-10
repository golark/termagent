import subprocess
import re
import os
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from agents.base_agent import BaseAgent
import sys
import tty
import termios

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class GitAgent(BaseAgent):
    """Git agent that handles git-specific commands and operations with LLM interface."""
    
    def __init__(self, llm_model: str = "gpt-3.5-turbo", debug: bool = False):
        super().__init__("git_agent")
        self.debug = debug
        
        # Initialize LLM if available and API key is set
        self.llm = None
        if LLM_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(model=llm_model, temperature=0)
                self._debug_print(f"✅ LLM initialized with model: {llm_model}")
            except Exception as e:
                self._debug_print(f"⚠️ LLM initialization failed: {e}")
        else:
            self._debug_print("⚠️ LLM not available - using fallback parsing")
        
        # System prompt for LLM
        self.system_prompt = """Convert natural language to Git commands. Return only the command, nothing else.

Examples:
- "check status" → "git status"
- "add all files" → "git add ."
- "commit with message update" → "git commit -m \"update\""
- "push to remote" → "git push"
- "commit and push" → "git add . && git commit -m \"Auto-commit\" && git push"

Convert this request to a Git command:"""
        
        self._debug_print("🤖 GitAgent initialized successfully")

    def _debug_print(self, message: str):
        """Print debug message only if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] GitAgent: {message}")
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this agent should handle the current input."""
        # This agent is called via MCP from the router
        should_handle = state.get("routed_to") == "git_agent"
        self._debug_print(f"should_handle: {should_handle} (routed_to: {state.get('routed_to')})")
        return should_handle
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process git commands with LLM support for natural language conversion."""
        command = state.get("last_command", "")
        self._debug_print(f"Processing command: {command}")
        
        if not command:
            self._debug_print("No command provided, returning current state")
            return state
        
        try:
            # First, try to convert natural language to git command using LLM
            self._debug_print("Converting natural language to git command...")
            converted_command = self._convert_natural_language_to_git(command)
            self._debug_print(f"Converted command: {converted_command}")
            
            # Check if this is a compound command with &&
            if "&&" in converted_command:
                self._debug_print("Detected compound command, processing...")
                return self._process_compound_command(state, converted_command)
            
            # Ask for confirmation before executing
            self._debug_print("Requesting user confirmation...")
            if not self._confirm_command_execution(converted_command):
                self._debug_print("Command cancelled by user")
                return self._add_cancelled_message(state, converted_command)
            
            # Execute the git command directly
            self._debug_print(f"Executing command: {converted_command}")
            result = self._execute_git_command(converted_command)
            self._debug_print(f"Command execution result: {result[:100]}...")
            return self._add_success_message(state, f"Executed: {converted_command}\nResult: {result}")
                
        except Exception as e:
            self._debug_print(f"Error in process: {str(e)}")
            return self._add_error_message(state, str(e))
    
    def _confirm_command_execution(self, command: str) -> bool:
        """Ask for user confirmation before executing a git command."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print("↵ to confirm, 'n' to skip")
                print(f"> {command}", end="")
                response = input().strip().lower()
                
                if response in ['n', 'no', 'cancel', 'skip']:
                    print("\n❌ Command cancelled by user")
                    self._debug_print("Command cancelled by user input")
                    return False
                else:
                    self._debug_print(f"User response: '{response}' (will proceed: True)")
                    return True
                    
            except KeyboardInterrupt:
                print("\n❌ Command cancelled by user")
                self._debug_print("Command cancelled by keyboard interrupt")
                return False
            except EOFError:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"\n⚠️  Input error, retrying... ({retry_count}/{max_retries})")
                    self._debug_print(f"EOFError occurred, retrying {retry_count}/{max_retries}")
                else:
                    print("\n❌ Command cancelled (too many input errors)")
                    self._debug_print("Command cancelled due to repeated EOFError")
                    return False
    
    def _get_single_char(self) -> str:
        """Get a single character input from the user."""
        try:
            # Save terminal settings
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            try:
                # Set terminal to raw mode
                tty.setraw(sys.stdin.fileno())
                
                # Read a single character
                ch = sys.stdin.read(1)
                
                # If it's the start of an escape sequence, read more
                if ch == '\x1b':
                    # Read additional characters to complete escape sequence
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        # This is an arrow key or other escape sequence, not just escape
                        ch3 = sys.stdin.read(1)
                        # Return a different character to indicate it's not escape
                        return 'arrow'
                    else:
                        # Just escape key
                        return '\x1b'
                
                return ch
                
            finally:
                # Restore terminal settings
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
        except Exception as e:
            # Fallback to regular input if raw mode fails
            self._debug_print(f"Raw mode failed: {e}, using fallback")
            return input().strip()
    
    def _convert_natural_language_to_git(self, natural_language: str) -> str:
        """Convert natural language to git command using LLM."""
        try:
            # If LLM is not available, use fallback parsing
            if not self.llm:
                self._debug_print("Using fallback parsing (LLM not available)")
                return self._fallback_parse(natural_language)
            
            # Create messages for LLM
            self._debug_print("Using LLM for natural language conversion")
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=natural_language)
            ]
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Extract the git command from the response
            git_command = response.content.strip()
            self._debug_print(f"LLM response: {git_command}")
            
            # Clean up the response (remove quotes, extra spaces, etc.)
            git_command = re.sub(r'^["\']|["\']$', '', git_command)  # Remove surrounding quotes
            git_command = re.sub(r'\s+', ' ', git_command)  # Normalize spaces
            self._debug_print(f"Cleaned command: {git_command}")
            
            return git_command
            
        except Exception as e:
            # If LLM fails, try to fall back to basic parsing
            self._debug_print(f"LLM conversion failed: {e}, using fallback parsing")
            return self._fallback_parse(natural_language)
    
    def _fallback_parse(self, natural_language: str) -> str:
        """Fallback parsing for natural language when LLM is not available."""
        self._debug_print(f"Fallback parsing: {natural_language}")
        text = natural_language.lower()
        
        # Basic keyword-based conversion
        if "status" in text:
            result = "git status"
        elif "add" in text or "stage" in text:
            result = "git add ."
        elif "commit" in text:
            # Try to extract commit message
            if "message" in text:
                # Extract message after "message" or "with message"
                message_match = re.search(r'(?:message|with message)\s+(.+)', text)
                if message_match:
                    message = message_match.group(1).strip()
                    result = f'git commit -m "{message}"'
                else:
                    result = 'git commit -m "Auto-commit"'
            else:
                result = 'git commit -m "Auto-commit"'
        elif "push" in text:
            result = "git push"
        elif "pull" in text:
            result = "git pull"
        elif "log" in text or "history" in text:
            result = "git log"
        elif "branch" in text:
            result = "git branch"
        elif "checkout" in text or "switch" in text:
            # Try to extract branch name
            branch_match = re.search(r'(?:to|branch|checkout)\s+(\w+)', text)
            if branch_match:
                branch = branch_match.group(1)
                result = f"git checkout {branch}"
            else:
                result = "git checkout"
        elif "merge" in text:
            result = "git merge"
        elif "diff" in text:
            result = "git diff"
        else:
            # If we can't parse it, just add git prefix
            result = f"git {natural_language}"
        
        self._debug_print(f"Fallback parse result: {result}")
        return result
    
    def _process_compound_command(self, state: Dict[str, Any], command: str) -> Dict[str, Any]:
        """Process compound commands with && operators."""
        self._debug_print(f"Processing compound command: {command}")
        # Split the command by &&
        commands = [cmd.strip() for cmd in command.split("&&")]
        self._debug_print(f"Split into {len(commands)} commands: {commands}")
        
        results = []
        
        for i, cmd in enumerate(commands, 1):
            if not cmd:
                self._debug_print(f"Skipping empty command at position {i}")
                continue
            
            try:
                self._debug_print(f"Executing command {i}/{len(commands)}: {cmd}")
                # Execute the git command directly
                result = self._execute_git_command(cmd)
                results.append(f"{cmd}: {result}")
                self._debug_print(f"Command {i} result: {result[:100]}...")
                    
            except Exception as e:
                error_msg = f"{cmd}: Error - {str(e)}"
                results.append(error_msg)
                self._debug_print(f"Command {i} failed: {str(e)}")
        
        # Combine all results
        combined_result = " | ".join(results)
        self._debug_print(f"Combined result: {combined_result[:200]}...")
        return self._add_success_message(state, combined_result)
    
    def _execute_git_command(self, command: str) -> str:
        """Execute a git command directly."""
        self._debug_print(f"Executing git command: {command}")
        try:
            # Parse the command to extract git and its arguments
            if command.lower().startswith("git "):
                # Remove "git" prefix and split arguments
                args = command[4:].split()
                git_args = ["git"] + args
                self._debug_print(f"Parsed git arguments: {git_args}")
            else:
                # If no "git" prefix, add it
                args = command.split()
                git_args = ["git"] + args
                self._debug_print(f"Added git prefix, arguments: {git_args}")
            
            # Execute the command
            self._debug_print(f"Running subprocess: {git_args}")
            result = subprocess.run(
                git_args,
                capture_output=True,
                text=True,
                cwd="."
            )
            
            self._debug_print(f"Subprocess return code: {result.returncode}")
            if result.returncode == 0:
                output = result.stdout.strip() if result.stdout.strip() else "Command executed successfully"
                self._debug_print(f"Command successful, output: {output[:100]}...")
                return output
            else:
                error_msg = result.stderr.strip() if result.stderr.strip() else "Unknown error"
                self._debug_print(f"Command failed, error: {error_msg[:100]}...")
                return f"Error: {error_msg}"
                
        except Exception as e:
            error_msg = f"Failed to execute git command: {str(e)}"
            self._debug_print(f"Exception during execution: {str(e)}")
            return error_msg
    
    def _add_success_message(self, state: Dict[str, Any], result: str) -> Dict[str, Any]:
        """Add a success message to the state."""
        self._debug_print(f"Adding success message: {result[:100]}...")
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Git command executed successfully: {result}"))
        
        return {
            **state,
            "messages": messages,
            "git_result": result
        }
    
    def _add_error_message(self, state: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Add an error message to the state."""
        self._debug_print(f"Adding error message: {error}")
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Git command failed: {error}"))
        
        return {
            **state,
            "messages": messages,
            "error": error
        }

    def _add_cancelled_message(self, state: Dict[str, Any], command: str) -> Dict[str, Any]:
        """Add a cancelled message to the state."""
        self._debug_print(f"Adding cancelled message for command: {command}")
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Command cancelled by user: {command}"))
        
        return {
            **state,
            "messages": messages,
            "cancelled": True
        }
