"""Private, owner-scoped resume upload, download, deletion and analysis."""
from io import BytesIO
from pathlib import Path
import uuid
import zipfile
from urllib.parse import quote
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.database.session import get_db
from app.integrations.ai_provider import generate_text
from app.models.platform import ResumeDocument
from app.models.user import User
from app.services.object_storage import delete_object, get_object, put_object

router = APIRouter(prefix="/resumes", tags=["Resumes"])
_ALLOWED = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".txt": "text/plain"}


def _public(record: ResumeDocument):
    return {"id": record.id, "filename": record.filename, "content_type": record.content_type, "size_bytes": record.size_bytes, "created_at": record.created_at, "has_extracted_text": bool(record.extracted_text)}


def _extract(extension: str, content: bytes) -> str:
    if extension == ".txt":
        try:
            return content.decode("utf-8-sig")[:100_000]
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="Text resume must be UTF-8 encoded") from exc
    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=422, detail="Uploaded file is not a valid PDF")
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(content), strict=True)
            if len(reader.pages) > 80:
                raise HTTPException(status_code=413, detail="Resume PDF exceeds the 80 page limit")
            return "\n".join(page.extract_text() or "" for page in reader.pages)[:100_000]
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Could not read the PDF resume") from exc
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = archive.namelist()
            if len(names) > 1000 or sum(info.file_size for info in archive.infolist()) > 20 * 1024 * 1024 or "word/document.xml" not in names:
                raise HTTPException(status_code=422, detail="Uploaded file is not a valid DOCX resume")
        from docx import Document
        document = Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)[:100_000]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Could not read the DOCX resume") from exc


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    filename = Path(file.filename or "resume").name
    extension = Path(filename).suffix.lower()
    if extension not in _ALLOWED:
        raise HTTPException(status_code=415, detail="Upload a PDF, DOCX, or UTF-8 text resume")
    content = await file.read(settings.MAX_RESUME_SIZE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Resume file is empty")
    if len(content) > settings.MAX_RESUME_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Resume exceeds the configured upload size limit")
    extracted = _extract(extension, content)
    content_type = _ALLOWED[extension]
    object_key = f"resumes/{user.id}/{uuid.uuid4().hex}{extension}"
    put_object(object_key, content, content_type)
    record = ResumeDocument(user_id=user.id, filename=filename[:255], content_type=content_type, size_bytes=len(content), object_key=object_key, extracted_text=extracted)
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        delete_object(object_key)
        raise
    return _public(record)


@router.get("")
def list_resumes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    records = db.query(ResumeDocument).filter_by(user_id=user.id).order_by(ResumeDocument.created_at.desc()).limit(100).all()
    return [_public(item) for item in records]


@router.get("/{resume_id}/download")
def download_resume(resume_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(ResumeDocument).filter_by(id=resume_id, user_id=user.id).first()
    if not record:
        raise NotFoundException("Resume", resume_id)
    content = get_object(record.object_key)
    return Response(content=content, media_type=record.content_type, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(record.filename)}", "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.post("/{resume_id}/analyze")
async def analyze_resume(resume_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(ResumeDocument).filter_by(id=resume_id, user_id=user.id).first()
    if not record:
        raise NotFoundException("Resume", resume_id)
    if not record.extracted_text.strip():
        raise HTTPException(status_code=422, detail="No readable text could be extracted from this resume")
    feedback = await generate_text(
        "Review the resume text below. Give concise, evidence-based feedback on clarity, measurable impact, relevant skills, and next improvements. Do not invent experience or personal data.\n\n" + record.extracted_text[:18000],
        system="You are a constructive resume coach. Do not repeat contact details or sensitive personal information.", max_tokens=900,
    )
    return {"resume_id": record.id, "feedback": feedback}


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(ResumeDocument).filter_by(id=resume_id, user_id=user.id).first()
    if not record:
        raise NotFoundException("Resume", resume_id)
    delete_object(record.object_key)
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
