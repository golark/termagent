from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import os
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



    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement this method")
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        raise NotImplementedError("Subclasses must implement this method")
