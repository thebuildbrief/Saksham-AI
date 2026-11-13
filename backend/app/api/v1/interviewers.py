"""Supported interviewer personas exposed to the client."""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/interviewers", tags=["Interviewers"])
_PERSONAS = [
    {"id": "recruiter", "name": "Recruiter", "focus": "communication, motivation, and experience", "types": ["behavioral"]},
    {"id": "engineer", "name": "Software Engineer", "focus": "coding fundamentals and problem solving", "types": ["technical"]},
    {"id": "architect", "name": "System Design Lead", "focus": "scalability, trade-offs, and architecture", "types": ["system_design"]},
    {"id": "hiring-manager", "name": "Hiring Manager", "focus": "role fit, ownership, and collaboration", "types": ["behavioral", "mixed"]},
]


@router.get("")
def list_interviewers():
    return _PERSONAS


@router.get("/{interviewer_id}")
def get_interviewer(interviewer_id: str):
    for persona in _PERSONAS:
        if persona["id"] == interviewer_id:
            return persona
    raise HTTPException(status_code=404, detail="Interviewer was not found")
