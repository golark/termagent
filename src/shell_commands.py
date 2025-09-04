"""Module to check if a command is a shell command and execute it using subprocess."""

import subprocess
import re
import sys
from typing import Optional, Tuple


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
    
    # Check against all regex patterns
    for pattern in SHELL_COMMAND_PATTERNS:
        if re.match(pattern, command_stripped, re.IGNORECASE):
            return True
    
    return False


def execute_shell_command(command: str, timeout: int = 30) -> Tuple[str, int]:
    """Execute a shell command and return output and return code."""
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
