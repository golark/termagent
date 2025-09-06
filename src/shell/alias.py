import subprocess
import os
import re
from typing import Optional, Dict


def get_shell_aliases() -> Dict[str, str]:
    aliases = {}
    
    try:
        # Try sourcing .zshrc first, then get aliases
        result = subprocess.run(
            'zsh -i -c alias',
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
            env=os.environ
        )
        if result.returncode == 0 and result.stdout:
            # Parse alias output - assume format: name='value' or name=value
            for line in result.stdout.strip().split('\n'):
                if '=' in line and not line.startswith('#'):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        name = parts[0].strip()
                        value = parts[1].strip().strip("'\"")
                        aliases[name] = value
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return aliases


def resolve_alias(command: str, aliases: Optional[Dict[str, str]] = None) -> str:
    """Resolve shell aliases in a command."""
    if not command or not command.strip():
        return command
    
    if aliases is None:
        aliases = get_shell_aliases()
    
    command_parts = command.strip().split()
    if not command_parts:
        return command
    
    # Get the first word (command name)
    command_name = command_parts[0]
    
    # Check if it's an alias
    if command_name in aliases:
        alias_value = aliases[command_name]
        
        # Replace the command name with the alias value
        resolved_parts = alias_value.split() + command_parts[1:]
        return ' '.join(resolved_parts)
    
    return command


def is_alias(command: str, aliases: Optional[Dict[str, str]] = None) -> bool:
    """Check if a command starts with an alias."""
    if not command or not command.strip():
        return False
    
    if aliases is None:
        aliases = get_shell_aliases()
    
    command_parts = command.strip().split()
    if not command_parts:
        return False
    
    command_name = command_parts[0]
    return command_name in aliases
