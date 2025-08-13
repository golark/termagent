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
    KNOWN_COMMANDS = {'ls', 'll', 'pwd', 'mkdir', 'rm', 'cp', 'grep', 'find', 'cat', 'head', 'tail', 'sort', 'uniq', 'wc', 'echo'}
    
    # Directory navigation commands that need special handling
    NAVIGATION_COMMANDS = {'cd'}
    
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
            if git_subcommand in self.GIT_COMMANDS:
                return True
        
        result = base_command in self.KNOWN_COMMANDS or base_command in self.INTERACTIVE_EDITORS or base_command in self.INTERACTIVE_COMMANDS or base_command in self.NAVIGATION_COMMANDS
        
        return result
    
    def execute_command(self, command: str, cwd: str = ".") -> Tuple[bool, str, Optional[int], str]:
        """Execute a shell command directly."""
        self._debug_print(f"execute_command called with command: '{command}', cwd: '{cwd}'")
        
        if not self.is_known_command(command):
            self._debug_print(f"command '{command}' is not a known command")
            return False, "Command is not a known shell command", None, cwd
        
        self._debug_print(f"executing: {command}")
        
        # Check if this is a git command
        is_git = self.is_git_command(command)
        if is_git:
            self._debug_print(f"detected git command: {command}")
        
        # Check if this is a navigation command (cd)
        is_navigation = self.is_navigation_command(command)
        if is_navigation:
            self._debug_print(f"detected navigation command: {command}")
            # Handle cd command specially - it changes working directory
            success, message, new_cwd = self.change_directory(command, cwd)
            if success:
                # Show the new working directory after successful cd
                message += f"\n{self.show_current_directory(new_cwd)}"
                return True, message, 0, new_cwd
            else:
                return False, message, 1, cwd
        
        # Check if this is pwd command to show current directory
        if command.strip().lower() == "pwd":
            self._debug_print("detected pwd command")
            return True, self.show_current_directory(cwd), 0, cwd
        
        # Handle command aliases
        if command.strip().lower() == "ll":
            self._debug_print("detected ll command (alias for ls -la)")
            # Execute ls -la directly instead of recursive call
            try:
                process_result = subprocess.run(
                    ["ls", "-la"],
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=30
                )
                
                if process_result.returncode == 0:
                    output = process_result.stdout.strip() if process_result.stdout.strip() else "✅ Command executed successfully"
                    return True, output, process_result.returncode, cwd
                else:
                    error_msg = process_result.stderr.strip() if process_result.stderr.strip() else "Command failed with no error output"
                    return False, f"❌ Command failed: {error_msg}", process_result.returncode, cwd
                    
            except subprocess.TimeoutExpired:
                return False, f"⏰ Command timed out after 30 seconds: ll", None, cwd
            except FileNotFoundError:
                return False, f"❌ Command not found: ll", None, cwd
            except Exception as e:
                return False, f"❌ Command execution error: ll\nError: {str(e)}", None, cwd
        
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
                return True, f"✅ Interactive {command_type} {base_command} finished {action} (exit code: {process_result.returncode})", process_result.returncode, cwd
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
                    return True, output, process_result.returncode, cwd
                else:
                    error_msg = process_result.stderr.strip() if process_result.stderr.strip() else "Command failed with no error output"
                    return False, f"❌ Command failed: {error_msg}", process_result.returncode, cwd
                 
        except subprocess.TimeoutExpired:
            return False, f"⏰ Command timed out after 30 seconds: {command}", None, cwd
        except FileNotFoundError:
            return False, f"❌ Command not found: {command}", None, cwd
        except Exception as e:
            return False, f"❌ Command execution error: {command}\nError: {str(e)}", None, cwd
    
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
        elif base_command in self.NAVIGATION_COMMANDS:
            return "navigation_command"
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
    
    def is_navigation_command(self, command: str) -> bool:
        """Check if a command is a navigation command (cd)."""
        if not command or not command.strip():
            return False
        
        parts = shlex.split(command.strip())
        if not parts:
            return False
        
        base_command = parts[0].lower()
        return base_command in self.NAVIGATION_COMMANDS
    
    def change_directory(self, command: str, current_cwd: str) -> Tuple[bool, str, str]:
        """Handle cd command and return new working directory."""
        self._debug_print(f"change_directory called with command: '{command}', current_cwd: '{current_cwd}'")
        
        if not self.is_navigation_command(command):
            self._debug_print(f"command '{command}' is not a navigation command")
            return False, "Not a navigation command", current_cwd
        
        parts = shlex.split(command.strip())
        if len(parts) < 2:
            # cd without arguments goes to home directory
            import os
            home_dir = os.path.expanduser("~")
            self._debug_print(f"cd: changing to home directory: {home_dir}")
            return True, f"✅ Changed directory to: {home_dir}", home_dir
        
        target_path = parts[1]
        
        # Handle special cd arguments
        if target_path == "-":
            # cd - goes to previous directory (we'll need to track this)
            self._debug_print("cd: attempting to go to previous directory (not implemented)")
            return False, "❌ cd - (previous directory) not implemented yet", current_cwd
        
        # Handle ~ for home directory
        if target_path.startswith("~"):
            import os
            home_dir = os.path.expanduser(target_path)
            self._debug_print(f"cd: expanding home directory: {target_path} -> {home_dir}")
            target_path = home_dir
        
        # Resolve relative paths
        import os
        if os.path.isabs(target_path):
            # Absolute path
            new_cwd = target_path
        else:
            # Relative path
            new_cwd = os.path.join(current_cwd, target_path)
        
        # Normalize the path
        new_cwd = os.path.normpath(new_cwd)
        
        # Check if directory exists
        if not os.path.isdir(new_cwd):
            return False, f"❌ Directory does not exist: {new_cwd}", current_cwd
        
        # Check if we have permission to access
        if not os.access(new_cwd, os.R_OK):
            return False, f"❌ Permission denied accessing directory: {new_cwd}", current_cwd
        
        self._debug_print(f"cd: changing from {current_cwd} to {new_cwd}")
        return True, f"✅ Changed directory to: {new_cwd}", new_cwd
    
    def get_current_directory(self) -> str:
        """Get the current working directory."""
        import os
        return os.getcwd()
    
    def show_current_directory(self, cwd: str = None) -> str:
        """Get a formatted string showing the current working directory."""
        if cwd is None:
            import os
            cwd = os.getcwd()
        return f"📁 Current working directory: {cwd}"
