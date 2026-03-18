from app.schemas.models import SkillProject
from app.services.llm_provider import llm_provider
from app.services.mcp.registry import MCP_TOOLS
from app.services.prompt_modules.ats import build_ats_prompt
from app.services.prompt_modules.cover_letter import build_cover_letter_prompt
from app.services.prompt_modules.rewriter import build_rewrite_prompt
from app.services.prompt_modules.skill_gap import build_skill_gap_prompt


class AgentOrchestrator:
    async def recruiter_rewrite(self, resume_text: str, job_description: str, role: str, industry: str) -> str:
        system, user = build_rewrite_prompt(resume_text, job_description, role, industry)
        return await llm_provider.generate(system, user)

    async def ats_optimize(self, resume_text: str, job_description: str, role: str, year: int | None) -> str:
        system, user = build_ats_prompt(resume_text, job_description, role, year)
        return await llm_provider.generate(system, user)

    async def cover_letter(
        self,
        resume_text: str,
        job_description: str,
        role: str,
        company: str | None,
    ) -> str:
        system, user = build_cover_letter_prompt(resume_text, job_description, role, company)
        return await llm_provider.generate(system, user)

    async def skill_gap(self, resume_text: str, job_description: str, role: str) -> tuple[str, list[dict]]:
        system, user = build_skill_gap_prompt(resume_text, job_description, role)
        summary = await llm_provider.generate(system, user)

        role_skills = MCP_TOOLS["role_skills.lookup"]({"role": role}).get("skills", [])
        gaps = []
        for skill in role_skills[:3]:
            resources = MCP_TOOLS["learning.free_resources"]({"skill": skill}).get("resources", [])
            gaps.append(
                {
                    "skill": skill,
                    "why_it_matters": f"Frequently requested in {role} postings and important for delivery impact.",
                    "free_resources": resources,
                }
            )
        return summary, gaps

    async def skill_to_projects(self, role: str, skills: list[str]) -> list[SkillProject]:
        projects: list[SkillProject] = []
        for skill in skills[:3]:
            template = MCP_TOOLS["projects.templates"]({"skill": skill, "role": role})["templates"][0]
            bullet = MCP_TOOLS["resume.format_bullet"](
                {"project_title": template["title"], "outcome": f"showcased practical {skill} capability"}
            )["bullet"]
            projects.append(
                SkillProject(
                    title=template["title"],
                    one_day_scope=template["scope"],
                    tasks=template["tasks"],
                    acceptance_criteria=[
                        "Core feature is functional",
                        "Project has clear README",
                        "Demo output can be shared in portfolio",
                    ],
                    resume_bullet=bullet,
                )
            )
        return projects


orchestrator = AgentOrchestrator()
