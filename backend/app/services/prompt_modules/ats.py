def build_ats_prompt(
    resume_text: str,
    job_description: str,
    role: str,
    year: int | None,
    *,
    variant_label: str = "truthful",
) -> tuple[str, str]:
    year_text = str(year) if year else "current year"
    variant_instruction = (
        "Do not add new projects, tools, or accomplishments that are not already supported by the resume input. Retain existing personal or portfolio projects whenever space permits, trimming lower-impact content first when compression is required."
        if variant_label == "truthful"
        else "Preserve the supplied project-enhanced content while improving ATS readability and keyword coverage. Keep personal or portfolio projects in the final output whenever there is room, reducing less relevant or lower-impact content before removing projects."
    )
    system = (
        "You optimize resumes for ATS parsing, keyword coverage, and plain, parser-safe formatting. "
        f"{variant_instruction}"
    )
    user = (
        f"Role: {role}\nYear Context: {year_text}\nVariant: {variant_label}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Resume:\n{resume_text}\n\n"
        "Return an ATS-optimized resume with standard section headings, strong JD keyword coverage, "
        "plain text readability, and no tables or decorative formatting. Rephrase existing evidence only. "
        "Use resume-authored voice and never refer to the writer as 'the candidate'. "
        "If you include an extra catch-all section, label it 'ADDITIONAL INFORMATION' only (never 'ADDITIONAL DETAILS' or 'ADDITIONAL NOTES'). "
        "Do not add new roles, projects, certifications, training, communities, or accomplishments that are not already present in the input resume. "
        "When length tradeoffs are needed, prioritize keeping personal/portfolio project evidence that aligns to JD requirements. "
        "If evidence for a JD requirement is missing, leave the gap unfilled instead of fabricating support."
    )
    return system, user
