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
    
    def _parse_common_pattern(self, natural_language: str) -> tuple[str, list]:
        """Parse natural language input using common patterns and return command and arguments."""
        for pattern, command in self.compiled_patterns.items():
            match = pattern.match(natural_language.strip())
            if match:
                args = [arg.strip() for arg in match.groups() if arg and arg.strip()]
                self._debug_print(f"Pattern match | {natural_language} -> {command} args:{args}")
                
                # For complex queries, prefer LLM over simple pattern matching
                if command == 'find' and len(args) > 0 and len(args[0]) > 20:
                    self._debug_print(f"Complex find query detected, using LLM instead")
                    return "", []
                if command == 'grep' and len(args) > 0 and len(args[0]) > 20:
                    self._debug_print(f"Complex grep query detected, using LLM instead")
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
        """Process file operations using pattern matching first, then LLM fallback."""
        command = state.get("last_command", "")
        self._debug_print(f"Processing command: {command}")
        
        if not command:
            return state
        
        try:
            # First try to match common patterns
            parsed_command, args = self._parse_common_pattern(command)
            
            if parsed_command:
                # Use common pattern match
                shell_command = self._build_command(parsed_command, args)
            else:
                # Fallback to LLM conversion
                converted_operation = self._convert_natural_language(command, self.system_prompt)
                shell_command = converted_operation
            
           
            if not self._confirm_operation_execution(shell_command, "operation"):
                return self._add_message(state, f"Operation cancelled: {shell_command}", "cancelled")
            
            # Check if this is an interactive command (vim or nano)
            if parsed_command in ['vim', 'nano'] or 'vim' in shell_command or 'nano' in shell_command:
                self._debug_print(f"fileagent: Executing interactive command: {shell_command}")
                result = self._execute_interactive_command(shell_command)
            else:
                result = self._execute_shell_command(shell_command)
            
            return self._add_message(state, result, "success", file_result=result)
            
        except Exception as e:
            if self.debug:
                self._debug_print(f"Error in process: {str(e)}")
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
    

    

    

    

    

    

    
