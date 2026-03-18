def get_role_skills(payload: dict) -> dict:
    role = payload.get("role", "generalist")
    common = ["communication", "problem solving", "collaboration"]
    role_map = {
        "software engineer": ["python", "apis", "testing", "sql"],
        "data analyst": ["sql", "excel", "dashboards", "statistics"],
        "ai engineer": ["python", "llm orchestration", "prompt design", "evaluation"],
    }
    return {"role": role, "skills": role_map.get(role.lower(), common + ["domain expertise"]) }


def get_free_resources(payload: dict) -> dict:
    skill = payload.get("skill", "general skill")
    return {
        "skill": skill,
        "resources": [
            f"YouTube crash course for {skill}",
            f"FreeCodeCamp module on {skill}",
            f"Official docs practice guide for {skill}",
        ],
    }


def get_project_templates(payload: dict) -> dict:
    skill = payload.get("skill", "core skill")
    role = payload.get("role", "target role")
    return {
        "skill": skill,
        "role": role,
        "templates": [
            {
                "title": f"1-Day {skill.title()} Mini Project",
                "scope": f"Build a focused {skill} project aligned to {role} responsibilities.",
                "tasks": [
                    "Set up project scaffold",
                    "Implement one core feature",
                    "Add basic validation/tests",
                    "Write concise README + demo notes",
                ],
            }
        ],
    }


def format_resume_bullet(payload: dict) -> dict:
    project_title = payload.get("project_title", "Project")
    outcome = payload.get("outcome", "delivered a usable MVP")
    return {
        "bullet": f"Built {project_title} in one day and {outcome}, demonstrating rapid execution and role-aligned skill growth."
    }
