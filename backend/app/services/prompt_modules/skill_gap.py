def build_skill_gap_prompt(resume_text: str, job_description: str, role: str) -> tuple[str, str]:
    system = "You identify skill gaps between resume and role requirements and suggest free resources."
    user = (
        f"Role: {role}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Resume:\n{resume_text}\n\n"
        "Return: (1) short summary, (2) list of missing skills, (3) why each matters,"
        " (4) free learning resources per skill."
    )
    return system, user
