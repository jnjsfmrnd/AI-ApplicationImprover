def build_ats_prompt(resume_text: str, job_description: str, role: str, year: int | None) -> tuple[str, str]:
    year_text = str(year) if year else "current year"
    system = "You optimize resumes for ATS parsing and role-keyword coverage."
    user = (
        f"Role: {role}\nYear Context: {year_text}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Resume:\n{resume_text}\n\n"
        "Return an ATS-optimized resume with relevant skills and phrases from the JD."
    )
    return system, user
