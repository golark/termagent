"""Tab completion functionality for shell commands, flags, and file paths."""

import os
import readline
from typing import List


def get_command_flags(command: str) -> List[str]:
    """Get common flags for a given command."""
    flags_map = {
        'ls': ['-a', '--all', '-l', '--long', '-h', '--human-readable', '-t', '--time', 
               '-r', '--reverse', '-S', '--size', '-R', '--recursive', '-d', '--directory',
               '-1', '--one-per-line', '-m', '--comma', '-x', '--horizontal', '-C', '--columns'],
        
        'grep': ['-i', '--ignore-case', '-v', '--invert-match', '-n', '--line-number',
                 '-c', '--count', '-l', '--files-with-matches', '-L', '--files-without-match',
                 '-r', '--recursive', '-R', '--dereference-recursive', '-w', '--word-regexp',
                 '-x', '--line-regexp', '-A', '--after-context', '-B', '--before-context',
                 '-C', '--context', '--color', '--no-color', '-E', '--extended-regexp',
                 '-F', '--fixed-strings', '-G', '--basic-regexp', '-P', '--perl-regexp'],
        
        'find': ['-name', '-iname', '-type', '-size', '-mtime', '-atime', '-ctime',
                 '-user', '-group', '-perm', '-exec', '-execdir', '-ok', '-okdir',
                 '-print', '-print0', '-printf', '-fprint', '-fprint0', '-fprintf',
                 '-ls', '-delete', '-prune', '-quit', '-maxdepth', '-mindepth',
                 '-follow', '-mount', '-xdev', '-noleaf', '-ignore_readdir_race'],
        
        'git': ['--version', '--help', '--exec-path', '--html-path', '--man-path', '--info-path',
                '--paginate', '--no-pager', '--no-replace-objects', '--bare', '--git-dir',
                '--work-tree', '--namespace', '--super-prefix', '--config-env', '--list-cmds',
                '--no-optional-locks', '--literal-pathspecs', '--glob-pathspecs', '--noglob-pathspecs',
                '--icase-pathspecs', '--no-icase-pathspecs', '--attr-source', '--attr-source-attr',
                '--no-attr-source', '--no-attr-source-attr', '--no-attr-source-attr',
                '--no-attr-source-attr', '--no-attr-source-attr', '--no-attr-source-attr'],
        
        'docker': ['--version', '--help', '-D', '--debug', '-H', '--host', '-l', '--log-level',
                   '--tls', '--tlscacert', '--tlscert', '--tlskey', '--tlsverify',
                   '--config', '--context', '--log-driver', '--log-opt', '--pidfile'],
        
        'python': ['-B', '-d', '-E', '-h', '--help', '-i', '-I', '-O', '-OO', '-q', '-s',
                   '-S', '-u', '-v', '-V', '--version', '-W', '-x', '-X', '-c', '-m'],
        
        'pip': ['--version', '--help', '-v', '--verbose', '-q', '--quiet', '--log', '--no-input',
                '--proxy', '--retries', '--timeout', '--exists-action', '--trusted-host',
                '--cert', '--client-cert', '--cache-dir', '--no-deps', '--pre', '--no-clean',
                '--require-hashes', '--no-binary', '--only-binary', '--prefer-binary',
                '--no-build-isolation', '--use-pep517', '--no-use-pep517', '--check-build-deps',
                '--break-system-packages', '--no-warn-script-location', '--no-warn-conflicts',
                '--force-reinstall', '--no-deps', '--upgrade', '--upgrade-strategy',
                '--force-reinstall', '--no-deps', '--ignore-installed', '--ignore-requires-python',
                '--no-warn-script-location', '--no-warn-conflicts', '--force-reinstall',
                '--no-deps', '--upgrade', '--upgrade-strategy', '--force-reinstall',
                '--no-deps', '--ignore-installed', '--ignore-requires-python'],
        
        'npm': ['--version', '--help', '-v', '--verbose', '-q', '--quiet', '--silent',
                '--no-progress', '--no-audit', '--no-fund', '--no-update-notifier',
                '--no-optional', '--no-shrinkwrap', '--no-package-lock', '--no-save',
                '--no-save-dev', '--no-save-optional', '--no-save-peer', '--no-save-bundle',
                '--no-save-exact', '--no-save-tilde', '--no-save-caret', '--no-save-tilde',
                '--no-save-caret', '--no-save-tilde', '--no-save-caret', '--no-save-tilde'],
        
        'node': ['--version', '--help', '-v', '--verbose', '-e', '--eval', '-p', '--print',
                 '-c', '--check', '-i', '--interactive', '-r', '--require', '--inspect',
                 '--inspect-brk', '--inspect-port', '--inspect-brk-node', '--inspect-brk-wait',
                 '--inspect-brk-wait', '--inspect-brk-wait', '--inspect-brk-wait']
    }
    
    return flags_map.get(command, [])


def get_common_commands() -> List[str]:
    """Get list of common shell commands."""
    return ['ls', 'cd', 'pwd', 'cat', 'grep', 'find', 'mkdir', 'rm', 'cp', 'mv', 
            'python', 'git', 'docker', 'pip', 'npm', 'node']


def get_file_commands() -> List[str]:
    """Get commands that typically work with files."""
    return ['cat', 'ls', 'cd', 'rm', 'cp', 'mv', 'grep', 'find', 'chmod', 'chown']


def complete_files(text: str, state: int) -> str:
    """Complete file paths in the current directory."""
    try:
        # Get all files in the directory
        files = os.listdir('.')
        # Filter files that start with the text
        matches = []
        for f in files:
            if f.startswith(text):
                full_path = os.path.join('.', f)
                if os.path.isdir(full_path):
                    matches.append(f + '/')
                else:
                    matches.append(f)
        
        return matches[state] if state < len(matches) else None
    except (OSError, PermissionError):
        return None


def complete_commands(text: str, state: int) -> str:
    """Complete shell commands."""
    commands = get_common_commands()
    matches = [cmd for cmd in commands if cmd.startswith(text)]
    return matches[state] if state < len(matches) else None


def complete_flags(command: str, text: str, state: int) -> str:
    """Complete flags for a given command."""
    flags = get_command_flags(command)
    matches = [flag for flag in flags if flag.startswith(text)]
    return matches[state] if state < len(matches) else None


def tab_completer(text: str, state: int) -> str:
    """Main tab completion function for commands, flags, and file paths."""
    # Get the current line
    line = readline.get_line_buffer()
    
    # Split the line into words
    words = line.split()
    
    if not words:
        # No words yet, suggest common commands
        return complete_commands(text, state)
    
    # If we're completing the first word (command)
    if len(words) == 1 and not line.endswith(' '):
        return complete_commands(text, state)
    
    # If we're completing flags/options for a command
    #if len(words) > 0 and words[0] in get_common_commands():
    #    command = words[0]
    #    last_word = words[-1]
        
    #    # If the last word starts with - or --, complete flags
    #    if last_word.startswith('-'):
    #        return complete_flags(command, last_word, state)
    
    # If we're completing a file path (after a command)
    if len(words) > 0:
        # Get the last word (which might be a file path)
        last_word = words[-1]
        
        # Commands that typically work with files
        file_commands = get_file_commands()
        
        # If it looks like a file path or the command works with files
        if ('/' in last_word or last_word.startswith('.') or 
            (len(words) > 0 and words[0] in file_commands)):
            # Use the dedicated complete_files function
            basename = os.path.basename(last_word)
            return complete_files(basename, state)
        else:
            # Command argument completion
            return complete_commands(text, state)
    
    return None
