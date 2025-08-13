import re
import subprocess
import shlex
from typing import Dict, Any, List, Tuple, Optional
from langchain_core.messages import HumanMessage, AIMessage
from termagent.agents.base_agent import BaseAgent


class ShellCommandDetector:
    """Detects and executes known shell commands directly."""
    
    # Basic shell commands that can be executed directly
    KNOWN_COMMANDS = {'ls', 'pwd', 'mkdir', 'rm', 'cp', 'grep', 'find', 'cat', 'head', 'tail', 'sort', 'uniq', 'wc', 'echo'}
    
    def __init__(self, debug: bool = False, no_confirm: bool = False):
        self.debug = debug
        self.no_confirm = no_confirm
    
    def _debug_print(self, message: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"shell_detector | {message}")
    
    def is_known_command(self, command: str) -> bool:
        """Check if the command is a known shell command."""
        if not command or not command.strip():
            return False
        
        parts = shlex.split(command.strip())
        if not parts:
            return False
        
        base_command = parts[0].lower()
        return base_command in self.KNOWN_COMMANDS
    
    def execute_command(self, command: str, cwd: str = ".") -> Tuple[bool, str, Optional[int]]:
        """Execute a shell command directly."""
        if not self.is_known_command(command):
            return False, "Command is not a known shell command", None
        
        self._debug_print(f"Executing shell command: {command}")
        
        try:
            # Check if command contains shell operators that require shell=True
            shell_operators = ['|', '>', '<', '>>', '<<', '&&', '||', ';', '(', ')', '`', '$(']
            needs_shell = any(op in command for op in shell_operators)
            
            if needs_shell:
                # Use shell=True for commands with operators
                process_result = subprocess.run(
                    command,
                    shell=True,
                    executable="/bin/zsh",
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=30
                )
            else:
                # Use shlex.split for simple commands without operators
                args = shlex.split(command)
                process_result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=30
                )
            
            if process_result.returncode == 0:
                output = process_result.stdout.strip() if process_result.stdout.strip() else "✅ Command executed successfully"
                return True, output, process_result.returncode
            else:
                error_msg = process_result.stderr.strip() if process_result.stderr.strip() else "Command failed with no error output"
                return False, f"❌ Command failed: {error_msg}", process_result.returncode
                
        except subprocess.TimeoutExpired:
            return False, f"⏰ Command timed out after 30 seconds: {command}", None
        except FileNotFoundError:
            return False, f"❌ Command not found: {command}", None
        except Exception as e:
            return False, f"❌ Command execution error: {command}\nError: {str(e)}", None
    
    def should_execute_directly(self, command: str) -> bool:
        """Determine if a command should be executed directly or routed to an agent."""
        return self.is_known_command(command)


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
        
        self._debug_print(f"No question indicators found in: {text}")
        return False
    
    def get_query_type(self, text: str) -> str:
        """Determine the type of query to help with routing."""
        text_lower = text.lower()
        
        # Kubernetes queries
        if any(word in text_lower for word in ['cluster', 'pod', 'deployment', 'service', 'node', 'namespace', 'k8s', 'kubernetes']):
            return 'k8s_query'
        
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
            self._debug_print("router: No messages in state")
            return False
        
        # Get the latest user message
        latest_message = messages[-1]
        if isinstance(latest_message, HumanMessage):
            self._debug_print(f"router: Found user message to process")
            return True
        
        return False
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Break down tasks into steps."""
        messages = state.get("messages", [])
        latest_message = messages[-1]
        
        if isinstance(latest_message, HumanMessage):
            content = latest_message.content
            
            self._debug_print(f"router: 🔀 Breaking down task: {content}")
            return self._break_down_task(state, content)
        
        self._debug_print("router: No HumanMessage found, returning current state")
        return state
    
    def _break_down_task(self, state: Dict[str, Any], task: str) -> Dict[str, Any]:
        """Break down a task into steps and determine appropriate agents."""
        self._debug_print(f"router: Breaking down task: {task}")
        
        # First, check if this is a question/informational query
        if self.query_detector.is_question(task):
            query_type = self.query_detector.get_query_type(task)
            self._debug_print(f"router: Task '{task}' is a {query_type}, routing to query handler")
            return self._create_query_state(state, task, query_type)
        
        # Check if this is a known shell command that should be executed directly
        if self.shell_detector.should_execute_directly(task):
            self._debug_print(f"router: Task '{task}' is a known shell command, routing to direct execution")
            return self._create_direct_execution_state(state, task)
        
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
            {"step": 1, "description": "Execute task", "agent": "shell_command", "command": task}
        ]
        return self._create_task_breakdown_state(state, task, fallback_breakdown)
    
    def _llm_task_breakdown(self, task: str) -> List[Dict[str, str]]:
        """Use LLM to intelligently break down a task into steps."""
        system_prompt = """You are a task analysis expert. Given a task, break it down into the MINIMAL number of logical steps and assign the most appropriate agent for each step.

IMPORTANT: Use the FEWEST possible steps to accomplish the task. Combine related operations into single steps when possible. Only create separate steps when they are truly sequential dependencies.

Available agents:
- k8s_agent: For Kubernetes operations (pods, deployments, services, etc.)
- shell_command: For system commands, git operations, file operations, and other operations

For each step, provide:
1. A clear description of what needs to be done
2. The most appropriate agent to handle it
3. Any specific commands or actions needed

Return the breakdown as a JSON list of objects with keys: "step", "description", "agent", "command".

Example (minimal steps):
[
  {
    "step": 1,
    "description": "Check git status and create backup directory",
    "agent": "shell_command",
    "command": "git status && mkdir backup"
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
    
    def _create_direct_execution_state(self, state: Dict[str, Any], task: str) -> Dict[str, Any]:
        """Create state for direct shell command execution."""
        messages = state.get("messages", [])
        
        # Create message indicating direct execution
        execution_text = f"⚡ Direct execution: {task}\n"
        execution_text += "This is a known shell command that will be executed directly."
        messages.append(AIMessage(content=execution_text))
        
        self._debug_print(f"router: Created direct execution state for: {task}")
        
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
        
        self._debug_print(f"router: Created query state for: {query} (type: {query_type})")
        
        # Route to appropriate agent based on query type
        if query_type == 'k8s_query':
            routed_to = "k8s_agent"
        elif query_type == 'shell_query':
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
