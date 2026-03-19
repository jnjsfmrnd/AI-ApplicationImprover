from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    resume_text: str
    source_filename: str | None = None


class JDRequest(BaseModel):
    job_description: str = Field(min_length=20)
    role: str | None = Field(default=None, min_length=2)
    industry: str | None = Field(default=None, min_length=2)
    company: str | None = None
    year: int | None = None


class GenerationInput(BaseModel):
    resume_text: str = Field(min_length=20)
    job_description: str = Field(min_length=20)
    role: str | None = Field(default=None, min_length=2)
    industry: str | None = Field(default=None, min_length=2)
    company: str | None = None
    year: int | None = None


class TailoredResumeRequest(GenerationInput):
    max_gap_skills: int = Field(default=3, ge=1, le=5)


class JobContextRequest(BaseModel):
    job_description: str = Field(min_length=20)


class JobContextResponse(BaseModel):
    role: str
    industry: str | None = None
    company: str | None = None
    year: int | None = None
    confidence: float = Field(ge=0, le=1, default=0)


class GeneratedArtifact(BaseModel):
    content: str
    model: str
    mode: str


class SkillGapItem(BaseModel):
    skill: str
    why_it_matters: str
    additional_notes: str = ""
    free_resources: list[str]


class SkillGapResponse(BaseModel):
    summary: str
    gaps: list[SkillGapItem]
    model: str


class SkillProject(BaseModel):
    title: str
    one_day_scope: str
    skills_covered: list[str]
    tasks: list[str]
    acceptance_criteria: list[str]
    resume_bullet: str
    resume_bullets: list[str]


class SkillProjectResponse(BaseModel):
    projects: list[SkillProject]
    model: str


class ResumeVariant(BaseModel):
    content: str
    stage: str
    variant: str


class TailoredResumeResponse(BaseModel):
    context: JobContextResponse
    skill_gap_summary: str
    skill_gaps: list[SkillGapItem]
    skill_projects: list[SkillProject]
    cover_letter: str
    truthful_rewrite: ResumeVariant
    project_enhanced_rewrite: ResumeVariant
    truthful_ats: ResumeVariant
    project_enhanced_ats: ResumeVariant
    default_final_variant: str
    model: str


class ExportPdfRequest(BaseModel):
    title: str = "Generated Document"
    content: str = Field(min_length=1)
