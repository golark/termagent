#!/usr/bin/env python3
"""
Directory context utility for providing local directory structure information to the LLM.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional


def get_directory_context(workspace_path: str = None, max_depth: int = 3, max_files_per_dir: int = 20) -> str:
    """Get a structured representation of the local directory for LLM context.
    
    Args:
        workspace_path: Path to the workspace directory (defaults to current working directory)
        max_depth: Maximum directory depth to explore
        max_files_per_dir: Maximum number of files to show per directory
        
    Returns:
        Formatted string representation of directory structure
    """
    if workspace_path is None:
        workspace_path = os.getcwd()
    
    workspace_path = Path(workspace_path).resolve()
    
    if not workspace_path.exists():
        return f"Workspace path does not exist: {workspace_path}"
    
    context_lines = [f"📁 Workspace: {workspace_path.name}"]
    context_lines.append(f"📍 Full path: {workspace_path}")
    context_lines.append("")
    
    try:
        _add_directory_content(context_lines, workspace_path, "", max_depth, max_files_per_dir)
    except Exception as e:
        context_lines.append(f"⚠️  Error reading directory: {e}")
    
    return "\n".join(context_lines)


def _add_directory_content(lines: List[str], directory: Path, prefix: str, depth: int, max_files: int):
    """Recursively add directory content to the context lines."""
    if depth <= 0:
        return
    
    try:
        # Get directory contents
        items = list(directory.iterdir())
        
        # Separate directories and files
        dirs = [item for item in items if item.is_dir() and not item.name.startswith('.')]
        files = [item for item in items if item.is_file() and not item.name.startswith('.')]
        
        # Sort alphabetically
        dirs.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())
        
        # Add directories
        for dir_item in dirs:
            lines.append(f"{prefix}📁 {dir_item.name}/")
            if depth > 1:
                _add_directory_content(lines, dir_item, prefix + "  ", depth - 1, max_files)
        
        # Add files (limited by max_files)
        if len(files) > max_files:
            shown_files = files[:max_files]
            remaining = len(files) - max_files
            for file_item in shown_files:
                lines.append(f"{prefix}📄 {file_item.name}")
            lines.append(f"{prefix}... and {remaining} more files")
        else:
            for file_item in files:
                lines.append(f"{prefix}📄 {file_item.name}")
                
    except PermissionError:
        lines.append(f"{prefix}⚠️  Permission denied")
    except Exception as e:
        lines.append(f"{prefix}⚠️  Error: {e}")


def get_file_content_summary(file_path: str, max_lines: int = 50) -> str:
    """Get a summary of file content for LLM context.
    
    Args:
        file_path: Path to the file
        max_lines: Maximum number of lines to include
        
    Returns:
        Summary of file content
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return f"File not found: {file_path}"
        
        if not file_path.is_file():
            return f"Not a file: {file_path}"
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > 1024 * 1024:  # 1MB
            return f"File too large ({file_size / (1024*1024):.1f}MB): {file_path}"
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if len(lines) <= max_lines:
            content = ''.join(lines)
        else:
            content = ''.join(lines[:max_lines]) + f"\n... and {len(lines) - max_lines} more lines"
        
        return f"📄 {file_path.name}:\n```\n{content}\n```"
        
    except Exception as e:
        return f"Error reading file {file_path}: {e}"


def get_relevant_files_context(workspace_path: str = None, file_patterns: List[str] = None) -> str:
    """Get context for relevant files based on patterns.
    
    Args:
        workspace_path: Path to the workspace directory
        file_patterns: List of file patterns to include (e.g., ['*.py', '*.md', '*.toml'])
        
    Returns:
        Context string for relevant files
    """
    if workspace_path is None:
        workspace_path = os.getcwd()
    
    if file_patterns is None:
        file_patterns = ['*.py', '*.md', '*.toml', '*.yaml', '*.yml', '*.json', '*.txt']
    
    workspace_path = Path(workspace_path).resolve()
    context_lines = [f"🔍 Relevant project files in {workspace_path.name}:"]
    
    try:
        for pattern in file_patterns:
            files = list(workspace_path.rglob(pattern))
            # Filter out virtual environment and hidden directories
            project_files = []
            for f in files:
                if not any(part.startswith('.') or part in ['venv', '.venv', '__pycache__', 'node_modules'] 
                          for part in f.parts):
                    project_files.append(f)
            
            if project_files:
                context_lines.append(f"\n📁 {pattern}:")
                for file_path in sorted(project_files, key=lambda x: x.name.lower())[:8]:  # Limit to 8 files per pattern
                    rel_path = file_path.relative_to(workspace_path)
                    context_lines.append(f"  📄 {rel_path}")
                    
    except Exception as e:
        context_lines.append(f"⚠️  Error scanning files: {e}")
    
    return "\n".join(context_lines)
