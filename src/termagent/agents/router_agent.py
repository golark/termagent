import re
import subprocess
import shlex
import os
from typing import Dict, Any, List, Tuple, Optional
from langchain_core.messages import HumanMessage, AIMessage
from termagent.agents.base_agent import BaseAgent
from termagent.shell_commands import ShellCommandDetector
from termagent.directory_context import get_directory_context, get_relevant_files_context
from termagent.task_complexity import TaskComplexityAnalyzer


class QueryDetector:
    """Detects if user input is a question/informational query."""
    
    # Question indicators
    QUESTION_WORDS = {
        'what', 'how', 'why', 'when', 'where', 'which', 'who', 'whose', 'whom',
        'can', 'could', 'would', 'should', 'will', 'do', 'does', 'did', 'is', 'are', 'was', 'were'
    }
    
    # Complex query indicators that suggest GPT-4o usage
    COMPLEX_QUERY_INDICATORS = {
        'how to', 'what is the best way', 'why does', 'when should',
        'which approach', 'compare', 'difference between', 'similarities',
        'pros and cons', 'advantages', 'disadvantages', 'trade-offs',
        'best practices', 'recommendations', 'suggestions', 'alternatives',
        'considerations', 'implications', 'consequences', 'impact',
        'evaluation', 'assessment', 'review', 'analysis of',
        'what would happen if', 'suppose that', 'imagine if',
        'under what circumstances', 'in what situations',
        'how would you', 'what would you recommend',
        'explain why', 'describe how', 'analyze the'
    }
    
    # Question patterns
    QUESTION_PATTERNS = [
        r'\?$',  # Ends with question mark
        r'^(what|how|why|when|where|which|who|whose|whom)\s+',  # Starts with question word
        r'\s+(what|how|why|when|where|which|who|whose|whom)\s+',  # Contains question word
        r'^(can|could|would|should|will|do|does|did|is|are|was|were)\s+',  # Starts with modal/auxiliary
        r'\s+(can|could|would|should|will|do|does|did|is|are|was|were)\s+',  # Contains modal/auxiliary
    ]
    
    # Complex query patterns
    COMPLEX_QUERY_PATTERNS = [
        r'\b(how to|what is the best way|why does|when should)\b',
        r'\b(which approach|compare|difference between|similarities)\b',
        r'\b(pros and cons|advantages|disadvantages|trade.?offs)\b',
        r'\b(best practices|recommendations|suggestions|alternatives)\b',
        r'\b(considerations|implications|consequences|impact)\b',
        r'\b(evaluation|assessment|review|analysis of)\b',
        r'\b(what would happen if|suppose that|imagine if)\b',
        r'\b(under what circumstances|in what situations)\b',
        r'\b(how would you|what would you recommend)\b',
        r'\b(explain why|describe how|analyze the)\b'
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
    
    def is_complex_query(self, text: str) -> bool:
        """Detect if the query is complex and would benefit from GPT-4o analysis."""
        if not text or not text.strip():
            return False
        
        text_lower = text.lower().strip()
        
        # Check for complex query indicators
        for indicator in self.COMPLEX_QUERY_INDICATORS:
            if indicator in text_lower:
                self._debug_print(f"Detected complex query indicator: {indicator}")
                return True
        
        # Check for complex query patterns
        for pattern in self.COMPLEX_QUERY_PATTERNS:
            if re.search(pattern, text_lower):
                self._debug_print(f"Detected complex query pattern: {pattern}")
                return True
        
        # Check for long, descriptive queries (more than 10 words often indicates complexity)
        if len(text.split()) > 10:
            self._debug_print(f"Detected long query ({len(text.split())} words), likely complex")
            return True
        
        return False
    
    def get_query_type(self, text: str) -> str:
        """All queries are shell queries."""
        return 'shell_query'


class RouterAgent(BaseAgent):
    """Router agent that breaks down tasks into steps."""
    
    def __init__(self, debug: bool = False, no_confirm: bool = False):
        super().__init__("router_agent", debug, no_confirm)
        
        # Initialize shell command detector
        self.shell_detector = ShellCommandDetector(debug=debug, no_confirm=no_confirm)
        
        # Initialize query detector
        self.query_detector = QueryDetector(debug=debug)
        
        # Initialize task complexity analyzer
        self.complexity_analyzer = TaskComplexityAnalyzer(debug=debug)
        
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

        # step 1 - Check if this is a known shell command that should be executed directly
        if self.shell_detector.is_shell_command(task):
            self._debug_print(f"Routing to direct shell execution")
            return self._create_direct_execution_state(state, task)
        
        
        # step 2 - check if this is a question/informational query
        if self.query_detector.is_question(task):
            # Check if this is a complex query that would benefit from GPT-4o
            is_complex = self.query_detector.is_complex_query(task)
            
            if is_complex:
                self._debug_print(f"Routing to query handler - complex query detected")
            else:
                self._debug_print(f"Routing to query handler - simple query")
            
            return self._create_query_state(state, task, is_complex)
        
       
        # step 3 - Check if we have a successful task breakdown in history
        successful_breakdowns = state.get("successful_task_breakdowns", [])
        if successful_breakdowns:
            self._debug_print(f"Checking {len(successful_breakdowns)} successful task breakdowns in history")
            historical_breakdown = self._search_successful_task_breakdowns(task, successful_breakdowns)
            if historical_breakdown:
                self._debug_print(f"Found matching task breakdown in history, reusing it")
                return self._create_task_breakdown_state(state, task, historical_breakdown)
       
        # Step 4 - Use LLM for intelligent task breakdown
        breakdown = self._llm_task_breakdown(task)
        if breakdown:
            self._debug_print(f"LLM breakdown successful, routing to task breakdown")
            return self._create_task_breakdown_state(state, task, breakdown)
        else:
            self._debug_print(f"LLM breakdown failed, falling back to direct execution")
            return self._create_direct_execution_state(state, task)
    
    def _llm_task_breakdown(self, task: str) -> List[Dict[str, str]]:
        """Use LLM to intelligently break down a task into steps."""
        
        # Analyze task complexity to determine the appropriate LLM model
        complexity_analysis = self.complexity_analyzer.analyze_complexity(task)
        recommended_model = complexity_analysis['recommended_model']
        
        self._debug_print(f"Task complexity analysis: {complexity_analysis['complexity_score']} score, {complexity_analysis['reasoning_score']} reasoning, using model: {recommended_model}")
        
        # Reinitialize LLM with the recommended model if different from current
        if not self.llm or getattr(self.llm, 'model_name', '') != recommended_model:
            self._debug_print(f"🔄 Switching LLM model to {recommended_model}")
            self._initialize_llm(recommended_model)
       
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
        
        # Customize system prompt based on complexity
        if recommended_model == "gpt-4o":
            complexity_note = """
IMPORTANT: This is a complex task requiring advanced reasoning. Use GPT-4o's enhanced capabilities to:
- Provide detailed, thoughtful analysis
- Consider multiple approaches and edge cases
- Break down complex logic into clear, actionable steps
- Consider performance, security, and maintainability implications
- Provide explanations for why certain approaches are chosen
"""
        else:
            complexity_note = """
This is a straightforward task. Provide a simple, direct breakdown focusing on efficiency.
"""
        
        system_prompt = f"""You are a task analysis expert. Given a task, break it down into the MINIMAL number of logical steps and assign the most appropriate agent for each step.

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
  {{
    "step": 1,
    "description": "Stop the Docker container named nginxx",
    "agent": "shell_command",
    "command": "docker stop nginxx"
  }}
]

Task: "create a new git branch called feature-x"
Breakdown: [
  {{
    "step": 1,
    "description": "Create and switch to new git branch feature-x",
    "agent": "shell_command",
    "command": "git checkout -b feature-x"
  }}
]

Task: "check how many python files are in this directory"
Breakdown: [
  {{
    "step": 1,
    "description": "Count Python files in current directory",
    "agent": "shell_command",
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
    
    def _search_successful_task_breakdowns(self, task: str, successful_breakdowns: List[Dict[str, Any]]) -> Optional[List[Dict[str, str]]]:
        """Search through successful task breakdowns for a matching command."""
        if not successful_breakdowns:
            return None
        
        task_lower = task.lower().strip()
        
        # First, try exact command matches
        for breakdown in successful_breakdowns:
            command = breakdown.get("command", "").lower().strip()
            if command == task_lower:
                self._debug_print(f"Found exact command match in successful breakdowns: {command}")
                return breakdown.get("task_breakdown")
               
        return None
    
    def _search_command_history(self, task: str) -> Optional[str]:
        """Search through command history for a matching command."""
        try:
            from termagent.input_handler import CommandHistory
            
            # Create a temporary command history instance to search
            history = CommandHistory()
            matches = history.search_history(task)
            
            if matches:
                # Return the most recent match
                best_match = matches[-1]
                self._debug_print(f"Found command in history: {best_match}")
                return best_match
            
        except Exception as e:
            self._debug_print(f"Error searching command history: {e}")
        
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
            breakdown_text += f"  Agent: {step_info['agent']}\n"
            breakdown_text += f"  Command: {step_info['command']}\n\n"
        
        breakdown_text += "🔄 Starting execution..."
        messages.append(AIMessage(content=breakdown_text))
        
        # Debug output: Print task steps
        if self.debug:
            self._debug_print(f"📋 Task Breakdown for: {task}")
            for step_info in breakdown:
                self._debug_print(f"  [{step_info['step']}] -- {step_info['description']}")
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

    def _create_query_state(self, state: Dict[str, Any], query: str, is_complex: bool) -> Dict[str, Any]:
        """Create state for handling informational queries."""
        messages = state.get("messages", [])
        
        # Analyze query complexity to determine if GPT-4o should be used
        complexity_analysis = self.complexity_analyzer.analyze_complexity(query)
        
        # Use both the query detector's complexity assessment and the complexity analyzer
        # If either indicates complexity, use GPT-4o
        should_use_gpt4o = is_complex or complexity_analysis['requires_complex_reasoning']
        recommended_model = complexity_analysis['recommended_model']
        
        # Override recommended model if complex query is detected
        if should_use_gpt4o:
            recommended_model = "gpt-4o"
        
        # Create message indicating query handling with model information
        query_text = f"🔍 Query detected: {query}\n"
        query_text += f"🧠 Complexity: {complexity_analysis['complexity_score']} score\n"
        
        if should_use_gpt4o:
            query_text += f"🧠 Using GPT-4o for complex reasoning\n"
            query_text += "This query requires advanced analysis and step-by-step guidance..."
        else:
            query_text += f"⚡ Using GPT-3.5-turbo for simple analysis\n"
            query_text += "This query will be handled efficiently..."
        
        query_text += "\nRouting to appropriate agent for information gathering..."
        messages.append(AIMessage(content=query_text))
        
        self._debug_print(f"Created query state for: {query}")
        if should_use_gpt4o:
            self._debug_print(f"🧠 Query requires GPT-4o for complex reasoning")
        else:
            self._debug_print(f"⚡ Query can use GPT-3.5-turbo for simple analysis")
        
        # All queries go to the query handler for GPT-4o analysis
        routed_to = "handle_query"
        
        # Add to state with complexity information
        return {
            **state,
            "messages": messages,
            "routed_to": routed_to,
            "last_command": query,
            "is_query": True,
            "query_complexity": complexity_analysis,
            "should_use_gpt4o": should_use_gpt4o,
            "is_complex_query": is_complex
        }
    



