"""
Coding Arena & Execution Schemas.
"""
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ExecuteCodeRequest(BaseModel):
    problem_id: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9][a-z0-9-]*$")
    language: Literal["python", "javascript", "cpp", "java"]
    code: str = Field(..., min_length=1, max_length=32768)
    custom_input: Optional[str] = Field(default="", max_length=16384)
    session_id: Optional[str] = Field(default=None, max_length=36)

    @field_validator("code")
    @classmethod
    def validate_code_size(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 32 * 1024:
            raise ValueError("Source code exceeds the 32 KiB limit")
        return value

    @field_validator("custom_input")
    @classmethod
    def validate_input_size(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value.encode("utf-8")) > 16 * 1024:
            raise ValueError("Custom input exceeds the 16 KiB limit")
        return value


class TestCaseResult(BaseModel):
    test_id: int
    passed: bool
    input_data: str
    expected_output: str
    actual_output: str
    error: Optional[str] = None


class ExecuteCodeResponse(BaseModel):
    status: str  # Accepted, Wrong Answer, Time Limit Exceeded, Compilation Error, Runtime Error
    passed_tests: int
    total_tests: int
    execution_time_ms: int
    memory_kb: int
    stdout: str = ""
    stderr: str = ""
    test_results: List[TestCaseResult] = Field(default_factory=list)
    ai_complexity_feedback: Dict[str, Any] = Field(default_factory=dict)


class ProblemSummaryResponse(BaseModel):
    id: str
    title: str
    difficulty: str
    category: str


class ProblemDetailResponse(BaseModel):
    id: str
    title: str
    difficulty: str
    category: str
    description: str
    constraints: List[str]
    examples: List[Dict[str, Any]]
    starter_code: Dict[str, str]
    hints: List[str]
