"""Minimal environment-configured OpenAI-compatible chat adapter."""

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class OpenAICompatibleChat:
    """Callable adapter matching CommerceAgent's provider-neutral LLM boundary."""

    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "OpenAICompatibleChat":
        """Load explicit smoke-test configuration without default credentials."""

        api_key = os.getenv("AGENTLAB_LLM_API_KEY", "").strip()
        base_url = os.getenv("AGENTLAB_LLM_BASE_URL", "").strip().rstrip("/")
        model = os.getenv("AGENTLAB_LLM_MODEL", "").strip()
        missing = [
            name
            for name, value in (
                ("AGENTLAB_LLM_API_KEY", api_key),
                ("AGENTLAB_LLM_BASE_URL", base_url),
                ("AGENTLAB_LLM_MODEL", model),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "Missing external-model configuration: " + ", ".join(missing)
            )
        timeout = float(os.getenv("AGENTLAB_LLM_TIMEOUT_SECONDS", "30"))
        if timeout <= 0:
            raise ValueError("AGENTLAB_LLM_TIMEOUT_SECONDS must be positive")
        return cls(api_key, base_url, model, timeout)

    def __call__(self, prompt: str) -> str:
        endpoint = f"{self.base_url}/chat/completions"
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"External model returned HTTP {error.code}: {detail}"
            ) from error
        except URLError as error:
            raise RuntimeError(f"External model request failed: {error.reason}") from error
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(
                "External model response lacks choices[0].message.content"
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("External model returned empty message content")
        return content
