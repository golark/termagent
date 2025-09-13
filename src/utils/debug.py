import os
import sys
from typing import Any


def debug_print(*args, **kwargs) -> None:
    """Print debug messages only if debug mode is enabled."""
    if is_debug_mode():
        print("DEBUG |", *args, **kwargs)


def is_debug_mode() -> bool:
    """Check if debug mode is enabled via environment variable or command line."""
    # Check environment variable
    if os.getenv('TERMAGENT_DEBUG', '').lower() in ('true', '1', 'yes', 'on'):
        return True
    
    # Check command line arguments
    if '--debug' in sys.argv or '-d' in sys.argv:
        return True
    
    return False
