import os
import asyncio


class LLMProvider:
    @property
    def github_token(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def model_name(self) -> str:
        return os.getenv("LLM_MODEL", "gpt-4o-mini")

    @property
    def endpoint(self) -> str:
        return os.getenv("AZURE_INFERENCE_ENDPOINT", "https://models.inference.ai.azure.com")

    async def _generate_with_sync_client(self, system_prompt: str, user_prompt: str) -> str:
        from azure.ai.inference import ChatCompletionsClient
        from azure.ai.inference.models import SystemMessage, UserMessage
        from azure.core.credentials import AzureKeyCredential

        def _call() -> str:
            with ChatCompletionsClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.github_token),
            ) as client:
                response = client.complete(
                    model=self.model_name,
                    messages=[
                        SystemMessage(content=system_prompt),
                        UserMessage(content=user_prompt),
                    ],
                    temperature=0.7,
                )
            return response.choices[0].message.content or ""

        return await asyncio.to_thread(_call)

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.github_token:
            try:
                from azure.ai.inference.aio import ChatCompletionsClient
                from azure.ai.inference.models import SystemMessage, UserMessage
                from azure.core.credentials import AzureKeyCredential

                async with ChatCompletionsClient(
                    endpoint=self.endpoint,
                    credential=AzureKeyCredential(self.github_token),
                ) as client:
                    response = await client.complete(
                        model=self.model_name,
                        messages=[
                            SystemMessage(content=system_prompt),
                            UserMessage(content=user_prompt),
                        ],
                        temperature=0.7,
                    )
                return response.choices[0].message.content or ""
            except ModuleNotFoundError as exc:
                if exc.name == "aiohttp":
                    try:
                        return await self._generate_with_sync_client(system_prompt, user_prompt)
                    except Exception as sync_exc:
                        return (
                            "[MOCK OUTPUT — Azure AI Inference call failed]\n"
                            f"Reason: {str(sync_exc)[:300]}\n\n"
                            f"System Intent: {system_prompt[:240]}\n\n"
                            f"Generated Draft Based On Input:\n{user_prompt[:1400]}"
                        )
                return (
                    "[MOCK OUTPUT — Azure AI Inference call failed]\n"
                    f"Reason: {str(exc)[:300]}\n\n"
                    f"System Intent: {system_prompt[:240]}\n\n"
                    f"Generated Draft Based On Input:\n{user_prompt[:1400]}"
                )
            except Exception as exc:
                return (
                    "[MOCK OUTPUT — Azure AI Inference call failed]\n"
                    f"Reason: {str(exc)[:300]}\n\n"
                    f"System Intent: {system_prompt[:240]}\n\n"
                    f"Generated Draft Based On Input:\n{user_prompt[:1400]}"
                )

        # --- Mock fallback (no GITHUB_TOKEN configured) ---
        return (
            "[MOCK OUTPUT — set GITHUB_TOKEN to use GitHub Models (gpt-4o-mini)]\n\n"
            f"System Intent: {system_prompt[:240]}\n\n"
            f"Generated Draft Based On Input:\n{user_prompt[:1400]}"
        )


llm_provider = LLMProvider()
