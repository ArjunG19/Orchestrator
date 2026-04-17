"""Groq LLM client wrapper for chat-completion calls."""

import logging
import os
from typing import Optional

import httpx

from app.config import DEFAULT_MODEL, DEFAULT_TEMPERATURE

logger = logging.getLogger(__name__)

GROQ_API_BASE_URL = "https://api.groq.com/openai/v1"


class LLMClient:
    """Thin wrapper around Groq chat completions API."""

    def __init__(self, model: Optional[str] = None):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY environment variable is not set")
        self.model = model or DEFAULT_MODEL
        self.api_key = api_key
        self.base_url = os.environ.get("GROQ_API_BASE_URL", GROQ_API_BASE_URL)

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 512,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """Send a Groq chat-completion request and return the generated text.

        Returns None when the API call fails (timeout, rate-limit, etc.).
        """
        target_model = model or self.model
        target_temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE
        messages = [{"role": "user", "content": prompt}]
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": target_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": target_temperature,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            payload = response.json()
            choices = payload.get("choices", [])
            if not choices:
                return None
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        part_text = part.get("text")
                        if isinstance(part_text, str):
                            text_parts.append(part_text)
                return "\n".join(text_parts) if text_parts else None
            return None
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Groq API error (%s): %s - %s",
                target_model,
                exc.response.status_code,
                exc.response.text,
            )
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected LLM client error: %s", exc)
            return None
