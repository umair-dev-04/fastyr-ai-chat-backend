import uuid
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models import ChatSession, ChatMessage, ConversationContext
from llm_integration import llm_integration
from tools import chatbot_tools

class ChatbotOrchestrator:
    def __init__(self):
        self.max_context_length = 4000  # Maximum tokens for context
        self.session_timeout = timedelta(hours=24)  # Session timeout
    
    def create_session(self, db: Session, user_id: int, title: str = None) -> ChatSession:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        
        # Generate title if not provided
        if not title:
            title = f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        session = ChatSession(
            user_id=user_id,
            session_id=session_id,
            title=title,
            is_active=True
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
    
    def get_session(self, db: Session, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by session_id"""
        return db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.is_active == True
        ).first()
    
    def get_user_sessions(self, db: Session, user_id: int) -> List[ChatSession]:
        """Get all sessions for a user"""
        return db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True
        ).order_by(ChatSession.updated_at.desc()).all()
    
    def save_message(self, db: Session, session_id: int, role: str, content: str, 
                    tokens_used: int = None, tool_calls: Dict[str, Any] = None) -> ChatMessage:
        """Save a message to the database"""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            tool_calls=tool_calls
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        return message
    
    def get_conversation_history(self, db: Session, session_id: int, 
                               limit: int = 20) -> List[ChatMessage]:
        """Get conversation history for a session - returns actual ChatMessage objects"""
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.asc()).limit(limit).all()
        
        return messages
    
    def get_conversation_history_for_llm(self, db: Session, session_id: int, 
                                       limit: int = 20) -> List[Dict[str, Any]]:
        """Get conversation history in format expected by LLM"""
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
        
        # Convert to format expected by LLM
        history = []
        for msg in reversed(messages):  # Reverse to get chronological order
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return history
    
    def get_context(self, db: Session, session_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation context for a session"""
        context = db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id
        ).first()
        
        if context and context.context_data:
            return context.context_data
        return None
    
    def save_context(self, db: Session, session_id: str, context_data: Dict[str, Any]):
        """Save conversation context"""
        context = db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id
        ).first()
        
        if context:
            context.context_data = context_data
            context.updated_at = datetime.utcnow()
        else:
            context = ConversationContext(
                session_id=session_id,
                context_data=context_data
            )
            db.add(context)
        
        db.commit()
        db.refresh(context)
        return context
    
    def update_context(self, db: Session, session_id: str, 
                      user_name: str = None, preferences: Dict[str, Any] = None):
        """Update conversation context with user information"""
        context_data = {}
        
        if user_name:
            context_data["user_name"] = user_name
        
        if preferences:
            context_data["preferences"] = preferences
        
        if context_data:
            self.save_context(db, session_id, context_data)
    
    async def process_message(self, db: Session, user_id: int, message: str, 
                            session_id: str = None) -> Dict[str, Any]:
        """Process a user message and return AI response"""
        try:
            # Get or create session
            session = None
            if session_id:
                session = self.get_session(db, session_id)
                if not session or session.user_id != user_id:
                    session = None
            
            if not session:
                session = self.create_session(db, user_id)
                session_id = session.session_id
            
            # Save user message
            user_message = self.save_message(db, session.id, "user", message)
            
            # Get conversation history for LLM
            history = self.get_conversation_history_for_llm(db, session.id)
            
            # Get context
            context = self.get_context(db, session_id)
            
            # Process with LLM
            response = await llm_integration.process_message(
                message=message,
                conversation_history=history,
                context=context,
                tools=chatbot_tools.get_tools()
            )
            
            # Save assistant message
            assistant_message = self.save_message(
                db, 
                session.id, 
                "assistant", 
                response["message"],
                tokens_used=response.get("tokens_used"),
                tool_calls=response.get("tool_calls")
            )
            
            # Update session
            session.updated_at = datetime.utcnow()
            db.commit()
            
            return {
                "message": response["message"],
                "session_id": session_id,
                "tokens_used": response.get("tokens_used"),
                "tool_calls": response.get("tool_calls"),
                "context": response.get("context"),
                "user_message_created_at": user_message.created_at,
                "assistant_message_created_at": assistant_message.created_at
            }
            
        except Exception as e:
            # Log error and return fallback response
            print(f"Error processing message: {str(e)}")
            return {
                "message": "I apologize, but I'm experiencing technical difficulties. Please try again later.",
                "session_id": session_id or "error",
                "error": str(e)
            }
    
    def cleanup_expired_sessions(self, db: Session):
        """Clean up expired sessions"""
        cutoff_time = datetime.utcnow() - self.session_timeout
        expired_sessions = db.query(ChatSession).filter(
            ChatSession.updated_at < cutoff_time,
            ChatSession.is_active == True
        ).all()
        
        for session in expired_sessions:
            session.is_active = False
        
        db.commit()

# Initialize global orchestrator
chatbot_orchestrator = ChatbotOrchestrator() 