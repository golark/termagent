#!/usr/bin/env python3
"""
Shell command detector and executor for TermAgent.
Handles direct execution of known shell commands.
"""

import os
import subprocess
import shlex
import re
from typing import Tuple, Optional, Dict


class ShellCommandHandler:
    """Detects and executes known shell commands directly."""
    
    BASIC_COMMANDS = {'ls', 'll', 'pwd', 'mkdir', 'rm', 'cp', 'grep', 'find', 'cat', 'head', 'tail', 'sort', 'uniq', 'wc', 'echo', 'which', 'ps'}
    NAVIGATION_COMMANDS = {'cd'}
    SOURCE_COMMANDS = {'source', '.'}
    COMMAND_PATTERNS = [
        r'^which\s+\w+$',                    # which <executable>
        r'^source\s+\S+$',                   # source <file>
        r'^source\s+\S+\s+\S+$',             # source <file> <args>
        r'^\.\s+\S+$',                       # . <file> (alternative to source)
        r'^\.\s+\S+\s+\S+$',                 # . <file> <args>
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
        
        # Docker commands
        r'^docker\s+.*$',                     # any docker command
        r'^podman\s+.*$',                     # any podman command
    ]
    EDITORS = {'vi', 'vim', 'emacs', 'nano'}
    INTERACTIVE_COMMANDS = {
        'top', 'htop', 'btop', 'bashtop', 'atop', 'glances', 'less', 'more', 'most', 'iftop', 'iotop', 'nethogs', 'nload', 'slurm', 'ttyplot',
        'man', 'info', 'ncdu', 'asciiquarium', 'cmatrix', 'hollywood', 'python', 'python3', 'node', 'nodejs', 'irb', 'pry', 'ghci', 'gdb', 'lldb'
    }

    def __init__(self, debug: bool = False, no_confirm: bool = False):
        self.debug = debug
        self.no_confirm = no_confirm
        self._aliases_cache = {}
        self._aliases_loaded = False
    
    def _debug_print(self, message: str):
        if self.debug:
            print(f"shell_commands | {message}")
    
    def is_shell_command(self, command: str) -> bool:
        if not command or not command.strip():
            return False
        
        # First, resolve alias if applicable
        resolved = self.resolve_alias(command)
        if resolved:
            command = resolved
        command = command.strip().lower()
        base = command.split()[0].lower()

        if (base in self.BASIC_COMMANDS or 
            base in self.EDITORS or 
            base in self.INTERACTIVE_COMMANDS or 
            base in self.NAVIGATION_COMMANDS or
            base in self.SOURCE_COMMANDS):
            self._debug_print(f'{command} is a shell command (base match)')
            return True

        # Check if command matches any known command patterns
        for pattern in self.COMMAND_PATTERNS:
            if re.match(pattern, command.strip()):
                self._debug_print(f'{command} is a shell command (pattern match)')
                return True
        return False
    
    def execute_command(self, command: str, cwd: str = ".") -> Tuple[bool, str, Optional[int], str]:
       
        # Resolve alias before execution
        resolved_command = self.resolve_alias(command)
        if resolved_command:
            command = resolved_command

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
        
        # Check if this is a source command
        is_source = self.is_source_command(command)
        if is_source:
            # Handle source command specially - it can modify environment
            success, message, _ = self.handle_source_command(command, cwd)
            if success:
                return True, message, 0, cwd
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
    
    def is_source_command(self, command: str) -> bool:
        """Check if a command is a source command (source or .)."""
        if not command or not command.strip():
            return False
        
        parts = shlex.split(command.strip())
        if not parts:
            return False
        
        base_command = parts[0].lower()
        return base_command in self.SOURCE_COMMANDS

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
    
    def handle_source_command(self, command: str, current_cwd: str) -> Tuple[bool, str, str]:
        """Handle source command and return updated environment info."""
        self._debug_print(f"handle_source_command called with command: '{command}', current_cwd: '{current_cwd}'")
        
        if not self.is_source_command(command):
            self._debug_print(f"command '{command}' is not a source command")
            return False, "Not a source command", current_cwd
        
        parts = shlex.split(command.strip())
        if len(parts) < 2:
            return False, "❌ Source command requires a file argument", current_cwd
        
        source_file = parts[1]
        
        # Handle special cases
        if source_file.startswith("~"):
            source_file = os.path.expanduser(source_file)
        
        # Resolve relative paths
        if not os.path.isabs(source_file):
            source_file = os.path.join(current_cwd, source_file)
        
        # Normalize the path
        source_file = os.path.normpath(source_file)
        
        # Check if file exists
        if not os.path.exists(source_file):
            return False, f"❌ Source file does not exist: {source_file}", current_cwd
        
        # Check if we have permission to read
        if not os.access(source_file, os.R_OK):
            return False, f"❌ Permission denied reading file: {source_file}", current_cwd
        
        try:
            # Read the source file to analyze its contents
            with open(source_file, 'r') as f:
                content = f.read()
            
            # Analyze what the source file does
            analysis = self._analyze_source_file(content, source_file)
            
            # For virtual environments, try to detect and activate them
            if self._is_virtual_environment_file(source_file, content):
                venv_info = self._activate_virtual_environment(source_file, current_cwd)
                if venv_info:
                    return True, f"✅ Virtual environment activated: {venv_info}\n\n{analysis}", current_cwd
            
            # For regular source files, show what they would do
            return True, f"✅ Source file analyzed: {source_file}\n\n{analysis}", current_cwd
            
        except Exception as e:
            return False, f"❌ Error reading source file: {str(e)}", current_cwd
    
    def _analyze_source_file(self, content: str, file_path: str) -> str:
        """Analyze the contents of a source file to understand what it does."""
        analysis = []
        
        # Look for common patterns in source files
        lines = content.split('\n')
        
        # Check for virtual environment activation
        if any('VIRTUAL_ENV' in line or 'venv' in line or 'activate' in line for line in lines):
            analysis.append("• Appears to be a virtual environment activation script")
        
        # Check for environment variable exports
        export_lines = [line for line in lines if line.strip().startswith('export ')]
        if export_lines:
            analysis.append(f"• Exports {len(export_lines)} environment variables")
            # Show a few examples
            for line in export_lines[:3]:
                var_name = line.split('=')[0].replace('export ', '').strip()
                analysis.append(f"  - {var_name}")
            if len(export_lines) > 3:
                analysis.append(f"  - ... and {len(export_lines) - 3} more")
        
        # Check for alias definitions
        alias_lines = [line for line in lines if line.strip().startswith('alias ')]
        if alias_lines:
            analysis.append(f"• Defines {len(alias_lines)} aliases")
        
        # Check for function definitions
        function_lines = [line for line in lines if line.strip().startswith('function ') or '()' in line]
        if function_lines:
            analysis.append(f"• Defines {len(function_lines)} functions")
        
        # Check for PATH modifications
        path_lines = [line for line in lines if 'PATH=' in line]
        if path_lines:
            analysis.append("• Modifies PATH environment variable")
        
        # Check for other common environment variables
        env_vars = ['HOME', 'USER', 'SHELL', 'LANG', 'LC_ALL', 'PWD', 'OLDPWD']
        for var in env_vars:
            if any(f'{var}=' in line for line in lines):
                analysis.append(f"• Modifies {var} environment variable")
        
        # Check for script execution
        if any('exec' in line or 'eval' in line for line in lines):
            analysis.append("• Contains script execution commands")
        
        # Check for conditional logic
        if any(line.strip().startswith(('if', 'elif', 'else', 'fi', 'case', 'esac')) for line in lines):
            analysis.append("• Contains conditional logic")
        
        # Check for loops
        if any(line.strip().startswith(('for', 'while', 'until', 'done')) for line in lines):
            analysis.append("• Contains loop constructs")
        
        if not analysis:
            analysis.append("• File contents analyzed but no clear patterns detected")
        
        return "\n".join(analysis)
    
    def _is_virtual_environment_file(self, file_path: str, content: str) -> bool:
        """Check if a source file is a virtual environment activation script."""
        # Common patterns for virtual environment activation
        venv_indicators = [
            'VIRTUAL_ENV',
            'venv',
            'activate',
            'deactivate',
            'conda activate',
            'conda deactivate',
            'pipenv',
            'poetry',
            'virtualenv',
            'pyenv',
            'asdf',
            'rvm',
            'rbenv',
            'nvm',
            'n',
            'fnm'
        ]
        
        # Check file path
        file_lower = file_path.lower()
        if any(indicator in file_lower for indicator in ['activate', 'venv', 'env']):
            return True
        
        # Check content
        content_lower = content.lower()
        if any(indicator in content_lower for indicator in venv_indicators):
            return True
        
        return False
    
    def _activate_virtual_environment(self, source_file: str, current_cwd: str) -> Optional[str]:
        """Attempt to activate a virtual environment and return info about it."""
        try:
            # Try to detect the type of virtual environment based on content and path
            file_lower = source_file.lower()
            content_lower = ""
            
            # Try to read the content to analyze it
            try:
                with open(source_file, 'r') as f:
                    content_lower = f.read().lower()
            except:
                pass
            
            # Check for specific virtual environment types
            if 'conda' in file_lower or 'conda' in content_lower:
                return "Conda environment detected"
            elif 'pipenv' in file_lower or 'pipenv' in content_lower:
                return "Pipenv environment detected"
            elif 'poetry' in file_lower or 'poetry' in content_lower:
                return "Poetry environment detected"
            elif 'virtualenv' in file_lower or 'virtualenv' in content_lower:
                return "Virtualenv environment detected"
            elif 'pyenv' in file_lower or 'pyenv' in content_lower:
                return "Pyenv environment detected"
            elif 'venv' in file_lower or 'activate' in file_lower or 'VIRTUAL_ENV' in content_lower:
                # Standard Python venv
                venv_dir = os.path.dirname(source_file)
                
                # Check for different Python executable locations
                python_paths = [
                    os.path.join(venv_dir, 'bin', 'python'),
                    os.path.join(venv_dir, 'bin', 'python3'),
                    os.path.join(venv_dir, 'Scripts', 'python.exe'),  # Windows
                    os.path.join(venv_dir, 'Scripts', 'python3.exe')  # Windows
                ]
                
                python_path = None
                for path in python_paths:
                    if os.path.exists(path):
                        python_path = path
                        break
                
                if python_path:
                    # Get Python version
                    result = subprocess.run([python_path, '--version'], 
                                         capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        return f"Python venv: {version} at {venv_dir}"
                    else:
                        return f"Python venv at {venv_dir}"
                else:
                    return f"Python venv at {venv_dir}"
            elif 'nvm' in file_lower or 'nvm' in content_lower:
                return "Node.js environment (nvm) detected"
            elif 'rvm' in file_lower or 'rvm' in content_lower:
                return "Ruby environment (rvm) detected"
            elif 'rbenv' in file_lower or 'rbenv' in content_lower:
                return "Ruby environment (rbenv) detected"
            else:
                return "Virtual environment (type unknown)"
                
        except Exception as e:
            self._debug_print(f"Error detecting virtual environment: {e}")
            return None
    
    def show_current_directory(self, cwd: str) -> str:
        """Show the current working directory."""
        return f"Current directory: {cwd}"

    def resolve_alias(self, command: str) -> Optional[str]:
        """Resolve shell alias to its actual command."""
        if not command or not command.strip():
            return None
        
        # Load aliases if not already loaded
        if not self._aliases_loaded:
            self._load_aliases()
        
        # Get the base command (first word)
        base_command = command.split()[0].strip()
        
        # Check if we have this alias cached
        if base_command in self._aliases_cache:
            alias_value = self._aliases_cache[base_command]
            self._debug_print(f"Resolved alias '{base_command}' -> '{alias_value}'")
            
            # Replace the base command with the alias value
            if len(command.split()) > 1:
                # Keep the arguments
                return f"{alias_value} {' '.join(command.split()[1:])}"
            else:
                return alias_value
        
        return None
    
    def _load_aliases(self):
        """Load shell aliases from configuration files and shell."""
        
        # Try to get aliases from the current shell
        try:
            # Use 'alias' command to get current shell aliases
            result = subprocess.run(
                ['alias'],
                capture_output=True,
                text=True,
                shell=True,
                executable="/bin/zsh"
            )
            
            if result.returncode == 0:
                self._parse_alias_output(result.stdout)
            
        except Exception as e:
            self._debug_print(f"Failed to load aliases from shell: {e}")
        
        # Also try to read from common shell config files
        self._load_aliases_from_files()
        
        self._aliases_loaded = True
    
    def _parse_alias_output(self, alias_output: str):
        """Parse the output of the 'alias' command."""
        for line in alias_output.strip().split('\n'):
            if '=' in line:
                # Format: alias name='value' or alias name="value"
                parts = line.split('=', 1)
                if len(parts) == 2:
                    alias_name = parts[0].replace('alias ', '').strip()
                    alias_value = parts[1].strip()
                    
                    # Remove quotes if present
                    if (alias_value.startswith("'") and alias_value.endswith("'")) or \
                       (alias_value.startswith('"') and alias_value.endswith('"')):
                        alias_value = alias_value[1:-1]
                    
                    self._aliases_cache[alias_name] = alias_value
    
    def _load_aliases_from_files(self):
        """Load aliases from common shell configuration files."""
        config_files = [
            os.path.expanduser("~/.zshrc"),
            os.path.expanduser("~/.bashrc"),
            os.path.expanduser("~/.bash_profile"),
            os.path.expanduser("~/.profile")
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                        self._parse_config_file(content)
                except Exception as e:
                    self._debug_print(f"Failed to read {config_file}: {e}")
    
    def _parse_config_file(self, content: str):
        """Parse shell configuration file content for alias definitions."""
        for line in content.split('\n'):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Look for alias definitions
            if line.startswith('alias '):
                # Format: alias name='value' or alias name="value"
                alias_part = line[6:]  # Remove 'alias ' prefix
                if '=' in alias_part:
                    parts = alias_part.split('=', 1)
                    if len(parts) == 2:
                        alias_name = parts[0].strip()
                        alias_value = parts[1].strip()
                        
                        # Remove quotes if present
                        if (alias_value.startswith("'") and alias_value.endswith("'")) or \
                           (alias_value.startswith('"') and alias_value.endswith('"')):
                            alias_value = alias_value[1:-1]
                        
                        # Only add if not already present (shell aliases take precedence)
                        if alias_name not in self._aliases_cache:
                            self._aliases_cache[alias_name] = alias_value
    
    def get_aliases(self) -> Dict[str, str]:
        """Get all loaded aliases."""
        if not self._aliases_loaded:
            self._load_aliases()
        return self._aliases_cache.copy()
    
    def clear_aliases_cache(self):
        """Clear the aliases cache to force reloading."""
        self._aliases_cache.clear()
        self._aliases_loaded = False
        self._debug_print("Aliases cache cleared")