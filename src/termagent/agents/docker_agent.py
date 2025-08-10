from typing import Dict, Any, List
from langchain_core.messages import AIMessage, HumanMessage
from termagent.agents.base_agent import BaseAgent

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain.chat_models import ChatOpenAI


class DockerAgent(BaseAgent):
    """Docker agent that handles container operations with LLM interface."""

    def __init__(self, llm_model: str = "gpt-3.5-turbo", debug: bool = False, no_confirm: bool = False):
        super().__init__("docker_agent", debug, no_confirm)
        
        # Initialize LLM using base class method
        self._initialize_llm(llm_model)
        
        # System prompt for LLM
        self.system_prompt = """Convert natural language to zsh-compatible Docker commands. Return only the command, nothing else.

IMPORTANT: Commands must work in zsh shell. Use zsh-compatible syntax.
- Use proper Docker CLI syntax
- Include necessary flags and options
- Handle container names, image names, and volumes correctly
- Avoid bash-specific syntax that might not work in zsh

Convert this request to a Docker command:"""
        
        # Planning prompt for complex tasks
        self.planning_prompt = """Create a step-by-step Docker execution plan with clear, actionable todos.

IMPORTANT: Put each action on a SEPARATE LINE. Do NOT combine multiple actions on one line.

Format your response as a simple list with one action per line. Each line should start with one of these markers:
- TODO: for tasks to complete
- Step: for sequential steps
- Action: for specific actions
- Execute: for commands to run

Keep each line concise and actionable. Focus on Docker commands and operations.

Example format:
TODO: Check Docker daemon status
Step 1: Verify Docker installation
Action: docker --version
Execute: docker info
TODO: Create application network
Action: docker network create app-network

CRITICAL: Each action must be on its own line. Do not combine multiple actions.

Now create a plan for this task:"""

        self._debug_print("🤖 DockerAgent initialized successfully")

    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this agent should handle the current input."""
        should_handle = state.get("routed_to") == "docker_agent"
        self._debug_print(f"should_handle: {should_handle} (routed_to: {state.get('routed_to')})")
        return should_handle

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process Docker commands with LLM support for natural language conversion and planning. Always treats tasks as complex tasks requiring execution plans."""
        command = state.get("last_command", "")
        self._debug_print(f"Processing command: {command}")

        if not command:
            return self._add_message(state, "❌ No command provided", "error")

        try:
            # Always treat Docker tasks as complex tasks that require planning
            self._debug_print("Creating execution plan for Docker task...")
            
            # Create a detailed plan for the task
            self._debug_print(f"dockeragent: Creating execution plan for: {command}")
            plan = self._create_task_plan(command)
            self._debug_print(f"dockeragent: Raw plan created: {plan}")
            
            # Normalize the plan to ensure proper line breaks
            self._debug_print("dockeragent: Normalizing plan format...")
            plan = self._normalize_plan(plan)
            self._debug_print(f"dockeragent: Normalized plan: {plan}")
            
            # Validate the plan
            self._debug_print("dockeragent: Validating plan...")
            if not self._validate_plan(plan):
                self._debug_print("Plan validation failed - falling back to direct execution")
                # Fall back to direct execution if plan is invalid
                converted_command = self._convert_natural_language_to_docker(command)
                if converted_command:
                    result = self._execute_shell_command(converted_command)
                    return self._add_message(state, result, "success", docker_result=result)
                else:
                    return self._add_message(state, "❌ Failed to convert command", "error")
            
            # Format the plan for better display
            self._debug_print("dockeragent: Formatting plan for display...")
            formatted_plan = self._format_plan_for_display(plan)
            self._debug_print(f"dockeragent: Formatted plan ready for display")
            
            # Show the plan to the user
            plan_message = f"📋 **Execution Plan for: {command}**\n\n{formatted_plan}\n\nProceed with plan execution?"
            state = self._add_message(state, plan_message, "info")
            self._debug_print("dockeragent: Plan displayed to user")
            
            # Ask for confirmation to execute the plan
            if not self.no_confirm:
                self._debug_print("dockeragent: Requesting user confirmation for plan execution...")
                if not self._confirm_command(f"Execute planned tasks for: {command}"):
                    self._debug_print("dockeragent: User cancelled plan execution")
                    return self._add_message(state, f"⏹️ Plan execution cancelled for: {command}", "cancelled")
                self._debug_print("dockeragent: User confirmed plan execution")
            
            # Allow plan modification if user wants
            if not self.no_confirm:
                self._debug_print("dockeragent: Offering plan modification options...")
                modified_plan = self._allow_plan_modification(plan, command)
                if modified_plan != plan:
                    self._debug_print("dockeragent: Plan modified by user")
                    plan = modified_plan
                else:
                    self._debug_print("dockeragent: Plan unchanged by user")
            
            # Execute the planned tasks
            plan_lines = len(plan.split('\n'))
            self._debug_print(f"dockeragent: Starting execution of {plan_lines} plan lines")
            result = self._execute_planned_tasks(plan, command)
            self._debug_print(f"dockeragent: Plan execution completed with result: {result}")
            return self._add_message(state, result, "success", docker_result=result)
                
        except Exception as e:
            self._debug_print(f"Error in process: {str(e)}")
            return self._add_message(state, f"❌ Docker command failed: {str(e)}", "error")

    def _convert_natural_language_to_docker(self, natural_language: str) -> str:
        """Convert natural language to Docker command using LLM."""
        result = self._convert_natural_language(natural_language, self.system_prompt)
        # Add docker prefix if the result doesn't already start with docker
        if result and not result.strip().startswith("docker"):
            result = f"docker {result}"
        return result
    
    def _is_complex_task(self, task: str) -> bool:
        """Determine if a task is complex and requires planning."""
        complex_keywords = [
            "multi-container", "orchestrate", "deploy", "production", "cluster",
            "network", "volume", "compose", "swarm", "kubernetes", "monitoring",
            "backup", "restore", "migration", "upgrade", "downgrade", "security",
            "performance", "optimization", "troubleshooting", "debugging",
            "setup", "configure", "install", "build", "test", "ci/cd", "pipeline",
            "environment", "staging", "development", "production", "load balancer",
            "database", "cache", "message queue", "logging", "metrics", "alerting"
        ]
        
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in complex_keywords)
    
    def _create_task_plan(self, task: str) -> str:
        """Create a detailed plan for complex Docker tasks."""
        try:
            self._debug_print("Creating task plan for complex operation...")
            
            # Use LLM to create a structured plan
            plan_prompt = f"Task: {task}\n\n{self.planning_prompt}"
            plan = self._convert_natural_language(task, self.planning_prompt)
            
            if not plan:
                return "⚠️ Failed to create plan - proceeding with direct execution"
            
            return plan
            
        except Exception as e:
            self._debug_print(f"Error creating plan: {str(e)}")
            return f"⚠️ Plan creation failed: {str(e)} - proceeding with direct execution"
    
    def _execute_planned_tasks(self, plan: str, original_task: str) -> str:
        """Execute tasks according to the created plan."""
        self._debug_print("Executing planned tasks...")
        
        # Parse the plan and execute step by step
        lines = plan.split('\n')
        results = []
        step_count = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
                
            # Look for actionable items (numbered steps, todos, etc.)
            if any(marker in line.lower() for marker in ['todo:', 'step', 'action:', 'execute:', 'run:']):
                step_count += 1
                self._debug_print(f"Processing step {step_count}: {line}")
                
                # Extract the command from the line
                command = self._extract_command_from_plan_line(line)
                if command:
                    try:
                        self._debug_print(f"dockeragent: Executing command: {command}")
                        result = self._execute_shell_command(command)
                        self._debug_print(f"dockeragent: Command output: {result}")
                        results.append(f"Step {step_count}: ✅ {result}")
                    except Exception as e:
                        error_msg = f"dockeragent: Command failed: {str(e)}"
                        self._debug_print(error_msg)
                        results.append(f"Step {step_count}: ❌ Failed - {str(e)}")
                else:
                    # For non-command lines, just note them
                    self._debug_print(f"dockeragent: No command to execute for step {step_count}: {line}")
                    results.append(f"Step {step_count}: ℹ️ {line}")
        
        if not results:
            return f"⚠️ No actionable steps found in plan. Original task: {original_task}"
        
        return "\n".join(results)
    
    def _normalize_plan(self, plan: str) -> str:
        """Normalize the plan to ensure proper line breaks."""
        # If the plan is all on one line, try to split it intelligently
        if '\n' not in plan or plan.count('\n') < 2:
            self._debug_print("Plan appears to be on one line, attempting to normalize...")
            
            # Split by common markers
            markers = ['TODO:', 'Step', 'Action:', 'Execute:', 'Run:']
            normalized_lines = []
            
            for marker in markers:
                if marker in plan:
                    # Split by this marker and keep the marker
                    parts = plan.split(marker)
                    for i, part in enumerate(parts):
                        if i == 0:  # First part doesn't have the marker
                            if part.strip():
                                normalized_lines.append(part.strip())
                        else:  # Subsequent parts have the marker
                            if part.strip():
                                normalized_lines.append(f"{marker}{part.strip()}")
            
            if normalized_lines:
                return '\n'.join(normalized_lines)
        
        return plan
    
    def _extract_command_from_plan_line(self, line: str) -> str:
        """Extract Docker command from a plan line."""
        # Look for docker commands in the line
        if 'docker' in line.lower():
            # Extract the docker command part
            parts = line.split()
            docker_index = -1
            for i, part in enumerate(parts):
                if part.lower() == 'docker':
                    docker_index = i
                    break
            
            if docker_index >= 0:
                # Only take the docker command and its immediate arguments, not the full description
                command_parts = [parts[docker_index]]
                
                # Look for common docker subcommands
                if docker_index + 1 < len(parts):
                    next_part = parts[docker_index + 1].lower()
                    if next_part in ['ps', 'images', 'containers', 'network', 'volume', 'compose', 'run', 'build', 'pull', 'push', 'stop', 'start', 'restart', 'rm', 'exec', 'logs', 'inspect', 'stats', 'swarm', 'service', 'stack']:
                        command_parts.append(parts[docker_index + 1])
                        
                        # Add common flags if they follow
                        if docker_index + 2 < len(parts):
                            flag_part = parts[docker_index + 2]
                            if flag_part.startswith('-'):
                                command_parts.append(flag_part)
                
                return ' '.join(command_parts)
        
        # Also look for other common command patterns
        if any(cmd in line.lower() for cmd in ['docker-compose', 'docker compose']):
            # Extract compose commands
            parts = line.split()
            compose_index = -1
            for i, part in enumerate(parts):
                if 'compose' in part.lower():
                    compose_index = i - 1  # Include 'docker' part
                    break
            
            if compose_index >= 0:
                return ' '.join(parts[compose_index:compose_index+2])  # Just 'docker compose'
        
        # If no specific command found, return empty to avoid executing incomplete commands
        return ""
    
    def _validate_plan(self, plan: str) -> bool:
        """Validate that the plan contains actionable items."""
        lines = plan.split('\n')
        actionable_lines = 0
        
        for line in lines:
            line = line.strip()
            if any(marker in line.lower() for marker in ['todo:', 'step', 'action:', 'execute:', 'run:', 'docker']):
                actionable_lines += 1
        
        return actionable_lines > 0
    
    def _format_plan_for_display(self, plan: str) -> str:
        """Format the plan for better display."""
        lines = plan.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Format different types of plan elements
            if line.lower().startswith('todo:'):
                formatted_lines.append(f"📝 {line}")
            elif line.lower().startswith('step'):
                formatted_lines.append(f"🔢 {line}")
            elif line.lower().startswith('action:'):
                formatted_lines.append(f"⚡ {line}")
            elif line.lower().startswith('execute:'):
                formatted_lines.append(f"🚀 {line}")
            elif line.lower().startswith('run:'):
                formatted_lines.append(f"▶️ {line}")
            elif 'docker' in line.lower():
                formatted_lines.append(f"🐳 {line}")
            else:
                formatted_lines.append(f"ℹ️ {line}")
        
        return '\n'.join(formatted_lines)
    
    def _allow_plan_modification(self, plan: str, task: str) -> str:
        """Allow user to modify the plan before execution."""
        print(f"\n📝 Current plan for: {task}")
        print("=" * 50)
        print(plan)
        print("=" * 50)
        print("\nOptions:")
        print("1. Press ↵ to proceed with current plan")
        print("2. Type 'edit' to modify the plan")
        print("3. Type 'save' to save plan for later")
        print("4. Type 'load' to load a saved plan")
        print("5. Type 'cancel' to abort")
        
        try:
            response = input("\nYour choice: ").strip().lower()
            
            if response == 'cancel':
                raise KeyboardInterrupt
            elif response == 'edit':
                print("\nEnter your modified plan (press Ctrl+D when done):")
                modified_lines = []
                try:
                    while True:
                        line = input()
                        modified_lines.append(line)
                except EOFError:
                    pass
                
                modified_plan = '\n'.join(modified_lines)
                if modified_plan.strip():
                    print("✅ Plan modified successfully")
                    return modified_plan
                else:
                    print("⚠️ No plan provided, using original")
                    return plan
            elif response == 'save':
                self._save_plan(task, plan)
                print("✅ Plan saved successfully")
                return plan
            elif response == 'load':
                loaded_plan = self._load_and_select_plan()
                if loaded_plan:
                    return loaded_plan
                else:
                    return plan
            else:
                return plan
                
        except KeyboardInterrupt:
            print("\n❌ Plan modification cancelled")
            raise
    
    def _save_plan(self, task: str, plan: str) -> None:
        """Save a plan to a file for later use."""
        try:
            import os
            from datetime import datetime
            
            # Create plans directory if it doesn't exist
            plans_dir = os.path.expanduser("~/.termagent/docker_plans")
            os.makedirs(plans_dir, exist_ok=True)
            
            # Create filename from task and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_task = "".join(c for c in task if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_task = safe_task.replace(' ', '_')[:50]  # Limit length
            filename = f"{safe_task}_{timestamp}.txt"
            filepath = os.path.join(plans_dir, filename)
            
            # Save the plan
            with open(filepath, 'w') as f:
                f.write(f"Task: {task}\n")
                f.write(f"Created: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n")
                f.write(plan)
            
            self._debug_print(f"Plan saved to: {filepath}")
            
        except Exception as e:
            self._debug_print(f"Failed to save plan: {str(e)}")
    
    def _load_saved_plans(self) -> List[str]:
        """Load list of saved plans."""
        try:
            import os
            import glob
            
            plans_dir = os.path.expanduser("~/.termagent/docker_plans")
            if not os.path.exists(plans_dir):
                return []
            
            plan_files = glob.glob(os.path.join(plans_dir, "*.txt"))
            return sorted(plan_files, reverse=True)  # Most recent first
            
        except Exception as e:
            self._debug_print(f"Failed to load saved plans: {str(e)}")
            return []
    
    def _load_and_select_plan(self) -> str:
        """Load and allow user to select a saved plan."""
        saved_plans = self._load_saved_plans()
        
        if not saved_plans:
            print("❌ No saved plans found")
            return ""
        
        print("\n📚 Saved Plans:")
        print("=" * 30)
        
        for i, plan_file in enumerate(saved_plans, 1):
            try:
                import os
                with open(plan_file, 'r') as f:
                    first_line = f.readline().strip()
                    task_name = first_line.replace("Task: ", "")
                    print(f"{i}. {task_name}")
                    print(f"   File: {os.path.basename(plan_file)}")
            except:
                print(f"{i}. [Error reading plan]")
        
        print("=" * 30)
        
        try:
            choice = input("\nSelect plan number (or 'cancel'): ").strip()
            
            if choice.lower() == 'cancel':
                return ""
            
            plan_index = int(choice) - 1
            if 0 <= plan_index < len(saved_plans):
                selected_plan_file = saved_plans[plan_index]
                
                # Read the plan content
                with open(selected_plan_file, 'r') as f:
                    content = f.read()
                
                # Extract just the plan part (after the header)
                lines = content.split('\n')
                plan_start = 0
                for i, line in enumerate(lines):
                    if line.startswith('=' * 50):
                        plan_start = i + 1
                        break
                
                plan_content = '\n'.join(lines[plan_start:]).strip()
                
                print(f"✅ Loaded plan from: {os.path.basename(selected_plan_file)}")
                return plan_content
            else:
                print("❌ Invalid plan number")
                return ""
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Invalid input or cancelled")
            return ""
