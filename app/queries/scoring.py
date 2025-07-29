from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.game_session import GameSession
from app.models.answer import Answer

async def get_game_session(
    db: AsyncSession,
    game_id: int,
    user_id: int
) -> Optional[GameSession]:
    result = await db.execute(
        select(GameSession).where(
            and_(
                GameSession.game_id == game_id,
                GameSession.user_id == user_id
            )
        )
    )
    return result.scalar_one_or_none()

async def create_answer(
    db: AsyncSession,
    game_session_id: int,
    question_id: int,
    user_answer: str,
    is_correct: bool,
    response_time: float,
    points_earned: float
) -> Answer:
    answer = Answer(
        game_session_id=game_session_id,
        question_id=question_id,
        user_answer=user_answer,
        is_correct=is_correct,
        response_time=response_time,
        points_earned=points_earned
    )
    db.add(answer)
    return answer

async def update_game_session_stats(
    db: AsyncSession,
    game_session: GameSession,
    points_earned: float,
    response_time: float,
    is_correct: bool
) -> None:
    game_session.total_score += points_earned
    game_session.total_answers += 1
    
    if is_correct:
        game_session.correct_answers += 1
    
    total_time = game_session.average_response_time * (game_session.total_answers - 1)
    game_session.average_response_time = (total_time + response_time) / game_session.total_answers
    
    await db.commit()

async def get_game_session_with_answers(
    db: AsyncSession,
    user_id: int,
    game_id: int
) -> Optional[GameSession]:
    result = await db.execute(
        select(GameSession).options(
            selectinload(GameSession.answers)
        ).where(
            and_(
                GameSession.user_id == user_id,
                GameSession.game_id == game_id
            )
        )
    )
    return result.scalar_one_or_none()