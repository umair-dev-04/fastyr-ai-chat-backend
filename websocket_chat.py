import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import User, ChatSession, ChatMessage
from auth import get_current_active_user_ws
from chatbot_orchestrator import chatbot_orchestrator
from security import security_manager

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    session_id: Optional[str] = None
):
    """
    WebSocket endpoint for real-time chat
    """
    try:
        # Get database session
        db = next(get_db())
        
        # Authenticate user
        user = get_current_active_user_ws(token, db)
        if not user:
            await websocket.close(code=4001, reason="Authentication failed")
            return
        
        # Connect to WebSocket
        await manager.connect(websocket, str(user.id))
        
        # Create or get chat session
        if session_id:
            chat_session = chatbot_orchestrator.get_session(db, session_id)
            if not chat_session or chat_session.user_id != user.id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid session"
                }))
                await websocket.close()
                return
        else:
            chat_session = chatbot_orchestrator.create_session(db, user.id)
            session_id = chat_session.session_id
        
        manager.user_sessions[str(user.id)] = session_id
        
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "session_created",
            "session_id": session_id,
            "message": "Connected to AI Chatbot. You can start chatting!"
        }))
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                if message_data.get("type") == "message":
                    user_message = message_data.get("content", "")
                    
                    # Security checks
                    if not security_manager.validate_message(user_message):
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Invalid message content"
                        }))
                        continue
                    
                    # Sanitize input
                    sanitized_message = security_manager.sanitize_input(user_message)
                    
                    # Send typing indicator
                    await websocket.send_text(json.dumps({
                        "type": "typing",
                        "message": "AI is thinking..."
                    }))
                    
                    # Process message
                    response = await chatbot_orchestrator.process_message(
                        db=db,
                        user_id=user.id,
                        message=sanitized_message,
                        session_id=session_id
                    )
                    
                    # Send response
                    await websocket.send_text(json.dumps({
                        "type": "message",
                        "role": "assistant",
                        "content": response["message"],
                        "session_id": session_id,
                        "tokens_used": response.get("tokens_used"),
                        "timestamp": datetime.now().isoformat()
                    }))
                
                elif message_data.get("type") == "typing":
                    # User is typing indicator
                    await websocket.send_text(json.dumps({
                        "type": "user_typing",
                        "user_id": str(user.id)
                    }))
                
                elif message_data.get("type") == "ping":
                    # Keep connection alive
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                }))
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Connection error: {str(e)}"
            }))
        except:
            pass
    finally:
        # Clean up connection
        if hasattr(websocket, 'user_id'):
            manager.disconnect(websocket.user_id) 