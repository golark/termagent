"""Unit tests for config module."""

import json
import os
import tempfile
import pytest
from pathlib import Path

from src.utils.config import Config, AutonomyLevel


class TestConfig:
    """Test Config class functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        assert config.autonomy_level == AutonomyLevel.MANUAL
        assert config.debug_mode is False
        assert config.max_context_length == 200000
        assert config.model == "claude-3-5-sonnet-20241022"

    def test_from_string_manual(self):
        """Test config creation from string - manual."""
        config = Config.from_string("manual")
        assert config.autonomy_level == AutonomyLevel.MANUAL

    def test_from_string_semi(self):
        """Test config creation from string - semi."""
        config = Config.from_string("semi")
        assert config.autonomy_level == AutonomyLevel.SEMI_AUTONOMOUS

    def test_from_string_full(self):
        """Test config creation from string - full."""
        config = Config.from_string("full")
        assert config.autonomy_level == AutonomyLevel.FULLY_AUTONOMOUS

    def test_from_string_invalid(self):
        """Test config creation from invalid string defaults to manual."""
        config = Config.from_string("invalid")
        assert config.autonomy_level == AutonomyLevel.MANUAL

    def test_save_and_load_config(self):
        """Test saving and loading configuration from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            
            # Create and save config
            config = Config(
                autonomy_level=AutonomyLevel.SEMI_AUTONOMOUS,
                debug_mode=True,
                max_context_length=150000,
                model="claude-3-opus"
            )
            config.save_to_file(config_path)
            
            # Load config and verify
            loaded_config = Config.from_file(config_path)
            assert loaded_config.autonomy_level == AutonomyLevel.SEMI_AUTONOMOUS
            assert loaded_config.debug_mode is True
            assert loaded_config.max_context_length == 150000
            assert loaded_config.model == "claude-3-opus"

    def test_from_file_creates_default(self):
        """Test loading from non-existent file creates default config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            config = Config.from_file(config_path)
            
            assert config.autonomy_level == AutonomyLevel.MANUAL
            assert os.path.exists(config_path)

    def test_from_file_invalid_json(self):
        """Test loading from invalid JSON file returns default config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            with open(config_path, 'w') as f:
                f.write("invalid json content")
            
            config = Config.from_file(config_path)
            assert config.autonomy_level == AutonomyLevel.MANUAL

    def test_should_ask_permission_manual(self):
        """Test permission checking in manual mode."""
        config = Config(autonomy_level=AutonomyLevel.MANUAL)
        
        # Manual mode should ask for everything except read_file
        assert config.should_ask_permission("bash", {"command": "ls"}) is True
        assert config.should_ask_permission("edit_file", {"path": "test.txt"}) is True
        assert config.should_ask_permission("read_file", {"path": "test.txt"}) is False

    def test_should_ask_permission_semi(self):
        """Test permission checking in semi-autonomous mode."""
        config = Config(autonomy_level=AutonomyLevel.SEMI_AUTONOMOUS)
        
        # Semi should ask for dangerous bash commands
        assert config.should_ask_permission("bash", {"command": "ls"}) is False
        assert config.should_ask_permission("bash", {"command": "rm -rf /"}) is True
        assert config.should_ask_permission("bash", {"command": "sudo apt-get install"}) is True
        assert config.should_ask_permission("edit_file", {"path": "test.txt"}) is True
        assert config.should_ask_permission("read_file", {"path": "test.txt"}) is False

    def test_should_ask_permission_full(self):
        """Test permission checking in fully autonomous mode."""
        config = Config(autonomy_level=AutonomyLevel.FULLY_AUTONOMOUS)
        
        # Full autonomous should never ask
        assert config.should_ask_permission("bash", {"command": "rm -rf /"}) is False
        assert config.should_ask_permission("edit_file", {"path": "test.txt"}) is False
        assert config.should_ask_permission("read_file", {"path": "test.txt"}) is False

    def test_set_autonomy_level(self):
        """Test setting autonomy level."""
        config = Config()
        
        config.set_autonomy_level("semi")
        assert config.autonomy_level == AutonomyLevel.SEMI_AUTONOMOUS
        
        config.set_autonomy_level("full")
        assert config.autonomy_level == AutonomyLevel.FULLY_AUTONOMOUS
        
        config.set_autonomy_level("manual")
        assert config.autonomy_level == AutonomyLevel.MANUAL

    def test_set_autonomy_level_invalid(self):
        """Test setting invalid autonomy level raises error."""
        config = Config()
        with pytest.raises(ValueError):
            config.set_autonomy_level("invalid")

    def test_display(self, capsys):
        """Test display method prints configuration."""
        config = Config(autonomy_level=AutonomyLevel.SEMI_AUTONOMOUS, debug_mode=True)
        config.display()
        
        captured = capsys.readouterr()
        assert "semi" in captured.out
        assert "True" in captured.out

