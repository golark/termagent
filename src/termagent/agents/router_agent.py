import re
import subprocess
import shlex
from typing import Dict, Any, List, Tuple, Optional
from langchain_core.messages import HumanMessage, AIMessage
from termagent.agents.base_agent import BaseAgent
from termagent.shell_commands import ShellCommandDetector


class QueryDetector:
    """Detects if user input is a question/informational query."""
    
    # Question indicators
    QUESTION_WORDS = {
        'what', 'how', 'why', 'when', 'where', 'which', 'who', 'whose', 'whom',
        'can', 'could', 'would', 'should', 'will', 'do', 'does', 'did', 'is', 'are', 'was', 'were'
    }
    
    # Question patterns
    QUESTION_PATTERNS = [
        r'\?$',  # Ends with question mark
        r'^(what|how|why|when|where|which|who|whose|whom)\s+',  # Starts with question word
        r'\s+(what|how|why|when|where|which|who|whose|whom)\s+',  # Contains question word
        r'^(can|could|would|should|will|do|does|did|is|are|was|were)\s+',  # Starts with modal/auxiliary
        r'\s+(can|could|would|should|will|do|does|did|is|are|was|were)\s+',  # Contains modal/auxiliary
    ]
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def _debug_print(self, message: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"query_detector | {message}")
    
    def is_question(self, text: str) -> bool:
        """Detect if the input is a question/informational query."""
        if not text or not text.strip():
            return False
        
        text_lower = text.lower().strip()
        
        # Check for question mark
        if text.strip().endswith('?'):
            self._debug_print(f"Detected question mark in: {text}")
            return True
        
        # Check for question words at start
        words = text_lower.split()
        if words and words[0] in self.QUESTION_WORDS:
            self._debug_print(f"Detected question word at start: {words[0]}")
            return True
        
        # Check for question patterns
        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, text_lower):
                self._debug_print(f"Detected question pattern: {pattern}")
                return True
        
        # Check for question words anywhere in the text
        for word in self.QUESTION_WORDS:
            if f' {word} ' in f' {text_lower} ':
                self._debug_print(f"Detected question word: {word}")
                return True
        
        return False
    
    def get_query_type(self, text: str) -> str:
        """Determine the type of query to help with routing."""
        text_lower = text.lower()
        
        # File, system, and git queries - route to shell handler
        if any(word in text_lower for word in ['file', 'directory', 'folder', 'path', 'size', 'python', 'count', 'list', 'show', 'container', 'image', 'docker', 'volume', 'network', 'process', 'memory', 'cpu', 'disk', 'system', 'status', 'git', 'commit', 'branch', 'remote', 'repository', 'permissions', 'attributes', 'owner', 'group']):
            return 'shell_query'
        
        return 'shell_query'


class RouterAgent(BaseAgent):
    """Router agent that breaks down tasks into steps."""
    
    def __init__(self, debug: bool = False, no_confirm: bool = False):
        super().__init__("router_agent", debug, no_confirm)
        
        # Initialize shell command detector
        self.shell_detector = ShellCommandDetector(debug=debug, no_confirm=no_confirm)
        
        # Initialize query detector
        self.query_detector = QueryDetector(debug=debug)
        
        # Initialize LLM for task breakdown if available
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
        """Break down a task into steps and determine appropriate agents."""
        
        # First, check if this is a question/informational query
        if self.query_detector.is_question(task):
            query_type = self.query_detector.get_query_type(task)
            self._debug_print(f"Routing to query handler (type: {query_type})")
            return self._create_query_state(state, task, query_type)
        
        # Check if this is a known shell command that should be executed directly
        if self.shell_detector.should_execute_directly(task):
            self._debug_print(f"Routing to direct shell execution")
            return self._create_direct_execution_state(state, task)
        
        # Use LLM for intelligent task breakdown
        self._debug_print(f"Attempting LLM task breakdown")
        breakdown = self._llm_task_breakdown(task)
        if breakdown:
            self._debug_print(f"LLM breakdown successful, routing to task breakdown")
            return self._create_task_breakdown_state(state, task, breakdown)
        else:
            self._debug_print(f"LLM breakdown failed, falling back to direct execution")
            return self._create_direct_execution_state(state, task)
    
    def _llm_task_breakdown(self, task: str) -> List[Dict[str, str]]:
        """Use LLM to intelligently break down a task into steps."""
        system_prompt = """You are a task analysis expert. Given a task, break it down into the MINIMAL number of logical steps and assign the most appropriate agent for each step.

CRITICAL RULES:
1. Use the FEWEST possible steps to accomplish the task
2. Each step must be ACTIONABLE and directly contribute to solving the task
3. Avoid unnecessary "discovery" steps unless they're absolutely required
4. If the user provides specific names/identifiers, use them directly
5. Combine related operations into single steps when possible
6. Only create separate steps when they are truly sequential dependencies

Available agents:
- shell_command: For system commands, git operations, file operations, Docker, and other operations

For each step, provide:
1. A clear description of what needs to be done
2. The most appropriate agent to handle it
3. Any specific commands or actions needed

Return the breakdown as a JSON list of objects with keys: "step", "description", "agent", "command".

EXAMPLES:

Task: "stop docker container nginxx"
Breakdown: [
  {
    "step": 1,
    "description": "Stop the Docker container named nginxx",
    "agent": "shell_command",
    "command": "docker stop nginxx"
  }
]

Task: "create a new git branch called feature-x"
Breakdown: [
  {
    "step": 1,
    "description": "Create and switch to new git branch feature-x",
    "agent": "shell_command",
    "command": "git checkout -b feature-x"
  }
]

Task: "check how many python files are in this directory"
Breakdown: [
  {
    "step": 1,
    "description": "Count Python files in current directory",
    "agent": "shell_command",
    "command": "ls *.py | wc -l"
  }
]

Task: "list all files in current directory"
Breakdown: [
  {
    "step": 1,
    "description": "List all files in current directory",
    "agent": "shell_command",
    "command": "ls -la"
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
            self._debug_print(f"LLM breakdown successful: {len(breakdown)} steps")
            return breakdown
            
        except Exception as e:
            self._debug_print(f"LLM breakdown failed: {e}")
            return []
    
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
            breakdown_text += f"Step {step_info['step']}: {step_info['description']}\n"
            breakdown_text += f"  Agent: {step_info['agent']}\n"
            breakdown_text += f"  Command: {step_info['command']}\n\n"
        
        breakdown_text += "🔄 Starting execution..."
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

    def _create_query_state(self, state: Dict[str, Any], query: str, query_type: str) -> Dict[str, Any]:
        """Create state for handling informational queries."""
        messages = state.get("messages", [])
        
        # Create message indicating query handling
        query_text = f"🔍 Query detected: {query}\n"
        query_text += f"Type: {query_type}\n"
        query_text += "Routing to appropriate agent for information gathering..."
        messages.append(AIMessage(content=query_text))
        
        self._debug_print(f"Created query state for: {query} (type: {query_type})")
        
        # Route to appropriate agent based on query type
        if query_type == 'shell_query':
            routed_to = "handle_shell"
        else:
            routed_to = "handle_query"
        
        # Add to state
        return {
            **state,
            "messages": messages,
            "routed_to": routed_to,
            "last_command": query,
            "is_query": True,
            "query_type": query_type
        }
    



