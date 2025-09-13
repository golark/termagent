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
from .input import (
    setup_readline,
    get_input,
)
from .history import (
    CommandHistory,
    command_history,
    save_command_history,
    load_command_history,
    get_history_file_path,
    add_to_history,
)

__all__ = [
    'is_shell_command',
    'is_cd', 
    'handle_cd_command',
    'execute_shell_command',
    'get_shell_aliases',
    'resolve_alias',
    'setup_readline',
    'add_to_history',
    'get_input',
    'CommandHistory',
    'command_history',
    'save_command_history',
    'load_command_history',
    'get_history_file_path',
]
