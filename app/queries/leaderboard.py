from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.models.user import User

async def get_global_leaderboard_entries(
    db: AsyncSession,
    offset: int,
    limit: int
) -> Tuple[List[User], int]:
    result = await db.execute(
        select(User)
        .where(User.total_games > 0)
        .order_by(desc(User.total_score))
        .offset(offset)
        .limit(limit)
    )
    users = result.scalars().all()
    
    count_result = await db.execute(
        select(func.count(User.id))
        .where(User.total_games > 0)
    )
    total_entries = count_result.scalar()
    
    return users, total_entries

async def get_location_leaderboard_entries(
    db: AsyncSession,
    country: str,
    offset: int,
    limit: int
) -> Tuple[List[User], int]:
    result = await db.execute(
        select(User)
        .where(and_(User.country == country, User.total_games > 0))
        .order_by(desc(User.total_score))
        .offset(offset)
        .limit(limit)
    )
    users = result.scalars().all()
    
    count_result = await db.execute(
        select(func.count(User.id))
        .where(and_(User.country == country, User.total_games > 0))
    )
    total_entries = count_result.scalar()
    
    return users, total_entries