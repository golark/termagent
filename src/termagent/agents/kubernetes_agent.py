import os
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage
from termagent.agents.base_agent import BaseAgent

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class KubernetesAgent(BaseAgent):
    """Kubernetes agent that handles k8s cluster administration commands with LLM interface."""
    
    def __init__(self, llm_model: str = "gpt-3.5-turbo", debug: bool = False, no_confirm: bool = False):
        super().__init__("kubernetes_agent", debug, no_confirm)
        
        # Initialize LLM using base class method
        self._initialize_llm(llm_model)
        
        # System prompt for LLM
        self.system_prompt = """Convert natural language to zsh-compatible Kubernetes commands. Return only the command, nothing else.

IMPORTANT: Commands must work in zsh shell. Use zsh-compatible syntax.

Examples:
- "check cluster status" → "kubectl cluster-info"
- "get all pods" → "kubectl get pods --all-namespaces"
- "get pods in default namespace" → "kubectl get pods"
- "describe pod nginx" → "kubectl describe pod nginx"
- "get services" → "kubectl get services"
- "get nodes" → "kubectl get nodes"
- "check cluster health" → "kubectl get componentstatuses"
- "get deployments" → "kubectl get deployments"
- "scale deployment nginx to 3 replicas" → "kubectl scale deployment nginx --replicas=3"
- "apply yaml file" → "kubectl apply -f deployment.yaml"
- "delete pod nginx" → "kubectl delete pod nginx"
- "port forward service nginx 8080:80" → "kubectl port-forward service/nginx 8080:80"
- "get logs from pod nginx" → "kubectl logs nginx"
- "exec into pod nginx" → "kubectl exec -it nginx -- /bin/bash"
- "check events" → "kubectl get events --sort-by='.lastTimestamp'"
- "get resource usage" → "kubectl top nodes && kubectl top pods"

ZSH COMPATIBILITY NOTES:
- Use single quotes for strings: 'pod-name'
- Use double quotes for variables: "kubectl get pods -l \"$LABEL\""
- Escape special characters properly
- Use zsh-compatible command chaining: && for success, || for fallback
- Avoid bash-specific syntax that might not work in zsh

Convert this request to a Kubernetes command:"""
        
        self._debug_print("🤖 KubernetesAgent initialized successfully")

    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this agent should handle the current input."""
        should_handle = state.get("routed_to") == "kubernetes_agent"
        self._debug_print(f"should_handle: {should_handle} (routed_to: {state.get('routed_to')})")
        return should_handle
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process kubernetes commands with LLM support for natural language conversion."""
        command = state.get("last_command", "")
        self._debug_print(f"Processing command: {command}")
        
        if not command:
            self._debug_print("No command provided, returning current state")
            return state
        
        try:
            # Convert natural language to kubernetes command using LLM
            self._debug_print("Converting natural language to kubernetes command...")
            converted_command = self._convert_natural_language_to_k8s(command)
            
            # Ask for confirmation before executing
            if not self._confirm_operation_execution(converted_command, "command"):
                self._debug_print("Command cancelled by user")
                return self._add_message(state, f"⏹️ Command cancelled: {converted_command}", "cancelled")
            
            # Execute the kubernetes command
            result = self._execute_shell_command(converted_command)
            return self._add_message(state, result, "success", kubernetes_result=result)
                
        except Exception as e:
            self._debug_print(f"Error in process: {str(e)}")
            return self._add_message(state, f"❌ Kubernetes command failed: {str(e)}", "error")
    
    def _convert_natural_language_to_k8s(self, natural_language: str) -> str:
        """Convert natural language to kubernetes command using LLM."""
        result = self._convert_natural_language(natural_language, self.system_prompt)
        # Add kubectl prefix if the result doesn't already start with kubectl
        if not result.lower().startswith("kubectl "):
            result = f"kubectl {result}"
        return result

