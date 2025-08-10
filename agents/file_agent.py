import os
import shutil
import glob
import re
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from agents.base_agent import BaseAgent
import sys
import tty
import termios

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class FileAgent(BaseAgent):
    """File agent that handles file operations like moving, copying, deleting files with LLM interface."""
    
    def __init__(self, llm_model: str = "gpt-3.5-turbo", debug: bool = False):
        super().__init__("file_agent")
        self.debug = debug
        
        # Initialize LLM if available and API key is set
        self.llm = None
        if LLM_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(model=llm_model, temperature=0)
                if self.debug:
                    self._debug_print(f"✅ LLM initialized with model: {llm_model}")
            except Exception as e:
                if self.debug:
                    self._debug_print(f"⚠️ LLM initialization failed: {e}")
        else:
            if self.debug:
                self._debug_print("⚠️ LLM not available - using fallback parsing")
        
        # System prompt for LLM
        self.system_prompt = """Convert natural language to valid shell commands. Return only the command, nothing else.

File Operations Examples:
- "move file.txt to folder/" → "mv file.txt folder/"
- "copy data.csv to backup/" → "cp data.csv backup/"
- "delete old.log" → "rm old.log"
- "create folder logs" → "mkdir logs"
- "list files in docs/" → "ls docs/"
- "find *.txt files" → "find . -name '*.txt'"
- "rename old.txt to new.txt" → "mv old.txt new.txt"
- "create directory backup" → "mkdir backup"
- "remove folder temp" → "rm -rf temp"
- "copy directory source to dest" → "cp -r source dest"
- "show contents of current directory" → "ls -la"
- "find files containing pattern" → "find . -name '*pattern*'"
- "list all files" → "ls -la"
- "show hidden files" → "ls -la"
- "create nested directories" → "mkdir -p parent/child"
- "remove file and ignore errors" → "rm -f file.txt"
- "copy with verbose output" → "cp -v source dest"
- "move with backup" → "mv -b file.txt file.txt~"

Common shell commands:
- mv (move/rename), cp (copy), rm (remove/delete), mkdir (create directory)
- ls (list), find (search), touch (create empty file), chmod (change permissions)
- Use -r for recursive operations on directories
- Use -f for force operations (ignore errors)
- Use -v for verbose output
- Use -p for creating parent directories

Return only the shell command, no explanations, quotes, or additional text:"""
        
        if self.debug:
            self._debug_print("🤖 FileAgent initialized successfully")

    def _debug_print(self, message: str):
        """Print debug message only if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] FileAgent: {message}")
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Check if this agent should handle the current input."""
        # This agent is called via MCP from the router
        should_handle = state.get("routed_to") == "file_agent"
        return should_handle
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process file operations with LLM support for natural language conversion."""
        command = state.get("last_command", "")
        if self.debug:
            self._debug_print(f"Processing command: {command}")
        
        if not command:
            return state
        
        try:
            # Convert natural language to file operation using LLM
            converted_operation = self._convert_natural_language_to_operation(command)
            if self.debug:
                self._debug_print(f"Converted operation: {converted_operation}")
            
            # Ask for confirmation before executing
            if not self._confirm_operation_execution(converted_operation):
                return self._add_cancelled_message(state, converted_operation)
            
            # Execute the file operation
            result = self._execute_file_operation(converted_operation)
            return self._add_success_message(state, f"Executed: {converted_operation}\nResult: {result}")
                
        except Exception as e:
            if self.debug:
                self._debug_print(f"Error in process: {str(e)}")
            return self._add_error_message(state, str(e))
    
    def _confirm_operation_execution(self, operation: str) -> bool:
        """Ask for user confirmation before executing a file operation."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print("↵ to confirm, 'n' to skip")
                print(f"> {operation}", end="")
                response = input().strip().lower()
                
                if response in ['n', 'no', 'cancel', 'skip']:
                    print("\n❌ Operation cancelled by user")
                    return False
                else:
                    return True
                    
            except KeyboardInterrupt:
                print("\n❌ Operation cancelled by user")
                return False
            except EOFError:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"\n⚠️  Input error, retrying... ({retry_count}/{max_retries})")
                else:
                    print("\n❌ Operation cancelled (too many input errors)")
                    return False
    
    def _get_single_char(self) -> str:
        """Get a single character input from the user."""
        try:
            # Save terminal settings
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            try:
                # Set terminal to raw mode
                tty.setraw(sys.stdin.fileno())
                
                # Read a single character
                ch = sys.stdin.read(1)
                
                # If it's the start of an escape sequence, read more
                if ch == '\x1b':
                    # Read additional characters to complete escape sequence
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        # This is an arrow key or other escape sequence, not just escape
                        ch3 = sys.stdin.read(1)
                        # Return a different character to indicate it's not escape
                        return 'arrow'
                    else:
                        # Just escape key
                        return '\x1b'
                
                return ch
                
            finally:
                # Restore terminal settings
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
        except Exception as e:
            # Fallback to regular input if raw mode fails
            if self.debug:
                self._debug_print(f"Raw mode failed: {e}, using fallback")
            return input().strip()
    
    def _convert_natural_language_to_operation(self, natural_language: str) -> str:
        """Convert natural language to file operation using LLM."""
        try:
            # If LLM is not available, use fallback parsing
            if not self.llm:
                if self.debug:
                    self._debug_print("Using fallback parsing (LLM not available)")
                return self._fallback_parse(natural_language)
            
            # Create messages for LLM
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=natural_language)
            ]
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Extract the operation from the response
            operation = response.content.strip()
            
            # Clean up the response (remove quotes, extra spaces, etc.)
            operation = re.sub(r'^["\']|["\']$', '', operation)  # Remove surrounding quotes
            operation = re.sub(r'\s+', ' ', operation)  # Normalize spaces
            
            return operation
            
        except Exception as e:
            # If LLM fails, try to fall back to basic parsing
            if self.debug:
                self._debug_print(f"LLM conversion failed: {e}, using fallback parsing")
            return self._fallback_parse(natural_language)
    
    def _fallback_parse(self, natural_language: str) -> str:
        """Fallback parsing for natural language when LLM is not available."""
        text = natural_language.lower()
        
        # Basic keyword-based conversion
        if "move" in text:
            # Extract source and destination
            move_match = re.search(r'move\s+([^\s]+(?:\s+[^\s]+)*?)\s+(?:to|into|in)\s+([^\s]+(?:\s+[^\s]+)*)', text)
            if move_match:
                source = move_match.group(1).strip()
                dest = move_match.group(2).strip()
                result = f"mv {source} {dest}"
            else:
                # Try simpler pattern
                parts = text.split()
                if len(parts) >= 3 and parts[0] == "move":
                    source = parts[1]
                    dest = parts[-1] if parts[-1] != "to" else parts[-2]
                    result = f"mv {source} {dest}"
                else:
                    result = f"mv {text[5:]}"
        elif "copy" in text:
            # Extract source and destination
            copy_match = re.search(r'copy\s+([^\s]+(?:\s+[^\s]+)*?)\s+(?:to|into|in)\s+([^\s]+(?:\s+[^\s]+)*)', text)
            if copy_match:
                source = copy_match.group(1).strip()
                dest = copy_match.group(2).strip()
                result = f"cp {source} {dest}"
            else:
                # Try simpler pattern
                parts = text.split()
                if len(parts) >= 3 and parts[0] == "copy":
                    source = parts[1]
                    dest = parts[-1] if parts[-1] != "to" else parts[-2]
                    result = f"cp {source} {dest}"
                else:
                    result = f"cp {text[5:]}"
        elif "delete" in text or "remove" in text:
            # Extract file/folder to delete
            delete_match = re.search(r'(?:delete|remove)\s+([^\s]+(?:\s+[^\s]+)*)', text)
            if delete_match:
                target = delete_match.group(1).strip()
                result = f"rm {target}"
            else:
                result = f"rm {text[7:] if 'delete' in text else text[7:]}"
        elif "create" in text and ("folder" in text or "directory" in text):
            # Extract folder name
            create_match = re.search(r'create\s+(?:folder|directory)\s+([^\s]+(?:\s+[^\s]+)*)', text)
            if create_match:
                folder = create_match.group(1).strip()
                result = f"mkdir {folder}"
            else:
                result = f"mkdir {text[7:]}"
        elif "list" in text and ("files" in text or "contents" in text):
            # Extract directory to list
            list_match = re.search(r'list\s+(?:files\s+)?(?:in\s+)?([^\s]+(?:\s+[^\s]+)*)', text)
            if list_match:
                directory = list_match.group(1).strip()
                result = f"ls {directory}"
            else:
                result = "ls ."
        elif "find" in text:
            # Extract pattern to find
            find_match = re.search(r'find\s+([^\s]+(?:\s+[^\s]+)*)', text)
            if find_match:
                pattern = find_match.group(1).strip()
                # Handle glob patterns and file extensions
                if '*' in pattern or pattern.endswith('.txt') or pattern.endswith('.py') or pattern.endswith('.js'):
                    result = f"find . -name '{pattern}'"
                else:
                    result = f"find . -name '*{pattern}*'"
            else:
                # Try to extract pattern after "find"
                parts = text.split()
                if len(parts) > 1 and parts[0] == "find":
                    pattern = parts[1]
                    if '*' in pattern or pattern.endswith('.txt') or pattern.endswith('.py') or pattern.endswith('.js'):
                        result = f"find . -name '{pattern}'"
                    else:
                        result = f"find . -name '*{pattern}*'"
                else:
                    result = f"find . -name '*{text[5:]}*'"
        elif "rename" in text:
            # Extract old and new names
            rename_match = re.search(r'rename\s+([^\s]+(?:\s+[^\s]+)*?)\s+(?:to|as)\s+([^\s]+(?:\s+[^\s]+)*)', text)
            if rename_match:
                old_name = rename_match.group(1).strip()
                new_name = rename_match.group(2).strip()
                result = f"mv {old_name} {new_name}"
            else:
                result = f"mv {text[7:]}"
        else:
            # If we can't parse it, just return as is
            result = natural_language
        
        return result
    
    def _execute_file_operation(self, operation: str) -> str:
        """Execute a shell command for file operations."""
        try:
            if self.debug:
                self._debug_print(f"Executing shell command: {operation}")
            
            # Execute the command using subprocess
            result = subprocess.run(
                operation,
                shell=True,
                capture_output=True,
                text=True,
                cwd="."
            )

            
            if result.returncode == 0:
                output = result.stdout.strip() if result.stdout.strip() else "Command executed successfully"
                if self.debug:
                    self._debug_print(f"Command successful, output: {output[:100]}...")
                return output
            else:
                error_msg = result.stderr.strip() if result.stderr.strip() else "Unknown error"
                if self.debug:
                    self._debug_print(f"Command failed, error: {error_msg[:100]}...")
                return f"Error: {error_msg}"
                
        except Exception as e:
            error_msg = f"Failed to execute shell command: {str(e)}"
            if self.debug:
                self._debug_print(f"Exception during execution: {str(e)}")
            return error_msg
    
    def _move_file(self, source: str, dest: str) -> str:
        """Move a file or directory."""
        try:
            source_path = Path(source)
            dest_path = Path(dest)
            
            if not source_path.exists():
                return f"Error: Source '{source}' does not exist"
            
            # If destination is a directory, append source filename
            if dest_path.is_dir() or (not dest_path.suffix and not dest_path.exists()):
                dest_path = dest_path / source_path.name
            
            # Create destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source_path), str(dest_path))
            return f"Moved '{source}' to '{dest_path}'"
        except Exception as e:
            return f"Error moving file: {str(e)}"
    
    def _copy_file(self, source: str, dest: str) -> str:
        """Copy a file or directory."""
        try:
            source_path = Path(source)
            dest_path = Path(dest)
            
            if not source_path.exists():
                return f"Error: Source '{source}' does not exist"
            
            # If destination is a directory, append source filename
            if dest_path.is_dir() or (not dest_path.suffix and not dest_path.exists()):
                dest_path = dest_path / source_path.name
            
            # Create destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            if source_path.is_dir():
                shutil.copytree(str(source_path), str(dest_path), dirs_exist_ok=True)
            else:
                shutil.copy2(str(source_path), str(dest_path))
            
            return f"Copied '{source}' to '{dest_path}'"
        except Exception as e:
            return f"Error copying file: {str(e)}"
    
    def _delete_file(self, target: str) -> str:
        """Delete a file or directory."""
        try:
            target_path = Path(target)
            
            if not target_path.exists():
                return f"Error: Target '{target}' does not exist"
            
            if target_path.is_dir():
                shutil.rmtree(str(target_path))
                return f"Deleted directory '{target}'"
            else:
                target_path.unlink()
                return f"Deleted file '{target}'"
        except Exception as e:
            return f"Error deleting file: {str(e)}"
    
    def _create_directory(self, folder: str) -> str:
        """Create a directory."""
        try:
            folder_path = Path(folder)
            
            if folder_path.exists():
                return f"Directory '{folder}' already exists"
            
            folder_path.mkdir(parents=True, exist_ok=True)
            return f"Created directory '{folder}'"
        except Exception as e:
            return f"Error creating directory: {str(e)}"
    
    def _list_directory(self, directory: str) -> str:
        """List contents of a directory."""
        try:
            dir_path = Path(directory)
            
            if not dir_path.exists():
                return f"Error: Directory '{directory}' does not exist"
            
            if not dir_path.is_dir():
                return f"Error: '{directory}' is not a directory"
            
            items = []
            for item in dir_path.iterdir():
                if item.is_dir():
                    items.append(f"[DIR] {item.name}/")
                else:
                    items.append(f"[FILE] {item.name}")
            
            if not items:
                return f"Directory '{directory}' is empty"
            
            return f"Contents of '{directory}':\n" + "\n".join(sorted(items))
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    def _find_files(self, pattern: str) -> str:
        """Find files matching a pattern."""
        try:
            # Handle glob patterns
            if '*' in pattern or '?' in pattern:
                matches = glob.glob(pattern, recursive=True)
            else:
                # Simple search for files containing the pattern
                matches = []
                for root, dirs, files in os.walk('.'):
                    for file in files:
                        if pattern.lower() in file.lower():
                            matches.append(os.path.join(root, file))
            
            if not matches:
                return f"No files found matching pattern '{pattern}'"
            
            return f"Found {len(matches)} file(s) matching '{pattern}':\n" + "\n".join(matches[:20])  # Limit to 20 results
        except Exception as e:
            return f"Error finding files: {str(e)}"
    
    def _rename_file(self, old_name: str, new_name: str) -> str:
        """Rename a file or directory."""
        try:
            old_path = Path(old_name)
            new_path = Path(new_name)
            
            if not old_path.exists():
                return f"Error: Source '{old_name}' does not exist"
            
            if new_path.exists():
                return f"Error: Destination '{new_name}' already exists"
            
            # Create destination directory if it doesn't exist
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            old_path.rename(new_path)
            return f"Renamed '{old_name}' to '{new_name}'"
        except Exception as e:
            return f"Error renaming file: {str(e)}"
    
    def _add_success_message(self, state: Dict[str, Any], result: str) -> Dict[str, Any]:
        """Add a success message to the state."""
        messages = state.get("messages", [])
        messages.append(AIMessage(content=result))
        
        return {
            **state,
            "messages": messages,
            "file_result": result
        }
    
    def _add_error_message(self, state: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Add an error message to the state."""
        messages = state.get("messages", [])
        messages.append(AIMessage(content=error))
        
        return {
            **state,
            "messages": messages,
            "error": error
        }

    def _add_cancelled_message(self, state: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Add a cancelled message to the state."""
        messages = state.get("messages", [])
        messages.append(AIMessage(content="Operation cancelled"))
        
        return {
            **state,
            "messages": messages,
            "cancelled": True
        }
