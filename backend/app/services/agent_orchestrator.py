import asyncio
import json
import re
from datetime import date

from app.schemas.models import SkillProject
from app.services.llm_provider import llm_provider
from app.services.mcp.registry import MCP_TOOLS
from app.services.prompt_modules.ats import build_ats_prompt
from app.services.prompt_modules.cover_letter import build_cover_letter_prompt
from app.services.prompt_modules.rewriter import build_rewrite_prompt
from app.services.prompt_modules.skill_gap import build_skill_gap_prompt
from app.services.prompt_modules.skill_projects import build_skill_project_prompt


class AgentOrchestrator:
    def _build_adaptation_note(self, skill: str, related_experience: str) -> str:
        clean_skill = skill.strip()
        clean_experience = related_experience.strip().rstrip(".")
        if not clean_skill or not clean_experience:
            return ""
        return (
            f"{clean_experience}. This experience transfers directly to {clean_skill} and supports a fast ramp to production-level execution."
        )

    def _replace_cover_letter_date_placeholder(self, text: str) -> str:
        today = date.today()
        formatted_today = f"{today:%B} {today.day}, {today:%Y}"
        return re.sub(r"\[date\]", formatted_today, text, flags=re.IGNORECASE)

    def _extract_json_object(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}

    def _normalize_gap_items(
        self,
        resume_text: str,
        role: str,
        parsed_output: dict,
        max_gap_skills: int,
    ) -> tuple[str, list[dict]]:
        summary = parsed_output.get("summary") if isinstance(parsed_output.get("summary"), str) else ""
        parsed_gaps = parsed_output.get("gaps") if isinstance(parsed_output.get("gaps"), list) else []
        role_skills = MCP_TOOLS["role_skills.lookup"]({"role": role}).get("skills", [])
        resume_lower = resume_text.lower()

        normalized: list[dict] = []
        seen_skills: set[str] = set()

        for raw_gap in parsed_gaps:
            if not isinstance(raw_gap, dict):
                continue
            skill = raw_gap.get("skill") if isinstance(raw_gap.get("skill"), str) else ""
            why_it_matters = raw_gap.get("why_it_matters") if isinstance(raw_gap.get("why_it_matters"), str) else ""
            related_experience = (
                raw_gap.get("related_experience") if isinstance(raw_gap.get("related_experience"), str) else ""
            )
            priority = raw_gap.get("priority") if isinstance(raw_gap.get("priority"), int) else 999

            skill_name = skill.strip()
            if not skill_name:
                continue

            normalized_key = skill_name.lower()
            if normalized_key in seen_skills:
                continue

            seen_skills.add(normalized_key)
            normalized.append(
                {
                    "skill": skill_name,
                    "why_it_matters": why_it_matters.strip()
                    or f"Frequently requested in {role} postings and important for delivery impact.",
                    "related_experience": related_experience.strip(),
                    "priority": priority,
                }
            )

        if not normalized:
            for priority, skill in enumerate(role_skills, start=1):
                if skill.lower() in resume_lower:
                    continue
                normalized.append(
                    {
                        "skill": skill,
                        "why_it_matters": f"Frequently requested in {role} postings and important for delivery impact.",
                        "related_experience": "",
                        "priority": priority,
                    }
                )
                if len(normalized) >= max_gap_skills:
                    break

        normalized.sort(key=lambda item: item.get("priority", 999))

        gaps: list[dict] = []
        for item in normalized[:max_gap_skills]:
            resources_payload = MCP_TOOLS["learning.free_resources"]({"skill": item["skill"]})
            resources = [] if resources_payload.get("is_fallback") else resources_payload.get("resources", [])
            additional_notes = ""
            if item["related_experience"]:
                additional_notes = self._build_adaptation_note(item["skill"], item["related_experience"])
            gaps.append(
                {
                    "skill": item["skill"],
                    "why_it_matters": item["why_it_matters"],
                    "additional_notes": additional_notes,
                    "free_resources": resources,
                }
            )

        if not summary:
            if gaps:
                top_skills = ", ".join(item["skill"] for item in gaps)
                summary = (
                    f"Top gaps for {role}: {top_skills}. Emphasize adjacent experience honestly, "
                    "then add targeted project work only in the aggressive resume variant."
                )
            else:
                summary = f"No major skill gaps were detected for {role}; focus on stronger positioning and ATS phrasing."

        return summary, gaps

    def _format_skill_gap_context(self, summary: str, gaps: list[dict]) -> str:
        lines = [summary.strip()]
        for item in gaps:
            line = f"- {item['skill']}: {item['why_it_matters']}"
            if isinstance(item.get("additional_notes"), str) and item["additional_notes"].strip():
                line = f"{line} ({item['additional_notes'].strip()})"
            lines.append(line)
        return "\n".join(line for line in lines if line).strip()

    def _format_project_context(self, projects: list[SkillProject]) -> str:
        if not projects:
            return ""

        blocks: list[str] = []
        for project in projects:
            tasks = "\n".join(f"- {task}" for task in project.tasks)
            acceptance = "\n".join(f"- {criterion}" for criterion in project.acceptance_criteria)
            bullets = "\n".join(f"- {bullet}" for bullet in project.resume_bullets)
            blocks.append(
                "\n".join(
                    [
                        f"Project Title: {project.title}",
                        f"Scope: {project.one_day_scope}",
                        f"Skills Covered: {', '.join(project.skills_covered)}",
                        "Tasks:",
                        tasks,
                        "Acceptance Criteria:",
                        acceptance,
                        "Resume Bullets:",
                        bullets,
                    ]
                )
            )
        return "\n\n".join(blocks)

    def _inject_projects_into_resume(self, resume_text: str, projects: list[SkillProject]) -> str:
        if not projects:
            return resume_text

        project_lines = ["Targeted Projects"]
        for project in projects:
            project_lines.append(project.title)
            project_lines.append(project.one_day_scope)
            project_lines.append(f"Skills Covered: {', '.join(project.skills_covered)}")
            project_lines.append(project.resume_bullet)
        return f"{resume_text.strip()}\n\n" + "\n".join(project_lines).strip()

    def _build_recruiter_ready_bullets(self, title: str, role: str, skills_covered: list[str]) -> list[str]:
        coverage_text = ", ".join(skills_covered[:3])
        bullets = [
            f"Built {title} to simulate core {role} work, combining {coverage_text} into one deliverable that produced a portfolio-ready artifact and demonstrated role-aligned execution."
        ]
        if skills_covered:
            bullets.append(
                f"Delivered a focused project that translated {coverage_text} into a practical workflow, showing how adjacent experience could be applied to the target role's highest-priority requirements."
            )
        bullets.append(
            f"Created documentation, demo output, and validation steps for {title}, making the work easy for a recruiter or hiring manager to evaluate as relevant portfolio evidence."
        )
        return bullets[:3]

    def _build_project_from_template(self, role: str, skills: list[str]) -> SkillProject:
        primary_skill = skills[0] if skills else "role-aligned delivery"
        secondary_skills = [skill for skill in skills[1:3] if skill]
        template = MCP_TOOLS["projects.templates"]({"skill": primary_skill, "role": role})["templates"][0]
        title_suffix = f" + {' + '.join(secondary_skills)}" if secondary_skills else ""
        title = f"{template['title']}{title_suffix}"
        scope = template["scope"]
        if secondary_skills:
            scope = (
                f"{template['scope']} Extend it to also demonstrate {', '.join(secondary_skills)} in the same workflow."
            )
        bullets = self._build_recruiter_ready_bullets(title, role, skills[:3])
        return SkillProject(
            title=title,
            one_day_scope=scope,
            skills_covered=skills[:3],
            tasks=template["tasks"],
            acceptance_criteria=[
                "Core feature is functional",
                "Project has clear README",
                "Demo output can be shared in portfolio",
            ],
            resume_bullet=bullets[0],
            resume_bullets=bullets,
        )

    async def _build_capstone_project(
        self,
        *,
        role: str,
        industry: str | None,
        job_description: str,
        gaps: list[dict],
    ) -> SkillProject:
        system, user = build_skill_project_prompt(
            role=role,
            industry=industry,
            job_description=job_description,
            gaps=gaps,
        )
        raw_output = await llm_provider.generate(system, user)
        parsed_output = self._extract_json_object(raw_output)

        title = parsed_output.get("title") if isinstance(parsed_output.get("title"), str) else ""
        one_day_scope = parsed_output.get("one_day_scope") if isinstance(parsed_output.get("one_day_scope"), str) else ""
        skills_covered = parsed_output.get("skills_covered") if isinstance(parsed_output.get("skills_covered"), list) else []
        tasks = parsed_output.get("tasks") if isinstance(parsed_output.get("tasks"), list) else []
        acceptance_criteria = (
            parsed_output.get("acceptance_criteria")
            if isinstance(parsed_output.get("acceptance_criteria"), list)
            else []
        )
        resume_bullets = parsed_output.get("resume_bullets") if isinstance(parsed_output.get("resume_bullets"), list) else []

        target_skills = [item["skill"] for item in gaps[:4]]
        normalized_covered_skills = [item.strip() for item in skills_covered if isinstance(item, str) and item.strip()]
        normalized_tasks = [item.strip() for item in tasks if isinstance(item, str) and item.strip()]
        normalized_criteria = [item.strip() for item in acceptance_criteria if isinstance(item, str) and item.strip()]
        normalized_bullets = [item.strip() for item in resume_bullets if isinstance(item, str) and item.strip()]

        if not title.strip() or not one_day_scope.strip() or not normalized_tasks or not normalized_criteria:
            return self._build_project_from_template(role, target_skills)

        if not normalized_covered_skills:
            normalized_covered_skills = target_skills

        if not normalized_bullets:
            normalized_bullets = self._build_recruiter_ready_bullets(
                title.strip(),
                role,
                normalized_covered_skills,
            )

        return SkillProject(
            title=title.strip(),
            one_day_scope=one_day_scope.strip(),
            skills_covered=normalized_covered_skills[:4],
            tasks=normalized_tasks[:5],
            acceptance_criteria=normalized_criteria[:4],
            resume_bullet=normalized_bullets[0],
            resume_bullets=normalized_bullets[:3],
        )

    def _extract_heading_set(self, text: str) -> set[str]:
        headings: set[str] = set()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            heading_match = re.match(r"^#{1,6}\s*(.+)$", line)
            if heading_match:
                heading = heading_match.group(1).strip().lower()
                headings.add(heading)
                continue

            plain = re.sub(r"[*_`]+", "", line).strip()
            letters = [char for char in plain if char.isalpha()]
            if letters and sum(1 for char in letters if char.isupper()) / len(letters) >= 0.85 and len(plain.split()) <= 6:
                headings.add(plain.lower())

        return headings

    def _guard_truthful_ats_output(self, source_resume: str, optimized_resume: str) -> str:
        source_headings = self._extract_heading_set(source_resume)
        optimized_headings = self._extract_heading_set(optimized_resume)
        if optimized_headings - source_headings:
            return source_resume
        return optimized_resume

    async def recruiter_rewrite(
        self,
        resume_text: str,
        job_description: str,
        role: str,
        industry: str | None,
        *,
        mode: str = "truthful",
        skill_gap_context: str | None = None,
        project_context: str | None = None,
    ) -> str:
        system, user = build_rewrite_prompt(
            resume_text,
            job_description,
            role,
            industry,
            mode=mode,
            skill_gap_context=skill_gap_context,
            project_context=project_context,
        )
        return await llm_provider.generate(system, user)

    async def ats_optimize(
        self,
        resume_text: str,
        job_description: str,
        role: str,
        year: int | None,
        *,
        variant_label: str = "truthful",
    ) -> str:
        system, user = build_ats_prompt(
            resume_text,
            job_description,
            role,
            year,
            variant_label=variant_label,
        )
        return await llm_provider.generate(system, user)

    async def cover_letter(
        self,
        resume_text: str,
        job_description: str,
        role: str,
        company: str | None,
    ) -> str:
        system, user = build_cover_letter_prompt(resume_text, job_description, role, company)
        generated = await llm_provider.generate(system, user)
        return self._replace_cover_letter_date_placeholder(generated)

    async def skill_gap(
        self,
        resume_text: str,
        job_description: str,
        role: str,
        max_gap_skills: int = 3,
    ) -> tuple[str, list[dict]]:
        system, user = build_skill_gap_prompt(resume_text, job_description, role)
        raw_output = await llm_provider.generate(system, user)
        parsed_output = self._extract_json_object(raw_output)
        return self._normalize_gap_items(resume_text, role, parsed_output, max_gap_skills)

    async def skill_to_projects(
        self,
        role: str,
        skills: list[str],
        *,
        job_description: str | None = None,
        industry: str | None = None,
        gaps: list[dict] | None = None,
    ) -> list[SkillProject]:
        if job_description and gaps:
            return [
                await self._build_capstone_project(
                    role=role,
                    industry=industry,
                    job_description=job_description,
                    gaps=gaps,
                )
            ]

        return [self._build_project_from_template(role, skills[:3])]

    async def generate_tailored_resume_pipeline(
        self,
        resume_text: str,
        job_description: str,
        role: str,
        industry: str | None,
        year: int | None,
        *,
        company: str | None = None,
        max_gap_skills: int = 3,
    ) -> dict:
        skill_gap_summary, gaps = await self.skill_gap(
            resume_text,
            job_description,
            role,
            max_gap_skills=max_gap_skills,
        )
        missing_skills = [item["skill"] for item in gaps]
        projects = await self.skill_to_projects(
            role=role,
            skills=missing_skills,
            job_description=job_description,
            industry=industry,
            gaps=gaps,
        )

        skill_gap_context = self._format_skill_gap_context(skill_gap_summary, gaps)
        project_context = self._format_project_context(projects)
        project_resume_text = self._inject_projects_into_resume(resume_text, projects)

        # Phase 3: rewrites and cover letter are independent — run concurrently
        truthful_rewrite, project_enhanced_rewrite, cover_letter_text = await asyncio.gather(
            self.recruiter_rewrite(
                resume_text,
                job_description,
                role,
                industry,
                mode="truthful",
                skill_gap_context=skill_gap_context,
            ),
            self.recruiter_rewrite(
                project_resume_text,
                job_description,
                role,
                industry,
                mode="project_enhanced",
                skill_gap_context=skill_gap_context,
                project_context=project_context,
            ),
            self.cover_letter(resume_text, job_description, role, company),
        )

        # Phase 4: both ATS passes are independent — run concurrently
        truthful_ats_raw, project_enhanced_ats = await asyncio.gather(
            self.ats_optimize(
                truthful_rewrite,
                job_description,
                role,
                year,
                variant_label="truthful",
            ),
            self.ats_optimize(
                project_enhanced_rewrite,
                job_description,
                role,
                year,
                variant_label="project_enhanced",
            ),
        )
        truthful_ats = self._guard_truthful_ats_output(truthful_rewrite, truthful_ats_raw)

        return {
            "skill_gap_summary": skill_gap_summary,
            "skill_gaps": gaps,
            "skill_projects": projects,
            "cover_letter": cover_letter_text,
            "truthful_rewrite": truthful_rewrite,
            "project_enhanced_rewrite": project_enhanced_rewrite,
            "truthful_ats": truthful_ats,
            "project_enhanced_ats": project_enhanced_ats,
            "default_final_variant": "truthful_ats",
        }


orchestrator = AgentOrchestrator()
