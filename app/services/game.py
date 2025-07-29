import json
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from datetime import datetime, timedelta
from sqlalchemy import select

from app.queries import game as game_queries
from app.models.game import GameStatus
from app.config.config import Config
from app.models.user import User

config = Config()

async def start_game(
    db: AsyncSession,
    redis_client: redis.Redis,
    game_id: int
) -> Dict[str, Any]:
    
    game = await game_queries.get_game_with_teams(db, game_id)
    
    if not game:
        raise ValueError("Game not found")
    
    if game.status != GameStatus.WAITING:
        raise ValueError("Game cannot be started")
    
    questions = await game_queries.get_random_unused_questions_by_subject(
        db, game.subject, 5
    )
    if len(questions) < 5:
        raise ValueError(f"Not enough questions for subject {game.subject}")
    
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(seconds=int(config.GAME_DURATION))
    
    await game_queries.update_game_status(
        db, game, GameStatus.IN_PROGRESS, start_time, end_time
    )
    
    all_players = []
    for team in game.teams:
        for member in team.members:
            all_players.append(member.user_id)
            await game_queries.create_game_session(db, game.id, member.user_id)
    
    await db.commit()
    
    game_data = {
        "game_id": game.id,
        "status": "in_progress",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "current_question": 0,
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "options": q.options,
                "correct_answer": q.correct_answer,
                "points": q.points
            } for q in questions
        ],
        "players": all_players,
        "teams": [
            {
                "team_id": team.id,
                "players": [member.user_id for member in team.members]
            } for team in game.teams
        ]
    }
    
    await redis_client.set(f"game:{game_id}", json.dumps(game_data), ex=3600)
    
    return {
        "game_id": game.id,
        "status": "started",
        "start_time": start_time,
        "end_time": end_time,
        "total_questions": len(questions),
        "players": all_players
    }

async def get_current_question(
    redis_client: redis.Redis,
    game_id: int
) -> Optional[Dict[str, Any]]:
    
    try:
        game_data = await redis_client.get(f"game:{game_id}")
        if not game_data:
            return {
                "success": False,
                "message": "Game not found or expired"
            }
        
        try:
            game_info = json.loads(game_data)
        except json.JSONDecodeError:
            return {
                "success": False,
                "message": "Invalid game data format"
            }
        
        if game_info.get("status") != "in_progress":
            return {
                "success": False,
                "message": f"Game is not in progress (status: {game_info.get('status')})"
            }
        
        current_question_idx = game_info.get("current_question", 0)
        questions = game_info.get("questions", [])
        
        if not questions:
            return {
                "success": False,
                "message": "No questions found for this game"
            }
        
        if current_question_idx >= len(questions):
            return {
                "success": False,
                "message": "All questions completed"
            }
        
        question = questions[current_question_idx]
        if not isinstance(question, dict):
            return {
                "success": False,
                "message": "Invalid question format"
            }
        
        used_question_ids = game_info.get("used_question_ids", [])
        if question["id"] not in used_question_ids:
            used_question_ids.append(question["id"])
            game_info["used_question_ids"] = used_question_ids
            await redis_client.set(f"game:{game_id}", json.dumps(game_info), ex=3600)
        
        return {
            "success": True,
            "question": {
                "id": question.get("id"),
                "question_text": question.get("question_text"),
                "options": question.get("options", []),
                "points": question.get("points", 10),
                "question_number": current_question_idx + 1,
                "total_questions": len(questions)
            }
        }
        
    except redis.RedisError as e:
        return {
            "success": False,
            "message": f"Redis error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}"
        }

async def check_and_advance_question(
    db: AsyncSession,
    redis_client: redis.Redis,
    game_id: int
) -> Optional[bool]:
    
    game_data = await redis_client.get(f"game:{game_id}")
    if not game_data:
        return None
    
    game_info = json.loads(game_data)
    current_question_idx = game_info["current_question"]
    current_question = game_info["questions"][current_question_idx]
    all_players = game_info["players"]
    
    answered_count = 0
    for player_id in all_players:
        answer_key = f"game:{game_id}:question:{current_question['id']}:user:{player_id}:answered"
        if await redis_client.get(answer_key):
            answered_count += 1
    
    if answered_count >= len(all_players):
        if current_question_idx >= 4:
            await end_game(db, redis_client, game_id)
            return False
        else:
            game_info["current_question"] += 1
            await redis_client.set(f"game:{game_id}", json.dumps(game_info), ex=3600)
            return True
    
    return None

async def end_game(
    db: AsyncSession,
    redis_client: redis.Redis,
    game_id: int
) -> Dict[str, Any]:
    
    game = await game_queries.get_game_with_teams_and_sessions(db, game_id)
    
    if not game:
        raise ValueError("Game not found")
    
    await game_queries.update_game_status(
        db, game, GameStatus.FINISHED, end_time=datetime.utcnow()
    )
    
    team_scores = {}
    for team in game.teams:
        team_total = 0
        for member in team.members:
            session = next(
                (gs for gs in game.game_sessions if gs.user_id == member.user_id),
                None
            )
            if session:
                team_total += session.total_score
                user_result = await db.execute(select(User).where(User.id == member.user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    user.total_games += 1
                    user.total_score += session.total_score
        
        team.total_score = team_total
        team_scores[team.id] = team_total
    
    winner_team_id = None
    if team_scores:
        winner_team_id = max(team_scores.items(), key=lambda x: x[1])[0]
        for team in game.teams:
            is_winner = (team.id == winner_team_id)
            team.is_winner = is_winner
            if is_winner:
                for member in team.members:
                    user_result = await db.execute(select(User).where(User.id == member.user_id))
                    user = user_result.scalar_one_or_none()
                    if user:
                        user.total_wins += 1
    
    await db.commit()
    
    await redis_client.delete(f"game:{game_id}")
    
    return {
        "game_id": game.id,
        "status": "finished",
        "teams": [
            {
                "team_id": team.id,
                "name": team.name,
                "total_score": team_scores.get(team.id, 0),
                "is_winner": team.id == winner_team_id,
                "members": [member.user_id for member in team.members]
            } for team in game.teams
        ],
        "team_scores": team_scores,
        "winner_team_id": winner_team_id
    }

async def get_game_state(
    db: AsyncSession,
    redis_client: redis.Redis,
    game_id: int
) -> Optional[Dict[str, Any]]:
    
    game_data = await redis_client.get(f"game:{game_id}")
    if game_data:
        game_info = json.loads(game_data)
        return {
            "game_id": game_info["game_id"],
            "status": game_info["status"],
            "start_time": game_info.get("start_time"),
            "end_time": game_info.get("end_time"),
            "current_question": game_info.get("current_question", 0),
            "total_questions": len(game_info.get("questions", [])),
            "players": game_info.get("players", []),
            "teams": game_info.get("teams", [])
        }
    
    game = await game_queries.get_game_with_teams_and_sessions(db, game_id)
    
    if not game:
        return None
    
    team_scores = {}
    for team in game.teams:
        team_total = sum(
            session.total_score 
            for session in game.game_sessions 
            if any(member.user_id == session.user_id for member in team.members)
        )
        team_scores[team.id] = team_total
    
    winner_team_id = max(team_scores.items(), key=lambda x: x[1])[0] if team_scores else None
    
    return {
        "game_id": game.id,
        "status": game.status.value,
        "start_time": game.start_time.isoformat() if game.start_time else None,
        "end_time": game.end_time.isoformat() if game.end_time else None,
        "teams": [
            {
                "team_id": team.id,
                "name": team.name,
                "total_score": team_scores.get(team.id, 0),
                "is_winner": team.id == winner_team_id,
                "members": [member.user_id for member in team.members]
            } for team in game.teams
        ],
        "team_scores": team_scores,
        "winner_team_id": winner_team_id
    } 