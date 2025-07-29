from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from typing import Optional

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    hashed_password: str,
    country: Optional[str] = None,
    city: Optional[str] = None
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        country=country,
        city=city
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user