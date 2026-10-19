"""Claude provider using the official Anthropic Python SDK (optional dependency)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from scimodel.domain.ports import LanguageModelError


class AnthropicProvider:
    """Calls Claude through ``anthropic.Anthropic().messages``.

    Credentials come from the environment (``ANTHROPIC_API_KEY`` or an
    ``ant auth login`` profile); SciModel never stores keys. Structured
    answers use JSON-schema structured outputs, and policy refusals are
    surfaced as :class:`LanguageModelError`. Server-side refusal fallback is
    enabled by default so a declined request is retried on a fallback model.
    """

    DEFAULT_MODEL = "claude-opus-5-5"
    FALLBACK_BETA = "server-side-fallback-2026-07-01"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        effort: str = "medium",
        client: Any | None = None,
        enable_fallback: bool = True,
    ) -> None:
        self._model = model
        self._effort = effort
        self._client = client
        self._enable_fallback = enable_fallback

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise LanguageModelError(
                    "The Claude provider requires the Anthropic SDK: pip install 'scimodel[claude]'"
                ) from exc
            self._client = anthropic.Anthropic()
        return self._client

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        json_schema: Mapping[str, Any] | None = None,
        max_tokens: int = 8000,
    ) -> str:
        client = self._get_client()
        output_config: dict[str, Any] = {"effort": self._effort}
        if json_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": dict(json_schema)}
        request: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": output_config,
        }
        try:
            if self._enable_fallback:
                response = client.beta.messages.create(
                    **request, betas=[self.FALLBACK_BETA], extra_body={"fallbacks": "default"}
                )
            else:
                response = client.messages.create(**request)
        except Exception as exc:  # The SDK raises typed errors; normalize them for callers.
            raise LanguageModelError(_describe_error(exc)) from exc

        if getattr(response, "stop_reason", None) == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            raise LanguageModelError(f"Claude declined the request (category: {category}).")
        if getattr(response, "stop_reason", None) == "max_tokens":
            raise LanguageModelError("Claude's answer was cut off by the max_tokens limit.")
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        if json_schema is not None:
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                raise LanguageModelError("Claude returned invalid JSON.") from exc
        return text


def _describe_error(error: Exception) -> str:
    name = type(error).__name__
    if name == "AuthenticationError":
        return "Claude authentication failed. Set ANTHROPIC_API_KEY or run 'ant auth login'."
    if name == "RateLimitError":
        return "Claude rate limit reached; retry later."
    if name == "APIConnectionError":
        return "Could not reach the Claude API; check the network connection."
    if name == "NotFoundError":
        return "The configured Claude model was not found."
    status = getattr(error, "status_code", None)
    suffix = f" (HTTP {status})" if status else ""
    return f"Claude request failed{suffix}: {error}"
