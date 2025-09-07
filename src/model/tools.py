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


def ask_tool_permission(tool_name: str, parameters: Dict[str, Any]) -> bool:
    """Ask user for permission before executing a tool"""
    
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
    """Execute a tool with the given parameters"""
    
    # Skip permission for safe operations like reading files
    if tool_name == "read_file":
        return read_file(parameters.get("filepath", ""))
    
    # Ask for user permission before executing other tools
    if not ask_tool_permission(tool_name, parameters):
        return "Tool execution cancelled by user"
    
    if tool_name == "bash":
        return execute_bash(parameters.get("command", ""))
    elif tool_name == "write_file":
        return write_file(parameters.get("filepath", ""), parameters.get("content", ""))
    else:
        return f"Unknown tool: {tool_name}"
