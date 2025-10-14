"""Tool functions for TermAgent."""

import subprocess
import os
from typing import Dict, Any, Optional
from src.utils.config import Config, AutonomyLevel
from src.utils.permissions import request_write_access
from src.utils.rules import add_rule, remove_rule, list_rules as get_rules_list


# Define available tools
TOOLS = [
    {
        "name": "bash",
        "description": "Execute bash commands in the terminal. Use this to run any shell command, check files, install packages, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file to read"
                }
            },
            "required": ["filepath"]
        }
    },
    {
        "name": "edit_file",
        "description": "Write content to a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["filepath", "content"]
        }
    },
    {
        "name": "list_dir",
        "description": "List the contents of a directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Path to the directory to list"
                }
            },
            "required": ["directory_path"]
        }
    },
    {
        "name": "delete_file",
        "description": "Delete a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file to delete"
                }
            },
            "required": ["filepath"]
        }
    },
    {
        "name": "rules",
        "description": "Manage user-defined rules and guidelines. Rules are appended to the system prompt and persist across sessions. Changes require restart to take effect.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'list', 'add', or 'remove'",
                    "enum": ["list", "add", "remove"]
                },
                "rule": {
                    "type": "string",
                    "description": "The rule text to add (required for 'add' action)"
                },
                "rule_id": {
                    "type": "integer",
                    "description": "The rule ID to remove (required for 'remove' action)"
                },
                "description": {
                    "type": "string",
                    "description": "Optional description for the rule (used with 'add' action)"
                }
            },
            "required": ["action"]
        }
    }
]


def execute_bash(command: str) -> str:
    """Execute a bash command and return the output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = f"Exit code: {result.returncode}\n"
        if result.stdout:
            output += f"{result.stdout}\n"
        if result.stderr:
            output += f"{result.stderr}\n"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


def read_file(filepath: str) -> str:
    """Read the contents of a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File '{filepath}' not found"
    except Exception as e:
        return f"Error reading file: {str(e)}"


def edit_file(filepath: str, content: str) -> str:
    """Write content to a file"""
    try:
        # Check write permissions first
        if not request_write_access(filepath):
            return f"Error: Write permission denied for '{filepath}'"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{filepath}'"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def list_dir(directory_path: str) -> str:
    """List the contents of a directory"""
    try:
        if not os.path.exists(directory_path):
            return f"Error: Directory '{directory_path}' does not exist"
        
        if not os.path.isdir(directory_path):
            return f"Error: '{directory_path}' is not a directory"
        
        items = os.listdir(directory_path)
        if not items:
            return f"Directory '{directory_path}' is empty"
        
        # Sort items with directories first
        dirs = []
        files = []
        
        for item in items:
            item_path = os.path.join(directory_path, item)
            if os.path.isdir(item_path):
                dirs.append(f"{item}/")
            else:
                files.append(item)
        
        # Combine and sort
        sorted_items = sorted(dirs) + sorted(files)
        
        result = f"Contents of '{directory_path}':\n"
        for item in sorted_items:
            result += f"  {item}\n"
        
        return result.strip()
        
    except PermissionError:
        return f"Error: Permission denied accessing '{directory_path}'"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def delete_file(filepath: str) -> str:
    """Delete a file"""
    try:
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist"
        
        if os.path.isdir(filepath):
            return f"Error: '{filepath}' is a directory, not a file"
        
        # Check write permissions first
        if not request_write_access(filepath):
            return f"Error: Write permission denied for '{filepath}'"
        
        os.remove(filepath)
        return f"Successfully deleted file '{filepath}'"
        
    except PermissionError:
        return f"Error: Permission denied deleting '{filepath}'"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


def manage_rules(action: str, rule: str = None, rule_id: int = None, description: str = None) -> str:
    """Manage user-defined rules"""
    try:
        if action == "list":
            rules = get_rules_list()
            if not rules:
                return "No rules defined."
            
            result = "User-Defined Rules:\n"
            for r in rules:
                if r.get('description'):
                    result += f"  {r['id']}. {r['rule']} ({r['description']})\n"
                else:
                    result += f"  {r['id']}. {r['rule']}\n"
            return result.strip()
        
        elif action == "add":
            if not rule:
                return "Error: 'rule' parameter is required for 'add' action"
            
            new_rule_id = add_rule(rule, description)
            return f"Successfully added rule #{new_rule_id}: {rule}"
        
        elif action == "remove":
            if rule_id is None:
                return "Error: 'rule_id' parameter is required for 'remove' action"
            
            if remove_rule(rule_id):
                return f"Successfully removed rule #{rule_id}"
            else:
                return f"Error: Rule #{rule_id} not found"
        
        else:
            return f"Error: Invalid action '{action}'. Must be 'list', 'add', or 'remove'"
            
    except Exception as e:
        return f"Error managing rules: {str(e)}"


def requires_permission(tool_name: str, parameters: Dict[str, Any] = None) -> bool:

    if tool_name == "edit_file":
        return True
    elif tool_name == "delete_file":
        return True
    elif tool_name == "read_file":
        return False
    elif tool_name == "list_dir":
        return False
    elif tool_name == "rules":
        return False
    elif tool_name == "bash":
        if parameters:
            command = parameters.get("command", "").strip()
            return not is_safe_bash_command(command)
        return True
    
    return True


def is_safe_bash_command(command: str) -> bool:
    """Check if a bash command is safe and doesn't require permission"""
    if not command:
        return False
    
    # Safe read-only commands
    safe_commands = [
        'ls', 'pwd', 'whoami', 'id', 'groups', 'date', 'uptime', 'uname',
        'ps', 'top', 'htop', 'df', 'du', 'free', 'history', 'env', 'printenv',
        'which', 'whereis', 'locate', 'find', 'grep', 'cat', 'head', 'tail',
        'wc', 'sort', 'uniq', 'cut', 'tr', 'awk', 'sed', 'less', 'more',
        'man', 'info', 'apropos', 'whatis', 'file', 'stat', 'lsblk', 'lscpu',
        'lspci', 'lsusb', 'mount', 'df', 'free', 'ps', 'netstat', 'ss',
        'ping', 'traceroute', 'nslookup', 'dig', 'curl', 'wget', 'git status',
        'git log', 'git diff', 'git branch', 'git remote', 'git show',
        'docker ps', 'docker images', 'docker logs', 'kubectl get', 'kubectl describe'
    ]
    
    # Get the base command (first word)
    base_command = command.split()[0].lower()
    
    # Check if it's a safe command
    if base_command in safe_commands:
        return True
    
    # Check for safe command patterns
    safe_patterns = [
        r'^ls\s+',  # ls with any arguments
        r'^cat\s+',  # cat with any arguments
        r'^grep\s+',  # grep with any arguments
        r'^find\s+',  # find with any arguments
        r'^git\s+(status|log|diff|branch|remote|show|add|commit|push|pull)',  # safe git commands
        r'^docker\s+(ps|images|logs|inspect)',  # safe docker commands
        r'^kubectl\s+(get|describe|logs)',  # safe kubectl commands
    ]
    
    import re
    for pattern in safe_patterns:
        if re.match(pattern, command, re.IGNORECASE):
            return True
    
    return False

def ask_tool_permission(tool_name: str, parameters: Dict[str, Any]) -> bool:
    
    print('')
    if tool_name == "bash":
        command = parameters.get("command", "")
        print(f"$ {command}")
    elif tool_name == "read_file":
        filepath = parameters.get("filepath", "")
        print(f"File: {filepath}")
    elif tool_name == "list_dir":
        directory_path = parameters.get("directory_path", "")
        print(f"Directory: {directory_path}")
    elif tool_name == "delete_file":
        filepath = parameters.get("filepath", "")
        print(f"File: {filepath}")
        print("This will permanently delete the file.")
    elif tool_name == "edit_file":
        filepath = parameters.get("filepath", "")
        content = parameters.get("content", "")
        print(f"File: {filepath}")
        print(f"Content length: {len(content)} characters")
        print("This will write content to a file.")
    else:
        print(f"Tool: {tool_name}")
        print(f"Parameters: {parameters}")
    
    while True:
        response = input("↵ to accept x to reject").strip().lower()
        print('')
        if response in ['', 'y', 'yes']:
            return True
        elif response in ['x']:
            return False
        else:
            print("Please press ↵ to accept or 'x' to reject.")


def execute_tool(tool_name: str, parameters: Dict[str, Any], config: Optional[Config] = None) -> str:
    """Execute a tool with optional autonomy level configuration."""
    
    # Use default config if none provided
    if config is None:
        config = Config()
    
    # Check if permission should be asked based on autonomy level
    if config.should_ask_permission(tool_name, parameters):
        if not ask_tool_permission(tool_name, parameters):
            return "Tool execution cancelled by user"
    
    if tool_name == "bash":
        return execute_bash(parameters.get("command", ""))
    elif tool_name == "edit_file":
        return edit_file(parameters.get("filepath", ""), parameters.get("content", ""))
    elif tool_name == "delete_file":
        return delete_file(parameters.get("filepath", ""))
    elif tool_name == "read_file":
        return read_file(parameters.get("filepath", ""))
    elif tool_name == "list_dir":
        return list_dir(parameters.get("directory_path", ""))
    elif tool_name == "rules":
        return manage_rules(
            parameters.get("action", ""),
            parameters.get("rule"),
            parameters.get("rule_id"),
            parameters.get("description")
        )
    else:
        return f"Unknown tool: {tool_name}"
