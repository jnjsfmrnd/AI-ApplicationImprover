def build_rewrite_prompt(
    resume_text: str,
    job_description: str,
    role: str,
    industry: str | None,
    *,
    mode: str = "truthful",
    skill_gap_context: str | None = None,
    project_context: str | None = None,
) -> tuple[str, str]:
    mode_instructions = (
        "Stay strictly truthful to the candidate's provided experience. Do not invent completed work."
        if mode == "truthful"
        else "Use the supplied project context as optional additional resume material while keeping all other claims grounded and recruiter-friendly."
    )
    system = (
        "You are a top recruiter. Rewrite resumes with quantified impact, clear achievements, "
        "role-specific language, and clean section structure. "
        f"{mode_instructions}"
    )
    user = (
        f"Industry: {industry or 'General'}\nRole: {role}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Candidate Resume:\n{resume_text}\n\n"
        f"Skill Gap Context:\n{skill_gap_context or 'None provided'}\n\n"
        f"Project Context:\n{project_context or 'Do not add hypothetical projects'}\n\n"
        "Output a polished resume draft with ATS-friendly section headings and stronger achievement bullets. "
        "Emphasize requirement match, adjacent transferable experience, and recruiter-readable phrasing. "
        "If a catch-all section is needed, use the heading 'ADDITIONAL INFORMATION' only."
    )
    return system, user
