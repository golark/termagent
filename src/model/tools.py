"""Tool functions for TermAgent."""

import subprocess
from typing import Dict, Any


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
        "name": "write_file",
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


def write_file(filepath: str, content: str) -> str:
    """Write content to a file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{filepath}'"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def requires_permission(tool_name: str, parameters: Dict[str, Any] = None) -> bool:

    if tool_name == "write_file":
        return True
    elif tool_name == "read_file":
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
    elif tool_name == "write_file":
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


def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> str:

    if requires_permission(tool_name, parameters):
        if not ask_tool_permission(tool_name, parameters):
            return "Tool execution cancelled by user"
    
    if tool_name == "bash":
        return execute_bash(parameters.get("command", ""))
    elif tool_name == "write_file":
        return write_file(parameters.get("filepath", ""), parameters.get("content", ""))
    elif tool_name == "read_file":
        return read_file(parameters.get("filepath", ""))
    else:
        return f"Unknown tool: {tool_name}"
