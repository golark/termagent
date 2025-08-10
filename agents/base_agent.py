from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
import json
import subprocess
import os
import re

# Try to import LLM components
try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class BaseAgent:
    """Base agent class for all agents in the system."""
    
    def __init__(self, name: str, debug: bool = False):
        self.name = name
        self.debug = debug
        self.llm = None
    
    def _debug_print(self, message: str):
        if self.debug:
            # Pad the name to ensure | appears after 12 characters
            print(f"{self.name:<12} | {message}")
    
    def _initialize_llm(self, llm_model: str = "gpt-3.5-turbo") -> bool:
        if LLM_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(model=llm_model, temperature=0)
                self._debug_print(f"✅ LLM initialized with model: {llm_model}")
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
            self._debug_print("Using LLM for natural language conversion")
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=natural_language)
            ]
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Extract the command from the response
            command = response.content.strip()
            self._debug_print(f"LLM response: {command}")
            
            # Clean up the response (remove quotes, extra spaces, etc.)
            command = re.sub(r'^["\']|["\']$', '', command)  # Remove surrounding quotes
            command = re.sub(r'\s+', ' ', command)  # Normalize spaces
            self._debug_print(f"Cleaned command: {command}")
            
            return command
            
        except Exception as e:
            # If LLM fails, return the input as-is
            self._debug_print(f"LLM conversion failed: {e}, using input as-is")
            return natural_language
    
    def _confirm_operation_execution(self, operation: str, operation_type: str = "operation") -> bool:
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
            if self.debug:
                self._debug_print(f"Executing shell command: {command}")
            
            # Execute the command using subprocess
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd
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
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement this method")
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        raise NotImplementedError("Subclasses must implement this method")
