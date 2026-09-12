import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from forensics_gate import classify_review_provenance  # noqa: E402


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_codex_audit_uses_isolated_reviewer_and_locked_upstream():
    text = read("skills/skills-codex/research-audit/SKILL.md")
    for token in (
        "resolve_anti_autoresearch.py",
        "fresh isolated Codex reviewer",
        "read-only",
        "forensics_gate.py",
    ):
        assert token in text
    assert "mcp__codex__codex-reply" not in text


def test_legacy_codex_audit_entry_is_only_a_router():
    text = read("skills/skills-codex/audit/SKILL.md").lower()
    assert "compatibility router" in text
    assert "/research-audit" in text
    assert "anti-autoresearch" in text


def test_same_family_is_not_same_context():
    gate = classify_review_provenance(
        executor="codex", reviewer="codex", isolated=True
    )
    assert gate == "same-family-isolated"


def test_same_context_is_explicitly_fail_closed():
    assert (
        classify_review_provenance(
            executor="codex", reviewer="codex", isolated=False
        )
        == "same-context"
    )
