from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import ResumeRecord
from app.schemas.models import ResumeUploadResponse
from app.services.resume_parser import parse_resume_file

router = APIRouter()


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
