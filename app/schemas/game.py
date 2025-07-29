from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.game import GameStatus

class GameCreate(BaseModel):
    subject: str

class TeamResponse(BaseModel):
    id: int
    name: str
    total_score: float
    is_winner: bool
    
    class Config:
        from_attributes = True

class GameResponse(BaseModel):
    id: int
    subject: str
    status: GameStatus
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    teams: List[TeamResponse] = []
    
    class Config:
        from_attributes = True

class MatchmakingRequest(BaseModel):
    subject: str

class MatchmakingResponse(BaseModel):
    game_id: int
    team_id: int
    teammate_username: Optional[str]
    status: str
    estimated_wait_time: Optional[int]

class GameSessionResponse(BaseModel):
    id: int
    game_id: int
    user_id: int
    total_score: float
    correct_answers: int
    total_answers: int
    average_response_time: float
    
    class Config:
        from_attributes = True 