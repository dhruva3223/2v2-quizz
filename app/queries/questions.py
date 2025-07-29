from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.question import Question

async def create_question(
    db: AsyncSession,
    subject: str,
    question_text: str,
    options: List[str],
    correct_answer: str,
    difficulty: str = "medium",
    points: int = 10
) -> Question:
    question = Question(
        subject=subject,
        question_text=question_text,
        options=options,
        correct_answer=correct_answer,
        difficulty=difficulty,
        points=points
    )
    
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question

async def get_questions_with_filters(
    db: AsyncSession,
    subject: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Question]:
    query = select(Question)
    
    if subject:
        query = query.where(Question.subject == subject)
    
    if difficulty:
        query = query.where(Question.difficulty == difficulty)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

async def get_question_by_id(db: AsyncSession, question_id: int) -> Optional[Question]:
    result = await db.execute(select(Question).where(Question.id == question_id))
    return result.scalar_one_or_none()

async def update_question(
    db: AsyncSession,
    question: Question,
    subject: str,
    question_text: str,
    options: List[str],
    correct_answer: str,
    difficulty: str,
    points: int
) -> Question:
    question.subject = subject
    question.question_text = question_text
    question.options = options
    question.correct_answer = correct_answer
    question.difficulty = difficulty
    question.points = points
    
    await db.commit()
    await db.refresh(question)
    return question

async def delete_question(db: AsyncSession, question: Question) -> None:
    await db.delete(question)
    await db.commit()

async def get_distinct_subjects(db: AsyncSession) -> List[str]:
    result = await db.execute(
        select(Question.subject).distinct().order_by(Question.subject)
    )
    return [row[0] for row in result.all()]

async def get_question_stats(db: AsyncSession) -> dict:
    total_result = await db.execute(select(func.count(Question.id)))
    total_count = total_result.scalar()
    
    subject_result = await db.execute(
        select(Question.subject, func.count(Question.id))
        .group_by(Question.subject)
        .order_by(Question.subject)
    )
    by_subject = {subject: count for subject, count in subject_result.all()}
    
    difficulty_result = await db.execute(
        select(Question.difficulty, func.count(Question.id))
        .group_by(Question.difficulty)
        .order_by(Question.difficulty)
    )
    by_difficulty = {difficulty: count for difficulty, count in difficulty_result.all()}
    
    return {
        "total_questions": total_count,
        "by_subject": by_subject,
        "by_difficulty": by_difficulty
    } 