def build_skill_project_prompt(
    *,
    role: str,
    industry: str | None,
    job_description: str,
    gaps: list[dict],
) -> tuple[str, str]:
    gap_lines = "\n".join(
        f"- {item['skill']}: {item['why_it_matters']}" for item in gaps if item.get("skill") and item.get("why_it_matters")
    )
    system = (
        "You design realistic one-day portfolio capstone projects that help a candidate close multiple job-specific skill gaps at once. "
        "Return strict JSON only."
    )
    user = (
        f"Role: {role}\n"
        f"Industry: {industry or 'General'}\n"
        f"Top Skill Gaps To Cover:\n{gap_lines}\n\n"
        f"Job Description:\n{job_description}\n\n"
        "Return JSON with this shape:\n"
        "{\n"
        '  "title": "project title",\n'
        '  "one_day_scope": "1-2 sentence scope aligned to the JD",\n'
        '  "skills_covered": ["gap 1", "gap 2", "gap 3"],\n'
        '  "tasks": ["task 1", "task 2", "task 3", "task 4"],\n'
        '  "acceptance_criteria": ["criterion 1", "criterion 2", "criterion 3"],\n'
        '  "resume_bullets": ["bullet 1", "bullet 2", "bullet 3"]\n'
        "}\n\n"
        "Rules:\n"
        "- Create one coherent capstone-style project, not one project per skill.\n"
        "- Make the project directly relevant to the pasted JD, not generic to one field.\n"
        "- Cover as many of the listed gaps as possible while staying feasible in one focused day.\n"
        "- Favor business-relevant outputs, demos, dashboards, automations, APIs, analyses, workflows, or tools depending on the role.\n"
        "- Return 2 to 3 distinct resume bullets.\n"
        "- Every bullet should sound recruiter-friendly, past tense, outcome-oriented, and specific enough to look like a real portfolio project rather than a template.\n"
        "- Prefer measurable scope, business value, and stakeholder-facing output in the bullets.\n"
        "- Make the bullets different from each other: one for delivery, one for business impact, one for stakeholder/tool/process fit when possible.\n"
        "- Output JSON only with no markdown fences."
    )
    return system, user