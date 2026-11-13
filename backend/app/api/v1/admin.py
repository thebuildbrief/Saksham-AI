"""Admin-only operational and account management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.v1.deps import get_current_user
from app.database.session import get_db
from app.models.coding import CodingSubmission
from app.models.interview import InterviewSession
from app.models.platform import ResumeDocument
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


def _admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")


@router.get("/overview")
def admin_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _admin(user)
    return {
        "users": db.query(func.count(User.id)).scalar() or 0,
        "interviews": db.query(func.count(InterviewSession.id)).scalar() or 0,
        "coding_submissions": db.query(func.count(CodingSubmission.id)).scalar() or 0,
        "resumes": db.query(func.count(ResumeDocument.id)).scalar() or 0,
    }


@router.get("/users")
def list_users(offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _admin(user)
    rows = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return [{"id": row.id, "email": row.email, "full_name": row.full_name, "role": row.role, "is_active": row.is_active, "created_at": row.created_at} for row in rows]


@router.patch("/users/{user_id}/active")
def set_user_active(user_id: str, is_active: bool, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _admin(user)
    target = db.query(User).filter_by(id=user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User was not found")
    if target.id == user.id and not is_active:
        raise HTTPException(status_code=409, detail="Administrators cannot deactivate their own account")
    target.is_active = is_active
    db.commit()
    return {"id": target.id, "is_active": target.is_active}
