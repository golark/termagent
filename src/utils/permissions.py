"""Permissions management for file system write access."""

import json
import os
from pathlib import Path
from typing import Set


class PermissionsManager:
    """Manages write permissions for directories."""
    
    def __init__(self, permissions_file: str = None):
        if permissions_file is None:
            permissions_file = os.path.expanduser("~/.termagent/permissions.json")
        
        self.permissions_file = permissions_file
        self.granted_paths: Set[str] = self._load_permissions()
    
    def _load_permissions(self) -> Set[str]:
        """Load granted permissions from file."""
        if not os.path.exists(self.permissions_file):
            return set()
        
        try:
            with open(self.permissions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('granted_paths', []))
        except (json.JSONDecodeError, IOError):
            return set()
    
    def _save_permissions(self) -> None:
        """Save granted permissions to file."""
        os.makedirs(os.path.dirname(self.permissions_file), exist_ok=True)
        
        data = {'granted_paths': sorted(list(self.granted_paths))}
        with open(self.permissions_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path to absolute form."""
        return str(Path(path).resolve())
    
    def _has_permission(self, target_path: str) -> bool:
        """Check if permission exists for target path or any parent."""
        target = self._normalize_path(target_path)
        target_parts = Path(target).parts
        
        for granted in self.granted_paths:
            granted_parts = Path(granted).parts
            
            # Check if granted path is a parent of target
            if len(granted_parts) <= len(target_parts):
                if target_parts[:len(granted_parts)] == granted_parts:
                    return True
        
        return False
    
    def _grant_permission(self, path: str) -> None:
        """Grant permission for a path."""
        normalized = self._normalize_path(path)
        self.granted_paths.add(normalized)
        self._save_permissions()
    
    def request_write_access(self, path: str) -> bool:
        """Request write access to a folder. Returns True if granted."""
        # If it's a file, get the directory
        path_obj = Path(path)
        if path_obj.is_file() or not path.endswith('/'):
            target_dir = str(path_obj.parent)
        else:
            target_dir = str(path_obj)
        
        # Check if permission already exists
        if self._has_permission(target_dir):
            return True
        
        # Ask for permission
        normalized = self._normalize_path(target_dir)
        print(f"\n✋ Write access requested for: {normalized}")
        
        try:
            response = input("Allow write access? (↵ to accept, x to deny): ").strip().lower()
            
            if response == 'x':
                print("✗ Permission denied")
                return False
            else:
                self._grant_permission(target_dir)
                print("✓ Permission granted")
                return True
        except (KeyboardInterrupt, EOFError):
            print("\n✗ Permission denied")
            return False
    
    def has_write_access(self, path: str) -> bool:
        """Check if write access is granted without prompting."""
        path_obj = Path(path)
        if path_obj.is_file() or not path.endswith('/'):
            target_dir = str(path_obj.parent)
        else:
            target_dir = str(path_obj)
        
        return self._has_permission(target_dir)
    
    def revoke_access(self, path: str) -> None:
        """Revoke access to a path."""
        normalized = self._normalize_path(path)
        if normalized in self.granted_paths:
            self.granted_paths.remove(normalized)
            self._save_permissions()
    
    def clear_all(self) -> None:
        """Clear all granted permissions."""
        self.granted_paths.clear()
        self._save_permissions()
    
    def list_permissions(self) -> list:
        """List all granted permissions."""
        return sorted(list(self.granted_paths))


# Global instance
_permissions_manager = None


def get_permissions_manager() -> PermissionsManager:
    """Get or create the global permissions manager instance."""
    global _permissions_manager
    if _permissions_manager is None:
        _permissions_manager = PermissionsManager()
    return _permissions_manager


def request_write_access(path: str) -> bool:
    """Request write access to a folder. Returns True if granted."""
    return get_permissions_manager().request_write_access(path)


def has_write_access(path: str) -> bool:
    """Check if write access is granted without prompting."""
    return get_permissions_manager().has_write_access(path)

