from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # List of options
    correct_answer = Column(String, nullable=False)
    difficulty = Column(String, default="medium")  # easy, medium, hard
    points = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    answers = relationship("Answer", back_populates="question")