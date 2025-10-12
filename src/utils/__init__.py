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

from .config import (
    Config,
    AutonomyLevel
)

from .permissions import (
    request_write_access,
    has_write_access,
    get_permissions_manager,
    PermissionsManager
)

from .rules import (
    add_rule,
    remove_rule,
    list_rules,
    get_rules_text,
    has_rules,
    get_rules_manager,
    RulesManager
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
    'dump_message_cache',
    
    # Config classes
    'Config',
    'AutonomyLevel',
    
    # Permissions functions
    'request_write_access',
    'has_write_access',
    'get_permissions_manager',
    'PermissionsManager',
    
    # Rules functions
    'add_rule',
    'remove_rule',
    'list_rules',
    'get_rules_text',
    'has_rules',
    'get_rules_manager',
    'RulesManager'
]
