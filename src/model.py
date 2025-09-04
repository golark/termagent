import os
import sys
from typing import Optional
import anthropic
from tools import TOOLS, execute_tool

# Load system prompt at module level
with open('system_prompt.txt', 'r', encoding='utf-8') as f:
    system_prompt = f.read().strip()

def call_anthropic(message: str, api_key: Optional[str] = None) -> str:
    try:
        # Get API key from parameter or environment
        key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not key:
            return "Error: No Anthropic API key provided. Set ANTHROPIC_API_KEY environment variable."
        
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
        
        print(f'response: {response}')

        # Handle tool calls in a loop until stop_reason is end_turn
        messages = [{"role": "user", "content": message}]
        current_response = response
        
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
        
        # Return the final text response
        if current_response.content:
            final_text = ""
            for content_block in current_response.content:
                if content_block.type == "text":
                    final_text += content_block.text
            return final_text if final_text else "No text response received"
        
        return "No response received"
        
    except Exception as e:
        return f"Error calling Anthropic API: {str(e)}"
