#!/usr/bin/env python3
"""
Shell command detector and executor for TermAgent.
Handles direct execution of known shell commands.
"""

import os
import subprocess
import shlex
import re
from typing import Tuple, Optional, List, Dict


class ShellCommandDetector:
    """Detects and executes known shell commands directly."""
    
    BASIC_COMMANDS = {'ls', 'll', 'pwd', 'mkdir', 'rm', 'cp', 'grep', 'find', 'cat', 'head', 'tail', 'sort', 'uniq', 'wc', 'echo', 'which'}
    NAVIGATION_COMMANDS = {'cd'}
    COMMAND_PATTERNS = [
        r'^which\s+\w+$',                    # which <executable>
        r'^git\s+\w+$',                      # git <subcommand>
        r'^git\s+\w+\s+\w+$',                # git <subcommand> <argument>
        r'^git\s+\w+\s+\w+\s+\w+$',          # git <subcommand> <arg1> <arg2>
        
        # Package manager commands
        r'^apt\s+\w+$',                      # apt <command>
        r'^apt\s+\w+\s+\w+$',                # apt <command> <package>
        r'^brew\s+\w+$',                     # brew <command>
        r'^brew\s+\w+\s+\w+$',               # brew <command> <package>
        r'^pip\s+\w+$',                      # pip <command>
        r'^pip\s+\w+\s+\w+$',                # pip <command> <package>
        r'^npm\s+\w+$',                      # npm <command>
        r'^npm\s+\w+\s+\w+$',                # npm <command> <package>
        r'^yarn\s+\w+$',                     # yarn <command>
        r'^yarn\s+\w+\s+\w+$',               # yarn <command> <package>
        r'^cargo\s+\w+$',                    # cargo <command>
        r'^cargo\s+\w+\s+\w+$',              # cargo <command> <package>
        r'^go\s+\w+$',                       # go <command>
        r'^go\s+\w+\s+\w+$',                 # go <command> <package>
        r'^gem\s+\w+$',                      # gem <command>
        r'^gem\s+\w+\s+\w+$',                # gem <command> <package>
        r'^snap\s+\w+$',                     # snap <command>
        r'^snap\s+\w+\s+\w+$',               # snap <command> <package>
        r'^flatpak\s+\w+$',                  # flatpak <command>
        r'^flatpak\s+\w+\s+\w+$',            # flatpak <command> <package>
        r'^pacman\s+\w+$',                   # pacman <command>
        r'^pacman\s+\w+\s+\w+$',             # pacman <command> <package>
        r'^zypper\s+\w+$',                   # zypper <command>
        r'^zypper\s+\w+\s+\w+$',             # zypper <command> <package>
        r'^dnf\s+\w+$',                      # dnf <command>
        r'^dnf\s+\w+\s+\w+$',                # dnf <command> <package>
        r'^yum\s+\w+$',                      # yum <command>
        r'^yum\s+\w+\s+\w+$',                # yum <command> <package>
    ]
    EDITORS = {'vi', 'vim', 'emacs', 'nano'}
    INTERACTIVE_COMMANDS = {
        'top', 'htop', 'btop', 'bashtop', 'atop', 'glances', 'less', 'more', 'most', 'iftop', 'iotop', 'nethogs', 'nload', 'slurm', 'ttyplot',
        'man', 'info', 'ncdu', 'asciiquarium', 'cmatrix', 'hollywood', 'python', 'python3', 'node', 'nodejs', 'irb', 'pry', 'ghci', 'gdb', 'lldb'
    }

    def __init__(self, debug: bool = False, no_confirm: bool = False):
        self.debug = debug
        self.no_confirm = no_confirm
    
    def _debug_print(self, message: str):
        if self.debug:
            print(f"shell_commands | {message}")
      
    def is_shell_command(self, command: str) -> bool:
        if not command or not command.strip():
            return False
        
        command = command.strip().lower()
        base = command.split()[0].lower()

        if (base in self.BASIC_COMMANDS or 
            base in self.EDITORS or 
            base in self.INTERACTIVE_COMMANDS or 
            base in self.NAVIGATION_COMMANDS):
            self._debug_print(f'{command} is a shell command (base match)')
            return True

        # Check if command matches any known command patterns
        for pattern in self.COMMAND_PATTERNS:
            if re.match(pattern, command.strip()):
                self._debug_print(f'{command} is a shell command (pattern match)')
                return True
        return False
    
    def execute_command(self, command: str, cwd: str = ".") -> Tuple[bool, str, Optional[int], str]:
        
        # Check if this is a navigation command (cd)
        is_navigation = self.is_navigation_command(command)
        if is_navigation:
            # Handle cd command specially - it changes working directory
            success, message, new_cwd = self.change_directory(command, cwd)
            if success:
                # Show the new working directory after successful cd
                message += f"\n{self.show_current_directory(new_cwd)}"
                return True, message, 0, new_cwd
            else:
                return False, message, 1, cwd
        
        
        # Check if this is an interactive command (editor or system command)
        parts = shlex.split(command.strip())
        base_command = parts[0].lower()
        is_interactive = base_command in self.EDITORS or base_command in self.INTERACTIVE_COMMANDS
        
        try:
            if is_interactive:
                # For interactive commands, start them in the foreground
                if base_command in self.EDITORS:
                    command_type = "text editor"
                    action = "editing"
                else:
                    command_type = "system command"
                    action = "monitoring"
                
                # Interactive command handling
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
  
    def is_interactive_command(self, command: str) -> bool:
        """Check if a command is interactive (editor or system command)."""
        if not command or not command.strip():
            return False
        
        parts = shlex.split(command.strip())
        if not parts:
            return False
        
        base_command = parts[0].lower()
        return base_command in self.EDITORS or base_command in self.INTERACTIVE_COMMANDS

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
  