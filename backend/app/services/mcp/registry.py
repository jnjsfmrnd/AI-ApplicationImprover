from app.services.mcp.tools import (
    format_resume_bullet,
    get_free_resources,
    get_project_templates,
    get_role_skills,
)


MCP_TOOLS = {
    "role_skills.lookup": get_role_skills,
    "learning.free_resources": get_free_resources,
    "projects.templates": get_project_templates,
    "resume.format_bullet": format_resume_bullet,
}
