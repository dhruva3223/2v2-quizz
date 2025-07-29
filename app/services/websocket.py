import json
import asyncio
from typing import Dict, List, Optional
from fastapi import WebSocket
import redis.asyncio as redis
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
        self.user_games: Dict[int, int] = {}
    
    async def connect(self, websocket: WebSocket, game_id: int, user_id: int):
        await websocket.accept()
        
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}
        
        self.active_connections[game_id][user_id] = websocket
        self.user_games[user_id] = game_id
        
        await self.broadcast_to_game(
            game_id,
            {
                "type": "player_connected",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            exclude_user=user_id
        )
    
    def disconnect(self, user_id: int):
        if user_id in self.user_games:
            game_id = self.user_games[user_id]
            
            if game_id in self.active_connections and user_id in self.active_connections[game_id]:
                del self.active_connections[game_id][user_id]
                
                if not self.active_connections[game_id]:
                    del self.active_connections[game_id]
            
            del self.user_games[user_id]
            
            asyncio.create_task(self.broadcast_to_game(
                game_id,
                {
                    "type": "player_disconnected",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_user=user_id
            ))
    
    async def broadcast_to_game(self, game_id: int, message: dict, exclude_user: Optional[int] = None):
        if game_id in self.active_connections:
            disconnected_users = []
            
            for user_id, websocket in self.active_connections[game_id].items():
                if exclude_user and user_id == exclude_user:
                    continue
                
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected_users.append(user_id)
            
            for user_id in disconnected_users:
                self.disconnect(user_id)
    
    async def broadcast_to_team(self, game_id: int, team_members: List[int], message: dict):
        if game_id in self.active_connections:
            for user_id in team_members:
                if user_id in self.active_connections[game_id]:
                    try:
                        websocket = self.active_connections[game_id][user_id]
                        await websocket.send_text(json.dumps(message))
                    except:
                        self.disconnect(user_id)
    
manager = ConnectionManager()

async def handle_websocket_message(
    websocket: WebSocket,
    redis_client: redis.Redis,
    user_id: int,
    game_id: int,
    message: dict
):
    
    message_type = message.get("type")
    
    if message_type == "ping":
        await websocket.send_text(json.dumps({"type": "pong"}))
    
    elif message_type == "team_chat":
        game_data = await redis_client.get(f"game:{game_id}")
        if game_data:
            game_info = json.loads(game_data)
            
            user_team_members = []
            for team in game_info.get("teams", []):
                if user_id in team["players"]:
                    user_team_members = team["players"]
                    break
            
            chat_message = {
                "type": "team_chat",
                "from_user_id": user_id,
                "message": message.get("message", ""),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await manager.broadcast_to_team(game_id, user_team_members, chat_message)
    
    elif message_type == "game_action":
        action = message.get("action")
        
        if action == "request_current_question":
            from app.services.game import get_current_question
            question = await get_current_question(redis_client, game_id)
            
            if question:
                await websocket.send_text(json.dumps({
                    "type": "current_question",
                    "question": question
                }))
        
        elif action == "request_scores":
            from app.services.scoring import get_real_time_scores
            scores = await get_real_time_scores(redis_client, game_id)
            
            await websocket.send_text(json.dumps({
                "type": "score_update",
                "scores": scores
            }))

async def broadcast_score_update(
    redis_client: redis.Redis,
    game_id: int,
    user_id: int,
    score_data: dict
):
    
    message = {
        "type": "score_update",
        "user_id": user_id,
        "score_data": score_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_to_game(game_id, message)

async def broadcast_game_end(
    redis_client: redis.Redis,
    game_id: int,
    final_results: dict
):
    
    message = {
        "type": "game_ended",
        "results": final_results,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_to_game(game_id, message)

async def notify_team_mate_answer(
    redis_client: redis.Redis,
    game_id: int,
    user_id: int,
    answer_data: dict
):
    
    game_data = await redis_client.get(f"game:{game_id}")
    if not game_data:
        return
    
    game_info = json.loads(game_data)
    
    team_members = []
    for team in game_info.get("teams", []):
        if user_id in team["players"]:
            team_members = [uid for uid in team["players"] if uid != user_id]
            break
    
    if team_members:
        message = {
            "type": "teammate_answered",
            "user_id": user_id,
            "answer_data": answer_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await manager.broadcast_to_team(game_id, team_members, message)
