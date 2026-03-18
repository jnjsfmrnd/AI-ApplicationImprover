from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import GenerationRecord
from app.schemas.models import (
    ExportPdfRequest,
    GeneratedArtifact,
    GenerationInput,
    SkillGapItem,
    SkillGapResponse,
    SkillProjectResponse,
)
from app.services.agent_orchestrator import orchestrator
from app.services.llm_provider import llm_provider

router = APIRouter()


@router.post("/generate/rewrite", response_model=GeneratedArtifact)
async def generate_rewrite(
    payload: GenerationInput,
    db: Session = Depends(get_db),
) -> GeneratedArtifact:
    content = await orchestrator.recruiter_rewrite(
        payload.resume_text, payload.job_description, payload.role, payload.industry
    )
    db.add(
        GenerationRecord(
            mode="rewrite",
            model=llm_provider.model_name,
            role=payload.role,
            industry=payload.industry,
            company=payload.company,
            year=payload.year,
            input_resume_text=payload.resume_text,
            job_description=payload.job_description,
            output_text=content,
            extra_json=None,
        )
    )
    db.commit()
    return GeneratedArtifact(content=content, model=llm_provider.model_name, mode="rewrite")


@router.post("/generate/ats", response_model=GeneratedArtifact)
async def generate_ats(
    payload: GenerationInput,
    db: Session = Depends(get_db),
) -> GeneratedArtifact:
    content = await orchestrator.ats_optimize(
        payload.resume_text, payload.job_description, payload.role, payload.year
    )
    db.add(
        GenerationRecord(
            mode="ats",
            model=llm_provider.model_name,
            role=payload.role,
            industry=payload.industry,
            company=payload.company,
            year=payload.year,
            input_resume_text=payload.resume_text,
            job_description=payload.job_description,
            output_text=content,
            extra_json=None,
        )
    )
    db.commit()
    return GeneratedArtifact(content=content, model=llm_provider.model_name, mode="ats")


@router.post("/generate/cover-letter", response_model=GeneratedArtifact)
async def generate_cover_letter(
    payload: GenerationInput,
    db: Session = Depends(get_db),
) -> GeneratedArtifact:
    content = await orchestrator.cover_letter(
        payload.resume_text,
        payload.job_description,
        payload.role,
        payload.company,
    )
    db.add(
        GenerationRecord(
            mode="cover_letter",
            model=llm_provider.model_name,
            role=payload.role,
            industry=payload.industry,
            company=payload.company,
            year=payload.year,
            input_resume_text=payload.resume_text,
            job_description=payload.job_description,
            output_text=content,
            extra_json=None,
        )
    )
    db.commit()
    return GeneratedArtifact(content=content, model=llm_provider.model_name, mode="cover_letter")


@router.post("/generate/skill-gap", response_model=SkillGapResponse)
async def generate_skill_gap(
    payload: GenerationInput,
    db: Session = Depends(get_db),
) -> SkillGapResponse:
    summary, gaps = await orchestrator.skill_gap(payload.resume_text, payload.job_description, payload.role)
    gap_items = [SkillGapItem(**item) for item in gaps]
    db.add(
        GenerationRecord(
            mode="skill_gap",
            model=llm_provider.model_name,
            role=payload.role,
            industry=payload.industry,
            company=payload.company,
            year=payload.year,
            input_resume_text=payload.resume_text,
            job_description=payload.job_description,
            output_text=summary,
            extra_json={"gaps": [item.model_dump() for item in gap_items]},
        )
    )
    db.commit()
    return SkillGapResponse(summary=summary, gaps=gap_items, model=llm_provider.model_name)


@router.post("/generate/skill-projects", response_model=SkillProjectResponse)
async def generate_skill_projects(
    payload: dict,
    db: Session = Depends(get_db),
) -> SkillProjectResponse:
    role = payload.get("role", "Target Role")
    skills = payload.get("skills", [])
    projects = await orchestrator.skill_to_projects(role=role, skills=skills)
    db.add(
        GenerationRecord(
            mode="skill_projects",
            model="mcp-agent-flow",
            role=role,
            industry=None,
            company=None,
            year=None,
            input_resume_text="",
            job_description="",
            output_text="Generated same-day skill project scopes",
            extra_json={"skills": skills, "projects": [project.model_dump() for project in projects]},
        )
    )
    db.commit()
    return SkillProjectResponse(projects=projects, model="mcp-agent-flow")


@router.post("/export/pdf")
async def export_pdf(payload: ExportPdfRequest) -> StreamingResponse:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, payload.title)
    y -= 30

    pdf.setFont("Helvetica", 10)
    for line in payload.content.split("\n"):
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = height - 50
        pdf.drawString(40, y, line[:120])
        y -= 14

    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={payload.title.replace(' ', '_')}.pdf"},
    )
