def build_cover_letter_prompt(
    resume_text: str,
    job_description: str,
    role: str,
    company: str | None,
) -> tuple[str, str]:
    system = "You write concise, personalized, professional cover letters."
    company_line = f"Company: {company}\n" if company else ""
    user = (
        f"Role: {role}\n{company_line}\n"
        f"Job Description:\n{job_description}\n\n"
        f"Candidate Resume:\n{resume_text}\n\n"
        "Write a tailored cover letter emphasizing unique value and motivation. "
        "If company is not explicitly known, avoid placeholder names and write naturally without one."
    )
    return system, user
