"""Unit tests for message_cache module."""

import os
import json
import tempfile
import pytest
from unittest.mock import patch

from src.utils.message_cache import (
    get_messages_file_path,
    initialize_messages,
    add_to_message_cache,
    get_command_messages,
    should_replay,
    serialize_messages,
    dump_message_cache,
    _serialize_content
)


class TestMessageCache:
    """Test message cache functionality."""

    def test_get_messages_file_path(self):
        """Test getting messages file path."""
        path = get_messages_file_path()
        assert '.termagent' in path
        assert 'messages.json' in path
        assert path.startswith(os.path.expanduser('~'))

    def test_initialize_messages_empty(self):
        """Test initializing messages with no existing file."""
        with patch('src.utils.message_cache.get_messages_file_path') as mock_path:
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp_path = tmp.name
            mock_path.return_value = tmp_path
            
            # Reset global variable
            import src.utils.message_cache
            src.utils.message_cache._messages_dict = None
            
            initialize_messages()
            
            from src.utils.message_cache import _messages_dict
            assert _messages_dict == {}

    def test_add_to_message_cache(self):
        """Test adding messages to cache."""
        with patch('src.utils.message_cache.get_messages_file_path') as mock_path:
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp_path = tmp.name
            mock_path.return_value = tmp_path
            
            # Reset global variable
            import src.utils.message_cache
            src.utils.message_cache._messages_dict = None
            
            initialize_messages()
            
            messages = [
                {'role': 'user', 'content': 'test command'},
                {'role': 'assistant', 'content': 'response'}
            ]
            
            add_to_message_cache('test command', messages)
            
            cached = get_command_messages('test command')
            assert len(cached) == 2
            assert cached[0]['role'] == 'user'

    def test_add_to_message_cache_with_error(self):
        """Test that messages with errors are not cached."""
        with patch('src.utils.message_cache.get_messages_file_path') as mock_path:
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp_path = tmp.name
            mock_path.return_value = tmp_path
            
            # Reset global variable
            import src.utils.message_cache
            src.utils.message_cache._messages_dict = None
            
            initialize_messages()
            
            messages = [
                {'role': 'user', 'content': 'test command'},
                {'role': 'error', 'content': 'error message'}
            ]
            
            add_to_message_cache('test command', messages)
            
            cached = get_command_messages('test command')
            assert len(cached) == 0

    def test_get_command_messages_nonexistent(self):
        """Test getting messages for non-existent command."""
        with patch('src.utils.message_cache.get_messages_file_path') as mock_path:
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp_path = tmp.name
            mock_path.return_value = tmp_path
            
            # Reset global variable
            import src.utils.message_cache
            src.utils.message_cache._messages_dict = None
            
            initialize_messages()
            
            cached = get_command_messages('nonexistent')
            assert cached == []

    def test_serialize_content_dict(self):
        """Test serializing dictionary content."""
        content = {'type': 'text', 'value': 'test'}
        result = _serialize_content(content)
        assert result == {'type': 'text', 'value': 'test'}

    def test_serialize_content_list(self):
        """Test serializing list content."""
        content = [{'type': 'text'}, {'type': 'tool_use'}]
        result = _serialize_content(content)
        assert len(result) == 2
        assert result[0] == {'type': 'text'}

    def test_serialize_content_object(self):
        """Test serializing object with attributes."""
        class MockContent:
            def __init__(self):
                self.type = 'text'
                self.text = 'content'
                self.id = '123'
                self.name = 'test'
                self.input = {}
        
        content = MockContent()
        result = _serialize_content(content)
        
        assert result['type'] == 'text'
        assert result['text'] == 'content'
        assert result['id'] == '123'

    def test_serialize_messages(self):
        """Test serializing messages list."""
        messages = [
            {'role': 'user', 'content': 'test'},
            {'role': 'assistant', 'content': [{'type': 'text', 'text': 'response'}]}
        ]
        
        serialized = serialize_messages(messages)
        
        assert len(serialized) == 2
        assert serialized[0]['role'] == 'user'
        assert serialized[0]['content'] == 'test'

    def test_should_replay_with_tool_use(self):
        """Test should_replay returns command when tool_use present."""
        with patch('src.utils.message_cache.get_messages_file_path') as mock_path:
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp_path = tmp.name
            mock_path.return_value = tmp_path
            
            # Reset global variable
            import src.utils.message_cache
            src.utils.message_cache._messages_dict = None
            
            initialize_messages()
            
            messages = [
                {'role': 'user', 'content': 'test'},
                {'role': 'assistant', 'content': [
                    {'type': 'tool_use', 'name': 'bash', 'input': {'command': 'ls -la'}}
                ]}
            ]
            
            add_to_message_cache('test', messages)
            
            result = should_replay('test')
            assert result == 'ls -la'

    def test_should_replay_no_tool_use(self):
        """Test should_replay returns None/False when no tool_use."""
        with patch('src.utils.message_cache.get_messages_file_path') as mock_path:
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp_path = tmp.name
            mock_path.return_value = tmp_path
            
            # Reset global variable
            import src.utils.message_cache
            src.utils.message_cache._messages_dict = None
            
            initialize_messages()
            
            messages = [
                {'role': 'user', 'content': 'test'},
                {'role': 'assistant', 'content': 'response'}
            ]
            
            add_to_message_cache('test', messages)
            
            result = should_replay('test')
            # The function returns False when no tool_use is found
            assert result is False

    def test_dump_message_cache(self):
        """Test dumping message cache to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_file = os.path.join(tmpdir, 'messages.json')
            
            with patch('src.utils.message_cache.get_messages_file_path') as mock_path:
                mock_path.return_value = messages_file
                
                # Reset global variable
                import src.utils.message_cache
                src.utils.message_cache._messages_dict = None
                
                initialize_messages()
                
                messages = [
                    {'role': 'user', 'content': 'test'},
                    {'role': 'assistant', 'content': 'response'}
                ]
                
                add_to_message_cache('test', messages)
                dump_message_cache()
                
                assert os.path.exists(messages_file)
                
                with open(messages_file, 'r') as f:
                    data = json.load(f)
                    assert 'test' in data

