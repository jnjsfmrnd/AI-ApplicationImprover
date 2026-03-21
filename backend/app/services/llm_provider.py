import os
import asyncio
import httpx
from collections.abc import Iterable

from azure.core.exceptions import HttpResponseError


class LLMProvider:
    @property
    def provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "auto").strip().lower()

    @property
    def azure_openai_endpoint(self) -> str:
        return os.getenv("AZURE_OPENAI_ENDPOINT", "")

    @property
    def azure_openai_api_key(self) -> str:
        return os.getenv("AZURE_OPENAI_API_KEY", "")

    @property
    def azure_openai_api_version(self) -> str:
        return os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    @property
    def azure_openai_deployment(self) -> str:
        return os.getenv("AZURE_OPENAI_DEPLOYMENT", self.model_name)

    @property
    def github_token(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    @property
    def gemini_model(self) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    @property
    def model_name(self) -> str:
        return os.getenv("LLM_MODEL", "gpt-4o-mini")

    @property
    def endpoint(self) -> str:
        return os.getenv("AZURE_INFERENCE_ENDPOINT", "https://models.inference.ai.azure.com")

    @property
    def github_model_candidates(self) -> list[str]:
        raw_candidates = os.getenv("GITHUB_MODEL_CANDIDATES", "")
        parsed_candidates = [part.strip() for part in raw_candidates.split(",") if part.strip()]
        baseline = [self.model_name, "gpt-4.1-mini", "gpt-4o-mini"]
        merged: list[str] = []
        seen: set[str] = set()
        for candidate in [*parsed_candidates, *baseline]:
            normalized = candidate.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            merged.append(candidate)
        return merged

    @property
    def github_model_retry_statuses(self) -> set[int]:
        raw_statuses = os.getenv("GITHUB_MODEL_RETRY_STATUSES", "408,409,425,429,500,502,503,504")
        statuses: set[int] = set()
        for part in raw_statuses.split(","):
            cleaned = part.strip()
            if not cleaned:
                continue
            try:
                statuses.add(int(cleaned))
            except ValueError:
                continue
        return statuses or {408, 409, 425, 429, 500, 502, 503, 504}

    @property
    def has_azure_openai(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    def _is_retryable_github_error(self, exc: Exception) -> bool:
        if isinstance(exc, HttpResponseError) and getattr(exc, "status_code", None) in self.github_model_retry_statuses:
            return True

        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int) and status_code in self.github_model_retry_statuses:
            return True

        response = getattr(exc, "response", None)
        response_status = getattr(response, "status_code", None)
        if isinstance(response_status, int) and response_status in self.github_model_retry_statuses:
            return True

        message = str(exc).lower()
        retry_markers = ["rate limit", "too many requests", "throttl", "temporar", "timeout", "unavailable"]
        return any(marker in message for marker in retry_markers)

    def _mock_output(self, provider_name: str, reason: str, system_prompt: str, user_prompt: str) -> str:
        return (
            f"[MOCK OUTPUT — {provider_name} call failed]\n"
            f"Reason: {reason[:300]}\n\n"
            f"System Intent: {system_prompt[:240]}\n\n"
            f"Generated Draft Based On Input:\n{user_prompt[:1400]}"
        )

    def _coerce_content_to_text(self, content: str | Iterable | None) -> str:
        if isinstance(content, str):
            return content
        if content is None:
            return ""

        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
                continue
            text = getattr(item, "text", None)
            if isinstance(text, str):
                chunks.append(text)
                continue
            maybe_text = item.get("text") if isinstance(item, dict) else None
            if isinstance(maybe_text, str):
                chunks.append(maybe_text)

        return "\n".join(part for part in chunks if part).strip()

    async def _generate_with_azure_openai(self, system_prompt: str, user_prompt: str) -> str:
        from openai import AzureOpenAI

        def _call() -> str:
            client = AzureOpenAI(
                azure_endpoint=self.azure_openai_endpoint,
                api_key=self.azure_openai_api_key,
                api_version=self.azure_openai_api_version,
                timeout=60.0,
            )
            response = client.chat.completions.create(
                model=self.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content or ""

        try:
            return await asyncio.wait_for(asyncio.to_thread(_call), timeout=65.0)
        except TimeoutError as exc:
            raise TimeoutError("Azure OpenAI request timed out after 65 seconds") from exc

    async def _generate_with_gemini(self, system_prompt: str, user_prompt: str) -> str:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
            },
        }

        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(endpoint, params={"key": self.gemini_api_key}, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return "\n".join(part for part in text_parts if part).strip()

    async def _generate_with_sync_client(self, model_name: str, system_prompt: str, user_prompt: str) -> str:
        from azure.ai.inference import ChatCompletionsClient
        from azure.ai.inference.models import SystemMessage, UserMessage
        from azure.core.credentials import AzureKeyCredential

        def _call() -> str:
            with ChatCompletionsClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.github_token),
                connection_timeout=10,
                read_timeout=60,
            ) as client:
                response = client.complete(
                    model=model_name,
                    messages=[
                        SystemMessage(content=system_prompt),
                        UserMessage(content=user_prompt),
                    ],
                    temperature=0.7,
                )
            return response.choices[0].message.content or ""

        try:
            return await asyncio.wait_for(asyncio.to_thread(_call), timeout=75.0)
        except TimeoutError as exc:
            raise TimeoutError("GitHub Models sync fallback timed out after 75 seconds") from exc

    async def _generate_with_github_models(self, model_name: str, system_prompt: str, user_prompt: str) -> str:
        try:
            from azure.ai.inference.aio import ChatCompletionsClient
            from azure.ai.inference.models import SystemMessage, UserMessage
            from azure.core.credentials import AzureKeyCredential

            async with ChatCompletionsClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.github_token),
                connection_timeout=10,
                read_timeout=60,
            ) as client:
                try:
                    response = await asyncio.wait_for(
                        client.complete(
                            model=model_name,
                            messages=[
                                SystemMessage(content=system_prompt),
                                UserMessage(content=user_prompt),
                            ],
                            temperature=0.7,
                        ),
                        timeout=65.0,
                    )
                except TimeoutError as exc:
                    raise TimeoutError("GitHub Models request timed out after 65 seconds") from exc
            return self._coerce_content_to_text(response.choices[0].message.content)
        except ModuleNotFoundError as exc:
            if exc.name == "aiohttp":
                return await self._generate_with_sync_client(model_name, system_prompt, user_prompt)
            raise

    async def _generate_with_github_model_routing(self, system_prompt: str, user_prompt: str) -> str:
        ordered_models = self.github_model_candidates
        errors: list[str] = []

        for index, candidate_model in enumerate(ordered_models):
            try:
                return await self._generate_with_github_models(candidate_model, system_prompt, user_prompt)
            except Exception as exc:
                errors.append(f"{candidate_model}: {str(exc)[:220]}")
                is_last_model = index == len(ordered_models) - 1
                if not self._is_retryable_github_error(exc) or is_last_model:
                    break

        joined_errors = " | ".join(errors) if errors else "unknown routing error"
        return self._mock_output("GitHub Models", joined_errors, system_prompt, user_prompt)

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider in {"github_models", "github", "auto"} and self.github_token:
            return await self._generate_with_github_model_routing(system_prompt, user_prompt)

        if self.provider in {"gemini", "auto"} and self.has_gemini:
            try:
                return await self._generate_with_gemini(system_prompt, user_prompt)
            except Exception as exc:
                return self._mock_output("Gemini", str(exc), system_prompt, user_prompt)

        if self.provider in {"azure_openai", "azure", "auto"} and self.has_azure_openai:
            try:
                return await self._generate_with_azure_openai(system_prompt, user_prompt)
            except Exception as exc:
                return self._mock_output("Azure OpenAI", str(exc), system_prompt, user_prompt)

        # --- Mock fallback (no provider configured) ---
        return (
            "[MOCK OUTPUT — configure GITHUB_TOKEN, GEMINI_API_KEY, or Azure OpenAI settings to enable live inference]\n\n"
            f"System Intent: {system_prompt[:240]}\n\n"
            f"Generated Draft Based On Input:\n{user_prompt[:1400]}"
        )


llm_provider = LLMProvider()
