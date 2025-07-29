from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.queries import questions as question_queries
from app.schemas.question import QuestionCreate, QuestionResponse
from app.models.question import Question

async def create_question(
    db: AsyncSession,
    question_data: QuestionCreate
) -> Question:
    try:
        return await question_queries.create_question(
            db=db,
            subject=question_data.subject,
            question_text=question_data.question_text,
            options=question_data.options,
            correct_answer=question_data.correct_answer,
            difficulty=question_data.difficulty,
            points=question_data.points
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create question: {str(e)}"
        )

async def get_questions(
    db: AsyncSession,
    subject: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Question]:
    try:
        return await question_queries.get_questions_with_filters(
            db=db,
            subject=subject,
            difficulty=difficulty,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get questions: {str(e)}"
        )

async def get_question_by_id(db: AsyncSession, question_id: int) -> Question:
    try:
        question = await question_queries.get_question_by_id(db, question_id)
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        return question
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get question: {str(e)}"
        )

async def update_question(
    db: AsyncSession,
    question_id: int,
    question_data: QuestionCreate
) -> Question:
    try:
        question = await question_queries.get_question_by_id(db, question_id)
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        return await question_queries.update_question(
            db=db,
            question=question,
            subject=question_data.subject,
            question_text=question_data.question_text,
            options=question_data.options,
            correct_answer=question_data.correct_answer,
            difficulty=question_data.difficulty,
            points=question_data.points
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update question: {str(e)}"
        )

async def delete_question(db: AsyncSession, question_id: int) -> dict:
    try:
        question = await question_queries.get_question_by_id(db, question_id)
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        await question_queries.delete_question(db, question)
        
        return {
            "success": True,
            "message": "Question deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete question: {str(e)}"
        )

async def get_available_subjects(db: AsyncSession) -> List[str]:
    try:
        return await question_queries.get_distinct_subjects(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subjects: {str(e)}"
        )

async def get_question_statistics(db: AsyncSession) -> dict:
    try:
        return await question_queries.get_question_stats(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get question stats: {str(e)}"
        ) 