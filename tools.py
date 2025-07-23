import httpx
import json
import math
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

class ChatbotTools:
    def __init__(self):
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Perform mathematical calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "The mathematical expression to evaluate"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "Get the current date and time",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "weather_search",
                    "description": "Search for weather information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The location to get weather for"
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        ]
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools"""
        return self.tools
    
    async def web_search(self, query: str) -> str:
        """Search the web for information"""
        try:
            # Using DuckDuckGo Instant Answer API (free, no API key required)
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("Abstract"):
                        return f"Search results for '{query}':\n\n{data['Abstract']}\n\nSource: {data.get('AbstractURL', 'N/A')}"
                    elif data.get("Answer"):
                        return f"Answer for '{query}':\n\n{data['Answer']}"
                    else:
                        return f"I couldn't find specific information for '{query}'. You might want to try a different search term or check a specific website."
                else:
                    return f"Sorry, I couldn't perform the web search for '{query}' at the moment."
                    
        except Exception as e:
            return f"Error performing web search: {str(e)}"
    
    def calculate(self, expression: str) -> str:
        """Perform mathematical calculations safely"""
        try:
            # Remove any potentially dangerous characters
            safe_expression = re.sub(r'[^0-9+\-*/().\s]', '', expression)
            
            # Evaluate the expression
            result = eval(safe_expression)
            
            return f"Calculation: {expression} = {result}"
            
        except Exception as e:
            return f"Error calculating '{expression}': {str(e)}"
    
    def get_current_time(self) -> str:
        """Get current date and time"""
        now = datetime.now()
        return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    
    async def weather_search(self, location: str) -> str:
        """Search for weather information"""
        try:
            # Using OpenWeatherMap API (free tier available)
            api_key = "YOUR_OPENWEATHER_API_KEY"  # You'll need to get this from openweathermap.org
            
            if api_key == "YOUR_OPENWEATHER_API_KEY":
                return f"I can't get weather information for '{location}' right now. To enable weather searches, you'll need to get a free API key from openweathermap.org and update the code."
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": location,
                        "appid": api_key,
                        "units": "metric"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    temp = data["main"]["temp"]
                    description = data["weather"][0]["description"]
                    humidity = data["main"]["humidity"]
                    
                    return f"Weather in {location}:\nTemperature: {temp}°C\nCondition: {description}\nHumidity: {humidity}%"
                else:
                    return f"Sorry, I couldn't get weather information for '{location}'."
                    
        except Exception as e:
            return f"Error getting weather for '{location}': {str(e)}"
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a specific tool"""
        if tool_name == "web_search":
            return await self.web_search(arguments.get("query", ""))
        elif tool_name == "calculate":
            return self.calculate(arguments.get("expression", ""))
        elif tool_name == "get_current_time":
            return self.get_current_time()
        elif tool_name == "weather_search":
            return await self.weather_search(arguments.get("location", ""))
        else:
            return f"Unknown tool: {tool_name}"

# Initialize global tools instance
chatbot_tools = ChatbotTools() 