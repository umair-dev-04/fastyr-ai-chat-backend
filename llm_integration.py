import os
import json
from typing import Dict, Any, List, Optional
import openai
from dotenv import load_dotenv

from tools import chatbot_tools

load_dotenv()

class LLMIntegration:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"  # Using GPT-4o for better performance
        self.max_tokens = 1000
        self.temperature = 0.7
        
        self.system_prompt = """You are a helpful AI assistant with access to various tools. You can:
- Perform calculations using the calculate tool
- Search the web for current information using web_search
- Get current time using get_current_time
- Get weather information using weather_search

When a user asks a question that requires using tools, use the appropriate tool and then provide a helpful response based on the tool's output. Always be helpful and informative in your responses."""

    async def process_message(
        self, 
        message: str, 
        conversation_history: List[Dict[str, Any]] = None,
        context: Dict[str, Any] = None,
        tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and return AI response with proper tool handling
        """
        try:
            # Prepare messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Add context if available
            if context:
                context_message = f"User context: {json.dumps(context)}"
                messages.append({"role": "system", "content": context_message})
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            # Prepare API call parameters
            params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            # Add tools if provided
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            
            # Make initial API call
            response = self.client.chat.completions.create(**params)
            assistant_message = response.choices[0].message
            tokens_used = response.usage.total_tokens if response.usage else None
            
            # Handle tool calls if any
            tool_calls = None
            if assistant_message.tool_calls:
                tool_calls = []
                for tool_call in assistant_message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
                
                # Execute tools and continue conversation
                messages.append(assistant_message)
                
                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    # Execute the tool
                    tool_result = await chatbot_tools.execute_tool(tool_name, arguments)
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                
                # Make another API call to get final response
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                final_assistant_message = final_response.choices[0].message
                final_tokens_used = final_response.usage.total_tokens if final_response.usage else None
                
                return {
                    "message": final_assistant_message.content or "",
                    "tokens_used": final_tokens_used,
                    "tool_calls": tool_calls,
                    "context": context
                }
            
            return {
                "message": assistant_message.content or "",
                "tokens_used": tokens_used,
                "tool_calls": tool_calls,
                "context": context
            }
            
        except Exception as e:
            return {
                "message": f"I apologize, but I encountered an error: {str(e)}",
                "tokens_used": None,
                "tool_calls": None,
                "context": context
            }
    
    def generate_response(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, Any]] = None,
        user_context: Dict[str, Any] = None,
        tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using OpenAI GPT-4 (legacy method)
        """
        try:
            # Prepare messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Add user context if available
            if user_context:
                context_message = f"User context: {json.dumps(user_context)}"
                messages.append({"role": "system", "content": context_message})
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Prepare API call parameters
            params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            # Add tools if provided
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            
            # Make API call
            response = self.client.chat.completions.create(**params)
            
            # Extract response
            assistant_message = response.choices[0].message
            tokens_used = response.usage.total_tokens if response.usage else None
            
            # Handle tool calls if any
            tool_calls = None
            if assistant_message.tool_calls:
                tool_calls = []
                for tool_call in assistant_message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
            
            return {
                "content": assistant_message.content,
                "tokens_used": tokens_used,
                "tool_calls": tool_calls
            }
            
        except Exception as e:
            return {
                "content": f"I apologize, but I encountered an error: {str(e)}",
                "tokens_used": None,
                "tool_calls": None
            }
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": text}],
                max_tokens=1
            )
            return response.usage.prompt_tokens if response.usage else 0
        except:
            # Fallback: rough estimation (1 token ≈ 4 characters)
            return len(text) // 4

# Initialize global LLM instance
llm_integration = LLMIntegration() 