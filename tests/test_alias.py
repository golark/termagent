"""Unit tests for alias module."""

import pytest
from unittest.mock import patch

from src.shell.alias import get_shell_aliases, resolve_alias


class TestAlias:
    """Test alias functionality."""

    def test_resolve_alias_with_existing_alias(self):
        """Test resolving a command with an existing alias."""
        aliases = {
            'll': 'ls -la',
            'gs': 'git status'
        }
        
        result = resolve_alias('ll', aliases)
        assert result == 'ls -la'
        
        result = resolve_alias('gs', aliases)
        assert result == 'git status'

    def test_resolve_alias_with_arguments(self):
        """Test resolving alias with additional arguments."""
        aliases = {
            'll': 'ls -la',
            'gs': 'git status'
        }
        
        result = resolve_alias('ll /tmp', aliases)
        assert result == 'ls -la /tmp'
        
        result = resolve_alias('gs -s', aliases)
        assert result == 'git status -s'

    def test_resolve_alias_no_match(self):
        """Test resolving command with no matching alias."""
        aliases = {
            'll': 'ls -la'
        }
        
        result = resolve_alias('pwd', aliases)
        assert result == 'pwd'

    def test_resolve_alias_empty_command(self):
        """Test resolving empty command."""
        aliases = {'ll': 'ls -la'}
        
        result = resolve_alias('', aliases)
        assert result == ''
        
        result = resolve_alias('   ', aliases)
        assert result == '   '

    def test_resolve_alias_none_aliases(self):
        """Test resolve_alias with None aliases calls get_shell_aliases."""
        with patch('src.shell.alias.get_shell_aliases', return_value={'ll': 'ls -la'}):
            result = resolve_alias('ll', None)
            assert result == 'ls -la'

    def test_get_shell_aliases_success(self):
        """Test getting shell aliases successfully."""
        mock_output = """ll='ls -la'
gs='git status'
gp='git push'"""
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_output
            
            aliases = get_shell_aliases()
            
            assert 'll' in aliases
            assert aliases['ll'] == 'ls -la'
            assert aliases['gs'] == 'git status'
            assert aliases['gp'] == 'git push'

    def test_get_shell_aliases_failure(self):
        """Test getting shell aliases when command fails."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ''
            
            aliases = get_shell_aliases()
            
            assert aliases == {}

    def test_get_shell_aliases_timeout(self):
        """Test getting shell aliases when command times out."""
        import subprocess
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 5)):
            aliases = get_shell_aliases()
            
            assert aliases == {}

    def test_resolve_alias_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        aliases = {'ll': 'ls -la'}
        
        result = resolve_alias('  ll  ', aliases)
        assert result == 'ls -la'
        
        result = resolve_alias('  ll   /tmp  ', aliases)
        assert result == 'ls -la /tmp'

