"""Curated public company practice catalog; descriptions are practice guidance, not hiring claims."""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/companies", tags=["Companies"])
_COMPANIES = [
    {"id": "google", "name": "Google", "industry": "Technology", "practice_focus": ["algorithms", "system design", "behavioral"]},
    {"id": "amazon", "name": "Amazon", "industry": "Technology", "practice_focus": ["data structures", "system design", "leadership examples"]},
    {"id": "microsoft", "name": "Microsoft", "industry": "Technology", "practice_focus": ["problem solving", "collaboration", "design"]},
    {"id": "meta", "name": "Meta", "industry": "Technology", "practice_focus": ["coding", "system design", "impact"]},
    {"id": "startup", "name": "Startup practice", "industry": "General", "practice_focus": ["ownership", "ambiguity", "product thinking"]},
]


@router.get("")
def list_companies():
    return _COMPANIES


@router.get("/{company_id}")
def get_company(company_id: str):
    item = next((entry for entry in _COMPANIES if entry["id"] == company_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Company practice profile was not found")
    return item
