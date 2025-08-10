"""
Professional Authentication Service for CAT Preparation App
Integrates with Firebase and provides secure token-based authentication
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
import logging

# Hard-coded admin email
ADMIN_EMAIL = "sumedhprabhu18@gmail.com"
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secure-jwt-secret-key-2025')
JWT_ALGORITHM = 'HS256'

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    is_admin: bool = False
    created_at: datetime
    email_verified: bool = False
    last_login: Optional[datetime] = None
    profile_image: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    name: str
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
    def __init__(self, db):
        self.db = db
        
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
    
    async def register_user(self, user_data: UserCreate) -> TokenResponse:
        """Register a new user"""
        # Check if user exists
        existing_user = await self.db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Determine if user should be admin
        is_admin = user_data.email == ADMIN_EMAIL
        
        # Create user document
        user_doc = {
            "id": str(uuid.uuid4()),
            "email": user_data.email,
            "name": user_data.name,
            "password_hash": self.hash_password(user_data.password),
            "is_admin": is_admin,
            "created_at": datetime.utcnow(),
            "email_verified": is_admin,  # Auto-verify admin
            "last_login": None,
            "profile_image": None
        }
        
        # Insert into database
        await self.db.users.insert_one(user_doc)
        
        # Create user object for response
        user = User(
            id=user_doc["id"],
            email=user_doc["email"],
            name=user_doc["name"],
            is_admin=user_doc["is_admin"],
            created_at=user_doc["created_at"],
            email_verified=user_doc["email_verified"]
        )
        
        # Generate token
        token = self.generate_token(user_doc)
        
        logger.info(f"New user registered: {user_data.email} (Admin: {is_admin})")
        
        return TokenResponse(
            access_token=token,
            user=user
        )
    
    async def login_user(self, login_data: UserLogin) -> TokenResponse:
        """Authenticate user and return token"""
        # Find user
        user_doc = await self.db.users.find_one({"email": login_data.email})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not self.verify_password(login_data.password, user_doc["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Update last login
        await self.db.users.update_one(
            {"email": login_data.email},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        user_doc["last_login"] = datetime.utcnow()
        
        # Create user object
        user = User(
            id=user_doc["id"],
            email=user_doc["email"],
            name=user_doc["name"],
            is_admin=user_doc["is_admin"],
            created_at=user_doc["created_at"],
            email_verified=user_doc.get("email_verified", False),
            last_login=user_doc["last_login"],
            profile_image=user_doc.get("profile_image")
        )
        
        # Generate token
        token = self.generate_token(user_doc)
        
        logger.info(f"User login: {login_data.email} (Admin: {user_doc['is_admin']})")
        
        return TokenResponse(
            access_token=token,
            user=user
        )
    
    async def get_current_user(self, token: str) -> User:
        """Get current user from token"""
        payload = self.verify_token(token)
        
        user_doc = await self.db.users.find_one({"id": payload["user_id"]})
        if not user_doc:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(
            id=user_doc["id"],
            email=user_doc["email"],
            name=user_doc["name"],
            is_admin=user_doc["is_admin"],
            created_at=user_doc["created_at"],
            email_verified=user_doc.get("email_verified", False),
            last_login=user_doc.get("last_login"),
            profile_image=user_doc.get("profile_image")
        )
    
    async def reset_password_request(self, email: EmailStr) -> Dict[str, str]:
        """Request password reset (simplified version)"""
        user_doc = await self.db.users.find_one({"email": email})
        if not user_doc:
            # Don't reveal if email exists or not for security
            return {"message": "If the email exists, a password reset link has been sent"}
        
        # In a real app, you would send an email with reset token
        # For now, we'll just log it for the admin
        reset_token = str(uuid.uuid4())
        
        await self.db.password_resets.insert_one({
            "user_id": user_doc["id"],
            "reset_token": reset_token,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "used": False
        })
        
        if email == ADMIN_EMAIL:
            logger.warning(f"Password reset requested for admin: {email}")
            logger.warning(f"Reset token: {reset_token}")
        
        return {"message": "If the email exists, a password reset link has been sent"}

# Dependency functions
async def get_auth_service(db) -> AuthService:
    """Get auth service instance"""
    return AuthService(db)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db = None
) -> Optional[User]:
    """Get current authenticated user"""
    if not credentials:
        return None
    
    auth_service = AuthService(db)
    try:
        return await auth_service.get_current_user(credentials.credentials)
    except HTTPException:
        return None

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = None
) -> User:
    """Require authenticated user"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    auth_service = AuthService(db)
    return await auth_service.get_current_user(credentials.credentials)

async def require_admin(
    current_user: User = Depends(require_auth)
) -> User:
    """Require admin user"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user