import os
import sys
from typing import Optional
import anthropic
from .tools import TOOLS, execute_tool
from src.utils.config import Config
from src.utils.rules import get_rules_text, has_rules
from src.utils.token_counter import count_conversation_tokens, display_token_usage, estimate_cost

# Load base system prompt at module level
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, 'system_prompt.txt'), 'r', encoding='utf-8') as f:
    base_system_prompt = f.read().strip()

ContextWindowLimit = 200000

def get_system_prompt() -> str:
    """Get system prompt with dynamically loaded rules."""
    if has_rules():
        return base_system_prompt + "\n\n" + get_rules_text()
    return base_system_prompt

class ContextWindowExceededError(Exception):
    """Raised when message exceeds the context window limit."""
    def __init__(self, char_count: int):
        self.char_count = char_count
        super().__init__(f"Exceeded context window limit: {ContextWindowLimit:,}, got {char_count:,}")

def call_anthropic(message: str, api_key: Optional[str] = None, config: Optional[Config] = None) -> tuple[str, list]:
    try:
        # Use config's context limit if available, otherwise use default
        context_limit = config.max_context_length if config else ContextWindowLimit
        
        # Check message length and warn if exceeds context window
        char_count = len(message)
        if char_count > context_limit:
            raise ContextWindowExceededError(char_count)
        
        # Get API key from parameter or environment
        key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not key:
            error_msg = "Error: No Anthropic API key provided. Set ANTHROPIC_API_KEY environment variable."
            return error_msg, [{"role": "error", "content": error_msg}]
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=key)
        
        # Use config's model if available, otherwise use default
        model_name = config.model if config else "claude-3-5-sonnet-20241022"
        
        # Get system prompt with current rules
        system_prompt = get_system_prompt()
        
        # Count input tokens before API call
        input_messages = [{"role": "user", "content": message}]
        input_tokens = count_conversation_tokens(input_messages, system_prompt)
        
        # Show input tokens only in debug mode
        if config and config.debug_mode:
            print(f"📥 Input tokens: {input_tokens:,}")
        
        # Make the API call with system message and tools
        response = client.messages.create(
            model=model_name,
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
            
            # Count output tokens
            output_tokens = count_conversation_tokens(messages, system_prompt) - input_tokens
            total_tokens = input_tokens + output_tokens
            
            # Print token usage
            debug_mode = config.debug_mode if config else False
            display_token_usage(input_tokens, output_tokens, total_tokens, debug_mode)
            
            # Show cost estimate only in debug mode
            if debug_mode:
                estimated_cost = estimate_cost(total_tokens, model_name)
                if estimated_cost > 0:
                    print(f"💰 Estimated cost: ${estimated_cost:.4f}")
            
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
                tool_result = execute_tool(tool_use.name, tool_use.input, config)
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
                model=model_name,
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
            
            # Count final output tokens
            output_tokens = count_conversation_tokens(messages, system_prompt) - input_tokens
            total_tokens = input_tokens + output_tokens
            
            display_token_usage(input_tokens, output_tokens, total_tokens, model_name, config.debug_mode if config else False)
            
            # Extract final message text for display
            final_message = ""
            for content_block in current_response.content:
                if content_block.type == "text":
                    final_message += content_block.text
            return final_message, messages
        
        error_msg = "No response received"
        return error_msg, [{"role": "error", "content": error_msg}]
        
    except ContextWindowExceededError as e:
        raise e
    except Exception as e:
        error_msg = f"Error calling Anthropic API: {str(e)}"
        return error_msg, [{"role": "error", "content": error_msg}]
