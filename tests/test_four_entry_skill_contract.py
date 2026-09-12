"""Contracts for the four focused ARIS public research entries."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CANONICAL = {
    "autoresearch-topic": "skills/skills-codex/autoresearch-topic/SKILL.md",
    "autoresearch-proposal": "skills/skills-codex/autoresearch-proposal/SKILL.md",
    "research-write": "skills/skills-codex/research-write/SKILL.md",
    "research-audit": "skills/skills-codex/research-audit/SKILL.md",
}
PUBLIC = {
    name: f"skills/{name}/SKILL.md" for name in CANONICAL
}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_four_canonical_entries_and_wrappers_exist() -> None:
    for name, path in CANONICAL.items():
        text = read(path)
        assert f"name: {name}" in text
        assert "Zotero" in text or "zotero" in text
        assert "sources: all" not in text.lower()

    for name, path in PUBLIC.items():
        text = read(path)
        assert f"skills-codex/{name}/SKILL.md" in text
        assert "compatibility" in text.lower() or "canonical" in text.lower()


def test_topic_and_proposal_are_separate_input_contracts() -> None:
    topic = read(CANONICAL["autoresearch-topic"]).lower()
    proposal = read(CANONICAL["autoresearch-proposal"]).lower()

    for token in ("topic", "research_brief.md", "branch_plan.md", "query_pack.md"):
        assert token in topic
    for token in ("proposal", "existing application draft", "draft_analysis.md", "branch_plan.md"):
        assert token in proposal

    assert "must not infer an application draft" in topic
    assert "must read" in proposal
    assert "autoresearch-proposal" not in topic or "do not invoke" in topic
    assert "autoresearch-topic" not in proposal or "shared" in proposal


def test_research_write_is_promotion_and_freeze_boundary() -> None:
    text = read(CANONICAL["research-write"])
    lowered = text.lower()
    for token in (
        "promotable",
        "promotable_with_obligations",
        "needs_work",
        "obligations.md",
        "writing_claims.md",
        "submission-freeze",
        "research-audit",
    ):
        assert token in lowered


def test_research_audit_is_both_branch_and_frozen_artifact_boundary() -> None:
    text = read(CANONICAL["research-audit"])
    lowered = text.lower()
    for token in (
        "branch evidence",
        "frozen artifact",
        "vendor/anti-autoresearch",
        "fresh isolated codex reviewer",
        "forensics_gate.py",
        "same-context",
    ):
        assert token in lowered
    assert "research-write" in lowered
