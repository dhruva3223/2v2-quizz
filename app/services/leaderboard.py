from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import json

from app.queries import leaderboard as leaderboard_queries

async def get_global_leaderboard(
    db: AsyncSession,
    redis_client: redis.Redis,
    page: int = 1,
    page_size: int = 50
) -> Dict[str, Any]:
    cache_key = f"leaderboard:global:page:{page}:size:{page_size}"
    
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    offset = (page - 1) * page_size
    users, total_entries = await leaderboard_queries.get_global_leaderboard_entries(
        db, offset, page_size
    )
    
    leaderboard_data = {
        "leaderboard": [
            {
                "rank": offset + i + 1,
                "username": user.username,
                "total_score": user.total_score,
                "total_games": user.total_games,
                "win_rate": (user.total_wins / user.total_games) if user.total_games > 0 else 0,
                "country": user.country
            } for i, user in enumerate(users)
        ],
        "total_entries": total_entries,
        "page": page,
        "page_size": page_size
    }
    
    await redis_client.setex(cache_key, 120, json.dumps(leaderboard_data))
    return leaderboard_data

async def get_location_leaderboard(
    db: AsyncSession,
    redis_client: redis.Redis,
    country: str,
    page: int = 1,
    page_size: int = 50
) -> Dict[str, Any]:
    cache_key = f"leaderboard:country:{country}:page:{page}:size:{page_size}"
    
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    offset = (page - 1) * page_size
    users, total_entries = await leaderboard_queries.get_location_leaderboard_entries(
        db, country, offset, page_size
    )
    
    leaderboard_data = {
        "leaderboard": [
            {
                "rank": offset + i + 1,
                "username": user.username,
                "total_score": user.total_score,
                "total_games": user.total_games,
                "win_rate": (user.total_wins / user.total_games) if user.total_games > 0 else 0,
                "country": country
            } for i, user in enumerate(users)
        ],
        "country": country,
        "total_entries": total_entries,
        "page": page,
        "page_size": page_size
    }
    
    await redis_client.setex(cache_key, 120, json.dumps(leaderboard_data))
    return leaderboard_data 