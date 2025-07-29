from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.models.game import Game, GameStatus
from app.models.team import Team
from app.models.team_member import TeamMember
from sqlalchemy.orm import selectinload
from sqlalchemy import and_

async def create_game(
    db: AsyncSession,
    subject: str,
    status: GameStatus = GameStatus.WAITING
) -> Game:
    game = Game(
        subject=subject,
        status=status,
        start_time=datetime.utcnow()
    )
    db.add(game)
    await db.flush()
    return game

async def create_team(
    db: AsyncSession,
    game_id: int,
    name: str
) -> Team:
    team = Team(
        game_id=game_id,
        name=name
    )
    db.add(team)
    await db.flush()
    return team

async def create_team_member(
    db: AsyncSession,
    team_id: int,
    user_id: int
) -> TeamMember:
    team_member = TeamMember(
        team_id=team_id,
        user_id=user_id
    )
    db.add(team_member)
    return team_member

async def get_game_with_teams(
    db: AsyncSession,
    game_id: int
) -> Optional[Game]:
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.teams)
            .selectinload(Team.members)
        )
    )
    return result.scalar_one_or_none()

async def get_user_active_game(
    db: AsyncSession,
    user_id: int
) -> Optional[Game]:
    result = await db.execute(
        select(Game)
        .join(Team, Game.id == Team.game_id)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .where(
            and_(
                TeamMember.user_id == user_id,
                Game.status.in_([GameStatus.WAITING, GameStatus.IN_PROGRESS])
            )
        )
    )
    return result.scalar_one_or_none()
