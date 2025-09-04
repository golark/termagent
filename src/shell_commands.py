"""Module to check if a command is a shell command and execute it using subprocess."""

import subprocess
import re
import sys
import os
from typing import Optional, Tuple

# Global variable to track the previous directory for 'cd -' functionality
_previous_directory: Optional[str] = None

# Cache for shell aliases to avoid repeated shell calls
_shell_aliases: Optional[dict] = None


def get_previous_directory() -> Optional[str]:
    """Get the previous directory for debugging or informational purposes."""
    return _previous_directory


def refresh_aliases() -> None:
    """Refresh the shell aliases cache."""
    global _shell_aliases
    _shell_aliases = None
    get_shell_aliases()


def get_shell_aliases() -> dict:
    """Get aliases from the current shell environment."""
    global _shell_aliases
    
    if _shell_aliases is not None:
        return _shell_aliases
    
    aliases = {}
    
    try:
        # Try to get aliases from the current shell
        # This works for bash, zsh, and other POSIX shells
        # Use the same shell as the current process
        shell = os.environ.get('SHELL', '/bin/sh')
        result = subprocess.run(
            f"{shell} -c 'alias'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    # Parse alias line: alias ll='ls -la'
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        alias_name = parts[0].replace('alias ', '').strip()
                        alias_value = parts[1].strip().strip("'\"")
                        aliases[alias_name] = alias_value
        
        # Add some common aliases that might not be in the shell
        common_aliases = {
            'll': 'ls -la',
            'la': 'ls -la',
            'l': 'ls -la',
            'lt': 'ls -lt',
            'lh': 'ls -lh',
            'lr': 'ls -lr',
            'lrt': 'ls -lrt',
            'lart': 'ls -lart',
            '..': 'cd ..',
            '...': 'cd ../..',
            '....': 'cd ../../..',
            'h': 'history',
            'grep': 'grep --color=auto',
            'ls': 'ls --color=auto',
            'vi': 'vim',
            'vim': 'vim',
            'cat': 'cat -n',
            'ps': 'ps aux',
            'df': 'df -h',
            'du': 'du -h',
            'free': 'free -h',
            'top': 'htop',
            'tree': 'tree -C',
            'mkdir': 'mkdir -p',
            'cp': 'cp -i',
            'mv': 'mv -i',
            'rm': 'rm -i',
            'which': 'which -a',
            'type': 'type -a',
            'jobs': 'jobs -l',
            'killall': 'killall -v',
            'ping': 'ping -c 4',
            'traceroute': 'traceroute -n',
            'netstat': 'netstat -tuln',
            'ss': 'ss -tuln',
            'mount': 'mount | column -t',
            'umount': 'umount -v',
            'chmod': 'chmod -v',
            'chown': 'chown -v',
            'chgrp': 'chgrp -v',
            'tar': 'tar -v',
            'zip': 'zip -r',
            'unzip': 'unzip -l',
            'gzip': 'gzip -v',
            'gunzip': 'gunzip -v',
            'bzip2': 'bzip2 -v',
            'bunzip2': 'bunzip2 -v',
            'xz': 'xz -v',
            'unxz': 'unxz -v',
            '7z': '7z a',
            '7za': '7z a',
            '7zr': '7z a',
            'rar': 'rar a',
            'unrar': 'unrar x',
            'zipinfo': 'zipinfo -v',
            'unzip': 'unzip -l',
            'zipgrep': 'zipgrep -n',
            'zipnote': 'zipnote -v',
            'zipsplit': 'zipsplit -n',
            'zipcloak': 'zipcloak -v',
            'zipdetails': 'zipdetails -v',
            'zipgrep': 'zipgrep -n',
            'zipnote': 'zipnote -v',
            'zipsplit': 'zipsplit -n',
            'zipcloak': 'zipcloak -v',
            'zipdetails': 'zipdetails -v'
        }
        
        # Merge shell aliases with common aliases (shell aliases take precedence)
        aliases.update(common_aliases)
        
    except Exception as e:
        # If we can't get shell aliases, just use common ones
        aliases = {
            'll': 'ls -la',
            'la': 'ls -la',
            'l': 'ls -la',
            'lt': 'ls -lt',
            'lh': 'ls -lh',
            'lr': 'ls -lr',
            'lrt': 'ls -lrt',
            'lart': 'ls -lart',
            '..': 'cd ..',
            '...': 'cd ../..',
            '....': 'cd ../../..',
            'h': 'history',
            'vi': 'vim',
            'cat': 'cat -n',
            'ps': 'ps aux',
            'df': 'df -h',
            'du': 'du -h',
            'free': 'free -h',
            'top': 'htop',
            'tree': 'tree -C',
            'mkdir': 'mkdir -p',
            'cp': 'cp -i',
            'mv': 'mv -i',
            'rm': 'rm -i',
            'which': 'which -a',
            'type': 'type -a',
            'jobs': 'jobs -l',
            'killall': 'killall -v',
            'ping': 'ping -c 4',
            'traceroute': 'traceroute -n',
            'netstat': 'netstat -tuln',
            'ss': 'ss -tuln',
            'mount': 'mount | column -t',
            'umount': 'umount -v',
            'chmod': 'chmod -v',
            'chown': 'chown -v',
            'chgrp': 'chgrp -v',
            'tar': 'tar -v',
            'zip': 'zip -r',
            'unzip': 'unzip -l',
            'gzip': 'gzip -v',
            'gunzip': 'gunzip -v',
            'bzip2': 'bzip2 -v',
            'bunzip2': 'bunzip2 -v',
            'xz': 'xz -v',
            'unxz': 'unxz -v',
            '7z': '7z a',
            '7za': '7z a',
            '7zr': '7z a',
            'rar': 'rar a',
            'unrar': 'unrar x',
            'zipinfo': 'zipinfo -v',
            'unzip': 'unzip -l',
            'zipgrep': 'zipgrep -n',
            'zipnote': 'zipnote -v',
            'zipsplit': 'zipsplit -n',
            'zipcloak': 'zipcloak -v',
            'zipdetails': 'zipdetails -v',
            'zipgrep': 'zipgrep -n',
            'zipnote': 'zipnote -v',
            'zipsplit': 'zipsplit -n',
            'zipcloak': 'zipcloak -v',
            'zipdetails': 'zipdetails -v'
        }
    
    _shell_aliases = aliases
    return aliases


def resolve_aliases(command: str) -> str:
    """Resolve aliases in a command string."""
    if not command or not command.strip():
        return command
    
    command_stripped = command.strip()
    aliases = get_shell_aliases()
    
    # Split command into parts
    parts = command_stripped.split()
    if not parts:
        return command
    
    # Check if the first part is an alias
    first_part = parts[0]
    if first_part in aliases:
        # Replace the alias with its value
        alias_value = aliases[first_part]
        
        # If there are additional arguments, append them
        if len(parts) > 1:
            remaining_args = ' '.join(parts[1:])
            resolved_command = f"{alias_value} {remaining_args}"
        else:
            resolved_command = alias_value
        
        return resolved_command
    
    return command


# Regex patterns for different types of shell commands
SHELL_COMMAND_PATTERNS = [
    # Basic file operations
    r'^(ls|pwd|cd|mkdir|rmdir|rm|cp|mv|cat|head|tail|touch|chmod|chown|chgrp|ln|tar|zip|unzip|gzip|gunzip)$',
    
    # Text processing and search
    r'^(grep|find|which|whereis|awk|sed|cut|sort|uniq|wc|tr|tee|locate|updatedb)$',
    
    # System monitoring and processes
    r'^(ps|top|htop|kill|killall|df|du|free|uptime|whoami|id|groups|history|clear|reset)$',
    
    # Date and time
    r'^(date|cal|sleep|wait|time|timeout|watch)$',
    
    # Job control
    r'^(jobs|bg|fg|nohup|screen|tmux)$',
    
    # Text editors and viewers
    r'^(vim|nano|emacs|less|more|man|info|apropos|whatis)$',
    
    # Shell built-ins and environment
    r'^(alias|unalias|export|unset|env|printenv|set|source|\.|exit|logout|shutdown|reboot|halt|poweroff)$',
    
    # System administration
    r'^(mount|umount|fdisk|parted|mkfs|fsck|systemctl|service|init|crontab|at|batch)$',
    
    # Network commands
    r'^(ifconfig|ip|netstat|ss|ping|traceroute|nslookup|dig|wget|curl|ssh|scp|rsync)$',
    
    # Version control
    r'^(git|hg|svn|bzr|darcs|fossil)$',
    
    # Container and orchestration
    r'^(docker|docker-compose|kubectl|helm)$',
    
    # Package managers and languages
    r'^(npm|yarn|pip|pip3|conda|mamba|python|python3|node|nodejs|ruby|perl|php)$',
    
    # Compilers and build tools
    r'^(gcc|g\+\+|clang|make|cmake|ninja)$',
    
    # Debugging and profiling
    r'^(gdb|lldb|valgrind|strace|ltrace)$',
    
    # Utilities
    r'^(xargs|parallel|echo|printf)$',
    
    # Commands with arguments (built-in shell commands)
    r'^(cd|export|unset|alias|unalias|source|exec|eval|set|readonly|declare|typeset|local|return|break|continue|shift)\s+',
    
    # Absolute paths to executables
    r'^/',
    
    # Relative paths to executables
    r'^(\./|\.\./)',
    
    # Commands with common flags (like ls -la, grep -r, etc.)
    r'^(ls|grep|find|ps|df|du|free|mount|umount|systemctl|docker|git|npm|pip|python|node|make|gcc|g\+\+|clang)\s+',
]


def is_shell_command(command: str) -> bool:
    """Check if a command is a shell command that should be executed directly."""
    if not command or not command.strip():
        return False
    
    command_stripped = command.strip()
    
    # Check if it's an alias first
    aliases = get_shell_aliases()
    first_part = command_stripped.split()[0] if command_stripped.split() else ""
    if first_part in aliases:
        return True
    
    # Check against all regex patterns
    for pattern in SHELL_COMMAND_PATTERNS:
        if re.match(pattern, command_stripped, re.IGNORECASE):
            return True
    
    return False


def is_cd_command(command: str) -> bool:
    """Check if the command is a cd command."""
    if not command or not command.strip():
        return False
    
    command_stripped = command.strip()
    return command_stripped.startswith('cd ') or command_stripped == 'cd'


def handle_cd_command(command: str) -> Tuple[str, int]:
    """Handle cd command by changing the current working directory."""
    global _previous_directory
    command_stripped = command.strip()
    
    # Get current directory before any changes
    current_dir = os.getcwd()
    
    # Handle 'cd' without arguments (go to home directory)
    if command_stripped == 'cd':
        try:
            home_dir = os.path.expanduser('~')
            os.chdir(home_dir)
            _previous_directory = current_dir
            return f"Changed to home directory: {home_dir}", 0
        except Exception as e:
            return f"Error changing to home directory: {str(e)}", 1
    
    # Handle 'cd <path>'
    if command_stripped.startswith('cd '):
        target_path = command_stripped[3:].strip()
        
        # Handle special cases
        if target_path == '-':
            # Go to previous directory
            if _previous_directory is None:
                return "cd -: No previous directory to change to", 1
            try:
                os.chdir(_previous_directory)
                new_current = os.getcwd()
                _previous_directory = current_dir
                return f"Changed to previous directory: {new_current}", 0
            except Exception as e:
                return f"Error changing to previous directory: {str(e)}", 1
        elif target_path == '..':
            # Go up one directory
            try:
                os.chdir('..')
                new_current = os.getcwd()
                _previous_directory = current_dir
                return f"Changed to parent directory: {new_current}", 0
            except Exception as e:
                return f"Error changing to parent directory: {str(e)}", 1
        else:
            # Regular path
            try:
                # Expand ~ and relative paths
                expanded_path = os.path.expanduser(target_path)
                os.chdir(expanded_path)
                new_current = os.getcwd()
                _previous_directory = current_dir
                return f"Changed to directory: {new_current}", 0
            except FileNotFoundError:
                return f"Directory not found: {target_path}", 1
            except PermissionError:
                return f"Permission denied: {target_path}", 1
            except Exception as e:
                return f"Error changing directory: {str(e)}", 1
    
    return "Invalid cd command", 1


def execute_shell_command(command: str, timeout: int = 30) -> Tuple[str, int]:
    """Execute a shell command and return output and return code."""
    # Resolve aliases first
    resolved_command = resolve_aliases(command)
    
    # Handle cd commands specially since they need to change the current working directory
    if is_cd_command(resolved_command):
        output, return_code = handle_cd_command(resolved_command)
        print(output)
        return output, return_code
    
    # Handle other shell commands with subprocess
    try:
        result = subprocess.run(
            resolved_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr

        print(output)
        
        return output, result.returncode
        
    except subprocess.TimeoutExpired:
        return "Error: Command timed out", 124
    except Exception as e:
        return f"Error executing command: {str(e)}", 1
