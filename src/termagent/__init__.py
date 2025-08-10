"""
TermAgent - A LangGraph-based agent system with router and specialized agents.
"""

__version__ = "0.1.0"
__author__ = "TermAgent Team"

from .main import main
from .termagent_graph import create_agent_graph, process_command

__all__ = ["main", "create_agent_graph", "process_command"]
