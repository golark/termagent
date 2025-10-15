"""TermAgent - An AI-powered terminal assistant."""

__version__ = "0.1.0"
__author__ = "termagent contributors"
__license__ = "MIT"

from .main import main, process_command
from .model import call_anthropic, ContextWindowExceededError
from .utils.config import Config, AutonomyLevel

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "main",
]

