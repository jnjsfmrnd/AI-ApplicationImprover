import os
import asyncio
import httpx
from contextlib import contextmanager
from contextvars import ContextVar


class LLMProvider:
    _model_override: ContextVar[str | None] = ContextVar("llm_model_override", default=None)

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
    def effective_model_name(self) -> str:
        override = self._model_override.get()
        return override.strip() if isinstance(override, str) and override.strip() else self.model_name

    @property
    def endpoint(self) -> str:
        return os.getenv("AZURE_INFERENCE_ENDPOINT", "https://models.inference.ai.azure.com")

    @property
    def has_azure_openai(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @contextmanager
    def use_model(self, model_name: str | None):
        token = self._model_override.set(model_name.strip() if isinstance(model_name, str) else None)
        try:
            yield
        finally:
            self._model_override.reset(token)

    def _mock_output(self, provider_name: str, reason: str, system_prompt: str, user_prompt: str) -> str:
        return (
            f"[MOCK OUTPUT — {provider_name} call failed]\n"
            f"Reason: {reason[:300]}\n\n"
            f"System Intent: {system_prompt[:240]}\n\n"
            f"Generated Draft Based On Input:\n{user_prompt[:1400]}"
        )


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

    async def _generate_with_sync_client(self, system_prompt: str, user_prompt: str) -> str:
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
                    model=self.effective_model_name,
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

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider in {"github_models", "github", "auto"} and self.github_token:
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
                                model=self.effective_model_name,
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
                return response.choices[0].message.content or ""
            except ModuleNotFoundError as exc:
                if exc.name == "aiohttp":
                    try:
                        return await self._generate_with_sync_client(system_prompt, user_prompt)
                    except Exception as sync_exc:
                        return self._mock_output("GitHub Models", str(sync_exc), system_prompt, user_prompt)
                return self._mock_output("GitHub Models", str(exc), system_prompt, user_prompt)
            except Exception as exc:
                return self._mock_output("GitHub Models", str(exc), system_prompt, user_prompt)

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
