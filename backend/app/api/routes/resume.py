from io import BytesIO
from pathlib import Path
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import ResumeRecord
from app.schemas.models import ResumeUploadResponse
from app.services.pdf_editor import normalize_resume_pdf_layout
from app.services.resume_parser import parse_resume_file

router = APIRouter()


def _normalize_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return cleaned or "resume"


@router.post("/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ResumeUploadResponse:
    text, filename = await parse_resume_file(file)
    if len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Resume content is too short.")

    db.add(ResumeRecord(source_filename=filename, resume_text=text))
    db.commit()

    return ResumeUploadResponse(resume_text=text, source_filename=filename)


@router.post("/resume/fix-pdf-layout")
async def fix_uploaded_pdf_layout(file: UploadFile = File(...)) -> StreamingResponse:
    filename = file.filename or "uploaded_resume.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files can be fixed directly.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        fixed_pdf = normalize_resume_pdf_layout(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF layout fix failed: {exc}") from exc

    file_name = _normalize_filename(Path(filename).stem)
    return StreamingResponse(
        BytesIO(fixed_pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={file_name}_fixed.pdf"
        },
    )
