from io import BytesIO

from fastapi import HTTPException, UploadFile
from docx import Document
from pypdf import PdfReader


async def parse_resume_file(file: UploadFile) -> tuple[str, str]:
    filename = file.filename or "uploaded_resume"
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    lower = filename.lower()
    if lower.endswith(".txt"):
        return content.decode("utf-8", errors="ignore"), filename

    if lower.endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(content))
            extracted = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
            if not extracted:
                raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
            return extracted, filename
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"PDF parsing failed: {exc}") from exc

    if lower.endswith(".docx"):
        try:
            document = Document(BytesIO(content))
            extracted = "\n".join(paragraph.text for paragraph in document.paragraphs).strip()
            if not extracted:
                raise HTTPException(status_code=400, detail="Could not extract text from DOCX.")
            return extracted, filename
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"DOCX parsing failed: {exc}") from exc

    raise HTTPException(status_code=400, detail="Unsupported file type. Use .txt, .pdf, or .docx.")
