"""
LLM provider abstraction layer.

Usage:
    from analyzers.llm_provider import get_provider
    llm = get_provider()
    text = llm.complete(prompt)

Configure via environment variables:
    LLM_PROVIDER=rule_based | openai | gemini
    OPENAI_API_KEY=sk-...
    GEMINI_API_KEY=...
    LLM_MODEL=gpt-4o-mini | gemini-1.5-flash | etc.
"""

import os
import logging
from abc import ABC, abstractmethod

log = logging.getLogger("llm_provider")


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 500) -> str:
        ...


class RuleBasedProvider(LLMProvider):
    """Default provider — returns the prompt itself as a signal to use rule-based logic."""
    def complete(self, prompt: str, max_tokens: int = 500) -> str:
        return ""  # empty string signals caller to use rule-based fallback


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o-mini"):
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            self._model  = model
        except ImportError:
            raise RuntimeError("Install openai: pip install openai")

    def complete(self, prompt: str, max_tokens: int = 500) -> str:
        resp = self._client.chat.completions.create(
            model    = self._model,
            messages = [{"role": "user", "content": prompt}],
            max_tokens = max_tokens,
            temperature = 0.4,
        )
        return resp.choices[0].message.content.strip()


class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-1.5-flash"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            self._model = genai.GenerativeModel(model)
        except ImportError:
            raise RuntimeError("Install google-generativeai: pip install google-generativeai")

    def complete(self, prompt: str, max_tokens: int = 500) -> str:
        resp = self._model.generate_content(prompt)
        return resp.text.strip()


def get_provider() -> LLMProvider:
    provider = os.environ.get("LLM_PROVIDER", "rule_based").lower()
    model    = os.environ.get("LLM_MODEL", "")

    if provider == "openai":
        return OpenAIProvider(model or "gpt-4o-mini")
    if provider == "gemini":
        return GeminiProvider(model or "gemini-1.5-flash")

    log.info("LLM_PROVIDER not set — using rule-based coaching")
    return RuleBasedProvider()
