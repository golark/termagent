import re
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from agents.base_agent import BaseAgent


class RouterAgent(BaseAgent):
    """Router agent that detects git commands and file operations and routes them to appropriate agents."""
    
    def __init__(self, debug: bool = False, no_confirm: bool = False):
        super().__init__("router_agent", debug, no_confirm)
        
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
        
        # File operation patterns to detect
        self.file_patterns = [
            r'^move\s+',     # move files
            r'^copy\s+',     # copy files
            r'^delete\s+',   # delete files
            r'^remove\s+',   # remove files
            r'^mkdir\s+',    # create directory
            r'^list\s+',     # list files
            r'^find\s+',     # find files
            r'^rename\s+',   # rename files
            r'^pwd$',        # show current directory
            r'^ls$',         # list files
            r'^dir$',        # list files
            r'^edit\s+',     # edit files
            r'^vim\s+',      # edit files with vim
            r'^nano\s+',     # edit files with nano
            r'^open\s+',     # open files
            # Natural language patterns
            r'move\s+.*?\s+to\s+',      # move X to Y
            r'copy\s+.*?\s+to\s+',      # copy X to Y
            r'delete\s+.*',             # delete X
            r'remove\s+.*',             # remove X
            r'create\s+.*?folder',      # create folder
            r'create\s+.*?directory',   # create directory
            r'list\s+.*?files',         # list files
            r'list\s+.*?contents',      # list contents
            r'find\s+.*?files',         # find files
            r'rename\s+.*?\s+to\s+',    # rename X to Y
            r'edit\s+.*?file',          # edit file
            r'open\s+.*?file',          # open file
            r'edit\s+.*?with\s+vim',    # edit with vim
            r'edit\s+.*?with\s+nano',   # edit with nano
        ]
        self.file_command = re.compile('|'.join(self.file_patterns), re.IGNORECASE)
        
        # Additional keywords that might indicate git operations
        self.git_keywords = [
            'commit', 'push', 'pull', 'status', 'add', 'branch', 'checkout',
            'merge', 'log', 'diff', 'stash', 'reset', 'clone', 'init',
            'remote', 'fetch', 'tag', 'rebase', 'cherry-pick', 'repository',
            'repo', 'version control', 'git'
        ]
        
        # Additional keywords that might indicate file operations
        self.file_keywords = [
            'move', 'copy', 'delete', 'remove', 'create', 'list', 'find', 
            'rename', 'folder', 'directory', 'file', 'files', 'backup',
            'transfer', 'duplicate', 'organize', 'sort', 'edit', 'open',
            'vim', 'nano', 'editor'
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
        """Check if the input contains a git command or file operation."""
        messages = state.get("messages", [])
        if not messages:
            self._debug_print("No messages in state")
            return False
        
        # Get the latest user message
        latest_message = messages[-1]
        if isinstance(latest_message, HumanMessage):
            content = latest_message.content.lower()
            self._debug_print(f"Checking content: {content}")
            
            # Check for exact git command patterns
            if self.git_command.search(content):
                self._debug_print(f"Found git command pattern in: {content}")
                return True
            
            # Check for exact file operation patterns
            if self.file_command.search(content):
                self._debug_print(f"Found file operation pattern in: {content}")
                return True
            
            # Check for compound commands
            for pattern in self.compound_patterns:
                if re.search(pattern, content):
                    self._debug_print(f"Found compound command pattern '{pattern}' in: {content}")
                    return True
            
            # Check for git-related keywords
            for keyword in self.git_keywords:
                if keyword in content:
                    self._debug_print(f"Found git keyword '{keyword}' in: {content}")
                    return True
            
            # Check for file-related keywords
            for keyword in self.file_keywords:
                if keyword in content:
                    self._debug_print(f"Found file keyword '{keyword}' in: {content}")
                    return True
            
            self._debug_print(f"No git or file patterns or keywords found in: {content}")
        
        return False
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Route git commands and file operations to appropriate agents."""
        messages = state.get("messages", [])
        latest_message = messages[-1]
        
        if isinstance(latest_message, HumanMessage):
            content = latest_message.content
            
            # Check if this is a git command
            if self._is_git_command(content):
                self._debug_print(f"🔀 Routing to GIT_AGENT: {content}")
                # Route to git agent
                return self._route_to_git_agent(state, content)
            # Check if this is a file operation
            elif self._is_file_operation(content):
                self._debug_print(f"🔀 Routing to FILE_AGENT: {content}")
                # Route to file agent
                return self._route_to_file_agent(state, content)
            else:
                self._debug_print(f"🔀 Routing to REGULAR_COMMAND_HANDLER: {content}")
                # Handle as regular command
                return self._handle_regular_command(state, content)
        
        self._debug_print("No HumanMessage found, returning current state")
        return state
    
    def _is_git_command(self, content: str) -> bool:
        """Check if the content is a git command."""
        content_lower = content.lower()
        
        # Check for exact git command patterns
        if self.git_command.search(content_lower):
            self._debug_print(f"Found exact git command pattern in: {content}")
            return True
        
        # Check for compound commands
        for pattern in self.compound_patterns:
            if re.search(pattern, content_lower):
                self._debug_print(f"Found compound command pattern '{pattern}' in: {content}")
                return True
        
        # Check for git-related keywords
        for keyword in self.git_keywords:
            if keyword in content_lower:
                self._debug_print(f"Found git keyword '{keyword}' in: {content}")
                return True
        
        return False
    
    def _is_file_operation(self, content: str) -> bool:
        """Check if the content is a file operation."""
        content_lower = content.lower()
        
        # Check for exact file operation patterns
        if self.file_command.search(content_lower):
            self._debug_print(f"Found exact file operation pattern in: {content}")
            return True
        
        # Check for file-related keywords
        for keyword in self.file_keywords:
            if keyword in content_lower:
                self._debug_print(f"Found file keyword '{keyword}' in: {content}")
                return True
        
        self._debug_print(f"No file operation patterns found in: {content}")
        return False
    
    def _route_to_git_agent(self, state: Dict[str, Any], command: str) -> Dict[str, Any]:
        """Route the command to the git agent."""
        # Add a message indicating routing to git agent
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Routing git command: {command}"))
        
        # Normalize the command to include "git" prefix if not present
        normalized_command = self._normalize_git_command(command)
        self._debug_print(f"Normalized command: {command} -> {normalized_command}")
        
        return {
            **state,
            "messages": messages,
            "routed_to": "git_agent",
            "last_command": normalized_command
        }
    
    def _route_to_file_agent(self, state: Dict[str, Any], command: str) -> Dict[str, Any]:
        """Route the command to the file agent."""
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Routing file operation: {command}"))
        
        return {
            **state,
            "messages": messages,
            "routed_to": "file_agent",
            "last_command": command
        }
    
    def _normalize_git_command(self, command: str) -> str:
        """Normalize git command to include 'git' prefix if not present."""
        command_lower = command.lower().strip()
        
        # If it already starts with "git", return as is
        if command_lower.startswith("git"):
            self._debug_print(f"Command already has git prefix: {command}")
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
                self._debug_print(f"Found compound command pattern '{pattern}', replacing with: {replacement}")
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
                    result = f"git {default}"
                    self._debug_print(f"Found git command '{cmd}', using default: {result}")
                    return result
                else:
                    # Extract the command and its arguments
                    args = command[len(cmd):].strip()
                    result = f"git {cmd} {args}"
                    self._debug_print(f"Found git command '{cmd}' with args '{args}': {result}")
                    return result
        
        # If not recognized, just add "git" prefix
        result = f"git {command}"
        self._debug_print(f"Command not recognized, adding git prefix: {result}")
        return result
    
    def _handle_regular_command(self, state: Dict[str, Any], command: str) -> Dict[str, Any]:
        """Handle non-git and non-file commands."""
        self._debug_print(f"Handling regular command: {command}")
        messages = state.get("messages", [])
        messages.append(AIMessage(content=f"Routing regular command: {command}"))
        
        return {
            **state,
            "messages": messages,
            "routed_to": "regular_command",
            "last_command": command
        }
