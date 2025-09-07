import subprocess
import re
import sys
import os
import tty
import termios
from typing import Optional, Tuple

_previous_directory: Optional[str] = None


def is_interactive_command(command: str) -> bool:
    if not command or not command.strip():
        return False
    
    command_stripped = command.strip()
    base_command = command_stripped.split()[0]
    
    return base_command in INTERACTIVE_COMMANDS


def is_shell_command(command: str) -> bool:
    if not command or not command.strip():
        return False
    
    command_stripped = command.strip()
    
    for pattern in SHELL_COMMAND_PATTERNS:
        if re.match(pattern, command_stripped, re.IGNORECASE):
            return True
    
    return False


def is_cd(command: str) -> bool:
    if not command or not command.strip():
        return False
    
    command_stripped = command.strip()
    return command_stripped.startswith('cd ') or command_stripped == 'cd'


def handle_cd_command(command: str) -> Tuple[str, int]:
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

    if is_cd(command):
        output, return_code = handle_cd_command(command)
        print(output)
        return output, return_code
    
    # Handle interactive commands that need TTY
    if is_interactive_command(command):
        return execute_interactive_command(command)
    
    try:
        result = subprocess.run(
            command,
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


def execute_interactive_command(command: str) -> Tuple[str, int]:
    """Execute an interactive command with proper TTY handling."""
    try:
        # Save current terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        
        # Set terminal to raw mode for interactive commands
        tty.setraw(sys.stdin.fileno())
        
        # Execute the command with proper TTY
        result = subprocess.run(
            command,
            shell=True,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True
        )
        
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
        return "", result.returncode
        
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        return "Command interrupted", 130
    except Exception as e:
        # Restore terminal settings on error
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except:
            pass
        return f"Error executing interactive command: {str(e)}", 1


# Commands that require interactive TTY
INTERACTIVE_COMMANDS = {
    'vim', 'vi', 'nano', 'emacs', 'htop', 'top', 'less', 'more', 
    'man', 'info', 'watch', 'screen', 'tmux', 'ssh', 'mysql', 
    'psql', 'python', 'python3', 'node', 'nodejs', 'irb', 'pry',
    'gdb', 'lldb', 'jdb', 'gdb-multiarch'
}


# Regex patterns for different types of shell commands
SHELL_COMMAND_PATTERNS = [
    # Basic file operations
    r'^(ls|pwd|cd|mkdir|rmdir|rm|cp|mv|cat|head|tail|touch|chmod|chown|chgrp|ln|tar|zip|unzip|gzip|gunzip)(\s+.*)?$',
    
    # Text processing and search
    r'^(grep|find|which|whereis|awk|sed|cut|sort|uniq|wc|tr|tee|locate|updatedb)(\s+.*)?$',
    
    # System monitoring and processes
    r'^(ps|top|htop|kill|killall|df|du|free|uptime|whoami|id|groups|history|clear|reset)(\s+.*)?$',
    
    # Date and time
    r'^(date|cal|sleep|wait|time|timeout|watch)(\s+.*)?$',
    
    # Job control
    r'^(jobs|bg|fg|nohup|screen|tmux)(\s+.*)?$',
    
    # Text editors and viewers
    r'^(vim|nano|emacs|less|more|man|info|apropos|whatis)(\s+.*)?$',
    
    # Shell built-ins and environment
    r'^(export|unset|env|printenv|set|source|\.|exit|logout|shutdown|reboot|halt|poweroff)$',
    
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
    r'^(cd|export|unset|source|exec|eval|set|readonly|declare|typeset|local|return|break|continue|shift)\s+',
    
    # Absolute paths to executables
    r'^/',
    
    # Relative paths to executables
    r'^(\./|\.\./)',
    
    # Commands with common flags (like ls -la, grep -r, etc.)
    r'^(ls|grep|find|ps|df|du|free|mount|umount|systemctl|docker|git|npm|pip|python|node|make|gcc|g\+\+|clang)\s+',
]
