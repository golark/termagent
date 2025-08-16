#!/usr/bin/env python3
"""Executable cache management for TermAgent."""

import os
import json
import pickle
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
import hashlib


class ExecutableCache:
    """Manages caching of available executables for improved performance."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.cache_dir = Path.home() / ".termagent"
        self.cache_file = self.cache_dir / "executables.pkl"
        self.metadata_file = self.cache_dir / "executables_metadata.json"
        self.cache_ttl_hours = 24  # Cache valid for 24 hours
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(exist_ok=True)
        
        if self.debug:
            print(f"fileagent: 📁 Cache directory: {self.cache_dir}")
            print(f"fileagent: 📁 Cache file: {self.cache_file}")
    
    def _get_path_hash(self) -> str:
        """Generate a hash of the current PATH to detect changes."""
        path_str = os.environ.get('PATH', '')
        return hashlib.md5(path_str.encode()).hexdigest()
    
    def _get_path_timestamp(self) -> float:
        """Get the timestamp of the most recently modified PATH directory."""
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        latest_mtime = 0
        
        for path_dir in path_dirs:
            if os.path.isdir(path_dir):
                try:
                    mtime = os.path.getmtime(path_dir)
                    latest_mtime = max(latest_mtime, mtime)
                except (OSError, PermissionError):
                    continue
        
        return latest_mtime
    
    def _is_cache_valid(self) -> bool:
        """Check if the cached executables are still valid."""
        if not self.cache_file.exists() or not self.metadata_file.exists():
            return False
        
        try:
            # Load metadata
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check if cache is expired
            cache_age = time.time() - metadata.get('timestamp', 0)
            if cache_age > (self.cache_ttl_hours * 3600):
                if self.debug:
                    print(f"fileagent: ⏰ Cache expired (age: {cache_age/3600:.1f}h)")
                return False
            
            # Check if PATH has changed
            current_path_hash = self._get_path_hash()
            if metadata.get('path_hash') != current_path_hash:
                if self.debug:
                    print(f"fileagent: 🔄 PATH changed, cache invalid")
                return False
            
            # Check if any PATH directory has been modified
            current_path_timestamp = self._get_path_timestamp()
            if metadata.get('path_timestamp', 0) < current_path_timestamp:
                if self.debug:
                    print(f"fileagent: 🔄 PATH directories modified, cache invalid")
                return False
            
            return True
            
        except (json.JSONDecodeError, IOError) as e:
            if self.debug:
                print(f"fileagent: ⚠️ Error reading cache metadata: {e}")
            return False
    
    def _save_cache(self, executables: Dict[str, str]) -> None:
        """Save executables and metadata to cache files."""
        try:
            # Save executables using pickle for better performance
            with open(self.cache_file, 'wb') as f:
                pickle.dump(executables, f)
            
            # Save metadata as JSON for easy inspection
            metadata = {
                'timestamp': time.time(),
                'path_hash': self._get_path_hash(),
                'path_timestamp': self._get_path_timestamp(),
                'executable_count': len(executables),
                'cache_version': '1.0'
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            if self.debug:
                print(f"fileagent: 💾 Cache saved: {len(executables)} executables")
                
        except Exception as e:
            if self.debug:
                print(f"fileagent: ❌ Error saving cache: {e}")
    
    def _load_cache(self) -> Optional[Dict[str, str]]:
        """Load executables from cache file."""
        try:
            with open(self.cache_file, 'rb') as f:
                executables = pickle.load(f)
            
            if self.debug:
                print(f"fileagent: 📂 Cache loaded: {len(executables)} executables")
            
            return executables
            
        except Exception as e:
            if self.debug:
                print(f"fileagent: ⚠️ Error loading cache: {e}")
            return None
    
    def scan_and_cache_executables(self, force_rescan: bool = False) -> Dict[str, str]:
        """Scan for executables and cache them, or load from cache if valid."""
        if not force_rescan and self._is_cache_valid():
            cached_executables = self._load_cache()
            if cached_executables:
                return cached_executables
        
        if self.debug:
            print(f"fileagent: 🔍 Scanning for executables...")
        
        # Perform fresh scan
        executables = self._scan_executables()
        
        # Save to cache
        self._save_cache(executables)
        
        return executables
    
    def _scan_executables(self) -> Dict[str, str]:
        """Scan the PATH for available executables."""
        executables = {}
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        
        if self.debug:
            print(f"fileagent: 🔍 Scanning {len(path_dirs)} PATH directories...")
        
        for i, path_dir in enumerate(path_dirs):
            if not os.path.isdir(path_dir):
                continue
                
            try:
                files = os.listdir(path_dir)
                if self.debug and i < 5:  # Show first 5 directories
                    print(f"fileagent:   📁 {path_dir} ({len(files)} files)")
                
                for filename in files:
                    file_path = os.path.join(path_dir, filename)
                    
                    # Check if it's an executable file
                    if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                        if filename not in executables:
                            executables[filename] = file_path
                            
            except (OSError, PermissionError) as e:
                if self.debug:
                    print(f"fileagent: ⚠️ Error accessing {path_dir}: {e}")
                continue
        
        if self.debug:
            print(f"fileagent: ✅ Found {len(executables)} executables")
        
        return executables
    
    def get_executables(self) -> Dict[str, str]:
        """Get cached executables, performing scan if necessary."""
        return self.scan_and_cache_executables()
    
    def clear_cache(self) -> None:
        """Clear the executable cache."""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            
            if self.debug:
                print(f"fileagent: 🗑️ Cache cleared")
                
        except Exception as e:
            if self.debug:
                print(f"fileagent: ❌ Error clearing cache: {e}")
    
    def get_cache_info(self) -> Dict[str, any]:
        """Get information about the current cache."""
        if not self.metadata_file.exists():
            return {'status': 'no_cache'}
        
        try:
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            
            cache_age = time.time() - metadata.get('timestamp', 0)
            metadata['cache_age_hours'] = cache_age / 3600
            metadata['status'] = 'valid' if self._is_cache_valid() else 'invalid'
            
            return metadata
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


# Global cache instance
_executable_cache: Optional[ExecutableCache] = None


def get_executable_cache(debug: bool = False) -> ExecutableCache:
    """Get or create the global executable cache instance."""
    global _executable_cache
    if _executable_cache is None:
        _executable_cache = ExecutableCache(debug=debug)
    return _executable_cache


def scan_available_executables() -> Dict[str, str]:
    """Get available executables from cache or scan if needed."""
    cache = get_executable_cache()
    return cache.get_executables()


def resolve_executable_path(command: str, available_executables: Dict[str, str]) -> str:
    """Resolve a command to its full executable path if it starts with an available executable."""
    if not command or ' ' not in command:
        return command
    
    # Get the first word (the command name)
    parts = command.split()
    command_name = parts[0]
    
    # Check if this command name exists in our available executables
    if command_name in available_executables:
        # Replace the command name with the full path
        parts[0] = available_executables[command_name]
        return ' '.join(parts)
    
    return command
