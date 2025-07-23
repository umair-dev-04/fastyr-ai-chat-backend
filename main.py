from fastapi import FastAPI, Depends, HTTPException, status, Request, WebSocket, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import os
from typing import List, Optional, Dict, Any

from database import get_db, engine
from models import Base, User, Token, ChatSession, ChatMessage, ConversationContext
from schemas import (
    UserCreate, UserLogin, UserUpdate, Token as TokenSchema, TokenRefresh, UserResponse,
    GoogleOAuthRequest, AvatarUploadResponse,
    ChatRequest, ChatResponse, ChatSession as ChatSessionSchema, ChatMessage as ChatMessageSchema, TokenWithUser
)
from auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    create_refresh_token,
    verify_refresh_token,
    get_current_active_user,
    save_token_to_db,
    revoke_token,
    revoke_user_tokens,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from oauth import get_google_oauth_url, handle_google_oauth
from chatbot_orchestrator import chatbot_orchestrator
from security import security_manager
from websocket_chat import websocket_endpoint
from file_upload import file_upload_manager

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Chatbot API",
    description="A complete AI chatbot system with authentication, LLM integration, and tools",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

security = HTTPBearer()

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Chatbot API"}

# Authentication endpoints
@app.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if full_name already exists
    db_user = db.query(User).filter(User.full_name == user.full_name).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        auth_provider="email"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        full_name=db_user.full_name,
        is_active=db_user.is_active,
        created_at=db_user.created_at,
        google_id=db_user.google_id,
        avatar_url=db_user.avatar_url,
        auth_provider=db_user.auth_provider
    )

@app.post("/login", response_model=TokenWithUser)
def login(
    user_credentials: UserLogin, 
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Login user and return access token, refresh token, and user information
    """
    # Find user by email
    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user has password (OAuth users might not have passwords)
    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account was created with Google OAuth. Please use Google login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"sub": user.email}, expires_delta=refresh_token_expires
    )
    
    # Save tokens to database
    save_token_to_db(db, user.id, access_token, refresh_token)
    
    # Generate dynamic avatar URL for response
    avatar_url = user.avatar_url
    if avatar_url and avatar_url.startswith('/uploads/'):
        avatar_url = file_upload_manager.get_avatar_url(user.avatar_url, request)
    
    return TokenWithUser(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            google_id=user.google_id,
            avatar_url=avatar_url,
            auth_provider=user.auth_provider
        )
    )

@app.post("/refresh", response_model=TokenSchema)
def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    email = verify_refresh_token(token_data.refresh_token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if refresh token is revoked
    db_token = db.query(Token).filter(
        Token.token == token_data.refresh_token,
        Token.token_type == "refresh",
        Token.is_revoked == True
    ).first()
    if db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Create new refresh token
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = create_refresh_token(
        data={"sub": user.email}, expires_delta=refresh_token_expires
    )
    
    # Revoke old refresh token
    revoke_token(db, token_data.refresh_token)
    
    # Save new tokens to database
    save_token_to_db(db, user.id, new_access_token, new_refresh_token)
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@app.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout user by revoking all tokens
    """
    token = credentials.credentials
    user = get_current_active_user(credentials, db)
    
    # Revoke all tokens for the user
    revoked_tokens = revoke_user_tokens(db, user.id)
    
    if revoked_tokens:
        return {"message": "Successfully logged out"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tokens found to revoke"
        )

@app.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """
    Get current user information
    """
    # Generate dynamic avatar URL
    avatar_url = None
    if current_user.avatar_url:
        avatar_url = file_upload_manager.get_avatar_url(current_user.avatar_url, request)
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        google_id=current_user.google_id,
        avatar_url=avatar_url,
        auth_provider=current_user.auth_provider
    )

@app.patch("/me", response_model=UserResponse)
def update_user_info(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Update current user information (full_name and avatar_url)
    """
    # Check if full_name is being updated and if it's already taken
    if user_update.full_name and user_update.full_name != current_user.full_name:
        existing_user = db.query(User).filter(
            User.full_name == user_update.full_name,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Full name already taken"
            )
    
    # Update user fields
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    
    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url
    
    # Update the updated_at timestamp
    current_user.updated_at = datetime.utcnow()
    
    # Save changes to database
    db.commit()
    db.refresh(current_user)
    
    # Generate dynamic avatar URL for response
    avatar_url = None
    if current_user.avatar_url:
        avatar_url = file_upload_manager.get_avatar_url(current_user.avatar_url, request)
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        google_id=current_user.google_id,
        avatar_url=avatar_url,
        auth_provider=current_user.auth_provider
    )

@app.post("/upload/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Upload avatar image for current user
    """
    try:
        # Save the uploaded file and get relative path
        relative_path = await file_upload_manager.save_avatar(file, current_user.id)
        
        # Delete old avatar if exists
        if current_user.avatar_url and current_user.avatar_url.startswith('/uploads/'):
            file_upload_manager.delete_avatar(current_user.avatar_url)
        
        # Store only the relative path in database
        current_user.avatar_url = relative_path
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        # Generate dynamic URL for response
        avatar_url = file_upload_manager.get_avatar_url(relative_path, request)
        
        return AvatarUploadResponse(
            avatar_url=avatar_url,
            message="Avatar uploaded successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}"
        )

# Chatbot endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    client_request: Request = None
):
    """
    Send a message to the AI chatbot
    """
    # Security checks
    client_ip = client_request.client.host if client_request else None
    
    # Check if IP is blocked
    if client_ip and security_manager.is_ip_blocked(client_ip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied due to suspicious activity"
        )
    
    # Validate message
    if not security_manager.validate_message(request.message):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message content or length"
        )
    
    # Check rate limit
    if not security_manager.check_rate_limit(current_user.id, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    # Detect suspicious activity
    if security_manager.detect_suspicious_activity(request.message, current_user.id, client_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Suspicious activity detected"
        )
    
    # Record request
    security_manager.record_request(current_user.id, client_ip)
    
    # Sanitize input
    sanitized_message = security_manager.sanitize_input(request.message)
    sanitized_context = security_manager.sanitize_context(request.context or {})
    
    # Validate session ID if provided
    if request.session_id and not security_manager.validate_session(request.session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    # Process message
    try:
        response = await chatbot_orchestrator.process_message(
            db=db,
            user_id=current_user.id,
            message=sanitized_message,
            session_id=request.session_id
        )
        
        return ChatResponse(
            message=response["message"],
            session_id=response["session_id"],
            tokens_used=response.get("tokens_used"),
            tool_calls=response.get("tool_calls"),
            context=response.get("context"),
            user_message_created_at=response.get("user_message_created_at"),
            assistant_message_created_at=response.get("assistant_message_created_at")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )

@app.get("/chat/sessions", response_model=List[ChatSessionSchema])
def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all chat sessions for the current user
    """
    sessions = chatbot_orchestrator.get_user_sessions(db, current_user.id)
    return sessions

@app.get("/chat/sessions/{session_id}", response_model=ChatSessionSchema)
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific chat session
    """
    if not security_manager.validate_session(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    session = chatbot_orchestrator.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return session

@app.get("/chat/sessions/{session_id}/messages", response_model=List[ChatMessageSchema])
def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages for a specific chat session
    """
    if not security_manager.validate_session(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    session = chatbot_orchestrator.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    messages = chatbot_orchestrator.get_conversation_history(db, session.id)
    return messages

@app.post("/chat/sessions", response_model=ChatSessionSchema)
def create_chat_session(
    session_data: dict = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new chat session
    """
    title = session_data.get("title") if session_data else None
    session = chatbot_orchestrator.create_session(db, current_user.id, title)
    return session

@app.delete("/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a chat session
    """
    if not security_manager.validate_session(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    session = chatbot_orchestrator.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    session.is_active = False
    db.commit()
    
    return {"message": "Session deleted successfully"}

@app.get("/admin/security/stats")
def get_security_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get security statistics (admin only)
    """
    # In a real application, you'd check if user is admin
    # For now, we'll allow any authenticated user
    stats = security_manager.get_security_stats()
    return stats

# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = None,
    session_id: str = None
):
    """
    WebSocket endpoint for real-time chat with the AI chatbot
    """
    await websocket_endpoint(websocket, token, session_id)

# OAuth endpoints
@app.get("/auth/google")
def google_oauth_start():
    """
    Start Google OAuth flow
    """
    auth_url = get_google_oauth_url()
    return {"url":auth_url}

@app.post("/auth/google/callback")
async def google_oauth_callback(
    request: GoogleOAuthRequest, 
    db: Session = Depends(get_db),
    client_request: Request = None
):
    """
    Handle Google OAuth callback (POST)
    """
    try:
        result = await handle_google_oauth(request.code, request.redirect_uri, db, client_request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {str(e)}"
        )

@app.get("/auth/google/callback")
async def google_oauth_callback_get(
    code: str, 
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Handle Google OAuth callback (GET)
    """
    try:
        # For GET requests, we'll use a default redirect URI
        # In production, you should handle this properly
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
        result = await handle_google_oauth(code, redirect_uri, db, request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

