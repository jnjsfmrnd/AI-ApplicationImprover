def build_cover_letter_prompt(
    resume_text: str,
    job_description: str,
    role: str,
    company: str | None,
) -> tuple[str, str]:
    system = "You write concise, personalized, professional cover letters."
    user = (
        f"Role: {role}\nCompany: {company or 'Target Company'}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Candidate Resume:\n{resume_text}\n\n"
        "Write a tailored cover letter emphasizing unique value and motivation."
    )
    return system, user
