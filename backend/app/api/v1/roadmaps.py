"""Role-based learning roadmaps. Items are static learning suggestions, not progress claims."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.v1.deps import get_current_user
from app.database.session import get_db
from app.models.platform import UserProfile
from app.models.user import User

router = APIRouter(prefix="/roadmaps", tags=["Roadmaps"])
_CORE = [
    {"id": "foundations", "title": "Review core data structures", "category": "Foundations", "minutes": 30},
    {"id": "practice", "title": "Solve a timed coding problem", "category": "Practice", "minutes": 45},
    {"id": "reflection", "title": "Practice one behavioral story", "category": "Communication", "minutes": 20},
    {"id": "review", "title": "Review a system design trade-off", "category": "Design", "minutes": 35},
]


@router.get("")
def get_roadmap(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = db.query(UserProfile).filter_by(user_id=user.id).first()
    target = (profile.data or {}).get("target_role", "Software Engineer") if profile else "Software Engineer"
    return {"target_role": target, "items": _CORE, "source": "curated"}


@router.get("/{role}")
def roadmap_for_role(role: str):
    return {"target_role": role.replace("-", " ")[:120], "items": _CORE, "source": "curated"}
