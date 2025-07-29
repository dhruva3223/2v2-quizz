from pydantic import BaseModel
from typing import List
from datetime import datetime

class QuestionResponse(BaseModel):
    id: int
    question_text: str
    options: List[str]
    difficulty: str
    points: int
    
    class Config:
        from_attributes = True

class AnswerSubmission(BaseModel):
    question_id: int
    user_answer: str
    response_time: float

class AnswerResponse(BaseModel):
    id: int
    question_id: int
    user_answer: str
    is_correct: bool
    response_time: float
    points_earned: float
    answered_at: datetime
    
    class Config:
        from_attributes = True

class QuestionCreate(BaseModel):
    subject: str
    question_text: str
    options: List[str]
    correct_answer: str
    difficulty: str = "medium"
    points: int = 10 