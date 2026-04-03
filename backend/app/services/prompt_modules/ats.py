def build_ats_prompt(
    resume_text: str,
    job_description: str,
    role: str,
    year: int | None,
    *,
    variant_label: str = "truthful",
) -> tuple[str, str]:
    year_text = str(year) if year else "current year"
    summary_instruction = (
        "Always include a 'PROFESSIONAL SUMMARY' section near the top of the resume (immediately after contact/header lines). "
        "Write 2-4 concise lines tailored to the JD, using only truthful evidence already present in the source content. "
        "Use JD-aligned keywords only when they are genuinely supported by the resume."
    )
    core_skills_instruction = (
        "For the CORE SKILLS section: treat the candidate's existing skills list from the resume as the only allowed skill pool - "
        "Output each skills category (such as Languages & Frameworks, Frontend, Backend & Architecture, etc.) as a bullet point, with the category name followed by a colon and the skills as plain text (not bolded). "
        "Do not bold, highlight, italicize, or apply any markdown or special formatting to any category or skill; use plain text only. Output all category names and skills as regular text, not bold, not italic, not underlined, and without any markdown or HTML tags. "
        "At the end of the section, add a bullet for soft skills (e.g., Collaboration, Communication, Problem-solving, Adaptability, Leadership) based on resume evidence. "
        "Keep the original core skills content as-is wherever possible, while reordering within existing groups only when that improves alignment to the job description. "
        "Prioritize the strongest ATS keyword matches for this specific JD using truthful evidence already supported by the resume. "
        "Use the exact skill keywords as written in the JD wherever the candidate's resume already supports them "
        "(e.g. prefer 'Machine Learning' over 'ML' if the JD uses the full form). "
        "If the JD asks for related technologies that are not explicitly listed in the resume but are reasonably supported by adjacent experience or similar tools already used, add them only in a clearly labeled line such as 'Familiar With' or 'Can Adapt Quickly To'. "
        "Those added items must remain separate from the candidate's core proven skills and must never be presented as direct hands-on expertise unless the resume already proves them. "
        "Do not invent unsupported skills, and do not remove existing subsections just to compress the section."
    )
    section_order_instruction = (
        "The very first lines of the output MUST be the candidate's full name (plain text, no heading marker) "
        "followed immediately by their contact details (title, email, phone, LinkedIn, location). "
        "Do NOT begin the output with 'PROFESSIONAL SUMMARY' or any other section heading - contact lines come first, always. "
        "Then use exactly this section order: (1) contact header (name + contact lines, no heading), (2) PROFESSIONAL SUMMARY, "
        "(3) EXPERIENCE (employment history), (4) PROJECTS (personal/portfolio), (5) CORE SKILLS - see core skills rules below, "
        "(6) CERTIFICATIONS, (7) EDUCATION, "
        "(8) ADDITIONAL INFORMATION (only if content exists). "
        "Do not include any section not listed above. Do not swap or reorder these sections. "
        f"{core_skills_instruction}"
    )
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
        f"{summary_instruction}\n"
        f"{section_order_instruction}\n"
        "Return an ATS-optimized resume with standard section headings, strong JD keyword coverage, "
        "plain text readability, and no tables or decorative formatting. Rephrase existing evidence only. "
        "Use resume-authored voice and never refer to the writer as 'the candidate'. "
        "If you include an extra catch-all section, label it 'ADDITIONAL INFORMATION' only (never 'ADDITIONAL DETAILS' or 'ADDITIONAL NOTES'). "
        "Do not add new roles, projects, certifications, training, communities, or accomplishments that are not already present in the input resume. "
        "When length tradeoffs are needed, prioritize keeping personal/portfolio project evidence that aligns to JD requirements. "
        "If evidence for a JD requirement is missing, leave the gap unfilled instead of fabricating support."
    )
    return system, user
