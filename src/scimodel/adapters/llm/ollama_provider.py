"""Local language-model provider using the Ollama HTTP API (no data leaves the machine)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

from scimodel.domain.ports import LanguageModelError


class OllamaProvider:
    """Calls a locally running Ollama server through its native ``/api/chat`` endpoint."""

    DEFAULT_MODEL = "llama3.1"
    DEFAULT_HOST = "http://localhost:11434"

    def __init__(
        self, *, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST, timeout: float = 300.0
    ) -> None:
        if not host.startswith(("http://", "https://")):
            raise LanguageModelError("The Ollama host must start with http:// or https://.")
        self._model = model
        self._host = host.rstrip("/")
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        json_schema: Mapping[str, Any] | None = None,
        max_tokens: int = 4096,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "options": {"num_predict": max_tokens, "temperature": 0},
        }
        if json_schema is not None:
            payload["format"] = dict(json_schema)
        request = urllib.request.Request(
            f"{self._host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise LanguageModelError(
                f"Could not reach Ollama at {self._host}. Is 'ollama serve' running? ({exc})"
            ) from exc
        except (json.JSONDecodeError, TimeoutError) as exc:
            raise LanguageModelError(f"Invalid response from Ollama: {exc}") from exc
        content = body.get("message", {}).get("content") if isinstance(body, dict) else None
        if not isinstance(content, str):
            raise LanguageModelError("Ollama returned no message content.")
        return content
