from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.queries import auth as auth_queries
from app.schemas.user import UserCreate, UserResponse
from app.utils.auth import get_password_hash, verify_password, create_access_token
from app.config.config import Config

config = Config()

async def register_user(
    db: AsyncSession,
    user_data: UserCreate
) -> UserResponse:
    
    existing_user = await auth_queries.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    existing_email = await auth_queries.get_user_by_email(db, user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    user = await auth_queries.create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        country=user_data.country,
        city=user_data.city
    )
    
    return user

async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str
) -> Tuple[str, UserResponse]:
    
    user = await auth_queries.get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=int(config.ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return access_token, user

async def get_current_user(
    db: AsyncSession,
    username: str
) -> UserResponse:
    
    user = await auth_queries.get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user