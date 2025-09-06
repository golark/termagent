"""Shell module for command execution and detection."""

from .shell import (
    is_shell_command,
    is_cd,
    handle_cd_command,
    execute_shell_command,
    SHELL_COMMAND_PATTERNS
)

__all__ = [
    'is_shell_command',
    'is_cd', 
    'handle_cd_command',
    'execute_shell_command',
    'SHELL_COMMAND_PATTERNS'
]
