"""
TermAgent - A LangGraph-based agent system with router and specialized agents.
"""

__version__ = "0.1.0"
__author__ = "TermAgent Team"

from .main import main
from .termagent_graph import create_agent_graph, process_command
from .input_handler import create_input_handler, InputHandler, CommandHistory

__all__ = ["main", "create_agent_graph", "process_command", "create_input_handler", "InputHandler", "CommandHistory"]
