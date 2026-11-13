"""Compatibility problem catalog routes backed by the coding domain."""
import json
from fastapi import APIRouter
from app.core.exceptions import NotFoundException
from app.database.session import SessionLocal
from app.services.execution_engine import ExecutionEngine

router = APIRouter(prefix="/problems", tags=["Problems"])


@router.get("")
def list_problems():
    with SessionLocal() as db:
        return [{"id": p.id, "title": p.title, "difficulty": p.difficulty, "category": p.category} for p in ExecutionEngine.get_problems(db)]


@router.get("/{problem_id}")
def get_problem(problem_id: str):
    with SessionLocal() as db:
        p = ExecutionEngine.get_problem_by_id(db, problem_id)
        if not p:
            raise NotFoundException("CodingProblem", problem_id)
        return {"id": p.id, "title": p.title, "difficulty": p.difficulty, "category": p.category, "description": p.description, "constraints": json.loads(p.constraints or "[]"), "examples": json.loads(p.examples or "[]"), "starter_code": json.loads(p.starter_code or "{}"), "hints": json.loads(p.hints or "[]")}
