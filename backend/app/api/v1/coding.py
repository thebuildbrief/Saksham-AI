"""
Coding Problems and Execution API Endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.coding import (
    ExecuteCodeRequest,
    ExecuteCodeResponse,
    ProblemSummaryResponse,
    ProblemDetailResponse
)
from app.services.execution_engine import ExecutionEngine
from app.core.exceptions import NotFoundException
import json

router = APIRouter(prefix="/coding", tags=["Coding"])


@router.get("/problems", response_model=List[ProblemSummaryResponse])
def get_all_problems(db: Session = Depends(get_db)):
    """Retrieve catalog of DSA coding challenges."""
    problems = ExecutionEngine.get_problems(db)
    return [
        ProblemSummaryResponse(
            id=p.id,
            title=p.title,
            difficulty=p.difficulty,
            category=p.category
        )
        for p in problems
    ]


@router.get("/problems/{problem_id}", response_model=ProblemDetailResponse)
def get_problem_detail(problem_id: str, db: Session = Depends(get_db)):
    """Retrieve problem details, constraints, examples, and starter templates."""
    problem = ExecutionEngine.get_problem_by_id(db, problem_id)
    if not problem:
        raise NotFoundException("CodingProblem", problem_id)

    return ProblemDetailResponse(
        id=problem.id,
        title=problem.title,
        difficulty=problem.difficulty,
        category=problem.category,
        description=problem.description,
        constraints=json.loads(problem.constraints or "[]"),
        examples=json.loads(problem.examples or "[]"),
        starter_code=json.loads(problem.starter_code or "{}"),
        hints=json.loads(problem.hints or "[]")
    )


@router.post("/execute", response_model=ExecuteCodeResponse)
async def execute_code(
    payload: ExecuteCodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute code using the configured external isolated provider."""
    res = await ExecutionEngine.execute_code(
        db=db,
        problem_id=payload.problem_id,
        language=payload.language,
        code=payload.code,
        user_id=current_user.id,
        custom_input=payload.custom_input or "",
        session_id=payload.session_id
    )
    return ExecuteCodeResponse(**res)
