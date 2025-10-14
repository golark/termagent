"""Unit tests for shell module."""

import os
import pytest
from unittest.mock import patch, MagicMock

from src.shell.shell import (
    is_shell_command,
    is_cd,
    handle_cd_command,
    execute_shell_command,
    is_interactive_command
)


class TestShellCommands:
    """Test shell command detection and execution."""

    def test_is_shell_command_basic_commands(self):
        """Test detection of basic shell commands."""
        assert is_shell_command('ls') is True
        assert is_shell_command('pwd') is True
        assert is_shell_command('cat file.txt') is True
        assert is_shell_command('grep pattern') is True

    def test_is_shell_command_with_flags(self):
        """Test detection of commands with flags."""
        assert is_shell_command('ls -la') is True
        assert is_shell_command('grep -r pattern') is True
        assert is_shell_command('ps aux') is True

    def test_is_shell_command_git_commands(self):
        """Test detection of git commands."""
        assert is_shell_command('git') is True
        assert is_shell_command('git status') is True
        assert is_shell_command('git commit -m "message"') is True

    def test_is_shell_command_paths(self):
        """Test detection of path-based commands."""
        assert is_shell_command('./script.sh') is True
        assert is_shell_command('../run.sh') is True
        assert is_shell_command('/usr/bin/python') is True

    def test_is_shell_command_not_shell(self):
        """Test that non-shell commands are not detected."""
        assert is_shell_command('please list files') is False
        assert is_shell_command('what is the weather') is False
        assert is_shell_command('') is False

    def test_is_interactive_command(self):
        """Test detection of interactive commands."""
        assert is_interactive_command('vim') is True
        assert is_interactive_command('nano') is True
        assert is_interactive_command('htop') is True
        assert is_interactive_command('less file.txt') is True
        assert is_interactive_command('ssh user@host') is True
        
        assert is_interactive_command('ls') is False
        assert is_interactive_command('cat') is False

    def test_is_cd_command(self):
        """Test detection of cd commands."""
        assert is_cd('cd') is True
        assert is_cd('cd /tmp') is True
        assert is_cd('cd ..') is True
        assert is_cd('cd -') is True
        
        assert is_cd('ls') is False
        assert is_cd('pwd') is False
        assert is_cd('') is False

    def test_handle_cd_home(self, tmp_path):
        """Test cd to home directory."""
        original_dir = os.getcwd()
        try:
            output, code = handle_cd_command('cd')
            assert code == 0
            assert 'home directory' in output.lower()
        finally:
            os.chdir(original_dir)

    def test_handle_cd_directory(self, tmp_path):
        """Test cd to a specific directory."""
        original_dir = os.getcwd()
        try:
            test_dir = tmp_path / "test"
            test_dir.mkdir()
            
            output, code = handle_cd_command(f'cd {test_dir}')
            assert code == 0
            assert str(test_dir) in output
            assert os.getcwd() == str(test_dir)
        finally:
            os.chdir(original_dir)

    def test_handle_cd_parent(self, tmp_path):
        """Test cd to parent directory."""
        original_dir = os.getcwd()
        try:
            test_dir = tmp_path / "test"
            test_dir.mkdir()
            os.chdir(test_dir)
            
            output, code = handle_cd_command('cd ..')
            assert code == 0
            assert 'parent directory' in output.lower()
            assert os.getcwd() == str(tmp_path)
        finally:
            os.chdir(original_dir)

    def test_handle_cd_previous(self, tmp_path):
        """Test cd to previous directory."""
        original_dir = os.getcwd()
        try:
            test_dir1 = tmp_path / "test1"
            test_dir2 = tmp_path / "test2"
            test_dir1.mkdir()
            test_dir2.mkdir()
            
            # First cd to establish previous directory
            handle_cd_command(f'cd {test_dir1}')
            handle_cd_command(f'cd {test_dir2}')
            
            # Now cd -
            output, code = handle_cd_command('cd -')
            assert code == 0
            assert 'previous directory' in output.lower()
            assert os.getcwd() == str(test_dir1)
        finally:
            os.chdir(original_dir)

    def test_handle_cd_nonexistent(self):
        """Test cd to non-existent directory."""
        output, code = handle_cd_command('cd /nonexistent/directory/path')
        assert code == 1
        assert 'not found' in output.lower()

    @patch('subprocess.run')
    def test_execute_shell_command_success(self, mock_run):
        """Test executing a successful shell command."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'command output'
        mock_run.return_value.stderr = ''
        
        with patch('builtins.print'):
            output, code = execute_shell_command('ls')
        
        assert code == 0
        assert 'command output' in output

    @patch('subprocess.run')
    def test_execute_shell_command_with_stderr(self, mock_run):
        """Test executing command with stderr output."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ''
        mock_run.return_value.stderr = 'error message'
        
        with patch('builtins.print'):
            output, code = execute_shell_command('invalid_command')
        
        assert code == 1
        assert 'error message' in output

    @patch('subprocess.run')
    def test_execute_shell_command_timeout(self, mock_run):
        """Test command timeout handling."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired('cmd', 30)
        
        with patch('builtins.print'):
            output, code = execute_shell_command('long_running_command')
        
        assert code == 124
        assert 'timed out' in output.lower()

    def test_execute_cd_command(self, tmp_path):
        """Test that cd commands are handled specially."""
        original_dir = os.getcwd()
        try:
            test_dir = tmp_path / "test"
            test_dir.mkdir()
            
            with patch('builtins.print'):
                output, code = execute_shell_command(f'cd {test_dir}')
            
            assert code == 0
            assert os.getcwd() == str(test_dir)
        finally:
            os.chdir(original_dir)

