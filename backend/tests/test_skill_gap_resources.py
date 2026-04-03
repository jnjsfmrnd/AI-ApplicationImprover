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

    def test_guard_truthful_ats_output_restores_missing_summary(self) -> None:
        orchestrator = AgentOrchestrator()
        source_resume = "\n".join(
            [
                "JANE DOE",
                "Senior Software Engineer | jane@example.com | +1 (555) 111-2222",
                "",
                "PROFESSIONAL SUMMARY",
                "Backend engineer with cloud delivery experience.",
                "",
                "EXPERIENCE",
                "Example Company",
            ]
        )
        optimized_resume = "\n".join(
            [
                "JANE DOE",
                "Senior Software Engineer | jane@example.com | +1 (555) 111-2222",
                "",
                "EXPERIENCE",
                "Example Company",
            ]
        )

        guarded = orchestrator._guard_truthful_ats_output(source_resume, optimized_resume)

        self.assertIn("PROFESSIONAL SUMMARY", guarded)
        self.assertIn("Backend engineer with cloud delivery experience.", guarded)

    def test_guard_truthful_ats_output_normalizes_unicode_separators(self) -> None:
        orchestrator = AgentOrchestrator()
        source_resume = "JANE DOE\nSenior Software Engineer • Cloud • APIs\n+1 (555) 111-2222"
        optimized_resume = source_resume

        guarded = orchestrator._guard_truthful_ats_output(source_resume, optimized_resume)

        self.assertIn("Senior Software Engineer | Cloud | APIs", guarded)
        self.assertNotIn("•", guarded)


if __name__ == "__main__":
    unittest.main()
