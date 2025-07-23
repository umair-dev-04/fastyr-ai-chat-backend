from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import UploadFile

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class AvatarUploadResponse(BaseModel):
    avatar_url: str
    message: str

class GoogleOAuthRequest(BaseModel):
    code: str
    redirect_uri: str

class GoogleUserInfo(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    verified_email: bool

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_provider: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_provider: str


class TokenWithUser(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


# Tool call schemas
class ToolCallFunction(BaseModel):
    name: str
    arguments: str

class ToolCall(BaseModel):
    id: str
    type: str
    function: ToolCallFunction

# Chatbot schemas
class ChatMessageBase(BaseModel):
    content: str
    role: str = "user"  # "user", "assistant", "system"

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessage(ChatMessageBase):
    id: int
    session_id: int
    tokens_used: Optional[int] = None
    tool_calls: Optional[List[ToolCall]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    title: Optional[str] = None

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSession(ChatSessionBase):
    id: int
    user_id: int
    session_id: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[ChatMessage] = []

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    message: str
    session_id: str
    tokens_used: Optional[int] = None
    tool_calls: Optional[List[ToolCall]] = None
    context: Optional[Dict[str, Any]] = None
    user_message_created_at: Optional[datetime] = None
    assistant_message_created_at: Optional[datetime] = None

class ConversationContext(BaseModel):
    session_id: str
    context_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 