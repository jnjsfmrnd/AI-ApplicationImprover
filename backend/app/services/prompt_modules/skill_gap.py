def build_skill_gap_prompt(resume_text: str, job_description: str, role: str) -> tuple[str, str]:
    system = (
        "You identify the highest-value skill gaps between a candidate resume and a job description. "
        "Return strict JSON only."
    )
    user = (
        f"Role: {role}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Resume:\n{resume_text}\n\n"
        "Return JSON with this shape:\n"
        "{\n"
        '  "summary": "2-4 sentence summary",\n'
        '  "gaps": [\n'
        "    {\n"
        '      "skill": "missing skill name",\n'
        '      "why_it_matters": "why the recruiter cares",\n'
        '      "related_experience": "similar experience from the resume or empty string",\n'
        '      "priority": 1\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Prioritize the 3 most important gaps for the target role.\n"
        "- If the candidate has adjacent experience, describe it in related_experience.\n"
        "- Only include skills that are requested or strongly implied by the JD.\n"
        "- Output JSON only with no markdown fences."
    )
    return system, user
