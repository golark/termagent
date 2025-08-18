#!/usr/bin/env python3
"""
Shell tool for agents to execute shell commands.
Provides a clean interface for command execution with proper error handling.
"""

import os
import subprocess
import shlex
from typing import Dict, Any, Tuple, Optional
from termagent.shell_commands import ShellCommandHandler


class ShellTool:
    """Tool for agents to execute shell commands."""
    
    def __init__(self, debug: bool = False, no_confirm: bool = False):
        self.debug = debug
        self.no_confirm = no_confirm
        self.shell_handler = ShellCommandHandler(debug=debug, no_confirm=no_confirm)
    
    def _debug_print(self, message: str):
        if self.debug:
            print(f"shell_tool | {message}")
    
    def execute(self, command: str, cwd: str = None) -> Dict[str, Any]:
        """Execute a shell command and return structured results."""
        if cwd is None:
            cwd = os.getcwd()
        
        self._debug_print(f"Executing command: {command} in {cwd}")
        
        try:
            success, output, return_code, new_cwd = self.shell_handler.execute_command(command, cwd)
            
            result = {
                "success": success,
                "command": command,
                "output": output,
                "return_code": return_code,
                "working_directory": new_cwd,
                "error": None
            }
            
            if not success:
                result["error"] = output
            
            self._debug_print(f"Command execution {'succeeded' if success else 'failed'}")
            return result
            
        except Exception as e:
            self._debug_print(f"Command execution error: {e}")
            return {
                "success": False,
                "command": command,
                "output": None,
                "return_code": None,
                "working_directory": cwd,
                "error": str(e)
            }
    
    def is_shell_command(self, command: str) -> bool:
        """Check if a command is a known shell command."""
        return self.shell_handler.is_shell_command(command)
    
    def is_interactive(self, command: str) -> bool:
        """Check if a command is interactive."""
        return self.shell_handler.is_interactive_command(command)
    
    def is_navigation(self, command: str) -> bool:
        """Check if a command is a navigation command."""
        return self.shell_handler.is_navigation_command(command)
    
    def get_working_directory(self) -> str:
        """Get the current working directory."""
        return os.getcwd()
    
    def change_directory(self, path: str) -> Dict[str, Any]:
        """Change to a specific directory."""
        command = f"cd {path}"
        return self.execute(command)
    
    def list_directory(self, path: str = ".") -> Dict[str, Any]:
        """List contents of a directory."""
        command = f"ls -la {path}"
        return self.execute(command)
    
    def check_file_exists(self, path: str) -> Dict[str, Any]:
        """Check if a file or directory exists."""
        command = f"test -e {path} && echo 'exists' || echo 'not found'"
        return self.execute(command)
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get detailed information about a file."""
        command = f"ls -la {path}"
        return self.execute(command)
    
    def search_files(self, pattern: str, directory: str = ".") -> Dict[str, Any]:
        """Search for files matching a pattern."""
        command = f"find {directory} -name '{pattern}' -type f"
        return self.execute(command)
    
    def grep_content(self, pattern: str, files: str = "*") -> Dict[str, Any]:
        """Search for content in files."""
        command = f"grep -r '{pattern}' {files}"
        return self.execute(command)
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        commands = {
            "os": "uname -s",
            "kernel": "uname -r",
            "hostname": "hostname",
            "user": "whoami",
            "shell": "echo $SHELL",
            "pwd": "pwd"
        }
        
        results = {}
        for key, cmd in commands.items():
            result = self.execute(cmd)
            if result["success"]:
                results[key] = result["output"].strip()
            else:
                results[key] = None
        
        return {
            "success": True,
            "system_info": results,
            "command": "system_info",
            "output": results,
            "return_code": 0,
            "working_directory": self.get_working_directory(),
            "error": None
        }
    
    def get_process_info(self) -> Dict[str, Any]:
        """Get information about running processes."""
        command = "ps aux --sort=-%cpu | head -10"
        return self.execute(command)
    
    def get_disk_usage(self, path: str = ".") -> Dict[str, Any]:
        """Get disk usage information."""
        command = f"du -sh {path}"
        return self.execute(command)
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory usage information."""
        command = "free -h"
        return self.execute(command)
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network interface information."""
        command = "ip addr show"
        return self.execute(command)
    
    def validate_command(self, command: str) -> Dict[str, Any]:
        """Validate if a command is safe to execute."""
        # Basic safety checks
        dangerous_patterns = [
            "rm -rf /",
            "rm -rf /*",
            "dd if=/dev/zero",
            "mkfs",
            "fdisk",
            "parted",
            "> /dev/sda",
            "> /dev/hda"
        ]
        
        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return {
                    "success": False,
                    "command": command,
                    "output": None,
                    "return_code": None,
                    "working_directory": self.get_working_directory(),
                    "error": f"Command contains dangerous pattern: {pattern}",
                    "safe": False
                }
        
        return {
            "success": True,
            "command": command,
            "output": None,
            "return_code": None,
            "working_directory": self.get_working_directory(),
            "error": None,
            "safe": True
        }
    
    def get_available_tools(self) -> Dict[str, Any]:
        """Get information about available shell tools."""
        tools = {
            "basic_execution": "execute(command, cwd=None) - Execute any shell command",
            "file_operations": {
                "list_directory": "list_directory(path='.') - List directory contents",
                "check_file_exists": "check_file_exists(path) - Check if file/directory exists",
                "get_file_info": "get_file_info(path) - Get detailed file information",
                "search_files": "search_files(pattern, directory='.') - Search for files",
                "grep_content": "grep_content(pattern, files='*') - Search file contents"
            },
            "system_info": {
                "get_system_info": "get_system_info() - Get basic system information",
                "get_process_info": "get_process_info() - Get running process information",
                "get_disk_usage": "get_disk_usage(path='.') - Get disk usage",
                "get_memory_info": "get_memory_info() - Get memory usage",
                "get_network_info": "get_network_info() - Get network information"
            },
            "utilities": {
                "is_shell_command": "is_shell_command(command) - Check if command is known",
                "is_interactive": "is_interactive(command) - Check if command is interactive",
                "is_navigation": "is_navigation(command) - Check if command is navigation",
                "validate_command": "validate_command(command) - Validate command safety",
                "get_working_directory": "get_working_directory() - Get current directory"
            }
        }
        
        return {
            "success": True,
            "command": "get_available_tools",
            "output": tools,
            "return_code": 0,
            "working_directory": self.get_working_directory(),
            "error": None,
            "tools": tools
        }
    
    def suggest_command_improvements(self, command: str, context: str = "") -> Dict[str, Any]:
        """Suggest improvements for a command based on context and best practices."""
        suggestions = []
        improvements = []
        
        try:
            # Check for common command improvements
            if "ls" in command and " -la" not in command and " -l" not in command:
                suggestions.append("Consider using 'ls -la' for detailed listing")
                improvements.append(command.replace("ls", "ls -la"))
            
            if "find" in command and " -type f" not in command and " -type d" not in command:
                suggestions.append("Consider specifying file type with -type f or -type d")
            
            if "grep" in command and " -r" not in command and " -R" not in command:
                if "find" not in command:  # Only suggest if not using find
                    suggestions.append("Consider using 'grep -r' for recursive search")
                    improvements.append(command.replace("grep", "grep -r"))
            
            if "docker" in command and "ps" in command and " -a" not in command:
                suggestions.append("Consider using 'docker ps -a' to see all containers")
                improvements.append(command.replace("docker ps", "docker ps -a"))
            
            if "git" in command and "status" in command and " --porcelain" not in command:
                suggestions.append("Consider using 'git status --porcelain' for script-friendly output")
                improvements.append(command.replace("git status", "git status --porcelain"))
            
            # Check for potential performance improvements
            if "find ." in command and " -maxdepth" not in command:
                suggestions.append("Consider adding -maxdepth to limit search depth for performance")
            
            if "grep" in command and " | head" not in command and " | tail" not in command:
                suggestions.append("Consider limiting output with | head or | tail for large results")
            
        except Exception as e:
            self._debug_print(f"Error suggesting improvements: {e}")
        
        return {
            "success": True,
            "command": command,
            "suggestions": suggestions,
            "improvements": improvements,
            "context": context,
            "working_directory": self.get_working_directory(),
            "error": None
        }
    
    def get_command_context(self, command: str) -> Dict[str, Any]:
        """Get contextual information about a command to help with execution."""
        context = {
            "command_type": "unknown",
            "dependencies": [],
            "environment_requirements": [],
            "potential_issues": [],
            "suggested_prerequisites": []
        }
        
        try:
            # Determine command type
            if command.startswith("git "):
                context["command_type"] = "git"
                context["dependencies"].append("git")
                context["suggested_prerequisites"].append("Check if in git repository: git rev-parse --git-dir")
            
            elif command.startswith("docker "):
                context["command_type"] = "docker"
                context["dependencies"].append("docker")
                context["suggested_prerequisites"].append("Check docker daemon: docker ps")
            
            elif command.startswith("npm ") or command.startswith("yarn "):
                context["command_type"] = "node_package_manager"
                context["dependencies"].extend(["node", "npm/yarn"])
                context["suggested_prerequisites"].append("Check package.json exists")
            
            elif command.startswith("pip ") or command.startswith("python "):
                context["command_type"] = "python"
                context["dependencies"].append("python")
                context["suggested_prerequisites"].append("Check virtual environment activation")
            
            elif "|" in command:
                context["command_type"] = "pipeline"
                context["suggested_prerequisites"].append("Verify all commands in pipeline are available")
            
            elif "&&" in command:
                context["command_type"] = "sequential"
                context["suggested_prerequisites"].append("Verify all commands can succeed")
            
            # Check for file operations
            if any(op in command for op in ["rm", "mv", "cp", "mkdir", "touch"]):
                context["environment_requirements"].append("File system write permissions")
                context["potential_issues"].append("Check file/directory existence before operations")
            
            # Check for network operations
            if any(op in command for op in ["curl", "wget", "ssh", "scp"]):
                context["environment_requirements"].append("Network connectivity")
                context["potential_issues"].append("Verify network access and credentials")
            
        except Exception as e:
            self._debug_print(f"Error getting command context: {e}")
            context["error"] = str(e)
        
        return {
            "success": True,
            "command": command,
            "context": context,
            "working_directory": self.get_working_directory(),
            "error": None
        }
    
    def preflight_check(self, command: str) -> Dict[str, Any]:
        """Perform a preflight check before executing a command."""
        checks = {
            "safety": self.validate_command(command),
            "context": self.get_command_context(command),
            "improvements": self.suggest_command_improvements(command),
            "file_dependencies": self._check_file_dependencies(command),
            "system_requirements": self._check_system_requirements(command)
        }
        
        # Overall assessment
        all_safe = all(check.get("safe", True) for check in checks.values() if isinstance(check, dict) and "safe" in check)
        has_issues = any(check.get("potential_issues") for check in checks.values() if isinstance(check, dict) and "potential_issues" in check)
        
        return {
            "success": True,
            "command": command,
            "checks": checks,
            "overall_safe": all_safe,
            "has_issues": has_issues,
            "working_directory": self.get_working_directory(),
            "error": None
        }
    
    def _check_file_dependencies(self, command: str) -> Dict[str, Any]:
        """Check if required files exist for the command."""
        dependencies = []
        missing = []
        
        try:
            # Extract potential file paths from command
            import re
            file_patterns = [
                r'([a-zA-Z0-9_\-\.\/]+\.(py|js|ts|java|cpp|c|h|txt|md|json|yaml|yml|toml|ini|conf|sh|bash|zsh))',
                r'([a-zA-Z0-9_\-\.\/]+\.(py|js|ts|java|cpp|c|h|txt|md|json|yaml|yml|toml|ini|conf|sh|bash|zsh))',
                r'([a-zA-Z0-9_\-\.\/]+\.(py|js|ts|java|cpp|c|h|txt|md|json|yaml|yml|toml|ini|conf|sh|bash|zsh))'
            ]
            
            for pattern in file_patterns:
                matches = re.findall(pattern, command)
                for match in matches:
                    if isinstance(match, tuple):
                        file_path = match[0]
                    else:
                        file_path = match
                    
                    if file_path and not file_path.startswith("-"):
                        dependencies.append(file_path)
                        if not self.check_file_exists(file_path)["success"]:
                            missing.append(file_path)
            
        except Exception as e:
            self._debug_print(f"Error checking file dependencies: {e}")
        
        return {
            "dependencies": dependencies,
            "missing": missing,
            "all_exist": len(missing) == 0
        }
    
    def _check_system_requirements(self, command: str) -> Dict[str, Any]:
        """Check if system requirements are met for the command."""
        requirements = []
        missing = []
        
        try:
            # Check for common command availability
            common_commands = ["git", "docker", "npm", "yarn", "pip", "python", "node", "java", "gcc", "make"]
            
            for cmd in common_commands:
                if cmd in command:
                    requirements.append(cmd)
                    # Check if command is available
                    result = self.execute(f"which {cmd}")
                    if not result["success"]:
                        missing.append(cmd)
            
        except Exception as e:
            self._debug_print(f"Error checking system requirements: {e}")
        
        return {
            "requirements": requirements,
            "missing": missing,
            "all_available": len(missing) == 0
        }
