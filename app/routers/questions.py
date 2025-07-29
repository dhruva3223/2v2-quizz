from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user, get_current_admin_user
from app.schemas.question import QuestionCreate, QuestionResponse
from app.services import questions as question_service

router = APIRouter(prefix="/questions", tags=["questions"])

@router.post("/create-question", response_model=QuestionResponse)
async def create_question(
    question_data: QuestionCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    return await question_service.create_question(db, question_data)

@router.get("/get-questions", response_model=List[QuestionResponse])
async def get_questions(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    limit: int = Query(50, ge=1, le=100, description="Number of questions to return"),
    offset: int = Query(0, ge=0, description="Number of questions to skip"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    return await question_service.get_questions(db, subject, difficulty, limit, offset)

@router.get("/subjects/available")
async def get_available_subjects(
    db: AsyncSession = Depends(get_db)
):
    subjects = await question_service.get_available_subjects(db)
    return {"subjects": subjects}

@router.get("/stats/count")
async def get_question_stats(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    return await question_service.get_question_statistics(db)

@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: int,
    question_data: QuestionCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    return await question_service.update_question(db, question_id, question_data)

@router.delete("/{question_id}")
async def delete_question(
    question_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    return await question_service.delete_question(db, question_id) 