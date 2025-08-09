import re
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from agents.base_agent import BaseAgent


class RouterAgent(BaseAgent):
    """Router agent that detects git commands and routes them to git agent."""
    
    def __init__(self):
        super().__init__("router")
        # Git command patterns to detect - both with and without "git" prefix
        self.git_patterns = [
            r'^git\s+',  # Starts with "git "
            r'^git$',    # Just "git"
            # Common git commands without "git" prefix
            r'^commit\s+',  # commit message
            r'^commit$',    # just commit
            r'^push\s+',    # push to remote
            r'^push$',      # just push
            r'^pull\s+',    # pull from remote
            r'^pull$',      # just pull
            r'^status$',    # git status
            r'^add\s+',     # add files
            r'^add$',       # just add
            r'^branch\s+',  # branch operations
            r'^branch$',    # just branch
            r'^checkout\s+', # checkout
            r'^checkout$',   # just checkout
            r'^merge\s+',   # merge
            r'^merge$',     # just merge
            r'^log\s+',     # log
            r'^log$',       # just log
            r'^diff\s+',    # diff
            r'^diff$',      # just diff
            r'^stash\s+',   # stash
            r'^stash$',     # just stash
            r'^reset\s+',   # reset
            r'^reset$',     # just reset
            r'^clone\s+',   # clone
            r'^clone$',     # just clone
            r'^init$',      # init
            r'^remote\s+',  # remote operations
            r'^remote$',    # just remote
            r'^fetch\s+',   # fetch
            r'^fetch$',     # just fetch
            r'^tag\s+',     # tag
            r'^tag$',       # just tag
            r'^rebase\s+',  # rebase
            r'^rebase$',    # just rebase
            r'^cherry-pick\s+', # cherry-pick
            r'^cherry-pick$',   # just cherry-pick
        ]
        self.git_command = re.compile('|'.join(self.git_patterns), re.IGNORECASE)
        
        # Additional keywords that might indicate git operations
        self.git_keywords = [
            'commit', 'push', 'pull', 'status', 'add', 'branch', 'checkout',
            'merge', 'log', 'diff', 'stash', 'reset', 'clone', 'init',
            'remote', 'fetch', 'tag', 'rebase', 'cherry-pick', 'repository',
            'repo', 'version control', 'git'
        ]
        
        # Compound command patterns
        self.compound_patterns = [
            r'commit\s+and\s+push',
            r'commit\s*&\s*push',
            r'add\s+and\s+commit',
            r'add\s*&\s*commit',
            r'add\s+commit\s+push',
            r'add\s+commit\s*&\s*push',
        ]
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if the input contains a git command."""
        messages = state.get("messages", [])
        if not messages:
            return False
        
        # Get the latest user message
        latest_message = messages[-1]
        if isinstance(latest_message, HumanMessage):
            content = latest_message.content.lower()
            # Check for exact git command patterns
            if self.git_command.search(content):
                return True
            
            # Check for compound commands
            for pattern in self.compound_patterns:
                if re.search(pattern, content):
                    return True
            
            # Check for git-related keywords
            for keyword in self.git_keywords:
                if keyword in content:
                    return True
        
        return False
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Route git commands to git agent."""
        messages = state.get("messages", [])
        latest_message = messages[-1]
        
        if isinstance(latest_message, HumanMessage):
            content = latest_message.content
            
            # Check if this is a git command
            if self._is_git_command(content):
                # Route to git agent
                return self._route_to_git_agent(state, content)
            else:
                # Handle as regular command
                return self._handle_regular_command(state, content)
        
        return state
    
    def _is_git_command(self, content: str) -> bool:
        """Check if the content is a git command."""
        content_lower = content.lower()
        
        # Check for exact git command patterns
        if self.git_command.search(content_lower):
            return True
        
        # Check for compound commands
        for pattern in self.compound_patterns:
            if re.search(pattern, content_lower):
                return True
        
        # Check for git-related keywords
        for keyword in self.git_keywords:
            if keyword in content_lower:
                return True
        
        return False
    
    def _route_to_git_agent(self, state: Dict[str, Any], command: str) -> Dict[str, Any]:
        """Route the command to the git agent."""
        # Add a message indicating routing to git agent
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Routing git command: {command}"))
        
        # Normalize the command to include "git" prefix if not present
        normalized_command = self._normalize_git_command(command)
        
        return {
            **state,
            "messages": messages,
            "routed_to": "git_agent",
            "last_command": normalized_command
        }
    
    def _normalize_git_command(self, command: str) -> str:
        """Normalize git command to include 'git' prefix if not present."""
        command_lower = command.lower().strip()
        
        # If it already starts with "git", return as is
        if command_lower.startswith("git"):
            return command
        
        # Check for compound commands first
        compound_commands = {
            r'commit\s+and\s+push': 'git add . && git commit -m "Auto-commit" && git push',
            r'commit\s*&\s*push': 'git add . && git commit -m "Auto-commit" && git push',
            r'add\s+and\s+commit': 'git add . && git commit -m "Auto-commit"',
            r'add\s*&\s*commit': 'git add . && git commit -m "Auto-commit"',
            r'add\s+commit\s+push': 'git add . && git commit -m "Auto-commit" && git push',
            r'add\s+commit\s*&\s*push': 'git add . && git commit -m "Auto-commit" && git push',
        }
        
        for pattern, replacement in compound_commands.items():
            if re.search(pattern, command_lower):
                return replacement
        
        # Map common git commands to their full form
        git_commands = {
            'commit': 'commit -m "Auto-commit"',
            'push': 'push',
            'pull': 'pull',
            'status': 'status',
            'add': 'add .',
            'branch': 'branch',
            'checkout': 'checkout',
            'merge': 'merge',
            'log': 'log',
            'diff': 'diff',
            'stash': 'stash',
            'reset': 'reset',
            'clone': 'clone',
            'init': 'init',
            'remote': 'remote',
            'fetch': 'fetch',
            'tag': 'tag',
            'rebase': 'rebase',
            'cherry-pick': 'cherry-pick'
        }
        
        # Check if it's a known git command
        for cmd, default in git_commands.items():
            if command_lower.startswith(cmd):
                # Handle commands with arguments
                if command_lower == cmd:
                    return f"git {default}"
                else:
                    # Extract the command and its arguments
                    args = command[len(cmd):].strip()
                    return f"git {cmd} {args}"
        
        # If not recognized, just add "git" prefix
        return f"git {command}"
    
    def _handle_regular_command(self, state: Dict[str, Any], command: str) -> Dict[str, Any]:
        """Handle non-git commands."""
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Routing regular command: {command}"))
        
        return {
            **state,
            "messages": messages,
            "routed_to": "regular_command",
            "last_command": command
        }
