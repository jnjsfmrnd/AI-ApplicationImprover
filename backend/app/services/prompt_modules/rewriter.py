def build_rewrite_prompt(resume_text: str, job_description: str, role: str, industry: str) -> tuple[str, str]:
    system = (
        "You are a top recruiter. Rewrite resumes with quantified impact, clear achievements, and"
        " role-specific language while staying truthful to provided experience."
    )
    user = (
        f"Industry: {industry}\nRole: {role}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Candidate Resume:\n{resume_text}\n\n"
        "Output a polished resume draft with clear sections and stronger achievement bullets."
    )
    return system, user
