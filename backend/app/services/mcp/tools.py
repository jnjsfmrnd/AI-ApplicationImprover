from urllib.parse import quote_plus


RESOURCE_CATALOG = {
    "python": [
        "YouTube: Corey Schafer Python Playlist - https://www.youtube.com/playlist?list=PL-osiE80TeTsqhIuOqKhwlXsIBIdSeYtc",
        "freeCodeCamp: Scientific Computing with Python - https://www.freecodecamp.org/learn/scientific-computing-with-python/",
        "Official docs: Python Tutorial - https://docs.python.org/3/tutorial/",
    ],
    "apis": [
        "YouTube: Build APIs with FastAPI (freeCodeCamp) - https://www.youtube.com/watch?v=0sOvCWFmrtA",
        "freeCodeCamp: Back End Development and APIs - https://www.freecodecamp.org/learn/back-end-development-and-apis/",
        "Official docs: FastAPI Tutorial - https://fastapi.tiangolo.com/tutorial/",
    ],
    "testing": [
        "YouTube: Pytest Tutorial (Corey Schafer) - https://www.youtube.com/watch?v=etosV2IWBF0",
        "freeCodeCamp: QA and Testing with Chai - https://www.freecodecamp.org/learn/quality-assurance/",
        "Official docs: pytest docs - https://docs.pytest.org/",
    ],
    "sql": [
        "YouTube: SQL Full Course (freeCodeCamp) - https://www.youtube.com/watch?v=HXV3zeQKqGY",
        "freeCodeCamp: Relational Database - https://www.freecodecamp.org/learn/relational-database/",
        "Official docs: PostgreSQL Tutorial - https://www.postgresql.org/docs/current/tutorial.html",
    ],
    "typescript": [
        "YouTube: TypeScript Full Course (freeCodeCamp) - https://www.youtube.com/watch?v=30LWjhZzg50",
        "freeCodeCamp: TypeScript curriculum articles - https://www.freecodecamp.org/news/learn-typescript-beginners-guide/",
        "Official docs: TypeScript Handbook - https://www.typescriptlang.org/docs/handbook/intro.html",
    ],
    "llm orchestration": [
        "YouTube: Intro to LangChain (freeCodeCamp) - https://www.youtube.com/watch?v=lG7Uxts9SXs",
        "freeCodeCamp: Building LLM Apps with LangChain (article) - https://www.freecodecamp.org/news/langchain-for-llm-application-development/",
        "Official docs: LangChain Docs - https://python.langchain.com/docs/introduction/",
    ],
    "prompt design": [
        "YouTube: Prompt Engineering Full Course (freeCodeCamp) - https://www.youtube.com/watch?v=_ZvnD73m40o",
        "freeCodeCamp: Prompt Engineering for Developers (article) - https://www.freecodecamp.org/news/prompt-engineering-cheat-sheet-for-gpt-4/",
        "Official docs: OpenAI Prompting Guide - https://platform.openai.com/docs/guides/prompt-engineering",
    ],
    "evaluation": [
        "YouTube: LLM Evaluation Crash Course - https://www.youtube.com/results?search_query=llm+evaluation+crash+course",
        "freeCodeCamp: Evaluation-focused LLM tutorials - https://www.freecodecamp.org/news/search/?query=llm%20evaluation",
        "Official docs: OpenAI Evals Guide - https://platform.openai.com/docs/guides/evals",
    ],
    "communication": [
        "YouTube: Engineering Communication Skills - https://www.youtube.com/results?search_query=engineering+communication+skills",
        "freeCodeCamp: Technical communication resources - https://www.freecodecamp.org/news/search/?query=technical%20communication",
        "Official docs: Google Technical Writing Course - https://developers.google.com/tech-writing",
    ],
    "problem solving": [
        "YouTube: Problem Solving for Software Engineers - https://www.youtube.com/results?search_query=problem+solving+for+software+engineers",
        "freeCodeCamp: JavaScript Algorithms and Data Structures - https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures-v8/",
        "Official docs: LeetCode Explore - https://leetcode.com/explore/",
    ],
    "collaboration": [
        "YouTube: Engineering Collaboration and Teamwork - https://www.youtube.com/results?search_query=engineering+collaboration+teamwork",
        "freeCodeCamp: Open source collaboration guide - https://www.freecodecamp.org/news/how-to-contribute-to-open-source-projects-beginners-guide/",
        "Official docs: GitHub Collaboration Docs - https://docs.github.com/en/get-started/collaborating-with-issues-and-pull-requests",
    ],
}


def _fallback_resources(skill: str) -> list[str]:
    encoded = quote_plus(skill)
    return [
        f"YouTube: {skill} learning path - https://www.youtube.com/results?search_query={encoded}",
        f"freeCodeCamp: {skill} resources - https://www.freecodecamp.org/news/search/?query={encoded}",
        f"Official docs/search: {skill} docs - https://duckduckgo.com/?q={encoded}+official+documentation",
    ]


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
    normalized = str(skill).strip().lower()
    is_fallback = normalized not in RESOURCE_CATALOG
    resources = RESOURCE_CATALOG.get(normalized, _fallback_resources(skill))
    return {
        "skill": skill,
        "resources": resources,
        "is_fallback": is_fallback,
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
