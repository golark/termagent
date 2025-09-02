import os
import sys
import subprocess
from typing import Optional, Dict, Any
import anthropic

# Load system prompt at module level
with open('system_prompt.txt', 'r', encoding='utf-8') as f:
    system_prompt = f.read().strip()

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
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
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

def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> str:
    """Execute a tool with the given parameters"""
    if tool_name == "bash":
        return execute_bash(parameters.get("command", ""))
    elif tool_name == "read_file":
        return read_file(parameters.get("filepath", ""))
    elif tool_name == "write_file":
        return write_file(parameters.get("filepath", ""), parameters.get("content", ""))
    else:
        return f"Unknown tool: {tool_name}"

def call_anthropic(message: str, api_key: Optional[str] = None) -> str:
    try:
        # Get API key from parameter or environment
        key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not key:
            return "Error: No Anthropic API key provided. Set ANTHROPIC_API_KEY environment variable."
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=key)
        
        # Make the API call with system message and tools
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": message}
            ],
            tools=TOOLS
        )
        
        print(f'response: {response}')

        # Handle tool calls in a loop until stop_reason is end_turn
        messages = [{"role": "user", "content": message}]
        current_response = response
        
        while current_response.stop_reason == "tool_use":
            # Collect all tool uses from the response
            tool_uses = []
            text_content = ""
            
            for content_block in current_response.content:
                if content_block.type == "text":
                    text_content += content_block.text
                elif content_block.type == "tool_use":
                    tool_uses.append(content_block)
            
            # Print text content if any
            if text_content:
                print(text_content)
            
            # Execute all tools
            tool_results = []
            for tool_use in tool_uses:
                tool_result = execute_tool(tool_use.name, tool_use.input)
                print(f'Tool {tool_use.name} result: {tool_result}')
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": tool_result
                })
            
            # Add assistant response to messages
            messages.append({
                "role": "assistant",
                "content": current_response.content
            })
            
            # Add tool results to messages
            messages.append({
                "role": "user",
                "content": tool_results
            })
            
            # Get next response from Anthropic
            current_response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system_prompt,
                messages=messages,
                tools=TOOLS
            )
        
        # Return the final text response
        if current_response.content:
            final_text = ""
            for content_block in current_response.content:
                if content_block.type == "text":
                    final_text += content_block.text
            return final_text if final_text else "No text response received"
        
        return "No response received"
        
    except Exception as e:
        return f"Error calling Anthropic API: {str(e)}"
