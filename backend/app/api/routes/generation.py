from io import BytesIO
import json
import re
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import GenerationRecord
from app.schemas.models import (
    ExportPdfRequest,
    GeneratedArtifact,
    GenerationInput,
    JobContextRequest,
    JobContextResponse,
    ResumeVariant,
    SkillGapItem,
    SkillGapResponse,
    SkillProjectResponse,
    TailoredResumeRequest,
    TailoredResumeResponse,
)
from app.services.agent_orchestrator import orchestrator
from app.services.llm_provider import llm_provider

router = APIRouter()

DEFAULT_ROLE = "Target Role"


def _coerce_year(value: object) -> int | None:
    if isinstance(value, int) and 1990 <= value <= 2100:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        if 1990 <= parsed <= 2100:
            return parsed
    return None


def _extract_json_object(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}


_COMPANY_NOISE = {"unknown", "n/a", "not specified", "not mentioned", "not provided", "not available", "confidential", "none"}


def _regex_extract_company(job_description: str) -> str | None:
    """Best-effort regex extraction of company name before hitting the LLM."""
    patterns = [
        r"(?:^|\n)\s*(?:about|overview)\s+([A-Z][\w&.,!\- ]{1,50})(?:\s*[:\n])",
        r"(?:^|\n)\s*company\s*:\s*([A-Z][\w&.,!\- ]{1,50})",
        r"(?:join|at|with)\s+([A-Z][\w&.]+(?:\s+[A-Z][\w&.]+){0,3})(?:\s*,|\s+we\b|\s+is\b|\s+are\b|\s+team)",
        r"([A-Z][\w&.]+(?:\s+[A-Z][\w&.]+){0,3})\s+is\s+(?:looking|hiring|seeking|searching)",
        r"([A-Z][\w&.]+(?:\s+[A-Z][\w&.]+){0,3})\s+(?:is|are)\s+a(?:n?)?\s+(?:fast|leading|global|top|growing)",
    ]
    for pattern in patterns:
        m = re.search(pattern, job_description, re.IGNORECASE | re.MULTILINE)
        if m:
            candidate = m.group(1).strip().rstrip(",.:;")
            if candidate.lower() not in _COMPANY_NOISE and len(candidate) >= 2:
                return candidate
    return None


async def _infer_job_context(job_description: str) -> JobContextResponse:
    regex_company = _regex_extract_company(job_description)

    system_prompt = (
        "Extract hiring metadata from a job description. Return strict JSON with keys "
        "role, industry, company, year, confidence. Confidence must be 0 to 1."
    )
    user_prompt = (
        "Job description:\n"
        f"{job_description}\n\n"
        "Rules:\n"
        "- role should be the best-fit target position title.\n"
        "- industry should be a concise sector label.\n"
        "- company: look carefully for a company or organisation name in the text (e.g. in 'About X', 'Join X', 'X is hiring', 'at X'). "
        "Set to null only if no organisation name is present at all.\n"
        "- year should be null unless a specific hiring year is clearly stated.\n"
        "- output JSON only, no markdown."
    )
    output = await llm_provider.generate(system_prompt, user_prompt)
    parsed = _extract_json_object(output)

    role = parsed.get("role") if isinstance(parsed.get("role"), str) else ""
    industry = parsed.get("industry") if isinstance(parsed.get("industry"), str) else None
    llm_company_raw = parsed.get("company")
    llm_company = (
        llm_company_raw.strip()
        if isinstance(llm_company_raw, str) and llm_company_raw.strip().lower() not in _COMPANY_NOISE
        else None
    )
    company = llm_company or regex_company
    year = _coerce_year(parsed.get("year"))

    confidence_raw = parsed.get("confidence")
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    return JobContextResponse(
        role=role.strip() or DEFAULT_ROLE,
        industry=industry.strip() if industry else None,
        company=company.strip() if company else None,
        year=year,
        confidence=confidence,
    )


async def _resolve_generation_context(payload: GenerationInput) -> JobContextResponse:
    role_value = (payload.role or "").strip()
    has_role = bool(role_value) and role_value != DEFAULT_ROLE
    has_industry = bool((payload.industry or "").strip())
    has_company = bool((payload.company or "").strip())
    has_year = payload.year is not None

    inferred = JobContextResponse(role=DEFAULT_ROLE)
    if not has_role or not has_company or (not has_industry and not has_year):
        inferred = await _infer_job_context(payload.job_description)

    return JobContextResponse(
        role=role_value if has_role else (inferred.role or DEFAULT_ROLE),
        industry=(payload.industry or "").strip() or inferred.industry,
        company=(payload.company or "").strip() or inferred.company,
        year=payload.year if payload.year is not None else inferred.year,
        confidence=inferred.confidence,
    )


def _normalize_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return cleaned or "Generated_Document"


def _markdown_inline_to_reportlab(line: str) -> str:
    # Remove all forced markdown or bold/italic conversion; output plain text only, except for job/company lines in EXPERIENCE section
    line = re.sub(r"(?<=\d)[–—−](?=\d)", "-", line)
    # Remove any markdown bold/italic/underline from input (if present)
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
    line = re.sub(r"__(.+?)__", r"\1", line)
    line = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", line)
    line = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", line)

    # Bold job title and company if line matches EXPERIENCE entry pattern (Job Title, Company, ...)
    # Example: Senior Software Engineer, Microsoft, Redmond, WA — 2021–2024
    exp_match = re.match(r"^([A-Za-z0-9 .\-/()]+),\s*([A-Za-z0-9 .&\-/()]+),?\s*([A-Za-z0-9 .,&\-/()]+)?\s*[—\-]+\s*([0-9]{4}(?:–[0-9]{4}|–Present|–Current)?)$", line)
    if exp_match:
        job_title = exp_match.group(1).strip()
        company = exp_match.group(2).strip()
        rest = line[len(exp_match.group(0)) - len(line):] if len(exp_match.groups()) > 3 else ''
        # Bold job title and company only
        formatted = f"<b>{escape(job_title)}</b>, <b>{escape(company)}</b>{escape(line[len(job_title) + len(company) + 2:])}"
        return formatted

    return escape(line)


def _strip_markdown_for_header(line: str) -> str:
    line = re.sub(r"(?<=\d)[–—−](?=\d)", "-", line)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_(?!_)(.*?)(?<!_)_(?!_)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text)
    return text.strip()


def _normalize_resume_export_text(text: str) -> str:
    normalized = text.replace("\u202f", " ").replace("\u00a0", " ")
    normalized = normalized.replace("\u2018", "'").replace("\u2019", "'")
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    normalized = re.sub(r"(?m)^\s*[•·●▪◦]\s+", "- ", normalized)
    normalized = re.sub(r"\s*[•·●▪◦]\s*", " | ", normalized)
    normalized = re.sub(r"[‐‑‒–—−]", "-", normalized)
    return normalized


def _should_skip_line(line: str) -> bool:
    normalized = re.sub(r"\s+", " ", line).strip().lower()
    if not normalized:
        return False
    if normalized.startswith("this polished resume"):
        return True
    if normalized.startswith("this resume"):
        return True
    if normalized.startswith("this resume highlights"):
        return True
    # catch separator lines followed by intro blurbs (the --- itself)
    return False


def _looks_like_name_line(line: str) -> bool:
    plain = re.sub(r"[*_#`]", "", line).strip()
    if not plain:
        return False
    words = [word for word in re.split(r"\s+", plain) if word]
    if len(words) < 2 or len(words) > 6:
        return False
    letters = [char for char in plain if char.isalpha()]
    if not letters:
        return False
    uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
    return uppercase_ratio >= 0.75


def _extract_heading_text(line: str) -> str | None:
    heading_match = re.match(r"^#{1,6}\s*(.+)$", line.strip())
    if heading_match:
        return heading_match.group(1).strip()

    plain = re.sub(r"[*_#`]", "", line).strip()
    if not plain:
        return None

    uppercase_ratio = 0.0
    letters = [char for char in plain if char.isalpha()]
    if letters:
        uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)

    if uppercase_ratio >= 0.75 and len(plain.split()) <= 5:
        return plain

    return None


def _map_heading_column(line: str) -> str | None:
    heading = _extract_heading_text(line)
    if not heading:
        return None

    normalized = re.sub(r"\s+", " ", heading).strip().lower()
    normalized = normalized.replace("&", "and")

    right_sections = {
        "core skills",
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
        "key competencies",
        "key skills",
        "education",
        "certifications",
        "certification",
        "languages",
        "tools",
    }
    left_sections = {
        "professional experience",
        "experience",
        "work experience",
        "additional",
        "additional information",
        "notes",
        "technical notes",
        "additional notes",
        "other",
        "other information",
    }

    if normalized in right_sections:
        return "right"
    if normalized in left_sections:
        return "left"
    return None


def _is_summary_heading(line: str) -> bool:
    heading = _extract_heading_text(line)
    if not heading:
        return False
    normalized = re.sub(r"\s+", " ", heading).strip().lower().replace("&", "and")
    return normalized in {
        "professional summary",
        "summary",
        "career summary",
        "professional profile",
        "profile",
        "about me",
        "objective",
        "career objective",
    }


@router.post("/extract/job-context", response_model=JobContextResponse)
async def extract_job_context(payload: JobContextRequest) -> JobContextResponse:
    return await _infer_job_context(payload.job_description)


@router.post("/generate/rewrite", response_model=GeneratedArtifact)
async def generate_rewrite(
    payload: GenerationInput,
    db: Session = Depends(get_db),
) -> GeneratedArtifact:
    context = await _resolve_generation_context(payload)
    with llm_provider.use_model(payload.model):
        content = await orchestrator.recruiter_rewrite(
            payload.resume_text,
            payload.job_description,
            context.role,
            context.industry,
        )
    used_model = payload.model.strip() if isinstance(payload.model, str) and payload.model.strip() else llm_provider.model_name
    db.add(
        GenerationRecord(
            mode="rewrite",
            model=used_model,
            role=context.role,
            industry=context.industry,
            company=context.company,
            year=context.year,
            input_resume_text=payload.resume_text,
            job_description=payload.job_description,
            output_text=content,
            extra_json=None,
        )
    )
    db.commit()
    return GeneratedArtifact(content=content, model=used_model, mode="rewrite")


@router.post("/generate/ats", response_model=GeneratedArtifact)
async def generate_ats(
    payload: GenerationInput,
    db: Session = Depends(get_db),
) -> GeneratedArtifact:
    context = await _resolve_generation_context(payload)
    with llm_provider.use_model(payload.model):
        content = await orchestrator.ats_optimize(
            payload.resume_text,
            payload.job_description,
            context.role,
            context.year,
        )
    used_model = payload.model.strip() if isinstance(payload.model, str) and payload.model.strip() else llm_provider.model_name
    db.add(
        GenerationRecord(
            mode="ats",
            model=used_model,
            role=context.role,
            industry=context.industry,
            company=context.company,
            year=context.year,
            input_resume_text=payload.resume_text,
            job_description=payload.job_description,
            output_text=content,
            extra_json=None,
        )
    )
    db.commit()
    return GeneratedArtifact(content=content, model=used_model, mode="ats")


@router.post("/generate/tailored-resume", response_model=TailoredResumeResponse)
async def generate_tailored_resume(
    payload: TailoredResumeRequest,
    db: Session = Depends(get_db),
) -> TailoredResumeResponse:
    context = await _resolve_generation_context(payload)
    with llm_provider.use_model(payload.model):
        pipeline_result = await orchestrator.generate_tailored_resume_pipeline(
            payload.resume_text,
            payload.job_description,
            context.role,
            context.industry,
            context.year,
            company=context.company,
            max_gap_skills=payload.max_gap_skills,
            include_cover_letter=payload.include_cover_letter,
        )
    used_model = payload.model.strip() if isinstance(payload.model, str) and payload.model.strip() else llm_provider.model_name

    gap_items = [SkillGapItem(**item) for item in pipeline_result["skill_gaps"]]
    projects = pipeline_result["skill_projects"]

    db.add(
        GenerationRecord(
            mode="tailored_resume",
            model=used_model,
            role=context.role,
            industry=context.industry,
            company=context.company,
            year=context.year,
            input_resume_text=payload.resume_text,
            job_description=payload.job_description,
            output_text=pipeline_result["truthful_ats"],
            extra_json={
                "skill_gap_summary": pipeline_result["skill_gap_summary"],
                "skill_gaps": [item.model_dump() for item in gap_items],
                "skill_projects": [project.model_dump() for project in projects],
                "cover_letter": pipeline_result["cover_letter"],
                "truthful_rewrite": pipeline_result["truthful_rewrite"],
                "project_enhanced_rewrite": pipeline_result["project_enhanced_rewrite"],
                "truthful_ats": pipeline_result["truthful_ats"],
                "project_enhanced_ats": pipeline_result["project_enhanced_ats"],
                "default_final_variant": pipeline_result["default_final_variant"],
            },
        )
    )
    db.commit()

    return TailoredResumeResponse(
        context=context,
        skill_gap_summary=pipeline_result["skill_gap_summary"],
        skill_gaps=gap_items,
        skill_projects=projects,
        cover_letter=pipeline_result["cover_letter"],
        truthful_rewrite=ResumeVariant(
            content=pipeline_result["truthful_rewrite"],
            stage="recruiter_rewrite",
            variant="truthful",
        ),
        project_enhanced_rewrite=ResumeVariant(
            content=pipeline_result["project_enhanced_rewrite"],
            stage="recruiter_rewrite",
            variant="project_enhanced",
        ),
        truthful_ats=ResumeVariant(
            content=pipeline_result["truthful_ats"],
            stage="ats",
            variant="truthful",
        ),
        project_enhanced_ats=ResumeVariant(
            content=pipeline_result["project_enhanced_ats"],
            stage="ats",
            variant="project_enhanced",
        ),
        default_final_variant=pipeline_result["default_final_variant"],
        model=used_model,
    )


@router.post("/generate/cover-letter", response_model=GeneratedArtifact)
async def generate_cover_letter(
    payload: GenerationInput,
    db: Session = Depends(get_db),
) -> GeneratedArtifact:
    context = await _resolve_generation_context(payload)
    with llm_provider.use_model(payload.model):
        content = await orchestrator.cover_letter(
            payload.resume_text,
            payload.job_description,
            context.role,
            context.company,
        )
    used_model = payload.model.strip() if isinstance(payload.model, str) and payload.model.strip() else llm_provider.model_name
    db.add(
        GenerationRecord(
            mode="cover_letter",
            model=used_model,
            role=context.role,
            industry=context.industry,
            company=context.company,
            year=context.year,
            input_resume_text=payload.resume_text,
            job_description=payload.job_description,
            output_text=content,
            extra_json=None,
        )
    )
    db.commit()
    return GeneratedArtifact(content=content, model=used_model, mode="cover_letter")


@router.post("/generate/skill-gap", response_model=SkillGapResponse)
async def generate_skill_gap(
    payload: GenerationInput,
    db: Session = Depends(get_db),
) -> SkillGapResponse:
    context = await _resolve_generation_context(payload)
    with llm_provider.use_model(payload.model):
        summary, gaps = await orchestrator.skill_gap(payload.resume_text, payload.job_description, context.role)
    used_model = payload.model.strip() if isinstance(payload.model, str) and payload.model.strip() else llm_provider.model_name
    gap_items = [SkillGapItem(**item) for item in gaps]
    db.add(
        GenerationRecord(
            mode="skill_gap",
            model=used_model,
            role=context.role,
            industry=context.industry,
            company=context.company,
            year=context.year,
            input_resume_text=payload.resume_text,
            job_description=payload.job_description,
            output_text=summary,
            extra_json={"gaps": [item.model_dump() for item in gap_items]},
        )
    )
    db.commit()
    return SkillGapResponse(summary=summary, gaps=gap_items, model=used_model)


@router.post("/generate/skill-projects", response_model=SkillProjectResponse)
async def generate_skill_projects(
    payload: dict,
    db: Session = Depends(get_db),
) -> SkillProjectResponse:
    role = payload.get("role", DEFAULT_ROLE)
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
@router.post("/export/pdf/resume")
async def export_pdf(payload: ExportPdfRequest) -> StreamingResponse:
    buffer = BytesIO()
    normalized_content = _normalize_resume_export_text(payload.content)

    # ATS-friendly resume export: single-column, parser-safe, and no one-page forcing.
    reserved_header_height = 1.12 * inch
    import reportlab.lib.pagesizes
    document = SimpleDocTemplate(
        buffer,
        pagesize=reportlab.lib.pagesizes.letter,
        leftMargin=0.42 * inch,
        rightMargin=0.42 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.5 * inch,
        title=payload.title,
    )

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.8,
        leading=11.6,
        textColor=colors.HexColor("#111827"),
        spaceAfter=2,
    )
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=10.8,
        leading=13,
        spaceBefore=3,
        spaceAfter=2,
    )
    bullet_style = ParagraphStyle(
        "BulletStyle",
        parent=body_style,
        leftIndent=9,
        bulletIndent=2,
        spaceAfter=0.5,
    )
    name_style = ParagraphStyle(
        "NameStyle",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=22,
        spaceAfter=4,
    )
    summary_style = ParagraphStyle(
        "SummaryStyle",
        parent=body_style,
        fontSize=9.5,
        leading=11.4,
        spaceAfter=1.5,
        spaceBefore=0,
    )

    header_lines: list[str] = []
    summary_lines: list[str] = []
    body_lines: list[str] = []
    in_header = True
    in_summary = False

    for raw_line in normalized_content.split("\n"):
        line = raw_line.strip()

        if _should_skip_line(line):
            continue
        if line in {"--", "---", "----"}:
            continue

        is_summary = _is_summary_heading(line)
        heading = _extract_heading_text(line)

        # A summary heading always ends the header phase.
        # Any other heading only ends the header phase after at least one contact line
        # has already been collected — otherwise an all-caps name on the first line
        # (detected as a heading) would leave header_lines empty.
        if in_header and (is_summary or (heading and len(header_lines) >= 1)):
            in_header = False

        if in_header:
            header_lines.append(line)
            continue

        if is_summary:
            in_summary = True
            # include the heading in summary_lines so it renders styled
            summary_lines.append(line)
            continue

        if heading and in_summary:
            in_summary = False

        if in_summary:
            summary_lines.append(line)
            continue

        body_lines.append(line)

    def _build_flowables(lines: list[str], allow_name_emphasis: bool, *, paragraph_style: ParagraphStyle) -> list:
        target_story: list = []
        rendered_name = False

        for line in lines:
            if not line:
                target_story.append(Spacer(1, 2))
                continue

            if allow_name_emphasis and not rendered_name and _looks_like_name_line(line):
                target_story.append(Paragraph(_markdown_inline_to_reportlab(line), name_style))
                rendered_name = True
                continue

            heading_match = re.match(r"^#{1,6}\s*(.+)$", line)
            if heading_match:
                target_story.append(Paragraph(_markdown_inline_to_reportlab(heading_match.group(1).strip()), heading_style))
                continue

            detected_heading = _extract_heading_text(line)
            if detected_heading and detected_heading == re.sub(r"[*_#`]", "", line).strip():
                target_story.append(Paragraph(_markdown_inline_to_reportlab(detected_heading), heading_style))
                continue

            is_bullet = line.startswith("- ") or line.startswith("* ")
            if is_bullet:
                bullet_text = line[2:].strip()
                target_story.append(
                    Paragraph(_markdown_inline_to_reportlab(bullet_text), bullet_style, bulletText="•")
                )
                continue

            target_story.append(Paragraph(_markdown_inline_to_reportlab(line), paragraph_style))

        return target_story

    summary_section_flowables = _build_flowables(
        summary_lines,
        allow_name_emphasis=False,
        paragraph_style=summary_style,
    )

    # Split body_lines at the PROJECTS section to insert a page break after it
    projects_idx = None
    for idx, line in enumerate(body_lines):
        if _extract_heading_text(line) and _extract_heading_text(line).strip().upper() == "PROJECTS":
            projects_idx = idx
            break

    # Find the end of the PROJECTS section (next heading or end of body_lines)
    page1_lines = body_lines
    page2_lines = []
    if projects_idx is not None:
        # Find next heading after PROJECTS
        end_projects_idx = None
        for idx in range(projects_idx + 1, len(body_lines)):
            if _extract_heading_text(body_lines[idx]):
                end_projects_idx = idx
                break
        if end_projects_idx is None:
            end_projects_idx = len(body_lines)
        page1_lines = body_lines[:end_projects_idx]
        page2_lines = body_lines[end_projects_idx:]


    # --- Dynamic font scaling for first page ---
    from reportlab.platypus import Frame, PageTemplate, BaseDocTemplate
    from reportlab.lib.pagesizes import letter
    import copy

    def build_scaled_flowables(font_size: float, lines: list[str]) -> list:
        scaled_body_style = copy.deepcopy(body_style)
        scaled_heading_style = copy.deepcopy(heading_style)
        scaled_bullet_style = copy.deepcopy(bullet_style)
        scaled_name_style = copy.deepcopy(name_style)
        scaled_summary_style = copy.deepcopy(summary_style)
        # Scale all font sizes proportionally
        scale = font_size / body_style.fontSize
        scaled_body_style.fontSize = font_size
        scaled_body_style.leading = int(body_style.leading * scale)
        scaled_heading_style.fontSize = max(9, int(heading_style.fontSize * scale))
        scaled_heading_style.leading = int(heading_style.leading * scale)
        scaled_bullet_style.fontSize = font_size
        scaled_bullet_style.leading = int(bullet_style.leading * scale) if hasattr(bullet_style, 'leading') else int(body_style.leading * scale)
        scaled_name_style.fontSize = int(name_style.fontSize * scale)
        scaled_name_style.leading = int(name_style.leading * scale)
        scaled_summary_style.fontSize = max(8, int(summary_style.fontSize * scale))
        scaled_summary_style.leading = int(summary_style.leading * scale)
        return _build_flowables(
            lines,
            allow_name_emphasis=False,
            paragraph_style=scaled_body_style,
        )

    # Try to fit all page1_lines on one page by scaling font size down if needed
    min_font_size = 7.5
    max_font_size = body_style.fontSize
    test_font_size = max_font_size
    fitted = False
    page1_flowables = None
    while test_font_size >= min_font_size:
        test_flowables = build_scaled_flowables(test_font_size, page1_lines)
        # Create a test doc to measure height
        test_buffer = BytesIO()
        test_doc = SimpleDocTemplate(
            test_buffer,
            pagesize=letter,
            leftMargin=document.leftMargin,
            rightMargin=document.rightMargin,
            topMargin=document.topMargin + reserved_header_height,
            bottomMargin=document.bottomMargin,
        )
        # Only measure the first page
        try:
            test_doc.build(test_flowables[:], onFirstPage=None)
            fitted = True
            page1_flowables = test_flowables
            break
        except Exception:
            test_font_size -= 0.5
    if not fitted:
        # Fallback: use min font size
        page1_flowables = build_scaled_flowables(min_font_size, page1_lines)

    # Page 2 and later: normal font size
    page2_flowables = _build_flowables(
        page2_lines,
        allow_name_emphasis=False,
        paragraph_style=body_style,
    )

    header_name = ""
    header_subtitle = ""
    header_details: list[str] = []

    for line in header_lines:
        if not line:
            continue
        clean = _strip_markdown_for_header(line)
        if not clean:
            continue
        if not header_name and _looks_like_name_line(line):
            header_name = clean
            continue
        if header_name and not header_subtitle:
            header_subtitle = clean
            continue
        header_details.append(clean)

    def draw_first_page_header(canv, doc) -> None:
        if not header_name and not header_subtitle and not header_details:
            return

        canv.saveState()
        x = doc.leftMargin
        import reportlab.lib.pagesizes
        y = reportlab.lib.pagesizes.letter[1] - 0.56 * inch

        if header_name:
            canv.setFont("Helvetica-Bold", 17)
            canv.setFillColor(colors.HexColor("#111827"))
            canv.drawString(x, y, header_name)
            y -= 0.28 * inch

        if header_subtitle:
            canv.setFont("Helvetica-Bold", 10.5)
            canv.drawString(x, y, header_subtitle)
            y -= 0.24 * inch

        canv.setFont("Helvetica", 10)
        for detail in header_details[:3]:
            canv.drawString(x, y, detail)
            y -= 0.23 * inch

        canv.restoreState()

    # Reserve header space on page 1 only; later pages should use the normal top margin.
    story: list = []
    story.append(Spacer(1, reserved_header_height))

    # Build story with optional negative spacer to close gap between header and summary.
    if summary_section_flowables:
        story.append(Spacer(1, -24))  # Negative spacer pulls summary closer to header
        story.extend(summary_section_flowables)
        story.append(Spacer(1, 8))

    story.extend(page1_flowables)
    if page2_flowables:
        from reportlab.platypus import PageBreak
        story.append(PageBreak())
        story.extend(page2_flowables)

    document.build(story, onFirstPage=draw_first_page_header)
    buffer.seek(0)

    file_name = _normalize_filename(payload.title)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={file_name}.pdf"},
    )


@router.post("/export/pdf/cover-letter")
async def export_cover_letter_pdf(payload: ExportPdfRequest) -> StreamingResponse:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
        title=payload.title,
    )

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#111827"),
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        spaceBefore=2,
        spaceAfter=2,
    )

    story: list = []
    lines = [line.rstrip() for line in payload.content.split("\n")]

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    previous_was_blank = False
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if not previous_was_blank:
                story.append(Spacer(1, 3))
            previous_was_blank = True
            continue

        previous_was_blank = False

        heading_match = re.match(r"^#{1,6}\s*(.+)$", line)
        if heading_match:
            story.append(Paragraph(_markdown_inline_to_reportlab(heading_match.group(1).strip()), heading_style))
        elif line.isupper() and len(line) > 3:
            story.append(Paragraph(_markdown_inline_to_reportlab(line), heading_style))
        else:
            story.append(Paragraph(_markdown_inline_to_reportlab(line), body_style))

    document.build(story)
    buffer.seek(0)

    file_name = _normalize_filename(payload.title)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={file_name}.pdf"},
    )
