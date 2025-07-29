from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from app.database import get_db, get_redis
from app.services.leaderboard import (
    get_global_leaderboard,
    get_location_leaderboard
)

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

@router.get("/global", response_model=dict)
async def get_global_leaderboard_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    try:
        leaderboard_data = await get_global_leaderboard(
            db, redis_client, page, page_size
        )
        
        return {
            "success": True,
            **leaderboard_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get global leaderboard: {str(e)}"
        )

@router.get("/location/{country}", response_model=dict)
async def get_location_leaderboard_endpoint(
    country: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    try:
        leaderboard_data = await get_location_leaderboard(
            db, redis_client, country, page, page_size
        )
        
        return {
            "success": True,
            **leaderboard_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get location leaderboard: {str(e)}"
        ) 