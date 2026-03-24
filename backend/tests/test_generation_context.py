import unittest
from unittest.mock import AsyncMock, patch

from app.api.routes import generation
from app.schemas.models import GenerationInput, JobContextResponse


class GenerationContextResolutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_placeholder_role_is_treated_as_missing(self) -> None:
        payload = GenerationInput(
            resume_text="Experienced engineer with backend and cloud delivery history.",
            job_description="We are hiring a Senior Data Engineer for platform modernization.",
            role="Target Role",
        )

        inferred = JobContextResponse(
            role="Senior Data Engineer",
            industry="Technology",
            company="Contoso",
            year=2026,
            confidence=0.91,
        )

        with patch("app.api.routes.generation._infer_job_context", new=AsyncMock(return_value=inferred)) as infer_mock:
            context = await generation._resolve_generation_context(payload)

        infer_mock.assert_awaited_once()
        self.assertEqual(context.role, "Senior Data Engineer")
        self.assertEqual(context.industry, "Technology")

    async def test_explicit_role_override_preserved(self) -> None:
        payload = GenerationInput(
            resume_text="Experienced engineer with backend and cloud delivery history.",
            job_description="We are hiring a Senior Data Engineer for platform modernization.",
            role="Staff Platform Engineer",
        )

        inferred = JobContextResponse(
            role="Senior Data Engineer",
            industry="Technology",
            company="Contoso",
            year=2026,
            confidence=0.88,
        )

        with patch("app.api.routes.generation._infer_job_context", new=AsyncMock(return_value=inferred)) as infer_mock:
            context = await generation._resolve_generation_context(payload)

        infer_mock.assert_awaited_once()
        self.assertEqual(context.role, "Staff Platform Engineer")
        self.assertEqual(context.company, "Contoso")


if __name__ == "__main__":
    unittest.main()
