"""Tests for language-model providers and the grounded research assistant (no network)."""

import io
import json
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scimodel.adapters.llm import AnthropicProvider, OllamaProvider, create_language_model
from scimodel.adapters.tabular_reader import read_table
from scimodel.application.discovery import DiscoveryOptions, discover
from scimodel.application.llm_assistant import (
    LLMResearchAssistant,
    interpret_goal_locally,
    parse_formula_candidates,
    profile_context,
)
from scimodel.application.profiling import profile_dataset
from scimodel.domain.ports import LanguageModelError

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


class FakeMessages:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response, self.error, self.calls = response, error, []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def _response(text: str, stop: str = "end_turn") -> Any:
    return SimpleNamespace(
        stop_reason=stop,
        stop_details=SimpleNamespace(category="cyber"),
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
    )


def _client(messages: FakeMessages) -> Any:
    return SimpleNamespace(beta=SimpleNamespace(messages=messages), messages=messages)


def test_anthropic_provider_structured_output_and_fallback() -> None:
    messages = FakeMessages(_response('{"ok": true}'))
    provider = AnthropicProvider(client=_client(messages))
    assert provider.provider_name == "anthropic" and provider.model_name == "claude-opus-5-5"
    assert provider.complete("sys", "hi", json_schema={"type": "object"}) == '{"ok": true}'
    call = messages.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["output_config"]["effort"] == "medium"
    assert call["betas"] == [AnthropicProvider.FALLBACK_BETA]
    assert call["extra_body"] == {"fallbacks": "default"}
    assert "thinking" not in call and "temperature" not in call


def test_anthropic_provider_errors() -> None:
    for stop, message in (("refusal", "declined"), ("max_tokens", "cut off")):
        provider = AnthropicProvider(client=_client(FakeMessages(_response("x", stop))))
        with pytest.raises(LanguageModelError, match=message):
            provider.complete("s", "p")
    invalid = AnthropicProvider(client=_client(FakeMessages(_response("not json"))))
    with pytest.raises(LanguageModelError, match="invalid JSON"):
        invalid.complete("s", "p", json_schema={})
    for name, message in (
        ("AuthenticationError", "authentication"),
        ("RateLimitError", "rate"),
        ("APIConnectionError", "reach"),
        ("NotFoundError", "not found"),
        ("OtherError", "failed"),
    ):
        error = type(name, (Exception,), {})("boom")
        provider = AnthropicProvider(
            client=_client(FakeMessages(error=error)), enable_fallback=False
        )
        with pytest.raises(LanguageModelError, match=message):
            provider.complete("s", "p")


def test_ollama_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float) -> Any:
        seen["body"] = json.loads(request.data)
        return io.BytesIO(json.dumps({"message": {"content": "hello"}}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OllamaProvider(model="qwen", host="http://localhost:11434/")
    assert provider.complete("s", "p", json_schema={"type": "object"}) == "hello"
    assert seen["body"]["format"] == {"type": "object"} and seen["body"]["model"] == "qwen"

    def offline(request: Any, timeout: float) -> Any:
        raise urllib.error.URLError("refused")

    monkeypatch.setattr("urllib.request.urlopen", offline)
    with pytest.raises(LanguageModelError, match="ollama serve"):
        provider.complete("s", "p")
    monkeypatch.setattr("urllib.request.urlopen", lambda r, timeout: io.BytesIO(b"{}"))
    with pytest.raises(LanguageModelError, match="no message"):
        provider.complete("s", "p")
    with pytest.raises(LanguageModelError, match="http"):
        OllamaProvider(host="localhost:11434")


def test_factory() -> None:
    assert create_language_model("none") is None
    assert isinstance(create_language_model("claude"), AnthropicProvider)
    assert create_language_model("ollama", model="m").model_name == "m"  # type: ignore[union-attr]
    with pytest.raises(LanguageModelError, match="Unknown"):
        create_language_model("gpt")


def test_parse_formula_candidates_rejects_unsafe_and_unrelated() -> None:
    raw = json.dumps(
        {
            "candidates": [
                {
                    "name": "Monod",
                    "expression": "mu*S/(Ks + S)",
                    "rationale": "growth",
                    "assumptions": ["single substrate"],
                    "parameters": [
                        {"name": "mu", "initial_guess": 1, "lower_bound": 0, "upper_bound": None},
                        {"name": "Ks", "initial_guess": 1, "lower_bound": 0, "upper_bound": None},
                    ],
                },
                {
                    "name": "evil",
                    "expression": "__import__('os').system('rm -rf /')",
                    "parameters": [],
                    "rationale": "",
                    "assumptions": [],
                },
                {
                    "name": "constant",
                    "expression": "c",
                    "rationale": "",
                    "assumptions": [],
                    "parameters": [
                        {"name": "c", "initial_guess": 1, "lower_bound": None, "upper_bound": None}
                    ],
                },
            ]
        }
    )
    proposals, rejected = parse_formula_candidates(raw, target="rate", predictors=["S"])
    assert [p.formula.name for p in proposals] == ["llm_monod"]
    assert proposals[0].origin == "llm" and proposals[0].formula.assumptions == (
        "single substrate",
    )
    assert len(rejected) == 2
    assert parse_formula_candidates("nope", target="y", predictors=["x"])[0] == []


class ScriptedModel:
    provider_name = "fake"
    model_name = "scripted"

    def __init__(self, answers: list[str]) -> None:
        self.answers, self.prompts = answers, []

    def complete(
        self, system: str, prompt: str, *, json_schema: Any = None, max_tokens: int = 4096
    ) -> str:
        self.prompts.append(prompt)
        answer = self.answers.pop(0)
        if answer == "RAISE":
            raise LanguageModelError("down")
        return answer


def test_llm_engine_inside_discovery_is_validated_and_private() -> None:
    dataset = read_table(EXAMPLES / "enzyme_kinetics_puromycin.csv")
    model = ScriptedModel(
        [
            json.dumps(
                {
                    "candidates": [
                        {
                            "name": "michaelis menten",
                            "expression": "V*substrate_conc/(K + substrate_conc)",
                            "rationale": "enzyme saturation",
                            "assumptions": [],
                            "parameters": [
                                {
                                    "name": "V",
                                    "initial_guess": 200,
                                    "lower_bound": 0,
                                    "upper_bound": None,
                                },
                                {
                                    "name": "K",
                                    "initial_guess": 0.1,
                                    "lower_bound": 0,
                                    "upper_bound": None,
                                },
                            ],
                        }
                    ]
                }
            )
        ]
    )
    result = discover(
        dataset,
        target="reaction_velocity",
        predictors=["substrate_conc"],
        options=DiscoveryOptions(engines=("llm",), language_model=model),
    )
    assert result.best is not None and result.best.origin == "llm"
    assert abs(result.best.fit.parameters["V"] - 212.68) < 0.5
    assert "sample_rows" not in model.prompts[0] and "76" not in model.prompts[0].split("JSON")[0]
    engine = next(e for e in result.engines if e.engine == "llm")
    assert engine.status == "ok" and result.settings["language_model"] == "fake:scripted"


def test_profile_context_shares_rows_only_on_opt_in() -> None:
    dataset = read_table(EXAMPLES / "kepler_planets.csv")
    profile = profile_dataset(dataset)
    assert "sample_rows" not in profile_context(profile, dataset)
    shared = profile_context(profile, dataset, share_sample=True)
    assert shared["sample_rows"][0]["planet"] == "Mercury"


def test_goal_interpretation_and_explanations() -> None:
    dataset = read_table(EXAMPLES / "catalysis_arrhenius.csv")
    profile = profile_dataset(dataset)
    local = interpret_goal_locally("How does rate depend on temperature?", profile)
    assert local["target"] == "rate" and local["predictors"] == ["temperature"]
    assert interpret_goal_locally("check for outliers", profile)["intent"] == "quality"
    assert interpret_goal_locally("write a report", profile)["intent"] == "report"

    assistant = LLMResearchAssistant(
        ScriptedModel(
            [
                json.dumps(
                    {
                        "intent": "discover",
                        "target": "bogus",
                        "predictors": ["temperature", "x"],
                        "formula": None,
                        "summary": "s",
                    }
                ),
                "RAISE",
                "## Interpretation\nArrhenius behaviour.",
                "RAISE",
                "answer",
            ]
        )
    )
    plan = assistant.interpret_goal("model it", profile, {})
    assert plan["target"] == "rate" and plan["predictors"] == ["temperature"]
    assert assistant.interpret_goal("again", profile, {})["source"] == "local-keywords"
    result = discover(
        dataset,
        target="rate",
        predictors=["temperature", "catalyst_loading"],
        options=DiscoveryOptions(engines=("sparse",)),
    )
    assert "Arrhenius" in (assistant.explain_result(result, "novice") or "")
    assert assistant.explain_result(result, "expert") is None
    assert assistant.answer("why?", {}) == "answer"
    offline = LLMResearchAssistant(None)
    assert not offline.available and offline.explain_result(result, "novice") is None
    assert offline.propose_formulas({}, target="y", predictors=["x"], objective="") == ([], [])
    with pytest.raises(LanguageModelError, match="No language model"):
        offline.answer("q", {})
