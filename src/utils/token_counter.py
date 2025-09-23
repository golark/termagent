"""Token counting utilities for AI model calls."""

import json
from typing import List, Dict, Any, Tuple


def count_tokens_approximate(text: str) -> int:
    """Approximate token count for text (roughly 4 characters per token)."""
    return len(text) // 4


def count_message_tokens(message: Dict[str, Any]) -> int:
    """Count tokens in a single message."""
    if message.get("role") == "user" and isinstance(message.get("content"), str):
        return count_tokens_approximate(message["content"])
    elif message.get("role") == "assistant" and isinstance(message.get("content"), list):
        # Handle assistant content blocks
        total_tokens = 0
        for content_block in message["content"]:
            # Handle both dict and object types
            if hasattr(content_block, 'type') and content_block.type == "text":
                text = getattr(content_block, 'text', '')
                total_tokens += count_tokens_approximate(text)
            elif isinstance(content_block, dict) and content_block.get("type") == "text":
                total_tokens += count_tokens_approximate(content_block.get("text", ""))
        return total_tokens
    elif message.get("role") == "user" and isinstance(message.get("content"), list):
        # Handle tool results
        total_tokens = 0
        for item in message["content"]:
            if isinstance(item, dict) and item.get("type") == "tool_result":
                total_tokens += count_tokens_approximate(str(item.get("content", "")))
        return total_tokens
    else:
        # Fallback for other message types
        return count_tokens_approximate(str(message))


def count_conversation_tokens(messages: List[Dict[str, Any]], system_prompt: str = "") -> int:
    """Count total tokens in a conversation including system prompt."""
    total_tokens = 0
    
    # Add system prompt tokens
    if system_prompt:
        total_tokens += count_tokens_approximate(system_prompt)
    
    # Add message tokens
    for message in messages:
        total_tokens += count_message_tokens(message)
    
    return total_tokens


def format_token_count(tokens: int) -> str:
    """Format token count with commas for readability."""
    return f"{tokens:,}"


def display_token_usage(input_tokens: int, output_tokens: int, total_tokens: int, model_name: str, debug_mode: bool = False) -> None:
    """Print token usage information."""
    if not debug_mode:
        return

    print(f"\n📊 Token Usage:")
    print(f"  Input:  {format_token_count(input_tokens)} tokens")
    print(f"  Output: {format_token_count(output_tokens)} tokens")
    print(f"  Total:  {format_token_count(total_tokens)} tokens")
    print()

    estimated_cost = estimate_cost(total_tokens, model_name)
    if estimated_cost > 0:
        print(f"💰 Estimated cost: ${estimated_cost:.4f}")
            

def estimate_cost(tokens: int, model: str = "claude-3-5-sonnet-20241022") -> float:
    """Estimate cost based on token count and model."""
    # Pricing per 1M tokens (as of 2024)
    pricing = {
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    }
    
    if model not in pricing:
        return 0.0
    
    # Assume 50/50 input/output split for estimation
    input_cost = (tokens * 0.5) / 1_000_000 * pricing[model]["input"]
    output_cost = (tokens * 0.5) / 1_000_000 * pricing[model]["output"]
    
    return input_cost + output_cost
