"""Unit tests for history module."""

import os
import tempfile
import pytest

from src.shell.history import CommandHistory, get_history_file_path


class TestCommandHistory:
    """Test CommandHistory class."""

    def test_add_command(self):
        """Test adding commands to history."""
        history = CommandHistory()
        history.add_command('ls -la')
        history.add_command('pwd')
        
        assert len(history.history) == 2
        assert history.history[0] == 'ls -la'
        assert history.history[1] == 'pwd'

    def test_add_duplicate_command(self):
        """Test that duplicate consecutive commands are not added."""
        history = CommandHistory()
        history.add_command('ls -la')
        history.add_command('ls -la')
        
        assert len(history.history) == 1

    def test_add_empty_command(self):
        """Test that empty commands are not added."""
        history = CommandHistory()
        history.add_command('')
        history.add_command('   ')
        
        assert len(history.history) == 0

    def test_max_history_limit(self):
        """Test that history respects max size."""
        history = CommandHistory(max_history=3)
        history.add_command('cmd1')
        history.add_command('cmd2')
        history.add_command('cmd3')
        history.add_command('cmd4')
        
        assert len(history.history) == 3
        assert history.history[0] == 'cmd2'
        assert history.history[-1] == 'cmd4'

    def test_get_previous(self):
        """Test getting previous command."""
        history = CommandHistory()
        history.add_command('cmd1')
        history.add_command('cmd2')
        history.add_command('cmd3')
        
        assert history.get_previous() == 'cmd3'
        assert history.get_previous() == 'cmd2'
        assert history.get_previous() == 'cmd1'
        assert history.get_previous() is None  # No more history

    def test_get_next(self):
        """Test getting next command."""
        history = CommandHistory()
        history.add_command('cmd1')
        history.add_command('cmd2')
        history.add_command('cmd3')
        
        # Go back first
        history.get_previous()  # Returns cmd3, now at index 2
        history.get_previous()  # Returns cmd2, now at index 1
        
        # Now go forward
        assert history.get_next() == 'cmd3'  # Returns cmd3, now at index 2
        assert history.get_next() == ''  # Future position returns empty string

    def test_clear_history(self):
        """Test clearing all history."""
        history = CommandHistory()
        history.add_command('cmd1')
        history.add_command('cmd2')
        
        history.clear_history()
        
        assert len(history.history) == 0
        assert history.current_index == 0

    def test_get_all_history(self):
        """Test getting all history."""
        history = CommandHistory()
        history.add_command('cmd1')
        history.add_command('cmd2')
        history.add_command('cmd3')
        
        all_history = history.get_all_history()
        
        assert len(all_history) == 3
        assert all_history[0] == 'cmd1'
        assert all_history[-1] == 'cmd3'
        
        # Verify it's a copy
        all_history.append('cmd4')
        assert len(history.history) == 3

    def test_search_history(self):
        """Test searching history."""
        history = CommandHistory()
        history.add_command('ls -la')
        history.add_command('cd /tmp')
        history.add_command('ls files/')
        history.add_command('pwd')
        
        results = history.search_history('ls')
        assert len(results) == 2
        assert 'ls -la' in results
        assert 'ls files/' in results
        
        results = history.search_history('cd')
        assert len(results) == 1
        assert 'cd /tmp' in results

    def test_search_history_case_insensitive(self):
        """Test that history search is case insensitive."""
        history = CommandHistory()
        history.add_command('Git Status')
        history.add_command('GIT LOG')
        
        results = history.search_history('git')
        assert len(results) == 2

    def test_get_history_file_path(self):
        """Test getting history file path."""
        path = get_history_file_path()
        assert '.termagent' in path
        assert 'history' in path
        assert path.startswith(os.path.expanduser('~'))

