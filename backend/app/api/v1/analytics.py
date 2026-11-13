"""Per-account activity summaries derived from persisted sessions and submissions."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.v1.deps import get_current_user
from app.database.session import get_db
from app.models.coding import CodingSubmission
from app.models.interview import InterviewSession
from app.models.platform import InterviewEvaluation, ResumeDocument
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    interview_count = db.query(func.count(InterviewSession.id)).filter_by(user_id=user.id).scalar() or 0
    submission_count = db.query(func.count(CodingSubmission.id)).filter_by(user_id=user.id).scalar() or 0
    accepted_count = db.query(func.count(CodingSubmission.id)).filter(CodingSubmission.user_id == user.id, CodingSubmission.status == "Accepted").scalar() or 0
    resume_count = db.query(func.count(ResumeDocument.id)).filter_by(user_id=user.id).scalar() or 0
    average_score = db.query(func.avg(InterviewEvaluation.total_score)).filter_by(user_id=user.id).scalar()
    return {"interviews": interview_count, "coding_submissions": submission_count, "accepted_submissions": accepted_count, "resumes": resume_count, "average_interview_score": round(float(average_score), 1) if average_score is not None else None}


@router.get("/coding")
def coding_analytics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(CodingSubmission.status, func.count(CodingSubmission.id)).filter_by(user_id=user.id).group_by(CodingSubmission.status).all()
    return {"submissions_by_status": {status: count for status, count in rows}}
