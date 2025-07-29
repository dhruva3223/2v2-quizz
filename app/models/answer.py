from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Answer(Base):
    __tablename__ = "answers"
    
    id = Column(Integer, primary_key=True, index=True)
    game_session_id = Column(Integer, ForeignKey("game_sessions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_answer = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    response_time = Column(Float, nullable=False)  # in seconds
    points_earned = Column(Float, default=0.0)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())
        
    game_session = relationship("GameSession", back_populates="answers")
    question = relationship("Question", back_populates="answers") 