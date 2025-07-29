from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import json
from app.database import get_db, get_redis
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.question import AnswerSubmission, AnswerResponse, QuestionResponse
from app.services.game import (
    start_game,
    get_current_question,
    end_game,
    get_game_state
)
from app.services.scoring import submit_answer, get_real_time_scores, get_user_game_stats
from app.services.websocket import (
    manager,
    handle_websocket_message,
    broadcast_score_update,
    notify_team_mate_answer
)

router = APIRouter(prefix="/game", tags=["game"])

@router.get("/{game_id}", response_model=dict)
async def get_game(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    
    try:
        game_state = await get_game_state(db, redis_client, game_id)
        
        if not game_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found"
            )
        
        return {
            "success": True,
            "game": game_state
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get game: {str(e)}"
        )

@router.get("/{game_id}/question", response_model=dict)
async def get_current_question_endpoint(
    game_id: int,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
):
    
    try:
        response = await get_current_question(redis_client, game_id)
        
        if not response.get("success"):
            if "not found" in response.get("message", "").lower() or "completed" in response.get("message", "").lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=response.get("message", "Question not available")
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response.get("message", "Failed to get question")
                )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current question: {str(e)}"
        )

@router.post("/{game_id}/answer", response_model=dict)
async def submit_answer_endpoint(
    game_id: int,
    answer_data: AnswerSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    
    try:
        result = await submit_answer(
            db=db,
            redis_client=redis_client,
            game_id=game_id,
            user_id=current_user.id,
            question_id=answer_data.question_id,
            user_answer=answer_data.user_answer,
            response_time=answer_data.response_time
        )
        
        await broadcast_score_update(redis_client, game_id, current_user.id, result)
        
        await notify_team_mate_answer(redis_client, game_id, current_user.id, result)
        
        return {
            "success": True,
            "message": "Answer submitted successfully",
            **result
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit answer: {str(e)}"
        )

@router.get("/{game_id}/stats", response_model=dict)
async def get_user_stats(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    try:
        stats = await get_user_game_stats(db, current_user.id, game_id)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game session not found"
            )
        
        return {
            "success": True,
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user stats: {str(e)}"
        )


@router.get("/{game_id}/results", response_model=dict)
async def get_game_results(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    
    try:
        game_state = await get_game_state(db, redis_client, game_id)
        
        if not game_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found"
            )
        
        if game_state["status"] == "finished":
            team_results = []
            for team in game_state["teams"]:
                team_result = {
                    "team_id": team["team_id"],
                    "name": team["name"],
                    "total_score": team["total_score"],
                    "is_winner": team["is_winner"],
                    "members": team["members"]
                }
                team_results.append(team_result)
            
            return {
                "success": True,
                "status": "finished",
                "results": {
                    "winner_team_id": game_state["winner_team_id"],
                    "teams": team_results,
                    "team_scores": game_state["team_scores"]
                }
            }
        
        current_question = game_state.get("current_question", 0)
        total_questions = 5
        
        return {
            "success": True,
            "status": "in_progress",
            "progress": {
                "current_question": current_question + 1,
                "total_questions": total_questions,
                "completion_percentage": ((current_question + 1) / total_questions) * 100
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get game results: {str(e)}"
        )

@router.websocket("/{game_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: int,
    token: str,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    
    try:
        # Verify token and get user
        from app.utils.auth import verify_token
        from sqlalchemy import select
        
        username = verify_token(token)
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        
        if not user:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        await manager.connect(websocket, game_id, user.id)
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_websocket_message(
                    websocket, redis_client, user.id, game_id, message
                )
                
        except WebSocketDisconnect:
            manager.disconnect(user.id)
            
    except Exception as e:
        try:
            await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except:
            pass 