"""User preference API; never returns authentication or provider configuration."""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.v1.deps import get_current_user
from app.database.session import get_db
from app.models.platform import UserProfile
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["Settings"])
_ALLOWED = {"theme", "language", "email_notifications", "practice_reminders", "weekly_goal"}


class SettingsPatch(BaseModel):
    values: dict[str, Any] = Field(max_length=20)


def _record(db: Session, user_id: str):
    row = db.query(UserProfile).filter_by(user_id=user_id).first()
    return row, dict(row.data or {}) if row else {}


@router.get("")
def get_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row, data = _record(db, user.id)
    prefs = data.get("settings", {})
    return {"settings": prefs, "updated_at": row.updated_at if row else None}


@router.patch("")
def patch_settings(payload: SettingsPatch, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    unknown = set(payload.values) - _ALLOWED
    if unknown:
        raise HTTPException(status_code=422, detail="Unsupported settings field")
    values = payload.values
    if "theme" in values and values["theme"] not in {"light", "dark", "system"}:
        raise HTTPException(status_code=422, detail="theme must be light, dark, or system")
    if "language" in values and (not isinstance(values["language"], str) or len(values["language"]) > 12):
        raise HTTPException(status_code=422, detail="Invalid language setting")
    for key in {"email_notifications", "practice_reminders"} & values.keys():
        if not isinstance(values[key], bool):
            raise HTTPException(status_code=422, detail=f"{key} must be a boolean")
    if "weekly_goal" in values and (not isinstance(values["weekly_goal"], int) or not 1 <= values["weekly_goal"] <= 30):
        raise HTTPException(status_code=422, detail="weekly_goal must be between 1 and 30")
    row, data = _record(db, user.id)
    data["settings"] = {**data.get("settings", {}), **values}
    if row:
        row.data = data
    else:
        row = UserProfile(user_id=user.id, data=data)
        db.add(row)
    db.commit()
    db.refresh(row)
    return {"settings": data["settings"], "updated_at": row.updated_at}
