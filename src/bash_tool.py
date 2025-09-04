#!/usr/bin/env python3
"""
Anthropic Bash Tool - A Python tool for executing bash commands with Anthropic AI integration
"""

import os
import subprocess
import json
import time
import signal
import sys
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CommandResult:
    """Result of a bash command execution"""
    command: str
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    cwd: str

class BashTool:
    """
    A bash tool designed for Anthropic models with enhanced features:
    - Secure command execution with safety checks
    - Persistent shell state
    - Command history and analysis
    - Integration with Anthropic API
    - Enhanced error handling and logging
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the Anthropic Bash Tool
        
        Args:
            api_key: Anthropic API key (if None, will try to get from environment)
            model: Anthropic model to use for analysis
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model
        self.current_dir = os.getcwd()
        self.command_history: List[CommandResult] = []
        self.dangerous_commands = self._load_dangerous_commands()
        self.max_history = 100
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"Bash Tool initialized with model: {self.model}")
    
    def _load_dangerous_commands(self) -> List[str]:
        """Load list of potentially dangerous commands"""
        return [
            'rm -rf /',
            'rm -rf /*',
            'rm -rf ~',
            'rm -rf .',
            'shutdown',
            'reboot',
            'halt',
            'poweroff',
            'mkfs',
            'dd',
            'fdisk',
            'curl | bash',
            'wget | bash',
            'curl | sh',
            'wget | sh',
            '> /dev/sda',
            '> /dev/hda',
            'DROP DATABASE',
            'DELETE FROM',
            'TRUNCATE TABLE',
        ]
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)
    
    def _is_dangerous_command(self, command: str) -> bool:
        """Check if a command contains potentially dangerous operations"""
        command_lower = command.lower().strip()
        return any(dangerous in command_lower for dangerous in self.dangerous_commands)
    
    def _analyze_command_with_anthropic(self, command: str) -> Dict[str, Any]:
        """
        Analyze a command using Anthropic's API for safety and suggestions
        
        Args:
            command: The bash command to analyze
            
        Returns:
            Dictionary with analysis results
        """
        if not self.api_key:
            logger.warning("No Anthropic API key provided, skipping command analysis")
            return {"analysis": "No API key available", "suggestions": []}
        
        try:
            # This would require the anthropic package
            # For now, return a placeholder response
            return {
                "analysis": "Command analysis not implemented (requires anthropic package)",
                "suggestions": [],
                "safety_score": 0.8
            }
        except Exception as e:
            logger.error(f"Error analyzing command with Anthropic: {e}")
            return {"analysis": f"Analysis failed: {e}", "suggestions": []}
    
    def execute_command(self, command: str, timeout: int = 120, analyze: bool = False) -> CommandResult:
        """
        Execute a bash command with safety checks and logging
        
        Args:
            command: The bash command to execute
            timeout: Maximum execution time in seconds
            analyze: Whether to analyze the command with Anthropic
            
        Returns:
            CommandResult object with execution details
        """
        start_time = time.time()
        
        # Safety check
        if self._is_dangerous_command(command):
            logger.warning(f"Potentially dangerous command blocked: {command}")
            return CommandResult(
                command=command,
                stdout="",
                stderr=f"Command blocked: potentially dangerous operation detected",
                exit_code=1,
                execution_time=0.0,
                cwd=self.current_dir
            )
        
        # Analyze command if requested
        analysis = None
        if analyze:
            analysis = self._analyze_command_with_anthropic(command)
            logger.info(f"Command analysis: {analysis}")
        
        logger.info(f"Executing command: {command} (cwd: {self.current_dir})")
        
        try:
            # Handle cd commands specially to maintain state
            if command.strip().startswith('cd '):
                return self._handle_cd_command(command, start_time)
            
            # Execute the command
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.current_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, 'PATH': os.environ.get('PATH', '')}
            )
            
            execution_time = time.time() - start_time
            
            # Create result object
            cmd_result = CommandResult(
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                execution_time=execution_time,
                cwd=self.current_dir
            )
            
            # Add to history
            self._add_to_history(cmd_result)
            
            logger.info(f"Command completed with exit code {result.returncode} in {execution_time:.2f}s")
            
            return cmd_result
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.error(f"Command timed out after {timeout} seconds: {command}")
            return CommandResult(
                command=command,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                exit_code=124,
                execution_time=execution_time,
                cwd=self.current_dir
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing command: {e}")
            return CommandResult(
                command=command,
                stdout="",
                stderr=f"Error: {str(e)}",
                exit_code=1,
                execution_time=execution_time,
                cwd=self.current_dir
            )
    
    def _handle_cd_command(self, command: str, start_time: float) -> CommandResult:
        """Handle cd commands to maintain working directory state"""
        try:
            # Extract target directory
            target_dir = command.strip()[3:].strip()
            
            if not target_dir:
                # cd without arguments goes to home directory
                target_dir = os.path.expanduser('~')
            elif target_dir.startswith('~'):
                # Handle ~ expansion
                target_dir = os.path.expanduser(target_dir)
            elif not os.path.isabs(target_dir):
                # Relative path
                target_dir = os.path.join(self.current_dir, target_dir)
            
            # Check if directory exists
            if not os.path.isdir(target_dir):
                execution_time = time.time() - start_time
                return CommandResult(
                    command=command,
                    stdout="",
                    stderr=f"cd: {target_dir}: No such file or directory",
                    exit_code=1,
                    execution_time=execution_time,
                    cwd=self.current_dir
                )
            
            # Update current directory
            self.current_dir = os.path.abspath(target_dir)
            execution_time = time.time() - start_time
            
            logger.info(f"Changed directory to: {self.current_dir}")
            
            return CommandResult(
                command=command,
                stdout="",
                stderr="",
                exit_code=0,
                execution_time=execution_time,
                cwd=self.current_dir
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return CommandResult(
                command=command,
                stdout="",
                stderr=f"cd error: {str(e)}",
                exit_code=1,
                execution_time=execution_time,
                cwd=self.current_dir
            )
    
    def _add_to_history(self, result: CommandResult):
        """Add command result to history"""
        self.command_history.append(result)
        
        # Keep only the last max_history commands
        if len(self.command_history) > self.max_history:
            self.command_history = self.command_history[-self.max_history:]
    
    def get_history(self, limit: Optional[int] = None) -> List[CommandResult]:
        """Get command execution history"""
        if limit:
            return self.command_history[-limit:]
        return self.command_history.copy()
    
    def get_current_directory(self) -> str:
        """Get current working directory"""
        return self.current_dir
    
    def set_current_directory(self, path: str) -> bool:
        """Set current working directory"""
        try:
            if os.path.isdir(path):
                self.current_dir = os.path.abspath(path)
                logger.info(f"Changed directory to: {self.current_dir}")
                return True
            else:
                logger.error(f"Directory does not exist: {path}")
                return False
        except Exception as e:
            logger.error(f"Error changing directory: {e}")
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                "platform": sys.platform,
                "python_version": sys.version,
                "current_directory": self.current_dir,
                "user": os.getenv('USER', 'unknown'),
                "home": os.path.expanduser('~'),
                "path": os.environ.get('PATH', ''),
                "command_count": len(self.command_history)
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}
    
    def export_history(self, filepath: str) -> bool:
        """Export command history to a JSON file"""
        try:
            history_data = []
            for result in self.command_history:
                history_data.append({
                    "command": result.command,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "execution_time": result.execution_time,
                    "cwd": result.cwd,
                    "timestamp": time.time()
                })
            
            with open(filepath, 'w') as f:
                json.dump(history_data, f, indent=2)
            
            logger.info(f"History exported to: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting history: {e}")
            return False
    
    def clear_history(self):
        """Clear command history"""
        self.command_history.clear()
        logger.info("Command history cleared")


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bash Tool')
    parser.add_argument('command', nargs='?', help='Command to execute')
    parser.add_argument('--api-key', help='Anthropic API key')
    parser.add_argument('--model', default='claude-3-5-sonnet-20241022', help='Anthropic model to use')
    parser.add_argument('--timeout', type=int, default=120, help='Command timeout in seconds')
    parser.add_argument('--analyze', action='store_true', help='Analyze command with Anthropic')
    parser.add_argument('--history', action='store_true', help='Show command history')
    parser.add_argument('--info', action='store_true', help='Show system information')
    parser.add_argument('--export-history', help='Export history to file')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    # Initialize tool
    tool = BashTool(api_key=args.api_key, model=args.model)
    
    if args.info:
        info = tool.get_system_info()
        print(json.dumps(info, indent=2))
        return
    
    if args.history:
        history = tool.get_history()
        for i, result in enumerate(history, 1):
            print(f"{i}. {result.command} (exit: {result.exit_code}, time: {result.execution_time:.2f}s)")
        return
    
    if args.export_history:
        success = tool.export_history(args.export_history)
        print(f"Export {'successful' if success else 'failed'}")
        return
    
    if args.interactive:
        print("Bash Tool - Interactive Mode")
        print("Type 'exit' to quit, 'help' for commands")
        
        while True:
            try:
                command = input(f"{tool.get_current_directory()}> ").strip()
                
                if not command:
                    continue
                
                if command.lower() in ['exit', 'quit', 'q']:
                    print("Goodbye!")
                    break
                
                if command.lower() == 'help':
                    print("Available commands:")
                    print("  help - Show this help")
                    print("  history - Show command history")
                    print("  info - Show system information")
                    print("  pwd - Show current directory")
                    print("  clear - Clear screen")
                    print("  exit/quit/q - Exit the tool")
                    continue
                
                if command.lower() == 'history':
                    history = tool.get_history(10)  # Show last 10 commands
                    for i, result in enumerate(history, 1):
                        print(f"{i}. {result.command} (exit: {result.exit_code})")
                    continue
                
                if command.lower() == 'info':
                    info = tool.get_system_info()
                    print(json.dumps(info, indent=2))
                    continue
                
                if command.lower() == 'pwd':
                    print(tool.get_current_directory())
                    continue
                
                if command.lower() == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    continue
                
                # Execute the command
                result = tool.execute_command(command, timeout=args.timeout, analyze=args.analyze)
                
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                
                if result.exit_code != 0:
                    print(f"Command failed with exit code: {result.exit_code}")
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except EOFError:
                print("\nGoodbye!")
                break
    
    elif args.command:
        # Execute single command
        result = tool.execute_command(args.command, timeout=args.timeout, analyze=args.analyze)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        sys.exit(result.exit_code)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
