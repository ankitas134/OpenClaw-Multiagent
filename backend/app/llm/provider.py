import os
import httpx
from app.core.config import settings

class BaseLLMProvider:
    async def generate(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
        raise NotImplementedError

    def generate_sync(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
        raise NotImplementedError

class GroqLLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    async def generate(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def generate_sync(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(self.url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

class TGILLMProvider(BaseLLMProvider):
    def __init__(self, endpoint_url: str):
        self.url = endpoint_url

    async def generate(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def generate_sync(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(self.url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

def get_llm_provider() -> BaseLLMProvider:
    provider_type = settings.LLM_PROVIDER.lower()
    if provider_type == "groq":
        return GroqLLMProvider(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
    elif provider_type == "tgi":
        return TGILLMProvider(endpoint_url=settings.TGI_ENDPOINT_URL)
    else:
        return GroqLLMProvider(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
