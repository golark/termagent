import os
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage
from termagent.agents.base_agent import BaseAgent

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class K8sAgent(BaseAgent):
    """K8s agent that handles k8s cluster administration commands with LLM interface."""
    
    def __init__(self, llm_model: str = "gpt-3.5-turbo", debug: bool = False, no_confirm: bool = False):
        super().__init__("k8s_agent", debug, no_confirm)
        
        # Initialize LLM using base class method
        self._initialize_llm(llm_model)
        
        # System prompt for LLM
        self.system_prompt = """Convert natural language to zsh-compatible K8s commands. Return only the command, nothing else.

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

Convert this request to a K8s command:"""
        
        # Enhanced system prompt for queries
        self.query_system_prompt = """You are a Kubernetes expert. Given a question about K8s clusters, generate the most appropriate kubectl commands to answer it.

For informational queries, you may need to run multiple commands to gather complete information. Return a JSON array of commands that will answer the question.

IMPORTANT: 
- Return ONLY valid JSON array of strings
- Each string should be a complete kubectl command
- Commands must work in zsh shell
- Use zsh-compatible syntax

Examples:
Question: "how many k8 clusters are running"
Response: ["kubectl config get-contexts", "kubectl cluster-info"]

Question: "what pods are running in the default namespace"
Response: ["kubectl get pods -n default"]

Question: "show me the status of all deployments"
Response: ["kubectl get deployments --all-namespaces", "kubectl get deployments --all-namespaces -o wide"]

Question: "what's the health of my cluster"
Response: ["kubectl get componentstatuses", "kubectl get nodes", "kubectl get events --sort-by='.lastTimestamp' --tail=20"]

Convert this question to K8s commands:"""
        
        self._debug_print("🤖 K8sAgent initialized successfully")

    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this agent should handle the current input."""
        should_handle = state.get("routed_to") == "k8s_agent"
        self._debug_print(f"should_handle: {should_handle} (routed_to: {state.get('routed_to')})")
        return should_handle
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process k8s commands with LLM support for natural language conversion."""
        command = state.get("last_command", "")
        is_query = state.get("is_query", False)
        self._debug_print(f"Processing {'query' if is_query else 'command'}: {command}")
        
        if not command:
            self._debug_print("No command provided, returning current state")
            return state
        
        try:
            if is_query:
                # Handle informational query
                self._debug_print("Handling informational query...")
                return self._handle_query(state, command)
            else:
                # Handle action command
                self._debug_print("Converting natural language to k8s command...")
                converted_command = self._convert_natural_language_to_k8s(command)
                
                # Ask for confirmation before executing
                if not self._confirm_operation_execution(converted_command, "command"):
                    self._debug_print("Command cancelled by user")
                    return self._add_message(state, f"⏹️ Command cancelled: {converted_command}", "cancelled")
                
                # Execute the k8s command
                result = self._execute_shell_command(converted_command)
                return self._add_message(state, result, "success", k8s_result=result)
                
        except Exception as e:
            self._debug_print(f"Error in process: {str(e)}")
            return self._add_message(state, f"❌ K8s operation failed: {str(e)}", "error")
    
    def _handle_query(self, state: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Handle informational queries by converting them to appropriate kubectl commands."""
        try:
            # Convert query to kubectl commands using LLM
            if self.llm:
                commands = self._convert_query_to_commands(query)
                if commands:
                    return self._execute_query_commands(state, query, commands)
                else:
                    return self._add_message(state, "❌ Failed to convert query to commands", "error")
            else:
                # Fallback for when LLM is not available
                commands = self._fallback_query_commands(query)
                return self._execute_query_commands(state, query, commands)
                
        except Exception as e:
            self._debug_print(f"Error handling query: {str(e)}")
            return self._add_message(state, f"❌ Query handling failed: {str(e)}", "error")
    
    def _convert_query_to_commands(self, query: str) -> list:
        """Convert a natural language query to a list of kubectl commands using LLM."""
        try:
            messages = [
                {"role": "system", "content": self.query_system_prompt},
                {"role": "user", "content": query}
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Try to extract JSON from the response
            import json
            # Look for JSON content between ```json and ``` markers
            import re
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
            
            commands = json.loads(json_str)
            self._debug_print(f"LLM generated commands: {commands}")
            return commands
            
        except Exception as e:
            self._debug_print(f"LLM query conversion failed: {e}")
            return []
    
    def _fallback_query_commands(self, query: str) -> list:
        """Fallback method to generate commands when LLM is not available."""
        query_lower = query.lower()
        
        # Common query patterns and their corresponding commands
        if 'cluster' in query_lower and ('how many' in query_lower or 'running' in query_lower):
            return ["kubectl config get-contexts", "kubectl cluster-info"]
        elif 'pod' in query_lower and ('running' in query_lower or 'status' in query_lower):
            return ["kubectl get pods --all-namespaces"]
        elif 'deployment' in query_lower and ('status' in query_lower or 'running' in query_lower):
            return ["kubectl get deployments --all-namespaces"]
        elif 'service' in query_lower:
            return ["kubectl get services --all-namespaces"]
        elif 'node' in query_lower:
            return ["kubectl get nodes", "kubectl top nodes"]
        elif 'health' in query_lower or 'status' in query_lower:
            return ["kubectl get componentstatuses", "kubectl get nodes"]
        else:
            # Generic fallback
            return ["kubectl cluster-info", "kubectl get pods --all-namespaces"]
    
    def _execute_query_commands(self, state: Dict[str, Any], query: str, commands: list) -> Dict[str, Any]:
        """Execute multiple commands to answer a query and format the response."""
        messages = state.get("messages", [])
        
        # Create query execution message
        query_msg = f"🔍 Executing commands to answer: {query}\n"
        query_msg += f"📋 Commands to run: {len(commands)}\n"
        messages.append(AIMessage(content=query_msg))
        
        # Execute each command and collect results
        results = []
        for i, command in enumerate(commands, 1):
            self._debug_print(f"Executing query command {i}/{len(commands)}: {command}")
            
            # Execute the command
            result = self._execute_shell_command(command)
            
            # Check if the result indicates success or failure
            if result.startswith("Error:"):
                results.append(f"❌ Command {i}: {command}\n{result}")
            else:
                results.append(f"✅ Command {i}: {command}\n{result}")
        
        # Format the final response
        response = f"🔍 Query: {query}\n\n"
        response += "📊 Results:\n"
        response += "=" * 50 + "\n"
        
        for result in results:
            response += f"{result}\n\n"
        
        # Add summary
        if len(commands) > 1:
            response += f"📋 Total commands executed: {len(commands)}\n"
        
        return self._add_message(state, response, "success", k8s_result=response)
    
    def _convert_natural_language_to_k8s(self, natural_language: str) -> str:
        """Convert natural language to k8s command using LLM."""
        result = self._convert_natural_language(natural_language, self.system_prompt)
        # Add kubectl prefix if the result doesn't already start with kubectl
        if not result.lower().startswith("kubectl "):
            result = f"kubectl {result}"
        return result

