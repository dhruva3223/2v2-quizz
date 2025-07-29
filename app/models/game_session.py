from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class GameSession(Base):
    __tablename__ = "game_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_score = Column(Float, default=0.0)
    correct_answers = Column(Integer, default=0)
    total_answers = Column(Integer, default=0)
    average_response_time = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    
    game = relationship("Game", back_populates="game_sessions")
    user = relationship("User", back_populates="game_sessions")
    answers = relationship("Answer", back_populates="game_session") 