"""
Coding Problems, Test Cases, and Candidate Submissions Models.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base


class CodingProblem(Base):
    __tablename__ = "coding_problems"

    id = Column(String(50), primary_key=True)  # slug: e.g. two-sum, reverse-linked-list
    title = Column(String(200), nullable=False)
    difficulty = Column(String(20), default="Medium")  # Easy, Medium, Hard
    category = Column(String(100), default="Arrays & Hashing")
    description = Column(Text, nullable=False)
    constraints = Column(Text, default="[]")  # JSON
    examples = Column(Text, default="[]")  # JSON
    starter_code = Column(Text, default="{}")  # JSON mapping lang -> starter code
    hints = Column(Text, default="[]")  # JSON
    time_limit_sec = Column(Integer, default=2)
    memory_limit_mb = Column(Integer, default=256)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    test_cases = relationship("CodingTestCase", back_populates="problem", cascade="all, delete-orphan")
    submissions = relationship("CodingSubmission", back_populates="problem")


class CodingTestCase(Base):
    __tablename__ = "coding_test_cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    problem_id = Column(String(50), ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False)
    input_data = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_hidden = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    problem = relationship("CodingProblem", back_populates="test_cases")


class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=True)
    problem_id = Column(String(50), ForeignKey("coding_problems.id"), nullable=False)
    language = Column(String(30), default="python")
    code = Column(Text, nullable=False)
    status = Column(String(30), default="Accepted")  # Accepted, Wrong Answer, TLE, Runtime Error
    passed_tests = Column(Integer, default=0)
    total_tests = Column(Integer, default=0)
    execution_time_ms = Column(Integer, default=0)
    memory_kb = Column(Integer, default=0)
    output = Column(Text, default="")
    ai_complexity_feedback = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("InterviewSession", back_populates="submissions")
    problem = relationship("CodingProblem", back_populates="submissions")
