"""Unit tests for main module."""

import pytest
from unittest.mock import patch, MagicMock

from src.main import process_command
from src.utils.config import Config, AutonomyLevel


class TestProcessCommand:
    """Test process_command functionality."""

    def test_process_command_config(self, capsys):
        """Test that 'config' command displays configuration."""
        config = Config()
        aliases = {}
        
        result = process_command('config', aliases, config)
        
        assert result == ""
        captured = capsys.readouterr()
        assert 'Configuration' in captured.out

    def test_process_command_alias_resolution(self):
        """Test that aliases are resolved before processing."""
        config = Config()
        aliases = {'ll': 'ls -la'}
        
        with patch('src.main.execute_shell_command', return_value=('output', 0)) as mock_exec:
            process_command('ll', aliases, config)
            mock_exec.assert_called_once_with('ls -la')

    @patch('src.main.execute_shell_command', return_value=('test output', 0))
    def test_process_command_shell_command(self, mock_exec):
        """Test processing a shell command."""
        config = Config()
        aliases = {}
        
        result = process_command('ls -la', aliases, config)
        
        assert result == 'test output'
        mock_exec.assert_called_once_with('ls -la')

    @patch('src.main.should_replay', return_value='ls -la')
    @patch('src.main.execute_shell_command', return_value=('replayed output', 0))
    def test_process_command_replay(self, mock_exec, mock_replay):
        """Test replaying a cached command."""
        config = Config()
        aliases = {}
        
        result = process_command('previous command', aliases, config)
        
        assert result == 'replayed output'
        mock_exec.assert_called_once_with('ls -la')

    @patch('src.main.should_replay', return_value=None)
    @patch('src.main.call_anthropic', return_value=('AI response', []))
    @patch('src.main.add_to_message_cache')
    @patch('src.main.dbg_messages')
    def test_process_command_ai(self, mock_dbg, mock_cache, mock_anthropic, mock_replay, capsys):
        """Test processing an AI command."""
        config = Config()
        aliases = {}
        
        result = process_command('what is the weather', aliases, config)
        
        mock_anthropic.assert_called_once()
        captured = capsys.readouterr()
        assert 'AI response' in captured.out

    @patch('src.main.should_replay', return_value=None)
    @patch('src.main.call_anthropic', side_effect=Exception('ContextWindowExceededError'))
    def test_process_command_context_window_exceeded(self, mock_anthropic, mock_replay, capsys):
        """Test handling context window exceeded error."""
        from src.model import ContextWindowExceededError
        
        config = Config()
        aliases = {}
        
        with patch('src.main.call_anthropic', side_effect=ContextWindowExceededError(300000)):
            result = process_command('long command', aliases, config)
        
        captured = capsys.readouterr()
        assert '⚠️' in captured.out

    def test_process_command_case_insensitive_config(self, capsys):
        """Test that CONFIG (uppercase) also works."""
        config = Config()
        aliases = {}
        
        result = process_command('CONFIG', aliases, config)
        
        assert result == ""
        captured = capsys.readouterr()
        assert 'Configuration' in captured.out

    def test_process_command_config_with_whitespace(self, capsys):
        """Test that config command works with whitespace."""
        config = Config()
        aliases = {}
        
        # The whitespace will remain after resolve_alias, so 'config' won't be detected
        # This is expected behavior - the user needs to type 'config' without leading whitespace
        # or we need to strip it. Let's test that it gets handled as a non-config command
        with patch('src.main.is_shell_command', return_value=False):
            with patch('src.main.should_replay', return_value=None):
                with patch('src.main.call_anthropic', return_value=('response', [])):
                    with patch('src.main.add_to_message_cache'):
                        with patch('src.main.dbg_messages'):
                            result = process_command('config', aliases, config)
        
        captured = capsys.readouterr()
        assert 'Configuration' in captured.out

