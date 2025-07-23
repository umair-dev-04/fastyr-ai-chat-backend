from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User, Token
import os

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "your-refresh-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        if email is None or token_type != "access":
            return None
        return email
    except JWTError:
        return None

def verify_refresh_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        if email is None or token_type != "refresh":
            return None
        return email
    except JWTError:
        return None

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    email = verify_token(token)
    if email is None:
        raise credentials_exception
    
    # Check if token is revoked
    db_token = db.query(Token).filter(Token.token == token, Token.is_revoked == True).first()
    if db_token:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_active_user_ws(token: str, db: Session) -> Optional[User]:
    """
    Authenticate user for WebSocket connection
    """
    try:
        email = verify_token(token)
        if email is None:
            return None
        
        # Check if token is revoked
        db_token = db.query(Token).filter(Token.token == token, Token.is_revoked == True).first()
        if db_token:
            return None
        
        user = db.query(User).filter(User.email == email).first()
        if user is None or not user.is_active:
            return None
        
        return user
    except Exception:
        return None

def save_token_to_db(db: Session, user_id: int, access_token: str, refresh_token: str):
    # Save access token
    access_db_token = Token(user_id=user_id, token=access_token, token_type="access")
    db.add(access_db_token)
    
    # Save refresh token
    refresh_db_token = Token(user_id=user_id, token=refresh_token, token_type="refresh")
    db.add(refresh_db_token)
    
    db.commit()
    return {"access_token": access_db_token, "refresh_token": refresh_db_token}

def revoke_token(db: Session, token: str):
    db_token = db.query(Token).filter(Token.token == token).first()
    if db_token:
        db_token.is_revoked = True
        db.commit()
    return db_token

def revoke_user_tokens(db: Session, user_id: int):
    """Revoke all tokens for a user (useful for logout)"""
    tokens = db.query(Token).filter(Token.user_id == user_id, Token.is_revoked == False).all()
    for token in tokens:
        token.is_revoked = True
    db.commit()
    return tokens 