"""Unit tests for permissions module."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from src.utils.permissions import PermissionsManager


class TestPermissionsManager:
    """Test PermissionsManager class."""

    def test_normalize_path(self):
        """Test path normalization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms = PermissionsManager(os.path.join(tmpdir, "permissions.json"))
            
            normalized = perms._normalize_path("test")
            assert os.path.isabs(normalized)

    def test_grant_permission(self):
        """Test granting permission for a path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            perms = PermissionsManager(perms_file)
            
            test_path = os.path.join(tmpdir, "test")
            perms._grant_permission(test_path)
            
            assert perms._has_permission(test_path)

    def test_has_permission_parent(self):
        """Test that permission on parent grants access to children."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            perms = PermissionsManager(perms_file)
            
            parent_path = os.path.join(tmpdir, "parent")
            child_path = os.path.join(parent_path, "child")
            
            perms._grant_permission(parent_path)
            
            assert perms._has_permission(parent_path)
            assert perms._has_permission(child_path)

    def test_has_permission_no_grant(self):
        """Test that permission check returns False for non-granted paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            perms = PermissionsManager(perms_file)
            
            test_path = os.path.join(tmpdir, "test")
            
            assert not perms._has_permission(test_path)

    @patch('builtins.input', return_value='')
    def test_request_write_access_accept(self, mock_input):
        """Test requesting write access and accepting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            perms = PermissionsManager(perms_file)
            
            test_path = os.path.join(tmpdir, "test")
            
            result = perms.request_write_access(test_path)
            
            assert result is True
            assert perms._has_permission(test_path)

    @patch('builtins.input', return_value='x')
    def test_request_write_access_deny(self, mock_input):
        """Test requesting write access and denying."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            perms = PermissionsManager(perms_file)
            
            test_path = os.path.join(tmpdir, "test")
            
            result = perms.request_write_access(test_path)
            
            assert result is False
            assert not perms._has_permission(test_path)

    def test_request_write_access_already_granted(self):
        """Test that already granted paths don't prompt again."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            perms = PermissionsManager(perms_file)
            
            # Grant permission to the temp directory itself
            # This way when we request access to a path within it, it will be granted
            perms._grant_permission(tmpdir)
            
            # Create a test path within the granted directory
            test_path = os.path.join(tmpdir, "test")
            
            # Should return True without prompting (no input mock needed)
            # because tmpdir is already granted and test_path is a child
            result = perms.request_write_access(test_path)
            
            assert result is True

    def test_revoke_access(self):
        """Test revoking access to a path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            perms = PermissionsManager(perms_file)
            
            test_path = os.path.join(tmpdir, "test")
            perms._grant_permission(test_path)
            
            assert perms._has_permission(test_path)
            
            perms.revoke_access(test_path)
            
            assert not perms._has_permission(test_path)

    def test_clear_all(self):
        """Test clearing all permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            perms = PermissionsManager(perms_file)
            
            perms._grant_permission(os.path.join(tmpdir, "test1"))
            perms._grant_permission(os.path.join(tmpdir, "test2"))
            
            assert len(perms.granted_paths) == 2
            
            perms.clear_all()
            
            assert len(perms.granted_paths) == 0

    def test_list_permissions(self):
        """Test listing all permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            perms = PermissionsManager(perms_file)
            
            path1 = os.path.join(tmpdir, "test1")
            path2 = os.path.join(tmpdir, "test2")
            
            perms._grant_permission(path1)
            perms._grant_permission(path2)
            
            permissions = perms.list_permissions()
            
            assert len(permissions) == 2
            assert any(path1 in p for p in permissions)
            assert any(path2 in p for p in permissions)

    def test_persistence(self):
        """Test that permissions persist across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            
            # Create first instance and grant permission
            perms1 = PermissionsManager(perms_file)
            test_path = os.path.join(tmpdir, "test")
            perms1._grant_permission(test_path)
            
            # Create second instance and verify permission exists
            perms2 = PermissionsManager(perms_file)
            
            assert perms2._has_permission(test_path)

    def test_has_write_access_for_file(self):
        """Test checking write access for a file (not directory)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            perms_file = os.path.join(tmpdir, "permissions.json")
            perms = PermissionsManager(perms_file)
            
            # Grant permission to directory
            perms._grant_permission(tmpdir)
            
            # Check permission for file in that directory
            test_file = os.path.join(tmpdir, "test.txt")
            
            assert perms.has_write_access(test_file)

