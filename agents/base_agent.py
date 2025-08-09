from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
import json


class BaseAgent:
    """Base agent class for all agents in the system."""
    
    def __init__(self, name: str):
        self.name = name
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state and return updated state."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the current input."""
        raise NotImplementedError("Subclasses must implement this method")
