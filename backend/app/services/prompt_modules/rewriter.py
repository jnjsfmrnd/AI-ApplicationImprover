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
    summary_instruction = (
        "Always include a 'PROFESSIONAL SUMMARY' section near the top of the output (right after contact/header lines). "
        "Write 2-4 concise lines tailored to the job description using only truthful evidence from the resume and provided context. "
        "Prioritize JD-aligned keywords that are actually supported by the candidate's background."
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
    mode_instructions = (
        "Stay strictly truthful to the candidate's provided experience. Do not invent completed work. Preserve existing personal or portfolio projects whenever space permits, prioritizing them over lower-impact filler lines if trimming is needed."
        if mode == "truthful"
        else "Use the supplied project context as optional additional resume material while keeping all other claims grounded and recruiter-friendly. Include personal or portfolio projects whenever space permits and trim less relevant or lower-impact content first if needed to fit length."
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
        f"{summary_instruction} "
        f"{section_order_instruction} "
        "Emphasize requirement match, adjacent transferable experience, and recruiter-readable phrasing. "
        "Try to keep personal or portfolio projects in the document when there is room, especially if they map to the JD's required skills. "
        "If a catch-all section is needed, use the heading 'ADDITIONAL INFORMATION' only."
    )
    return system, user
