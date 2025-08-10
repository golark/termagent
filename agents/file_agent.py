import os
import subprocess
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage
from agents.base_agent import BaseAgent

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class FileAgent(BaseAgent):
    """File agent that handles file operations like moving, copying, deleting files with LLM interface."""
    
    def __init__(self, llm_model: str = "gpt-3.5-turbo", debug: bool = False):
        super().__init__("file_agent", debug)
        
        # Initialize LLM using base class method
        self._initialize_llm(llm_model)
        
        # System prompt for LLM
        self.system_prompt = """Convert natural language to valid shell commands. Return only the command, nothing else.

File Operations Examples:
- "move file.txt to folder/" → "mv file.txt folder/"
- "copy data.csv to backup/" → "cp data.csv backup/"
- "delete old.log" → "rm old.log"
- "create folder logs" → "mkdir logs"
- "list files in docs/" → "ls docs/"
- "find *.txt files" → "find . -name '*.txt'"
- "rename old.txt to new.txt" → "mv old.txt new.txt"
- "create directory backup" → "mkdir backup"
- "remove folder temp" → "rm -rf temp"
- "copy directory source to dest" → "cp -r source dest"
- "show contents of current directory" → "ls -la"
- "find files containing pattern" → "find . -name '*pattern*'"
- "list all files" → "ls -la"
- "show hidden files" → "ls -la"
- "create nested directories" → "mkdir -p parent/child"
- "remove file and ignore errors" → "rm -f file.txt"
- "copy with verbose output" → "cp -v source dest"
- "move with backup" → "mv -b file.txt file.txt~"

Common shell commands:
- mv (move/rename), cp (copy), rm (remove/delete), mkdir (create directory)
- ls (list), find (search), touch (create empty file), chmod (change permissions)
- Use -r for recursive operations on directories
- Use -f for force operations (ignore errors)
- Use -v for verbose output
- Use -p for creating parent directories

Return only the shell command, no explanations, quotes, or additional text:"""
        
        self._debug_print("🤖 FileAgent initialized successfully")


    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this agent should handle the current input."""
        # This agent is called via MCP from the router
        should_handle = state.get("routed_to") == "file_agent"
        return should_handle
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process file operations with LLM support for natural language conversion."""
        command = state.get("last_command", "")
        self._debug_print(f"Processing command: {command}")
        
        if not command:
            return state
        
        try:
            # Convert natural language to file operation using LLM
            converted_operation = self._convert_natural_language_to_operation(command)
            if self.debug:
                self._debug_print(f"Converted operation: {converted_operation}")
            
            # Ask for confirmation before executing
            if not self._confirm_operation_execution(converted_operation, "operation"):
                return self._add_message(state, "Operation cancelled", "cancelled")
            
            # Execute the file operation
            result = self._execute_shell_command(converted_operation)
            return self._add_message(state, f"Executed: {converted_operation}\nResult: {result}", "success")
                
        except Exception as e:
            if self.debug:
                self._debug_print(f"Error in process: {str(e)}")
            return self._add_message(state, str(e), "error")
    

       
    def _convert_natural_language_to_operation(self, natural_language: str) -> str:
        """Convert natural language to file operation using LLM."""
        return self._convert_natural_language(natural_language, self.system_prompt)
    

    
    def _execute_file_operation(self, operation: str) -> str:
        """Execute a shell command for file operations."""
        try:
            if self.debug:
                self._debug_print(f"Executing shell command: {operation}")
            
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
                if self.debug:
                    self._debug_print(f"Command successful, output: {output[:100]}...")
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
    

    

    

    

    

    

    
