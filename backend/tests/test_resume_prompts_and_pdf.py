import unittest

from app.api.routes.generation import export_pdf
from app.schemas.models import ExportPdfRequest
from app.services.prompt_modules.ats import build_ats_prompt
from app.services.prompt_modules.rewriter import build_rewrite_prompt


class ResumePromptSummaryTests(unittest.TestCase):
    def test_rewrite_prompt_requires_professional_summary(self) -> None:
        _, user_prompt = build_rewrite_prompt(
            resume_text="Built APIs and reduced incidents by 40%.",
            job_description="Hiring a backend engineer with Python, SQL, and cloud experience.",
            role="Backend Engineer",
            industry="Technology",
        )

        self.assertIn("PROFESSIONAL SUMMARY", user_prompt)
        self.assertIn("2-4 concise lines", user_prompt)
        self.assertIn("Output each skills category (such as Languages & Frameworks, Frontend, Backend & Architecture, etc.) as a bullet point", user_prompt)
        self.assertIn("Do not bold, highlight, italicize, or apply any markdown or special formatting to any category or skill", user_prompt)
        self.assertIn("add a bullet for soft skills", user_prompt)
        self.assertIn("(3) EXPERIENCE (employment history), (4) PROJECTS (personal/portfolio), (5) CORE SKILLS", user_prompt)

    def test_ats_prompt_requires_professional_summary(self) -> None:
        _, user_prompt = build_ats_prompt(
            resume_text="Built APIs and reduced incidents by 40%.",
            job_description="Hiring a backend engineer with Python, SQL, and cloud experience.",
            role="Backend Engineer",
            year=2026,
        )

        self.assertIn("PROFESSIONAL SUMMARY", user_prompt)
        self.assertIn("2-4 concise lines", user_prompt)
        self.assertIn("Output each skills category (such as Languages & Frameworks, Frontend, Backend & Architecture, etc.) as a bullet point", user_prompt)
        self.assertIn("Do not bold, highlight, italicize, or apply any markdown or special formatting to any category or skill", user_prompt)
        self.assertIn("add a bullet for soft skills", user_prompt)
        self.assertIn("(3) EXPERIENCE (employment history), (4) PROJECTS (personal/portfolio), (5) CORE SKILLS", user_prompt)


class ResumePdfExportTests(unittest.IsolatedAsyncioTestCase):
    async def test_export_pdf_handles_long_resume_content(self) -> None:
        content_lines = [
            "JANE DOE",
            "Senior Software Engineer",
            "Seattle, WA | jane@example.com | linkedin.com/in/janedoe",
            "",
            "PROFESSIONAL SUMMARY",
            "Backend and platform engineer with strong production ownership and cloud delivery experience.",
            "Focuses on measurable outcomes, reliability, and scalable services aligned to role requirements.",
            "",
            "EXPERIENCE",
        ]
        content_lines.extend(
            [
                f"- Led service modernization initiative {idx}, improving latency and deployment safety across teams."
                for idx in range(1, 220)
            ]
        )

        response = await export_pdf(
            ExportPdfRequest(
                title="ATS Resume",
                content="\n".join(content_lines),
            )
        )

        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        pdf_bytes = b"".join(chunks)

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 2000)


if __name__ == "__main__":
    unittest.main()
