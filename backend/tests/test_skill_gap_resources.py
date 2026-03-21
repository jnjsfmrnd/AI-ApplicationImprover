import unittest

from app.services.agent_orchestrator import AgentOrchestrator
from app.services.mcp.tools import get_free_resources


class SkillGapResourceTests(unittest.TestCase):
    def test_curated_resources_are_returned(self) -> None:
        payload = get_free_resources({"skill": "python"})

        self.assertFalse(payload.get("is_fallback"))
        self.assertGreater(len(payload.get("resources", [])), 0)

    def test_fallback_resources_are_suppressed_in_gap_output(self) -> None:
        orchestrator = AgentOrchestrator()
        parsed_output = {
            "summary": "",
            "gaps": [
                {
                    "skill": "Leading high-performing engineering teams",
                    "why_it_matters": "Critical for senior-level impact.",
                    "priority": 1,
                }
            ],
        }

        _, gaps = orchestrator._normalize_gap_items(
            resume_text="Built backend APIs and improved reliability.",
            role="software engineer",
            parsed_output=parsed_output,
            max_gap_skills=3,
        )

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["skill"], "Leading high-performing engineering teams")
        self.assertEqual(gaps[0]["free_resources"], [])


if __name__ == "__main__":
    unittest.main()
