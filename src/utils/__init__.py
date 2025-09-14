"""Utilities module for TermAgent."""

from .debug import (
    dbg,
    is_debug_mode
)

from .message_cache import (
    initialize_messages,
    add_to_message_cache,
    get_command_messages,
    should_replay,
    dump_message_cache
)

__all__ = [
    # Debug functions
    'dbg',
    'is_debug_mode',
    
    # Message cache functions
    'initialize_messages',
    'add_to_message_cache',
    'get_command_messages',
    'should_replay',
    'dump_message_cache'
]
