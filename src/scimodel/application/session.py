"""UI-independent research session: the state behind the interactive assistant."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scimodel.adapters.tabular_reader import read_table
from scimodel.application.discovery import DiscoveryOptions, discover
from scimodel.application.llm_assistant import LLMResearchAssistant, profile_context
from scimodel.application.profiling import DatasetProfile, profile_dataset
from scimodel.application.suggestions import Suggestion, suggest_actions
from scimodel.application.workspace import WorkspaceEntry, scan_workspace
from scimodel.domain.dataset import Dataset, DatasetError
from scimodel.domain.discovery import DiscoveryResult, ExpertiseLevel
from scimodel.domain.ports import LanguageModelPort
from scimodel.reporting.discovery_report import ReportBundle, write_discovery_report


@dataclass
class ResearchSession:
    """Holds the workspace, the active dataset, and the latest discovery result."""

    root: Path
    level: ExpertiseLevel = "intermediate"
    language_model: LanguageModelPort | None = None
    reports_dir: str = "scimodel_reports"
    seed: int = 0
    time_budget: float = 15.0
    share_data_sample: bool = False
    entries: list[WorkspaceEntry] = field(default_factory=list)
    dataset: Dataset | None = None
    profile: DatasetProfile | None = None
    result: DiscoveryResult | None = None
    objective: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def assistant(self) -> LLMResearchAssistant:
        return LLMResearchAssistant(self.language_model)

    def scan(self) -> list[WorkspaceEntry]:
        self.entries = scan_workspace(self.root)
        return self.entries

    def open(self, path: Path) -> DatasetProfile:
        self.dataset = read_table(path)
        self.profile = profile_dataset(self.dataset)
        self.result = None
        self._log("open", path=str(path))
        return self.profile

    def suggestions(self) -> list[Suggestion]:
        profile = self._require_profile()
        return suggest_actions(profile, level=self.level)

    def interpret(self, goal: str) -> dict[str, Any]:
        profile = self._require_profile()
        self.objective = goal
        context = profile_context(profile, self.dataset, share_sample=self.share_data_sample)
        plan = self.assistant.interpret_goal(goal, profile, context)
        self._log("interpret", goal=goal, plan=plan)
        return plan

    def run_discovery(
        self,
        target: str,
        predictors: Sequence[str],
        *,
        formulas: Sequence[str] = (),
        engines: Sequence[str] | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> DiscoveryResult:
        dataset = self._require_dataset()
        dataset.require_numeric([target, *predictors])
        profile = profile_dataset(dataset, target=target, predictors=tuple(predictors))
        self.profile = profile
        options = DiscoveryOptions(
            engines=tuple(engines) if engines else DiscoveryOptions().engines,
            seed=self.seed,
            time_budget=self.time_budget,
            objective=self.objective,
            user_formulas=tuple(formulas),
            language_model=self.language_model,
            share_data_sample=self.share_data_sample,
        )
        self.result = discover(
            dataset,
            target=target,
            predictors=predictors,
            options=options,
            profile=profile,
            progress=progress,
        )
        self._log("discover", target=target, predictors=list(predictors))
        return self.result

    def write_report(self, *, explain: bool = True) -> ReportBundle:
        dataset, profile = self._require_dataset(), self._require_profile()
        if self.result is None:
            raise DatasetError("Run a discovery before writing a report.")
        narrative = (
            self.assistant.explain_result(self.result, self.level, self.objective)
            if explain
            else None
        )
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        directory = self.root / self.reports_dir / f"{dataset.name}-{stamp}"
        source = (
            f"{self.language_model.provider_name}:{self.language_model.model_name}"
            if self.language_model
            else None
        )
        bundle = write_discovery_report(
            self.result,
            dataset,
            profile,
            directory,
            level=self.level,
            narrative=narrative,
            narrative_source=source,
        )
        self._log("report", directory=str(directory))
        return bundle

    def ask(self, question: str) -> str:
        profile = self._require_profile()
        context: dict[str, Any] = {
            "profile": profile_context(profile, self.dataset, share_sample=self.share_data_sample),
            "expertise_level": self.level,
        }
        if self.result is not None:
            context["result"] = {
                "best": self.result.best.to_dict() if self.result.best else None,
                "quality": {k: v.to_dict() for k, v in self.result.quality.items()},
                "warnings": list(self.result.warnings),
            }
        return self.assistant.answer(question, context)

    def _require_dataset(self) -> Dataset:
        if self.dataset is None:
            raise DatasetError("No dataset is open.")
        return self.dataset

    def _require_profile(self) -> DatasetProfile:
        if self.profile is None:
            raise DatasetError("No dataset is open.")
        return self.profile

    def _log(self, action: str, **details: Any) -> None:
        self.history.append({"at": datetime.now(UTC).isoformat(), "action": action, **details})
