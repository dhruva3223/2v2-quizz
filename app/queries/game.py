from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime
from app.models.game import Game, GameStatus
from app.models.game_session import GameSession
from app.models.team import Team
from app.models.question import Question

async def get_game_with_teams_and_sessions(
    db: AsyncSession,
    game_id: int
) -> Optional[Game]:
    result = await db.execute(
        select(Game).options(
            selectinload(Game.teams).selectinload(Team.members),
            selectinload(Game.game_sessions)
        ).where(Game.id == game_id)
    )
    return result.scalar_one_or_none()

async def get_game_with_teams(
    db: AsyncSession,
    game_id: int
) -> Optional[Game]:
    result = await db.execute(
        select(Game).options(
            selectinload(Game.teams).selectinload(Team.members)
        ).where(Game.id == game_id)
    )
    return result.scalar_one_or_none()

async def update_game_status(
    db: AsyncSession,
    game: Game,
    status: GameStatus,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> None:
    game.status = status
    if start_time:
        game.start_time = start_time
    if end_time:
        game.end_time = end_time
    await db.commit()

async def create_game_session(
    db: AsyncSession,
    game_id: int,
    user_id: int
) -> GameSession:
    game_session = GameSession(
        game_id=game_id,
        user_id=user_id
    )
    db.add(game_session)
    return game_session

async def get_random_unused_questions_by_subject(
    db: AsyncSession,
    subject: str,
    count: int,
    exclude_ids: List[int] = None
) -> List[Question]:
    query = select(Question).where(Question.subject == subject)
    
    if exclude_ids:
        query = query.where(~Question.id.in_(exclude_ids))
    
    query = query.order_by(func.random()).limit(count)
    
    result = await db.execute(query)
    return result.scalars().all()