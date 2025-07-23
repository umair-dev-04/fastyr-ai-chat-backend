import os
from urllib.request import Request

import httpx
from typing import Optional
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, Token
from auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

# Google OAuth URLs
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_google_oauth_url():
    """Generate Google OAuth URL"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{GOOGLE_AUTH_URL}?{query_string}"

async def get_google_access_token(code: str, redirect_uri: str) -> Optional[str]:
    """Exchange authorization code for access token"""
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        response = await client.post(GOOGLE_TOKEN_URL, data=data)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get access token from Google"
            )
        
        token_data = response.json()
        return token_data.get("access_token")

async def get_google_user_info(access_token: str):
    """Get user information from Google"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        return response.json()

def get_or_create_google_user(db: Session, google_user_info: dict):
    """Get existing user or create new user from Google OAuth"""
    google_id = google_user_info["id"]
    email = google_user_info["email"]
    full_name = google_user_info["name"]
    avatar_url = google_user_info.get("picture")
    
    # Check if user exists by Google ID
    user = db.query(User).filter(User.google_id == google_id).first()
    if user:
        return user
    
    # Check if user exists by email
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Update existing user with Google info
        user.google_id = google_id
        user.auth_provider = "google"
        user.avatar_url = avatar_url
        db.commit()
        db.refresh(user)
        return user
    
    # Create new user
    user = User(
        email=email,
        full_name=full_name,
        google_id=google_id,
        avatar_url=avatar_url,
        auth_provider="google",
        hashed_password=None  # OAuth users don't have passwords
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def save_oauth_token_to_db(db: Session, user_id: int, access_token: str):
    """Save OAuth access token to database (no refresh token needed)"""
    access_db_token = Token(user_id=user_id, token=access_token, token_type="access")
    db.add(access_db_token)
    db.commit()
    return access_db_token

async def handle_google_oauth(code: str, redirect_uri: str, db: Session, request: Request = None):
    """Handle complete Google OAuth flow"""
    # Get access token
    access_token = await get_google_access_token(code, redirect_uri)
    
    # Get user info
    google_user_info = await get_google_user_info(access_token)
    
    # Get or create user
    user = get_or_create_google_user(db, google_user_info)
    
    # Create JWT token
    token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_token = create_access_token(
        data={"sub": user.email}, expires_delta=token_expires
    )
    
    # Save token to database (OAuth doesn't need refresh tokens)
    save_oauth_token_to_db(db, user.id, jwt_token)
    
    # Generate dynamic avatar URL for response (only for our own uploaded files)
    avatar_url = user.avatar_url
    if avatar_url and avatar_url.startswith('/uploads/'):
        # Import here to avoid circular imports
        from file_upload import file_upload_manager
        avatar_url = file_upload_manager.get_avatar_url(user.avatar_url, request)
    
    return {
        "access_token": jwt_token,
        "refresh_token": None,  # OAuth doesn't use refresh tokens
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "google_id": user.google_id,
            "avatar_url": avatar_url,
            "auth_provider": user.auth_provider
        }
    } 