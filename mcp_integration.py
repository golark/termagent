import asyncio
import json
from typing import Dict, Any, Optional
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
)
import subprocess


class GitMCPTool:
    """MCP tool for git operations."""
    
    def __init__(self, name: str, description: str, command: str):
        self.name = name
        self.description = description
        self.command = command
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Git command arguments"
                    }
                },
                "required": ["args"]
            }
        }


class GitMCPServer:
    """MCP server for git operations."""
    
    def __init__(self):
        self.tools = [
            GitMCPTool(
                "git_status",
                "Get the current git status",
                "status"
            ),
            GitMCPTool(
                "git_add",
                "Add files to staging area",
                "add"
            ),
            GitMCPTool(
                "git_commit",
                "Commit staged changes",
                "commit"
            ),
            GitMCPTool(
                "git_push",
                "Push commits to remote",
                "push"
            ),
            GitMCPTool(
                "git_pull",
                "Pull changes from remote",
                "pull"
            ),
            GitMCPTool(
                "git_log",
                "Show commit history",
                "log"
            ),
            GitMCPTool(
                "git_branch",
                "List or create branches",
                "branch"
            ),
            GitMCPTool(
                "git_checkout",
                "Switch branches or restore files",
                "checkout"
            ),
            GitMCPTool(
                "git_merge",
                "Merge branches",
                "merge"
            ),
            GitMCPTool(
                "git_diff",
                "Show differences",
                "diff"
            ),
        ]
    
    async def handle_list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """Handle list tools request."""
        return ListToolsResult(
            tools=[
                Tool(
                    name=tool.name,
                    description=tool.description,
                    inputSchema=tool.to_dict()["inputSchema"]
                )
                for tool in self.tools
            ]
        )
    
    async def handle_call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Handle call tool request."""
        tool_name = request.name
        args = request.arguments.get("args", [])
        
        # Find the tool
        tool = next((t for t in self.tools if t.name == tool_name), None)
        if not tool:
            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Unknown tool: {tool_name}"
                    }
                ]
            )
        
        try:
            # Execute the git command
            result = subprocess.run(
                ["git", tool.command] + args,
                capture_output=True,
                text=True,
                cwd="."
            )
            
            if result.returncode == 0:
                return CallToolResult(
                    content=[
                        {
                            "type": "text",
                            "text": result.stdout.strip()
                        }
                    ]
                )
            else:
                return CallToolResult(
                    content=[
                        {
                            "type": "text",
                            "text": f"Error: {result.stderr.strip()}"
                        }
                    ]
                )
        except Exception as e:
            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Failed to execute git command: {str(e)}"
                    }
                ]
            )


class MCPClient:
    """MCP client for connecting to the git agent."""
    
    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or "stdio://"
        self.server = GitMCPServer()
    
    async def call_git_agent(self, command: str) -> str:
        """Call the git agent via MCP."""
        try:
            # Parse the command
            if command.lower().startswith("git "):
                command = command[4:]
            elif command.lower() == "git":
                command = "status"
            
            # Split into command and args
            parts = command.split()
            if not parts:
                return "No command specified"
            
            command_name = parts[0]
            args = parts[1:]
            
            # Map command to tool
            tool_mapping = {
                "status": "git_status",
                "add": "git_add",
                "commit": "git_commit",
                "push": "git_push",
                "pull": "git_pull",
                "log": "git_log",
                "branch": "git_branch",
                "checkout": "git_checkout",
                "merge": "git_merge",
                "diff": "git_diff",
            }
            
            tool_name = tool_mapping.get(command_name)
            if not tool_name:
                return f"Unknown git command: {command_name}"
            
            # Call the tool
            request = CallToolRequest(
                name=tool_name,
                arguments={"args": args}
            )
            
            result = await self.server.handle_call_tool(request)
            return result.content[0]["text"] if result.content else "No result"
            
        except Exception as e:
            return f"Failed to call git agent: {str(e)}"
    
    def call_git_agent_sync(self, command: str) -> str:
        """Synchronous wrapper for calling the git agent."""
        return asyncio.run(self.call_git_agent(command))


# Global MCP client instance
mcp_client = MCPClient()
