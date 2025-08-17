import re
import subprocess
import shlex
import os
from typing import Dict, Any, List, Tuple, Optional
from langchain_core.messages import HumanMessage, AIMessage
from termagent.agents.base_agent import BaseAgent
from termagent.shell_commands import ShellCommandHandler
from termagent.directory_context import get_directory_context, get_relevant_files_context

   
class RouterAgent(BaseAgent):
    """Router agent that breaks down tasks into steps."""
    
    def __init__(self, debug: bool = False, no_confirm: bool = False, llm_model: str = "gpt-3.5-turbo"):
        super().__init__("router_agent", debug, no_confirm)
        
        self.shell_detector = ShellCommandHandler(debug=debug, no_confirm=no_confirm)
        
        self._initialize_llm(llm_model)
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if there are messages to process."""
        messages = state.get("messages", [])
        if not messages:
            self._debug_print("No messages in state")
            return False
        
        # Get the latest user message
        latest_message = messages[-1]
        if isinstance(latest_message, HumanMessage):
            self._debug_print(f"Found user message to process")
            return True
        
        return False
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Break down tasks into steps."""
        messages = state.get("messages", [])
        latest_message = messages[-1]
        
        if isinstance(latest_message, HumanMessage):
            content = latest_message.content
            
            return self._break_down_task(state, content)
        
        self._debug_print("No HumanMessage found, returning current state")
        return state
    
    def _break_down_task(self, state: Dict[str, Any], task: str) -> Dict[str, Any]:

        # step 1 - Check if this is a known shell command that should be executed directly
        if self.shell_detector.is_shell_command(task):
            self._debug_print(f"Routing to direct shell execution")
            return self._create_direct_execution_state(state, task)
       
        # step 2 - Check if we have a successful task breakdown in history
        successful_breakdowns = state.get("successful_task_breakdowns", [])
        if successful_breakdowns:
            historical_breakdown = self._search_task_breakdown_cache(task, successful_breakdowns)
            if historical_breakdown:
                return self._create_task_breakdown_state(state, task, historical_breakdown)
       
        # Step 3 - Use LLM for intelligent task breakdown
        breakdown = self._llm_task_breakdown(task)
        if breakdown:
            return self._create_task_breakdown_state(state, task, breakdown)

        self._debug_print("Unable to handle this command. No breakdown or direct execution available.")
        messages = state.get("messages", [])
        messages.append(AIMessage(content="❌ Sorry, I cannot handle this command."))
        return {**state, "messages": messages}

    def _llm_task_breakdown(self, task: str) -> List[Dict[str, str]]:
        # Get directory context for the LLM
        try:
            current_dir = os.getcwd()
            directory_context = get_directory_context(current_dir, max_depth=2, max_files_per_dir=15)
            relevant_files = get_relevant_files_context(current_dir)
            
            context_info = f"""📁 CURRENT WORKSPACE CONTEXT:
{directory_context}

{relevant_files}

"""
        except Exception as e:
            context_info = f"⚠️  Could not get directory context: {e}\n\n"

        
        
        system_prompt = f"""You are a task analysis expert. Your job is to break down a given task into the absolute MINIMAL number of logical steps.

{context_info}

RULES:
1. Use the FEWEST possible steps — combine actions when they can be done in a single command.
2. Each step must be ACTIONABLE (something a user can execute directly).
3. Avoid unnecessary "discovery" or exploratory steps unless required by the task.
4. If specific names/identifiers are given, use them directly (no guessing).
5. Reference actual files/directories from the provided workspace context when relevant.
6. When the output of one command is used in the next, prefer a single step with pipes (|).
7. When independent commands can be executed together, prefer a one-liner with `&&`.
8. Only separate steps if they are true sequential dependencies that cannot be merged.
9. Before returning the breakdown, perform a META-CHECK:  
   - Verify that no two steps can be combined into a one-liner with `|` or `&&`.  
   - Verify that each step is absolutely necessary.  
   - If possible, reduce the total number of steps further.

OUTPUT FORMAT:
Return the breakdown as a JSON array of objects.  
Each object must have:
- `"step"`: sequential number starting at 1  
- `"description"`: clear explanation of the action  
- `"command"`: the exact command to run  

EXAMPLES:

Task: "stop docker container nginxx"  
Breakdown: [
  {{
    "step": 1,
    "description": "Stop the Docker container named nginxx",
    "command": "docker stop nginxx"
  }}
]

Task: "create a new git branch called feature-x"  
Breakdown: [
  {{
    "step": 1,
    "description": "Create and switch to new git branch feature-x",
    "command": "git checkout -b feature-x"
  }}
]

Task: "check how many python files are in this directory"  
Breakdown: [
  {{
    "step": 1,
    "description": "Count Python files in current directory",
    "command": "ls *.py | wc -l"
  }}
]

Task: "what is the largest file in directory?"  
Breakdown: [
  {{
    "step": 1,
    "description": "List files by size and return the largest one",
    "command": "ls -lS | head -n 1"
  }}
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
            self._debug_print(f"LLM breakdown successful: {len(breakdown)} steps")
            return breakdown
            
        except Exception as e:
            self._debug_print(f"LLM breakdown failed: {e}")
            return []
    
    def _search_task_breakdown_cache(self, task: str, cache: List[Dict[str, Any]]) -> Optional[List[Dict[str, str]]]:
        if not cache:
            return None
        
        task_lower = task.lower().strip()
        
        # First, try exact command matches
        for breakdown in cache:
            command = breakdown.get("command", "").lower().strip()
            if command == task_lower:
                self._debug_print(f"Found exact command match in cache: {command}")
                return breakdown.get("task_breakdown")
               
        return None
   
    def _create_task_breakdown_state(self, state: Dict[str, Any], task: str, breakdown: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create state with task breakdown information."""
        messages = state.get("messages", [])
        
        # Create breakdown message
        breakdown_text = f"📋 Task Breakdown for: {task}\n\n"
        
        # Add summary of what will be accomplished
        if len(breakdown) == 1:
            breakdown_text += f"🎯 This task will be completed in 1 step:\n\n"
        else:
            breakdown_text += f"🎯 This task will be completed in {len(breakdown)} steps:\n\n"
        
        for step_info in breakdown:
            breakdown_text += f"[{step_info['step']}] -- {step_info['description']}\n"
            breakdown_text += f"  Command: {step_info['command']}\n\n"
        
        breakdown_text += "🔄 Starting execution..."
        messages.append(AIMessage(content=breakdown_text))
        
        # Debug output: Print task steps
        if self.debug:
            self._debug_print(f"📋 Task Breakdown for: {task}")
            for step_info in breakdown:
                self._debug_print(f"  [{step_info['step']}] -- {step_info['description']}")
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
    
    def _create_direct_execution_state(self, state: Dict[str, Any], task: str) -> Dict[str, Any]:
        """Create state for direct shell command execution."""
        messages = state.get("messages", [])
        
        # Create message indicating direct execution
        execution_text = f"⚡ Direct execution: {task}\n"
        execution_text += "This is a known shell command that will be executed directly."
        messages.append(AIMessage(content=execution_text))
        
        # Add to state
        return {
            **state,
            "messages": messages,
            "routed_to": "handle_direct_execution",
            "last_command": task
        }


    



