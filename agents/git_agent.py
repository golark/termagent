import os
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage
from agents.base_agent import BaseAgent

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class GitAgent(BaseAgent):
    """Git agent that handles git-specific commands and operations with LLM interface."""
    
    def __init__(self, llm_model: str = "gpt-3.5-turbo", debug: bool = False):
        super().__init__("git_agent", debug)
        
        # Initialize LLM using base class method
        self._initialize_llm(llm_model)
        
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


    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this agent should handle the current input."""
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
            # Convert natural language to git command using LLM
            self._debug_print("Converting natural language to git command...")
            converted_command = self._convert_natural_language_to_git(command)
            self._debug_print(f"Converted command: {converted_command}")
            
            # Ask for confirmation before executing
            if not self._confirm_operation_execution(converted_command, "command"):
                self._debug_print("Command cancelled by user")
                return self._add_message(state, f"⏹️ Command cancelled: {converted_command}", "cancelled")
            
            # Execute the git command
            self._debug_print(f"Executing command: {converted_command}")
            result = self._execute_shell_command(converted_command)
            self._debug_print(f"Command execution result: {result[:100]}...")
            return self._add_message(state, f"✅ Git command executed successfully: {result}", "success", git_result=result)
                
        except Exception as e:
            self._debug_print(f"Error in process: {str(e)}")
            return self._add_message(state, f"❌ Git command failed: {str(e)}", "error")
    

    
    def _convert_natural_language_to_git(self, natural_language: str) -> str:
        """Convert natural language to git command using LLM."""
        result = self._convert_natural_language(natural_language, self.system_prompt)
        # Add git prefix if the result doesn't already start with git
        if not result.lower().startswith("git "):
            result = f"git {result}"
        return result
    

    

    

    

    
