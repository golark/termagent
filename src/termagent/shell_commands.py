#!/usr/bin/env python3
"""
Shell command detector and executor for TermAgent.
Handles direct execution of known shell commands.
"""

import subprocess
import shlex
from typing import Tuple, Optional


class ShellCommandDetector:
    """Detects and executes known shell commands directly."""
    
    # Basic shell commands that can be executed directly with output capture
    KNOWN_COMMANDS = {'ls', 'pwd', 'mkdir', 'rm', 'cp', 'grep', 'find', 'cat', 'head', 'tail', 'sort', 'uniq', 'wc', 'echo'}
    
    # Git commands that can be executed directly
    GIT_COMMANDS = {
        'git status', 'git add', 'git commit', 'git push', 'git pull', 'git fetch',
        'git branch', 'git checkout', 'git merge', 'git rebase', 'git log', 'git diff',
        'git show', 'git stash', 'git reset', 'git revert', 'git tag', 'git remote',
        'git clone', 'git init', 'git config', 'git help', 'git clean', 'git rm',
        'git mv', 'git blame', 'git bisect', 'git cherry-pick', 'git reflog',
        'git worktree', 'git submodule', 'git notes', 'git archive', 'git bundle'
    }
    
    # Git command patterns (base commands that can have arguments)
    GIT_COMMAND_PATTERNS = {
        'git add', 'git commit', 'git push', 'git pull', 'git fetch', 'git branch',
        'git checkout', 'git merge', 'git rebase', 'git log', 'git diff', 'git show',
        'git stash', 'git reset', 'git revert', 'git tag', 'git remote', 'git clone',
        'git init', 'git config', 'git help', 'git status', 'git clean', 'git rm',
        'git mv', 'git blame', 'git bisect', 'git cherry-pick', 'git reflog',
        'git worktree', 'git submodule', 'git notes', 'git archive', 'git bundle'
    }
    
    # Interactive text editors that need special handling (run in foreground, block until closed)
    INTERACTIVE_EDITORS = {'vi', 'vim', 'emacs', 'nano'}
    
    # Interactive system commands that need special handling (run in foreground, block until closed)
    INTERACTIVE_COMMANDS = {
        # System monitoring
        'top', 'htop', 'btop', 'bashtop', 'atop', 'glances',
        # File viewing
        'less', 'more', 'most',
        # Network monitoring
        'iftop', 'iotop', 'nethogs', 'nload', 'slurm', 'ttyplot',
        # Documentation
        'man', 'info',
        # Disk usage
        'ncdu',
        # Fun/visual
        'asciiquarium', 'cmatrix', 'hollywood',
        # Development tools
        'python', 'python3', 'node', 'nodejs', 'irb', 'pry', 'ghci', 'gdb', 'lldb'
    }
    
    def __init__(self, debug: bool = False, no_confirm: bool = False):
        self.debug = debug
        self.no_confirm = no_confirm
    
    def _debug_print(self, message: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"shell_comm   | {message}")
    
    def is_known_command(self, command: str) -> bool:
        """Check if the command is a known shell command."""
        if not command or not command.strip():
            return False
        
        command_lower = command.strip().lower()
        
        # Check for git commands first (exact match for common patterns)
        if command_lower in self.GIT_COMMANDS:
            return True
        
        parts = shlex.split(command.strip())
        if not parts:
            return False
        
        base_command = parts[0].lower()
        
        # Check if it's a git command with arguments
        if base_command == 'git' and len(parts) > 1:
            git_subcommand = f"git {parts[1]}"
            if git_subcommand in self.GIT_COMMAND_PATTERNS:
                return True
        
        return base_command in self.KNOWN_COMMANDS or base_command in self.INTERACTIVE_EDITORS or base_command in self.INTERACTIVE_COMMANDS
    
    def execute_command(self, command: str, cwd: str = ".") -> Tuple[bool, str, Optional[int]]:
        """Execute a shell command directly."""
        if not self.is_known_command(command):
            return False, "Command is not a known shell command", None
        
        self._debug_print(f"executing: {command}")
        
        # Check if this is a git command
        is_git = self.is_git_command(command)
        if is_git:
            self._debug_print(f"detected git command: {command}")
        
        # Check if this is an interactive command (editor or system command)
        parts = shlex.split(command.strip())
        base_command = parts[0].lower()
        is_interactive = base_command in self.INTERACTIVE_EDITORS or base_command in self.INTERACTIVE_COMMANDS
        
        try:
            if is_interactive:
                # For interactive commands, start them in the foreground
                if base_command in self.INTERACTIVE_EDITORS:
                    command_type = "text editor"
                    action = "editing"
                else:
                    command_type = "system command"
                    action = "monitoring"
                
                self._debug_print(f"Starting interactive {command_type}: {command}")
                # Note: This will block until the command is closed
                process_result = subprocess.run(
                    command,
                    shell=True,
                    executable="/bin/zsh",
                    cwd=cwd
                )
                return True, f"✅ Interactive {command_type} {base_command} finished {action} (exit code: {process_result.returncode})", process_result.returncode
            else:
                # Regular command execution with output capture
                # Check if command contains shell operators that require shell=True
                shell_operators = ['|', '>', '<', '>>', '<<', '&&', '||', ';', '(', ')', '`', '$(']
                needs_shell = any(op in command for op in shell_operators)
                
                if needs_shell:
                    # Use shell=True for commands with operators
                    process_result = subprocess.run(
                        command,
                        shell=True,
                        executable="/bin/zsh",
                        capture_output=True,
                        text=True,
                        cwd=cwd,
                        timeout=30
                    )
                else:
                    # Use shlex.split for simple commands without operators
                    args = shlex.split(command)
                    process_result = subprocess.run(
                        args,
                        capture_output=True,
                        text=True,
                        cwd=cwd,
                        timeout=30
                    )
                
                if process_result.returncode == 0:
                    output = process_result.stdout.strip() if process_result.stdout.strip() else "✅ Command executed successfully"
                    return True, output, process_result.returncode
                else:
                    error_msg = process_result.stderr.strip() if process_result.stderr.strip() else "Command failed with no error output"
                    return False, f"❌ Command failed: {error_msg}", process_result.returncode
                 
        except subprocess.TimeoutExpired:
            return False, f"⏰ Command timed out after 30 seconds: {command}", None
        except FileNotFoundError:
            return False, f"❌ Command not found: {command}", None
        except Exception as e:
            return False, f"❌ Command execution error: {command}\nError: {str(e)}", None
    
    def should_execute_directly(self, command: str) -> bool:
        """Determine if a command should be executed directly or routed to an agent."""
        return self.is_known_command(command)
    
    def is_interactive_command(self, command: str) -> bool:
        """Check if a command is interactive (editor or system command)."""
        if not command or not command.strip():
            return False
        
        parts = shlex.split(command.strip())
        if not parts:
            return False
        
        base_command = parts[0].lower()
        return base_command in self.INTERACTIVE_EDITORS or base_command in self.INTERACTIVE_COMMANDS
    
    def get_command_type(self, command: str) -> str:
        """Get the type of command for better user feedback."""
        if not command or not command.strip():
            return "unknown"
        
        command_lower = command.strip().lower()
        
        # Check for git commands first
        if command_lower in self.GIT_COMMANDS:
            return "git_command"
        
        parts = shlex.split(command.strip())
        if not parts:
            return "unknown"
        
        base_command = parts[0].lower()
        
        # Check if it's a git command with arguments
        if base_command == 'git' and len(parts) > 1:
            git_subcommand = f"git {parts[1]}"
            if git_subcommand in self.GIT_COMMAND_PATTERNS:
                return "git_command"
        
        if base_command in self.INTERACTIVE_EDITORS:
            return "interactive_editor"
        elif base_command in self.INTERACTIVE_COMMANDS:
            return "interactive_command"
        elif base_command in self.KNOWN_COMMANDS:
            return "basic_command"
        else:
            return "unknown"
    
    def get_git_command_suggestions(self) -> list:
        """Get a list of commonly used git commands for suggestions."""
        return sorted(list(self.GIT_COMMANDS))
    
    def is_git_command(self, command: str) -> bool:
        """Check if a command is a git command."""
        command_type = self.get_command_type(command)
        return command_type == "git_command"
