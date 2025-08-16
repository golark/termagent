from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
import json
import subprocess
import os
import re
import shlex
from termagent.task_complexity import TaskComplexityAnalyzer


# Try to import LLM components
try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class BaseAgent:
    """Base agent class for all agents in the system."""
    
    def __init__(self, name: str, debug: bool = False, no_confirm: bool = False):
        self.name = name
        self.debug = debug
        self.no_confirm = no_confirm
        self.llm = None
    
    def _debug_print(self, message: str):
        if self.debug:
            # Pad the name to ensure | appears after 12 characters
            print(f"{self.name:<12} | {message}")
    
    def _initialize_llm(self, llm_model: str = "gpt-3.5-turbo") -> bool:
        if LLM_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(model=llm_model, temperature=0)
                # Store the model name for comparison
                self.llm.model_name = llm_model
                
                # Add debug message when GPT-4o is used
                if llm_model == "gpt-4o":
                    self._debug_print(f"🧠 Initialized GPT-4o for enhanced reasoning capabilities")
                else:
                    self._debug_print(f"⚡ Initialized {llm_model} for efficient processing")
                
                return True
            except Exception as e:
                self._debug_print(f"⚠️ LLM initialization failed: {e}")
                return False
        else:
            self._debug_print("⚠️ LLM not available - using fallback parsing")
            return False
    
    def _convert_natural_language(self, natural_language: str, system_prompt: str) -> str:
        try:
            # If LLM is not available, return the input as-is
            if not self.llm:
                self._debug_print("LLM not available, using input as-is")
                return natural_language
            
            # Create messages for LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=natural_language)
            ]
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Extract the command from the response
            command = response.content.strip()
            
            # Clean up the response (remove quotes, extra spaces, etc.)
            # Only remove quotes that truly surround the entire command
            command = command.strip()
            if (command.startswith('"') and command.endswith('"')) or (command.startswith("'") and command.endswith("'")):
                command = command[1:-1]  # Remove surrounding quotes
            command = re.sub(r'\s+', ' ', command)  # Normalize spaces
            
            # Ensure zsh compatibility
            command = self._ensure_zsh_compatibility(command)
            self._debug_print(f"🧠 LLM response: {response.content.strip()} | Cleaned: {command}")
            
            return command
            
        except Exception as e:
            # If LLM fails, return the input as-is
            self._debug_print(f"LLM conversion failed: {e}, using input as-is")
            return natural_language
    
    def _ensure_zsh_compatibility(self, command: str) -> str:
        """Ensure the command is compatible with zsh shell."""
        if not command:
            return command
        
        # Fix common bash-specific patterns that might not work in zsh
        # Replace bash-specific syntax with zsh-compatible alternatives
        
        # Fix array syntax: bash uses ${array[@]}, zsh prefers ${array[@]}
        # (zsh supports both, but let's ensure consistency)
        
        # Fix function declaration syntax
        command = re.sub(r'function\s+(\w+)\s*\(\s*\)', r'\1()', command)
        
        # Ensure proper quoting for variables
        # Replace unquoted variables in certain contexts with quoted versions
        command = re.sub(r'([^"\'])\$([A-Za-z_][A-Za-z0-9_]*)', r'\1"$\2"', command)
        
        # Fix command substitution syntax if needed
        # zsh supports both $(command) and `command`, prefer $(command)
        command = re.sub(r'`([^`]+)`', r'$(\1)', command)
        
        # Ensure proper escaping for special characters in strings
        # This is a basic fix - more complex cases might need manual review
        
        return command
    
    def _confirm_operation_execution(self, operation: str, operation_type: str = "operation") -> bool:
        # Skip confirmation if no_confirm flag is set
        if self.no_confirm:
            print(f"✅ {operation}")
            return True
            
        print(f"Execute: {operation}")
        print(f"Press ↵ to confirm, 'n' to cancel: ", end="")
        
        try:
            response = input().strip().lower()
            if response in ['n', 'no', 'cancel', 'skip']:
                print(f"❌ {operation_type.capitalize()} cancelled")
                return False
            else:
                print(f"✅ Proceeding with {operation_type}")
                return True
        except KeyboardInterrupt:
            print(f"\n❌ {operation_type.capitalize()} cancelled")
            return False
    
    def _execute_shell_command(self, command: str, cwd: str = ".") -> str:
        try:
            # Check if confirmation is needed
            if not self.no_confirm:
                print(f"Execute shell command: {command}")
                print(f"Press ↵ to confirm, 'n' to cancel: ", end="")
                
                try:
                    response = input().strip().lower()
                    if response in ['n', 'no', 'cancel', 'skip']:
                        return "Command cancelled by user"
                except KeyboardInterrupt:
                    print("\n❌ Command cancelled")
                    return "Command cancelled by user"
            
            if self.debug:
                self._debug_print(f"🔍 Executing command: {command}")
            
            # Execute the command using zsh explicitly
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/zsh",
                capture_output=True,
                text=True,
                cwd=cwd
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
    
    def _add_message(self, state: Dict[str, Any], content: str, message_type: str = "success", **kwargs) -> Dict[str, Any]:
        messages = state.get("messages", [])
        messages.append(AIMessage(content=content))
        
        # Create the updated state
        updated_state = {
            **state,
            "messages": messages
        }
        
        # Add type-specific fields
        if message_type == "success":
            updated_state["result"] = content
        elif message_type == "error":
            updated_state["error"] = content
        elif message_type == "cancelled":
            updated_state["cancelled"] = True
        
        # Add any additional fields passed as kwargs
        updated_state.update(kwargs)
        
        return updated_state
    
    def _continue_task_breakdown(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Continue with task breakdown after agent completion."""
        task_breakdown = state.get("task_breakdown")
        current_step = state.get("current_step", 0)
        total_steps = state.get("total_steps", 0)
        
        if not task_breakdown or current_step >= total_steps:
            # Task breakdown is complete
            return {
                **state,
                "routed_to": "shell_command",
                "task_breakdown": None,
                "current_step": None,
                "total_steps": None
            }
        
        # Continue with next step
        return {
            **state,
            "routed_to": "task_breakdown"
        }
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement this method")
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        raise NotImplementedError("Subclasses must implement this method")
