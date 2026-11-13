"""Authenticated interview evaluation endpoint with provider-backed scoring."""
import json
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.v1.deps import get_current_user
from app.database.session import get_db
from app.integrations.ai_provider import generate_text
from app.models.interview import InterviewSession
from app.models.platform import InterviewContext, InterviewEvaluation, InterviewTurn
from app.models.user import User
from app.schemas.platform import EvaluationResponse

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])
_KEYS = ("communication", "problem_solving", "role_knowledge", "structure", "overall")


def _owned(db: Session, session_id: str, user_id: str) -> InterviewSession:
    session = db.query(InterviewSession).filter_by(id=session_id, user_id=user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session was not found")
    return session


@router.post("/{session_id}", response_model=EvaluationResponse)
async def evaluate_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = _owned(db, session_id, user.id)
    turns = db.query(InterviewTurn).filter_by(session_id=session.id, role="user").order_by(InterviewTurn.created_at.asc()).all()
    if not turns:
        raise HTTPException(status_code=409, detail="Answer at least one interview question before requesting feedback")
    context = db.query(InterviewContext).filter_by(session_id=session.id).first()
    transcript = "\n".join(f"Candidate: {t.content}" for t in turns)
    prompt = (
        "Evaluate this candidate's interview responses. Return only a JSON object with integer scores 0-100 for "
        "communication, problem_solving, role_knowledge, structure, overall and a concise summary string. "
        "Do not infer facts not in the transcript.\nRole: " + (context.role if context else "general") + "\n" + transcript[:24000]
    )
    raw = await generate_text(prompt, system="You are a fair interview coach. Be specific, constructive, and evidence-based.", max_tokens=500)
    try:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise ValueError("missing JSON")
        data = json.loads(match.group())
        rubric = {key: max(0, min(100, int(data[key]))) for key in _KEYS}
        summary = str(data["summary"]).strip()[:3000]
        if not summary:
            raise ValueError("empty summary")
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="AI service returned an invalid evaluation; try again") from exc
    record = InterviewEvaluation(session_id=session.id, user_id=user.id, total_score=rubric["overall"], rubric=rubric, summary=summary)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{session_id}", response_model=EvaluationResponse)
def get_evaluation(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _owned(db, session_id, user.id)
    record = db.query(InterviewEvaluation).filter_by(session_id=session_id, user_id=user.id).order_by(InterviewEvaluation.created_at.desc()).first()
    if not record:
        raise HTTPException(status_code=404, detail="Evaluation was not found")
    return record
