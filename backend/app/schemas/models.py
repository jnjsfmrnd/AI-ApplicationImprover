from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    resume_text: str
    source_filename: str | None = None


class JDRequest(BaseModel):
    job_description: str = Field(min_length=20)
    role: str = Field(min_length=2)
    industry: str = Field(min_length=2)
    company: str | None = None
    year: int | None = None


class GenerationInput(BaseModel):
    resume_text: str = Field(min_length=20)
    job_description: str = Field(min_length=20)
    role: str = Field(min_length=2)
    industry: str = Field(min_length=2)
    company: str | None = None
    year: int | None = None


class GeneratedArtifact(BaseModel):
    content: str
    model: str
    mode: str


class SkillGapItem(BaseModel):
    skill: str
    why_it_matters: str
    free_resources: list[str]


class SkillGapResponse(BaseModel):
    summary: str
    gaps: list[SkillGapItem]
    model: str


class SkillProject(BaseModel):
    title: str
    one_day_scope: str
    tasks: list[str]
    acceptance_criteria: list[str]
    resume_bullet: str


class SkillProjectResponse(BaseModel):
    projects: list[SkillProject]
    model: str


class ExportPdfRequest(BaseModel):
    title: str = "Generated Document"
    content: str = Field(min_length=1)
