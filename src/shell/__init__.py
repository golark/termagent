"""Shell module for command execution and detection."""

from .shell import (
    is_shell_command,
    is_cd,
    handle_cd_command,
    execute_shell_command,
)
from .alias import (
    get_shell_aliases,
    resolve_alias,
)

__all__ = [
    'is_shell_command',
    'is_cd', 
    'handle_cd_command',
    'execute_shell_command',
    'get_shell_aliases',
    'resolve_alias',
]
