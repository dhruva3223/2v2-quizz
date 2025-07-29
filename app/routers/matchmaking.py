from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.database import get_db, get_redis
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.game import MatchmakingRequest, MatchmakingResponse
from app.services.matchmaking import (
    join_matchmaking_queue,
    leave_matchmaking_queue
)

router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])

@router.post("/join", response_model=dict)
async def join_queue(
    request: MatchmakingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    
    try:
        result = await join_matchmaking_queue(
            db=db,
            redis_client=redis_client,
            user_id=current_user.id,
            subject=request.subject
        )
        
        return {
            "success": True,
            "message": "Successfully joined matchmaking queue",
            **result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to join queue: {str(e)}"
        )

@router.delete("/leave")
async def leave_queue(
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
):
    
    try:
        success = await leave_matchmaking_queue(redis_client, current_user.id)
        
        if success:
            return {
                "success": True,
                "message": "Successfully left matchmaking queue"
            }
        else:
            return {
                "success": False,
                "message": "User was not in queue"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to leave queue: {str(e)}"
        )

@router.get("/available-subjects")
async def get_available_subjects():
    subjects = [
        "Mathematics",
        "Science",
        "History", 
        "Geography",
        "Literature",
        "Sports",
        "Technology",
        "Art",
        "Music",
        "General Knowledge"
    ]
    
    return {
        "subjects": subjects
    } 