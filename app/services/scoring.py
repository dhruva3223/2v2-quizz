import json
import math
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from app.queries import scoring as scoring_queries

async def submit_answer(
    db: AsyncSession,
    redis_client: redis.Redis,
    game_id: int,
    user_id: int,
    question_id: int,
    user_answer: str,
    response_time: float
) -> Dict[str, Any]:
    
    game_data = await redis_client.get(f"game:{game_id}")
    if not game_data:
        raise ValueError("Game not found or not active")
    
    game_info = json.loads(game_data)
    
    if game_info["status"] != "in_progress":
        raise ValueError("Game is not in progress")
    
    question_data = None
    for q in game_info["questions"]:
        if q["id"] == question_id:
            question_data = q
            break
    
    if not question_data:
        raise ValueError("Question not found in current game")
    
    is_correct = user_answer.lower().strip() == question_data["correct_answer"].lower().strip()
    
    points_earned = calculate_points(
        is_correct=is_correct,
        base_points=question_data["points"],
        response_time=response_time,
        max_time=10
    )
    
    game_session = await scoring_queries.get_game_session(db, game_id, user_id)
    
    if not game_session:
        raise ValueError("Game session not found")
    
    await scoring_queries.create_answer(
        db, game_session.id, question_id, user_answer, 
        is_correct, response_time, points_earned
    )
    
    await scoring_queries.update_game_session_stats(
        db, game_session, points_earned, response_time, is_correct
    )
    
    await update_real_time_scores(redis_client, game_id, user_id, points_earned)
    
    answer_key = f"game:{game_id}:question:{question_id}:user:{user_id}:answered"
    await redis_client.set(answer_key, "1", ex=3600)
    
    from app.services.game import check_and_advance_question
    await check_and_advance_question(db, redis_client, game_id)
    
    return {
        "is_correct": is_correct,
        "points_earned": points_earned,
        "total_score": game_session.total_score,
        "correct_answers": game_session.correct_answers,
        "total_answers": game_session.total_answers
    }

def calculate_points(
    is_correct: bool,
    base_points: int,
    response_time: float,
    max_time: float
) -> float:
    
    if not is_correct:
        return 0.0
    
    k = math.log(2) / max_time
    time_multiplier = math.exp(-k * response_time)
    
    time_multiplier = max(0.5, time_multiplier)
    
    return base_points * time_multiplier

async def update_real_time_scores(
    redis_client: redis.Redis,
    game_id: int,
    user_id: int,
    points_earned: float
) -> None:
    
    user_score_key = f"game:{game_id}:user:{user_id}:score"
    await redis_client.incrbyfloat(user_score_key, points_earned)
    await redis_client.expire(user_score_key, 3600)
    
    game_data = await redis_client.get(f"game:{game_id}")
    if game_data:
        game_info = json.loads(game_data)
        
        user_team_id = None
        for team in game_info.get("teams", []):
            if user_id in team["players"]:
                user_team_id = team["team_id"]
                break
        
        if user_team_id:
            team_score_key = f"game:{game_id}:team:{user_team_id}:score"
            await redis_client.incrbyfloat(team_score_key, points_earned)
            await redis_client.expire(team_score_key, 3600)

async def get_real_time_scores(
    redis_client: redis.Redis,
    game_id: int
) -> Dict[str, Any]:
    
    game_data = await redis_client.get(f"game:{game_id}")
    if not game_data:
        return {}
    
    game_info = json.loads(game_data)
    
    team_scores = {}
    user_scores = {}
    
    for team in game_info.get("teams", []):
        team_id = team["team_id"]
        team_score_key = f"game:{game_id}:team:{team_id}:score"
        team_score = await redis_client.get(team_score_key)
        team_scores[team_id] = float(team_score) if team_score else 0.0
        
        team_user_scores = {}
        for user_id in team["players"]:
            user_score_key = f"game:{game_id}:user:{user_id}:score"
            user_score = await redis_client.get(user_score_key)
            user_scores[user_id] = float(user_score) if user_score else 0.0
            team_user_scores[user_id] = user_scores[user_id]
        
        team_scores[team_id] = {
            "total_score": team_scores[team_id],
            "user_scores": team_user_scores
        }
    
    return {
        "game_id": game_id,
        "team_scores": team_scores,
        "user_scores": user_scores
    }

async def get_user_game_stats(
    db: AsyncSession,
    user_id: int,
    game_id: int
) -> Optional[Dict[str, Any]]:
    
    game_session = await scoring_queries.get_game_session_with_answers(
        db, user_id, game_id
    )
    
    if not game_session:
        return None
    
    return {
        "game_id": game_id,
        "user_id": user_id,
        "total_score": game_session.total_score,
        "correct_answers": game_session.correct_answers,
        "total_answers": game_session.total_answers,
        "accuracy": (game_session.correct_answers / game_session.total_answers) if game_session.total_answers > 0 else 0,
        "average_response_time": game_session.average_response_time,
        "answers": [
            {
                "question_id": answer.question_id,
                "user_answer": answer.user_answer,
                "is_correct": answer.is_correct,
                "points_earned": answer.points_earned,
                "response_time": answer.response_time
            } for answer in game_session.answers
        ]
    } 