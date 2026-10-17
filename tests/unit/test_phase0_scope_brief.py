"""Unit test verifying that Phase 0 Scope Brief and decisions are complete and valid."""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCOPE_BRIEF = PROJECT_ROOT / "docs" / "PHASE_0_SCOPE_BRIEF.md"
ADR_001 = PROJECT_ROOT / "docs" / "decisions" / "0001-phase-0-scientific-domain-selection.md"
STATUS_REPORT = PROJECT_ROOT / "docs" / "PROJECT_STATUS_REPORT.md"


def test_phase0_scope_brief_exists_and_complete():
    """Verify PHASE_0_SCOPE_BRIEF.md exists and contains no unreplaced template placeholders."""
    assert SCOPE_BRIEF.is_file(), f"Missing {SCOPE_BRIEF}"
    content = SCOPE_BRIEF.read_text(encoding="utf-8")

    # Check for unreplaced template placeholders like [choose one domain] or [list]
    pattern = (
        r"\[(choose|what|who|why|file|synthetic|list|rows|missing|"
        r"none|model|leave|known|values|tolerance|criteria|case)[^\]]*\]"
    )
    unreplaced = re.findall(pattern, content)
    assert not unreplaced, f"Unreplaced template placeholders found: {unreplaced}"

    # Verify critical sections and keywords
    required_keywords = [
        "Biochemical Reaction Kinetics",
        "Michaelis-Menten",
        "Lineweaver-Burk",
        "Puromycin",
        "V_{\\max}",
        "K_m",
        "212.684",
        "0.06412",
        "Unsupported cases",
        "Approval gate",
    ]
    for kw in required_keywords:
        assert kw in content, f"Missing required keyword '{kw}' in {SCOPE_BRIEF.name}"


def test_phase0_adr_decision_record_exists():
    """Verify ADR 001 exists and records the Phase 0 domain decision."""
    assert ADR_001.is_file(), f"Missing {ADR_001}"
    content = ADR_001.read_text(encoding="utf-8")
    assert "ADR 001" in content
    assert "Enzyme Kinetics" in content
    assert "Accepted" in content


def test_status_report_reflects_phase0_completion():
    """Verify PROJECT_STATUS_REPORT.md marks Phase 0 as complete with exit gate evidence."""
    assert STATUS_REPORT.is_file(), f"Missing {STATUS_REPORT}"
    content = STATUS_REPORT.read_text(encoding="utf-8")
    assert "Phase 0 complete" in content or "Phase 0 — Scope and Test Case Definition" in content
    assert "PHASE_0_SCOPE_BRIEF.md" in content
    assert "0001-phase-0-scientific-domain-selection.md" in content
