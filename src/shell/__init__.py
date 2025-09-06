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
from .history import (
    setup_readline_history,
    save_history,
    add_to_history,
    get_input,
)

__all__ = [
    'is_shell_command',
    'is_cd', 
    'handle_cd_command',
    'execute_shell_command',
    'get_shell_aliases',
    'resolve_alias',
    'setup_readline_history',
    'save_history',
    'add_to_history',
    'get_input',
]
