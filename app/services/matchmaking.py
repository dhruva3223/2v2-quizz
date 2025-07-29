import json
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from datetime import datetime

from app.queries import matchmaking as matchmaking_queries
from app.config.config import Config

config = Config()

async def join_matchmaking_queue(
    db: AsyncSession,
    redis_client: redis.Redis,
    user_id: int,
    subject: str
) -> Dict[str, Any]:
    
    existing = await redis_client.get(f"user_queue:{user_id}")
    if existing:
        return {"status": "already_in_queue", "subject": json.loads(existing)["subject"]}
    
    queue_key = f"matchmaking_queue:{subject}"
    user_data = {
        "user_id": user_id,
        "joined_at": datetime.utcnow().isoformat(),
        "subject": subject
    }
    
    await redis_client.lpush(queue_key, json.dumps(user_data))
    await redis_client.set(
        f"user_queue:{user_id}",
        json.dumps(user_data),
        ex=int(config.MATCHMAKING_TIMEOUT)
    )
    
    team_result = await try_form_team(db, redis_client, subject)
    if team_result:
        return team_result
    
    queue_length = await redis_client.llen(queue_key)
    estimated_wait = min(queue_length * 2, int(config.MATCHMAKING_TIMEOUT))
    
    return {
        "status": "waiting",
        "estimated_wait_time": estimated_wait,
        "queue_position": queue_length
    }

async def try_form_team(
    db: AsyncSession,
    redis_client: redis.Redis,
    subject: str
) -> Optional[Dict[str, Any]]:
    
    queue_key = f"matchmaking_queue:{subject}"
    
    players_data = []
    for _ in range(int(config.MAX_TEAM_SIZE)):
        player_json = await redis_client.rpop(queue_key)
        if not player_json:
            for pd in players_data:
                await redis_client.rpush(queue_key, json.dumps(pd))
            return None
        players_data.append(json.loads(player_json))
    
    for player_data in players_data:
        await redis_client.delete(f"user_queue:{player_data['user_id']}")
    
    teams_waiting_key = f"teams_waiting:{subject}"
    opposing_team_data = await redis_client.rpop(teams_waiting_key)
    
    if opposing_team_data:
        opposing_team = json.loads(opposing_team_data)
        game_result = await create_game_with_teams(db, redis_client, subject,
            players_data, opposing_team["players"]
        )
        return game_result
    else:
        team_data = {
            "players": players_data,
            "created_at": datetime.utcnow().isoformat()
        }
        await redis_client.lpush(teams_waiting_key, json.dumps(team_data))
        
        return {
            "status": "team_formed_waiting_opponent",
            "team_players": [p["user_id"] for p in players_data]
        }

async def create_game_with_teams(
    db: AsyncSession,
    redis_client: redis.Redis,
    subject: str,
    team1_players: List[Dict],
    team2_players: List[Dict]
) -> Dict[str, Any]:
    
    game = await matchmaking_queries.create_game(db, subject)
    
    teams = []
    all_players = [team1_players, team2_players]
    
    for i, team_players in enumerate(all_players):
        team = await matchmaking_queries.create_team(
            db,
            game.id,
            f"Team {i + 1}"
        )
        
        for player_data in team_players:
            await matchmaking_queries.create_team_member(
                db,
                team.id,
                player_data["user_id"]
            )
        
        teams.append(team)
    
    await db.commit()
    
    from app.services.game import start_game
    try:
        await start_game(db, redis_client, game.id)
        game_status = "started"
    except Exception as e:
        game_status = "waiting"
    
    return {
        "status": "matched",
        "game_id": game.id,
        "game_status": game_status,
        "team_id": teams[0].id if team1_players[0]["user_id"] else teams[1].id,
        "all_players": [p["user_id"] for p in team1_players + team2_players]
    }

async def leave_matchmaking_queue(
    redis_client: redis.Redis,
    user_id: int
) -> bool:
    
    user_data = await redis_client.get(f"user_queue:{user_id}")
    if not user_data:
        return False
    
    user_info = json.loads(user_data)
    subject = user_info["subject"]
    queue_key = f"matchmaking_queue:{subject}"
    
    queue_items = await redis_client.lrange(queue_key, 0, -1)
    await redis_client.delete(queue_key)
    
    for item in queue_items:
        item_data = json.loads(item)
        if item_data["user_id"] != user_id:
            await redis_client.lpush(queue_key, item)
    
    await redis_client.delete(f"user_queue:{user_id}")
    return True