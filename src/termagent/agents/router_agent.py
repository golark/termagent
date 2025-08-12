import re
from typing import Dict, Any, List, Tuple
from langchain_core.messages import HumanMessage, AIMessage
from termagent.agents.base_agent import BaseAgent


class RouterAgent(BaseAgent):
    """Router agent that detects complex tasks and breaks them down into steps."""
    
    def __init__(self, debug: bool = False, no_confirm: bool = False):
        super().__init__("router_agent", debug, no_confirm)
        
        # Initialize LLM for task breakdown if available
        self._initialize_llm()
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if the input contains a complex task that needs breakdown."""
        messages = state.get("messages", [])
        if not messages:
            self._debug_print("router: No messages in state")
            return False
        
        # Get the latest user message
        latest_message = messages[-1]
        if isinstance(latest_message, HumanMessage):
            content = latest_message.content.lower()
            self._debug_print(f"router: Checking content: {content}")
            
            # Check for complex tasks that need breakdown
            if self._is_complex_task(content):
                self._debug_print(f"router: Found complex task pattern in: {content}")
                return True
            
            self._debug_print(f"router: No complex task patterns found in: {content}")
        
        return False
    
    def _is_complex_task(self, content: str) -> bool:
        """Check if the content represents a complex task that needs breakdown."""
        content_lower = content.lower()
        
        # Check for multi-step indicators
        multi_step_indicators = [
            r'first\s+.*?then',           # first X then Y
            r'step\s+\d+',                # step 1, step 2, etc.
            r'phase\s+\d+',               # phase 1, phase 2, etc.
            r'stage\s+\d+',               # stage 1, stage 2, etc.
            r'and\s+then',                # and then
            r'after\s+.*?do',             # after X do Y
            r'before\s+.*?do',            # before X do Y
            r'while\s+.*?also',           # while X also Y
            r'along\s+with',              # along with
            r'in\s+addition\s+to',        # in addition to
            r'as\s+well\s+as',            # as well as
        ]
        
        for indicator in multi_step_indicators:
            if re.search(indicator, content_lower):
                self._debug_print(f"router: Found multi-step indicator '{indicator}' in: {content}")
                return True
        
        return False
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Route complex tasks to task breakdown or handle as regular commands."""
        messages = state.get("messages", [])
        latest_message = messages[-1]
        
        if isinstance(latest_message, HumanMessage):
            content = latest_message.content
            
            # Check if this is a complex task that needs breakdown
            if self._is_complex_task(content):
                self._debug_print(f"router: 🔀 Breaking down complex task: {content}")
                return self._break_down_task(state, content)
            else:
                self._debug_print(f"router: 🔀 Routing to REGULAR_COMMAND_HANDLER: {content}")
                # Handle as regular command
                return self._handle_regular_command(state, content)
        
        self._debug_print("router: No HumanMessage found, returning current state")
        return state
    
    def _break_down_task(self, state: Dict[str, Any], task: str) -> Dict[str, Any]:
        """Break down a complex task into steps and determine appropriate agents."""
        self._debug_print(f"router: Breaking down task: {task}")
        
        # Use LLM for intelligent task breakdown
        if self.llm:
            try:
                breakdown = self._llm_task_breakdown(task)
                if breakdown:
                    return self._create_task_breakdown_state(state, task, breakdown)
            except Exception as e:
                self._debug_print(f"router: LLM task breakdown failed: {e}")
        
        # If LLM is not available or fails, create a simple fallback
        fallback_breakdown = [
            {"step": 1, "description": "Execute task", "agent": "regular_command", "command": task}
        ]
        return self._create_task_breakdown_state(state, task, fallback_breakdown)
    
    def _llm_task_breakdown(self, task: str) -> List[Dict[str, str]]:
        """Use LLM to intelligently break down a task into steps."""
        system_prompt = """You are a task analysis expert. Given a complex task, break it down into logical steps and assign the most appropriate agent for each step.

Available agents:
- git_agent: For git operations (commit, push, pull, branch, etc.)
- file_agent: For file operations (move, copy, delete, edit, etc.)
- k8s_agent: For Kubernetes operations (pods, deployments, services, etc.)
- docker_agent: For Docker operations (containers, images, build, etc.)
- regular_command: For system commands and other operations

For each step, provide:
1. A clear description of what needs to be done
2. The most appropriate agent to handle it
3. Any specific commands or actions needed

Return the breakdown as a JSON list of objects with keys: "step", "description", "agent", "command".

Example:
[
  {
    "step": 1,
    "description": "Check current git status",
    "agent": "git_agent",
    "command": "git status"
  },
  {
    "step": 2,
    "description": "Create backup directory",
    "agent": "file_agent", 
    "command": "mkdir backup"
  }
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
            self._debug_print(f"router: LLM breakdown successful: {len(breakdown)} steps")
            return breakdown
            
        except Exception as e:
            self._debug_print(f"router: LLM breakdown failed: {e}")
            return []
    
    def _create_task_breakdown_state(self, state: Dict[str, Any], task: str, breakdown: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create state with task breakdown information."""
        messages = state.get("messages", [])
        
        # Create breakdown message
        breakdown_text = f"📋 Task Breakdown for: {task}\n\n"
        for step_info in breakdown:
            breakdown_text += f"Step {step_info['step']}: {step_info['description']}\n"
            breakdown_text += f"  Agent: {step_info['agent']}\n"
            breakdown_text += f"  Command: {step_info['command']}\n\n"
        
        breakdown_text += "🔄 Starting execution of first step..."
        messages.append(AIMessage(content=breakdown_text))
        
        # Debug output: Print task steps
        if self.debug:
            self._debug_print(f"📋 Task Breakdown for: {task}")
            for step_info in breakdown:
                self._debug_print(f"  Step {step_info['step']}: {step_info['description']}")
                self._debug_print(f"    Agent: {step_info['agent']}")
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
    
    def _handle_regular_command(self, state: Dict[str, Any], command: str) -> Dict[str, Any]:
        """Handle non-git and non-file commands."""
        self._debug_print(f"Handling regular command: {command}")
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Routing regular command: {command}"))
        
        return {
            **state,
            "messages": messages,
            "routed_to": "regular_command",
            "last_command": command
        }
