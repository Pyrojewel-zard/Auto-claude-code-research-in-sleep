from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_write_consumes_only_promoted_evidence():
    text = read("skills/skills-codex/research-write/SKILL.md")
    for token in (
        "PROMOTABLE",
        "PROMOTABLE_WITH_OBLIGATIONS",
        "NEEDS_WORK",
        "OBLIGATIONS.md",
    ):
        assert token in text


def test_unverified_evidence_cannot_be_load_bearing():
    text = read("skills/skills-codex/research-write/SKILL.md")
    assert "UNVERIFIED" in text
    assert "qualified gap" in text.lower()
    assert "not load-bearing support" in text.lower()


def test_write_has_proposal_and_paper_modes_and_claim_boundaries():
    text = read("skills/skills-codex/research-write/SKILL.md").lower()
    for token in (
        "proposal mode",
        "paper mode",
        "future-work",
        "observed",
        "inferred",
        "research-audit",
        "research_gate.py",
        "freeze",
    ):
        assert token in text


def test_write_wrapper_points_to_codex_canonical_entry():
    text = read("skills/write/SKILL.md").lower()
    assert "skills-codex/write" in text
    assert "/research-write" in text
    assert "evidence-gated" in text or "promoted" in text


def test_legacy_codex_write_entry_is_only_a_router():
    text = read("skills/skills-codex/write/SKILL.md").lower()
    assert "compatibility router" in text
    assert "/research-write" in text
    assert "mcp__zotero_mcp__semantic_search" not in text
