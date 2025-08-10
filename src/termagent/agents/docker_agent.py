from typing import Dict, Any
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

        self._debug_print("🤖 DockerAgent initialized successfully")

    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this agent should handle the current input."""
        should_handle = state.get("routed_to") == "docker_agent"
        self._debug_print(f"should_handle: {should_handle} (routed_to: {state.get('routed_to')})")
        return should_handle

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process Docker commands with LLM support for natural language conversion."""
        command = state.get("last_command", "")
        self._debug_print(f"Processing command: {command}")

        if not command:
            return self._add_message(state, "❌ No command provided", "error")

        try:
            # Convert natural language to Docker command using LLM
            self._debug_print("Converting natural language to Docker command...")
            converted_command = self._convert_natural_language_to_docker(command)
            
            if not converted_command:
                return self._add_message(state, "❌ Failed to convert command", "error")

            self._debug_print(f"Converted command: {converted_command}")

            # Ask for confirmation unless in no-confirm mode
            if not self.no_confirm:
                if not self._confirm_command(converted_command):
                    return self._add_message(state, f"⏹️ Command cancelled: {converted_command}", "cancelled")
            
            # Execute the Docker command
            result = self._execute_shell_command(converted_command)
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
