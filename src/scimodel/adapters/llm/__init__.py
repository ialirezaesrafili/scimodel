"""Language-model provider adapters (opt-in; scientific computation never depends on them)."""

from __future__ import annotations

from scimodel.adapters.llm.anthropic_provider import AnthropicProvider
from scimodel.adapters.llm.ollama_provider import OllamaProvider
from scimodel.domain.ports import LanguageModelError, LanguageModelPort

PROVIDERS = ("none", "anthropic", "ollama")


def create_language_model(
    provider: str, *, model: str | None = None, host: str | None = None
) -> LanguageModelPort | None:
    """Build the configured provider, or return None when language models are disabled."""
    name = provider.strip().lower()
    if name in ("", "none", "off"):
        return None
    if name in ("anthropic", "claude"):
        return AnthropicProvider(model=model or AnthropicProvider.DEFAULT_MODEL)
    if name == "ollama":
        return OllamaProvider(
            model=model or OllamaProvider.DEFAULT_MODEL, host=host or OllamaProvider.DEFAULT_HOST
        )
    raise LanguageModelError(
        f"Unknown language-model provider '{provider}'. Choose one of: {', '.join(PROVIDERS)}."
    )


__all__ = ["PROVIDERS", "AnthropicProvider", "OllamaProvider", "create_language_model"]
