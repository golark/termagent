import os
import sys
from typing import Optional
import anthropic
from .tools import TOOLS, execute_tool
from utils.message_cache import get_command_messages

# Load system prompt at module level
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, 'system_prompt.txt'), 'r', encoding='utf-8') as f:
    system_prompt = f.read().strip()


def should_replay(command) -> bool:
    messages = get_command_messages(command)

    if not messages:
        return False

    tool_use_idx = -1
    for i,m in enumerate(messages):
        if not m['role'] == 'assistant':
            continue
        if not isinstance(m['content'], list):
            continue
        for content in m['content']:
            if content['type'] == 'tool_use':
                tool_use_idx = i
                break

    if tool_use_idx == -1:
        return False

    for i in range(tool_use_idx + 1, len(messages)):
        if messages[i]['role'] == 'assistant' and messages[i]['content']:
            return False

    return True


def replay_message(messages: list) -> str:
    """Replay messages by finding the first tool call, executing it, and returning the result."""
    try:
        # Find the first assistant message with tool calls
        for message in messages:
            if message.get("role") == "assistant" and isinstance(message.get("content"), list):
                for content_block in message["content"]:
                    # Handle both serialized and unserialized content blocks
                    if isinstance(content_block, dict):
                        if content_block.get('type') == "tool_use":
                            # Execute the first tool call found
                            tool_result = execute_tool(content_block.get('name'), content_block.get('input'))
                            return tool_result
                    elif hasattr(content_block, 'type') and content_block.type == "tool_use":
                        # Execute the first tool call found
                        tool_result = execute_tool(content_block.name, content_block.input)
                        return tool_result
        
        # If no tool calls found, return empty string
        return ""
        
    except Exception as e:
        return f"Error replaying message: {str(e)}"


def call_anthropic(message: str, api_key: Optional[str] = None) -> tuple[str, list]:
    try:
        # Get API key from parameter or environment
        key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not key:
            error_msg = "Error: No Anthropic API key provided. Set ANTHROPIC_API_KEY environment variable."
            return error_msg, [{"role": "error", "content": error_msg}]
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=key)
        
        # Make the API call with system message and tools
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": message}
            ],
            tools=TOOLS
        )
        
        # Handle tool calls in a loop until stop_reason is end_turn
        messages = [{"role": "user", "content": message}]
        current_response = response
        
        # Process initial response if it has text content
        if current_response.stop_reason == "end_turn":
            messages.append({
                "role": "assistant",
                "content": current_response.content
            })
            # Extract final message text for display
            final_message = ""
            for content_block in current_response.content:
                if content_block.type == "text":
                    final_message += content_block.text
            return final_message, messages
        
        while current_response.stop_reason == "tool_use":
            # Collect all tool uses from the response
            tool_uses = []
            text_content = ""
            
            for content_block in current_response.content:
                if content_block.type == "text":
                    text_content += content_block.text
                elif content_block.type == "tool_use":
                    tool_uses.append(content_block)
            
            # Print text content if any
            if text_content:
                print(text_content)
            
            # Execute all tools
            tool_results = []
            for tool_use in tool_uses:
                tool_result = execute_tool(tool_use.name, tool_use.input)
                print(f'Tool {tool_use.name} result: {tool_result}')
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": tool_result
                })
            
            # Add assistant response to messages
            messages.append({
                "role": "assistant",
                "content": current_response.content
            })
            
            # Add tool results to messages
            messages.append({
                "role": "user",
                "content": tool_results
            })
            
            # Get next response from Anthropic
            current_response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system_prompt,
                messages=messages,
                tools=TOOLS
            )

        # Return the final text response after tool execution
        if current_response.stop_reason == "end_turn":
            messages.append({
                "role": "assistant",
                "content": current_response.content
            })
            # Extract final message text for display
            final_message = ""
            for content_block in current_response.content:
                if content_block.type == "text":
                    final_message += content_block.text
            return final_message, messages
        
        error_msg = "No response received"
        return error_msg, [{"role": "error", "content": error_msg}]
        
    except Exception as e:
        error_msg = f"Error calling Anthropic API: {str(e)}"
        return error_msg, [{"role": "error", "content": error_msg}]
