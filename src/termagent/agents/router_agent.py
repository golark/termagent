import re
import subprocess
import shlex
import os
from typing import Dict, Any, List, Tuple, Optional
from langchain_core.messages import HumanMessage, AIMessage
from termagent.agents.base_agent import BaseAgent
from termagent.shell_commands import ShellCommandDetector
from termagent.directory_context import get_directory_context, get_relevant_files_context

   
class RouterAgent(BaseAgent):
    """Router agent that breaks down tasks into steps."""
    
    def __init__(self, debug: bool = False, no_confirm: bool = False):
        super().__init__("router_agent", debug, no_confirm)
        
        self.shell_detector = ShellCommandDetector(debug=debug, no_confirm=no_confirm)
        
        self._initialize_llm()
    
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
            self._debug_print(f"Checking {len(successful_breakdowns)} successful task breakdowns in history")
            historical_breakdown = self._search_task_breakdown_cache(task, successful_breakdowns)
            if historical_breakdown:
                self._debug_print(f"Found matching task breakdown in history, reusing it")
                return self._create_task_breakdown_state(state, task, historical_breakdown)
       
        # Step 3 - Use LLM for intelligent task breakdown
        breakdown = self._llm_task_breakdown(task)
        if breakdown:
            self._debug_print(f"LLM breakdown successful, routing to task breakdown")
            return self._create_task_breakdown_state(state, task, breakdown)
        else:
            self._debug_print(f"LLM breakdown failed, falling back to direct execution")
            return self._create_direct_execution_state(state, task)
    

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
        
        # Use simple complexity note for 3.5
        complexity_note = """
This is a straightforward task. Provide a simple, direct breakdown focusing on efficiency.
"""
        
        system_prompt = f"""You are a task analysis expert. Given a task or a query, break it down into the MINIMAL number of logical steps. 

{context_info}

{complexity_note}

CRITICAL RULES:
1. Use the FEWEST possible steps to accomplish the task
2. Each step must be ACTIONABLE and directly contribute to solving the task
3. Avoid unnecessary "discovery" steps unless they're absolutely required
4. If the user provides specific names/identifiers, use them directly
5. Combine related operations into single steps when possible
6. Only create separate steps when they are truly sequential dependencies
7. Use the directory context above to understand the current workspace structure
8. Reference specific files and directories that exist in the workspace when relevant

For each step, provide:
1. A clear description of what needs to be done
2. Any specific commands or actions needed

Return the breakdown as a JSON list of objects with keys: "step", "description", "command".

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

Task: "list all files in current directory"
Breakdown: [
  {{
    "step": 1,
    "description": "List all files in current directory",
    "agent": "shell_command",
    "command": "ls -la"
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
                self._debug_print(f"Found exact command match in successful breakdowns: {command}")
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


    



