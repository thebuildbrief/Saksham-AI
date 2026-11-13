"""Authenticated account and public profile endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.v1.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.platform import UserProfile
from app.schemas.platform import ProfileUpdate, SettingsResponse, UserPublic, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserPublic)
def read_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserPublic)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/profile", response_model=SettingsResponse)
def read_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    return {"data": profile.data if profile else {}, "updated_at": profile.updated_at if profile else None}


@router.patch("/me/profile", response_model=SettingsResponse)
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile is None:
        profile = UserProfile(user_id=user.id, data={})
        db.add(profile)
    data = dict(profile.data or {})
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            data[key] = value
    profile.data = data
    db.commit()
    db.refresh(profile)
    return {"data": profile.data, "updated_at": profile.updated_at}
