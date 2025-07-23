import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv

load_dotenv()

class LLMIntegration:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.max_tokens = 4000
        self.temperature = 0.7
        
        # Initialize LangChain chat model
        self.langchain_model = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # System prompt for the chatbot
        self.system_prompt = """You are a helpful AI assistant. You can help users with various tasks including:
        - Answering questions
        - Providing information
        - Helping with calculations
        - Writing and editing text
        - Analyzing data
        - And much more!
        
        Always be helpful, accurate, and friendly. If you're not sure about something, say so rather than guessing.
        Remember the user's name and preferences from the conversation context."""
    
    async def process_message(
        self, 
        message: str, 
        conversation_history: List[Dict[str, Any]] = None,
        context: Dict[str, Any] = None,
        tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and return AI response
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
    
    def generate_response_with_langchain(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate response using LangChain (alternative method)
        """
        try:
            # Convert conversation history to LangChain format
            messages = []
            
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))
            
            # Add current user message
            messages.append(HumanMessage(content=user_message))
            
            # Generate response
            response = self.langchain_model.invoke(messages)
            
            return response.content
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"
    
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