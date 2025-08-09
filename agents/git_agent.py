import subprocess
import re
import os
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from agents.base_agent import BaseAgent

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class GitAgent(BaseAgent):
    """Git agent that handles git-specific commands and operations with LLM interface."""
    
    def __init__(self, llm_model: str = "gpt-3.5-turbo"):
        super().__init__("git_agent")
        
        # Initialize LLM if available and API key is set
        self.llm = None
        if LLM_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(model=llm_model, temperature=0)
            except Exception as e:
                print(f"Warning: LLM initialization failed: {e}")
        
        # System prompt for LLM
        self.system_prompt = """You are a Git expert assistant. Your job is to convert natural language requests into valid Git commands.

Available Git commands and their common usage:
- `git status` - Check the current status of the repository
- `git add <files>` - Add files to staging area (use . for all files)
- `git commit -m "<message>"` - Commit staged changes with a message
- `git push` - Push commits to remote repository
- `git pull` - Pull changes from remote repository
- `git log` - Show commit history
- `git branch` - List branches (use -a for all branches)
- `git checkout <branch>` - Switch to a branch
- `git merge <branch>` - Merge a branch into current branch
- `git diff` - Show differences
- `git stash` - Stash changes
- `git reset` - Reset changes
- `git clone <url>` - Clone a repository
- `git init` - Initialize a new repository
- `git remote` - Manage remote repositories
- `git fetch` - Fetch from remote repository
- `git tag` - Manage tags
- `git rebase` - Rebase commits
- `git cherry-pick` - Apply specific commits

Rules:
1. Always return only the Git command, nothing else
2. Use appropriate flags and options based on the request
3. For commit messages, use descriptive but concise messages
4. If multiple commands are needed, separate them with "&&"
5. If the request is unclear, use the most common interpretation
6. For file operations, use "." if no specific files are mentioned

Examples:
- "check status" → "git status"
- "add all files" → "git add ."
- "commit with message update readme" → "git commit -m \"update readme\""
- "push to remote" → "git push"
- "create and switch to new branch feature" → "git checkout -b feature"
- "commit and push" → "git add . && git commit -m \"Auto-commit\" && git push"

Now convert the following natural language request to a Git command:"""

    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this agent should handle the current input."""
        # This agent is called via MCP from the router
        return state.get("routed_to") == "git_agent"
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process git commands with LLM support for natural language conversion."""
        command = state.get("last_command", "")
        if not command:
            return state
        
        try:
            # First, try to convert natural language to git command using LLM
            converted_command = self._convert_natural_language_to_git(command)
            
            # Check if this is a compound command with &&
            if "&&" in converted_command:
                return self._process_compound_command(state, converted_command)
            
            # Execute the git command directly
            result = self._execute_git_command(converted_command)
            return self._add_success_message(state, f"Executed: {converted_command}\nResult: {result}")
                
        except Exception as e:
            return self._add_error_message(state, str(e))
    
    def _convert_natural_language_to_git(self, natural_language: str) -> str:
        """Convert natural language to git command using LLM."""
        try:
            # Check if it's already a git command
            if self._is_already_git_command(natural_language):
                return natural_language
            
            # If LLM is not available, use fallback parsing
            if not self.llm:
                return self._fallback_parse(natural_language)
            
            # Create messages for LLM
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=natural_language)
            ]
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Extract the git command from the response
            git_command = response.content.strip()
            
            # Clean up the response (remove quotes, extra spaces, etc.)
            git_command = re.sub(r'^["\']|["\']$', '', git_command)  # Remove surrounding quotes
            git_command = re.sub(r'\s+', ' ', git_command)  # Normalize spaces
            
            return git_command
            
        except Exception as e:
            # If LLM fails, try to fall back to basic parsing
            print(f"LLM conversion failed: {e}, using fallback parsing")
            return self._fallback_parse(natural_language)
    
    def _is_already_git_command(self, command: str) -> bool:
        """Check if the command is already a valid git command."""
        command_lower = command.lower().strip()
        
        # Check if it starts with git
        if command_lower.startswith("git "):
            return True
        
        # Check if it's a known git command without prefix
        git_commands = ["status", "add", "commit", "push", "pull", "log", "branch", 
                       "checkout", "merge", "diff", "stash", "reset", "clone", "init", 
                       "remote", "fetch", "tag", "rebase", "cherry-pick"]
        
        for git_cmd in git_commands:
            if command_lower.startswith(git_cmd):
                return True
        
        return False
    
    def _fallback_parse(self, natural_language: str) -> str:
        """Fallback parsing for natural language when LLM is not available."""
        text = natural_language.lower()
        
        # Basic keyword-based conversion
        if "status" in text:
            return "git status"
        elif "add" in text or "stage" in text:
            return "git add ."
        elif "commit" in text:
            # Try to extract commit message
            if "message" in text:
                # Extract message after "message" or "with message"
                message_match = re.search(r'(?:message|with message)\s+(.+)', text)
                if message_match:
                    message = message_match.group(1).strip()
                    return f'git commit -m "{message}"'
                else:
                    return 'git commit -m "Auto-commit"'
            else:
                return 'git commit -m "Auto-commit"'
        elif "push" in text:
            return "git push"
        elif "pull" in text:
            return "git pull"
        elif "log" in text or "history" in text:
            return "git log"
        elif "branch" in text:
            return "git branch"
        elif "checkout" in text or "switch" in text:
            # Try to extract branch name
            branch_match = re.search(r'(?:to|branch|checkout)\s+(\w+)', text)
            if branch_match:
                branch = branch_match.group(1)
                return f"git checkout {branch}"
            else:
                return "git checkout"
        elif "merge" in text:
            return "git merge"
        elif "diff" in text:
            return "git diff"
        else:
            # If we can't parse it, just add git prefix
            return f"git {natural_language}"
    
    def _process_compound_command(self, state: Dict[str, Any], command: str) -> Dict[str, Any]:
        """Process compound commands with && operators."""
        # Split the command by &&
        commands = [cmd.strip() for cmd in command.split("&&")]
        results = []
        
        for cmd in commands:
            if not cmd:
                continue
            
            try:
                # Execute the git command directly
                result = self._execute_git_command(cmd)
                results.append(f"{cmd}: {result}")
                    
            except Exception as e:
                results.append(f"{cmd}: Error - {str(e)}")
        
        # Combine all results
        combined_result = " | ".join(results)
        return self._add_success_message(state, combined_result)
    
    def _execute_git_command(self, command: str) -> str:
        """Execute a git command directly."""
        try:
            # Parse the command to extract git and its arguments
            if command.lower().startswith("git "):
                # Remove "git" prefix and split arguments
                args = command[4:].split()
                git_args = ["git"] + args
            else:
                # If no "git" prefix, add it
                args = command.split()
                git_args = ["git"] + args
            
            # Execute the command
            result = subprocess.run(
                git_args,
                capture_output=True,
                text=True,
                cwd="."
            )
            
            if result.returncode == 0:
                return result.stdout.strip() if result.stdout.strip() else "Command executed successfully"
            else:
                error_msg = result.stderr.strip() if result.stderr.strip() else "Unknown error"
                return f"Error: {error_msg}"
                
        except Exception as e:
            return f"Failed to execute git command: {str(e)}"
    
    def _add_success_message(self, state: Dict[str, Any], result: str) -> Dict[str, Any]:
        """Add a success message to the state."""
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Git command executed successfully: {result}"))
        
        return {
            **state,
            "messages": messages,
            "git_result": result
        }
    
    def _add_error_message(self, state: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Add an error message to the state."""
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Git command failed: {error}"))
        
        return {
            **state,
            "messages": messages,
            "error": error
        }
