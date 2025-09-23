"""Configuration management for TermAgent."""

import json
import os
from enum import Enum
from typing import Optional, Dict, Any


class AutonomyLevel(Enum):
    """Autonomy levels for tool execution."""
    MANUAL = "manual"  # Always ask for permission
    SEMI_AUTONOMOUS = "semi"  # Ask for permission for dangerous operations
    FULLY_AUTONOMOUS = "full"  # Never ask for permission


class Config:
    """Configuration class for TermAgent."""
    
    def __init__(self, autonomy_level: AutonomyLevel = AutonomyLevel.MANUAL, 
                 debug_mode: bool = False, max_context_length: int = 200000,
                 model: str = "claude-3-5-sonnet-20241022"):
        self.autonomy_level = autonomy_level
        self.debug_mode = debug_mode
        self.max_context_length = max_context_length
        self.model = model
    
    @classmethod
    def from_string(cls, autonomy_str: str) -> 'Config':
        """Create config from string representation."""
        autonomy_map = {
            "manual": AutonomyLevel.MANUAL,
            "semi": AutonomyLevel.SEMI_AUTONOMOUS,
            "full": AutonomyLevel.FULLY_AUTONOMOUS
        }
        
        autonomy_level = autonomy_map.get(autonomy_str.lower(), AutonomyLevel.MANUAL)
        return cls(autonomy_level)
    
    @classmethod
    def from_file(cls, config_path: Optional[str] = None) -> 'Config':
        """Load configuration from JSON file."""
        if config_path is None:
            config_path = os.path.expanduser("~/.termagent/config.json")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            autonomy_str = config_data.get("autonomy_level", "manual")
            autonomy_map = {
                "manual": AutonomyLevel.MANUAL,
                "semi": AutonomyLevel.SEMI_AUTONOMOUS,
                "full": AutonomyLevel.FULLY_AUTONOMOUS
            }
            autonomy_level = autonomy_map.get(autonomy_str.lower(), AutonomyLevel.MANUAL)
            c = cls(
                autonomy_level=autonomy_level,
                debug_mode=config_data.get("debug_mode", False),
                max_context_length=config_data.get("max_context_length", 200000),
                model=config_data.get("model", "claude-3-5-sonnet-20241022")
            )
            return c 

        except FileNotFoundError:
            # Create default config file and return default config
            default_config = cls()
            default_config.save_to_file(config_path)
            print(f"Created default config file at {config_path}")
            return default_config
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Invalid config file at {config_path}: {e}")
            print("Using default configuration.")
            return cls()
    
    def save_to_file(self, config_path: Optional[str] = None) -> None:
        """Save configuration to JSON file."""
        if config_path is None:
            config_path = os.path.expanduser("~/.termagent/config.json")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        config_data = {
            "autonomy_level": self.autonomy_level.value,
            "debug_mode": self.debug_mode,
            "max_context_length": self.max_context_length,
            "model": self.model
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
    
    def should_ask_permission(self, tool_name: str, parameters: dict) -> bool:
        """Determine if permission should be asked based on autonomy level."""
        # Read operations never require permission
        if tool_name == "read_file":
            return False
            
        if self.autonomy_level == AutonomyLevel.FULLY_AUTONOMOUS:
            return False
        elif self.autonomy_level == AutonomyLevel.SEMI_AUTONOMOUS:
            # For semi-autonomous, only ask for very dangerous operations
            if tool_name == "bash":
                command = parameters.get("command", "").strip()
                # Only ask for commands that could be very destructive
                dangerous_patterns = [
                    "rm -rf", "sudo", "chmod 777", "chown", "dd if=",
                    "mkfs", "fdisk", "parted", "format", "del /f",
                    "shutdown", "reboot", "halt", "poweroff"
                ]
                return any(pattern in command.lower() for pattern in dangerous_patterns)
            elif tool_name == "edit_file":
                # Ask for write operations in semi-autonomous mode
                return True
            return False
        else:  # MANUAL
            return True
    
    def set_autonomy_level(self, autonomy_level: str) -> None:
        """Set autonomy level from string."""
        autonomy_map = {
            "manual": AutonomyLevel.MANUAL,
            "semi": AutonomyLevel.SEMI_AUTONOMOUS,
            "full": AutonomyLevel.FULLY_AUTONOMOUS
        }
        
        if autonomy_level.lower() not in autonomy_map:
            raise ValueError(f"Invalid autonomy level: {autonomy_level}. Must be one of: manual, semi, full")
        
        self.autonomy_level = autonomy_map[autonomy_level.lower()]
    
    def print_autonomy_info(self) -> None:
        """Print autonomy level information."""
        if self.autonomy_level == AutonomyLevel.FULLY_AUTONOMOUS:
            print("🤖 Running in FULLY AUTONOMOUS mode - no permission prompts")
        elif self.autonomy_level == AutonomyLevel.SEMI_AUTONOMOUS:
            print("⚡ Running in SEMI-AUTONOMOUS mode - minimal permission prompts")
        else:
            print("👤 Running in MANUAL mode - permission required for all operations")
    
    def display(self) -> None:
        """Display current configuration settings."""
        print("\n📋 Current Configuration:")
        print(f"  Autonomy Level: {self.autonomy_level.value}")
        print(f"  Debug Mode: {self.debug_mode}")
        print(f"  Max Context Length: {self.max_context_length:,}")
        print(f"  Model: {self.model}")
        print()
