"""
Professional Authentication Service for CAT Preparation App v2.0
Updated for PostgreSQL integration
"""

import os
import jwt
import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

# Import database models
from database import User as DBUser

# Hard-coded admin email
ADMIN_EMAIL = "sumedhprabhu18@gmail.com"
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secure-jwt-secret-key-2025')
JWT_ALGORITHM = 'HS256'

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

class User(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_admin: bool = False
    created_at: datetime
    tz: str = "Asia/Kolkata"

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User
    expires_in: int = 86400  # 24 hours

class AuthService:
    def __init__(self):
        pass
        
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT token"""
        payload = {
            'user_id': user_data['id'],
            'email': user_data['email'],
            'is_admin': user_data['is_admin'],
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
            'iss': 'cat-prep-app'
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def register_user_v2(self, user_data: UserCreate, db: AsyncSession) -> TokenResponse:
        """Register a new user (PostgreSQL version)"""
        # Check if user exists
        result = await db.execute(select(DBUser).where(DBUser.email == user_data.email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Determine if user should be admin
        is_admin = user_data.email == ADMIN_EMAIL
        
        # Create user
        db_user = DBUser(
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=self.hash_password(user_data.password),
            is_admin=is_admin,
            created_at=datetime.utcnow()
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        # Create response user object
        user = User(
            id=str(db_user.id),
            email=db_user.email,
            full_name=db_user.full_name,
            is_admin=db_user.is_admin,
            created_at=db_user.created_at,
            tz=db_user.tz
        )
        
        # Generate token
        token = self.generate_token({
            "id": str(db_user.id),
            "email": db_user.email,
            "is_admin": db_user.is_admin
        })
        
        logger.info(f"New user registered: {user_data.email} (Admin: {is_admin})")
        
        return TokenResponse(
            access_token=token,
            user=user
        )
    
    async def login_user_v2(self, login_data: UserLogin, db: AsyncSession) -> TokenResponse:
        """Authenticate user and return token (PostgreSQL version)"""
        # Find user
        result = await db.execute(select(DBUser).where(DBUser.email == login_data.email))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not self.verify_password(login_data.password, db_user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create user object
        user = User(
            id=str(db_user.id),
            email=db_user.email,
            full_name=db_user.full_name,
            is_admin=db_user.is_admin,
            created_at=db_user.created_at,
            tz=db_user.tz
        )
        
        # Generate token
        token = self.generate_token({
            "id": str(db_user.id),
            "email": db_user.email,
            "is_admin": db_user.is_admin
        })
        
        logger.info(f"User login: {login_data.email} (Admin: {db_user.is_admin})")
        
        return TokenResponse(
            access_token=token,
            user=user
        )
    
    async def get_current_user_v2(self, token: str, db: AsyncSession) -> User:
        """Get current user from token (PostgreSQL version)"""
        payload = self.verify_token(token)
        
        result = await db.execute(select(DBUser).where(DBUser.id == payload["user_id"]))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(
            id=str(db_user.id),
            email=db_user.email,
            full_name=db_user.full_name,
            is_admin=db_user.is_admin,
            created_at=db_user.created_at,
            tz=db_user.tz
        )

# Dependency functions for FastAPI
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get current authenticated user"""
    if not credentials:
        return None
    
    from database import get_database
    
    auth_service = AuthService()
    async for db in get_database():
        try:
            return await auth_service.get_current_user_v2(credentials.credentials, db)
        except HTTPException:
            return None

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Require authenticated user"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    from database import get_database
    
    auth_service = AuthService()
    async for db in get_database():
        return await auth_service.get_current_user_v2(credentials.credentials, db)

async def require_admin(
    current_user: User = Depends(require_auth)
) -> User:
    """Require admin user"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user