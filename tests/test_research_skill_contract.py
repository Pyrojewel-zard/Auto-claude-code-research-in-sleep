"""Static contracts for the canonical Codex research entry.

The research entry is an executable instruction surface rather than a Python
implementation.  These tests keep the workflow's safety and provenance
requirements visible while the skill text evolves.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = "skills/skills-codex/research/SKILL.md"
TOPIC = "skills/skills-codex/autoresearch-topic/SKILL.md"
PROPOSAL = "skills/skills-codex/autoresearch-proposal/SKILL.md"
PUBLIC = "skills/research/SKILL.md"
LEGACY_TOPIC = "skills/research-lit/SKILL.md"
LEGACY_PROPOSAL = "skills/grant-proposal/SKILL.md"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_legacy_research_is_only_a_router() -> None:
    text = read(CANONICAL)
    lowered = text.lower()

    for token in (
        "compatibility router",
        "/autoresearch-topic",
        "/autoresearch-proposal",
        "four canonical entries",
    ):
        assert token.lower() in lowered, f"canonical research is missing {token}"

    assert "mcp__zotero_mcp__semantic_search" not in text
    assert "sources: all" not in lowered


def test_canonical_entries_define_zotero_query_and_evidence_contract() -> None:
    text = read(TOPIC) + "\n" + read(PROPOSAL)
    lowered = text.lower()

    assert "mcp__zotero_mcp__semantic_search" in text
    assert "exactly one" in lowered or "one primary semantic-search call" in lowered
    assert "alias" in lowered and "once" in lowered
    assert "item details" in lowered
    assert "get_content" in lowered or "content" in lowered
    assert "annotations" in lowered
    assert "evidence_matrix.md" in lowered
    assert "coverage" in lowered

    for status in ("SEARCHED", "NO_HIT", "UNVERIFIED", "UNSEARCHABLE", "ERROR"):
        assert status in text, f"canonical research is missing terminal status {status}"


def test_canonical_research_defines_four_query_families() -> None:
    lowered = (read(TOPIC) + "\n" + read(PROPOSAL)).lower()

    families = (
        ("mechanism", "central mechanism"),
        ("aliases", "predecessor"),
        ("counter-evidence", "novelty"),
        ("boundaries", "limitations"),
    )
    for first, second in families:
        assert first in lowered and second in lowered, (
            f"query family must cover {first} and {second}"
        )


def test_branch_audit_is_after_research_completion_and_before_synthesis() -> None:
    text = read(TOPIC)
    lowered = text.lower()

    assert "BRANCH_RESEARCHED" in text
    assert "fresh isolated" in lowered or "isolated reviewer" in lowered
    assert "/research-audit" in text

    completion = text.index("BRANCH_RESEARCHED")
    audit = lowered.index("/research-audit", completion)
    synthesis = lowered.index("synthesize", audit)
    assert completion < audit < synthesis


def test_external_expansion_is_explicit_and_follows_zotero_coverage() -> None:
    text = read(PROPOSAL)
    lowered = text.lower()

    for policy in ("external_expansion: ask", "never", "allow"):
        assert policy in lowered, f"missing external expansion policy {policy}"
    assert "external retrieval is not an automatic fallback" in lowered
    assert "asked once after" in lowered
    assert "named gaps" in lowered
    assert "silently" in lowered

    coverage = lowered.index("coverage_report.md")
    expansion = lowered.index("external_expansion: ask")
    assert coverage < expansion


def test_public_and_legacy_entries_are_compatibility_wrappers() -> None:
    public = read(PUBLIC)
    codex_legacy = read(CANONICAL)
    topic = read(LEGACY_TOPIC)
    proposal = read(LEGACY_PROPOSAL)

    assert "skills-codex/research/SKILL.md" in public
    assert "compatibility router" in codex_legacy.lower()
    assert "/autoresearch-topic" in codex_legacy
    assert "/autoresearch-proposal" in codex_legacy
    assert "topic-mode" in topic.lower()
    assert "compatibility wrapper" in topic.lower()
    assert "proposal research" in proposal.lower()
    assert "/research-write" in proposal
    for text in (public, codex_legacy, topic, proposal):
        assert "sources: all" not in text.lower()


def test_legacy_proposal_wrapper_keeps_query_pack_evidence_handoff() -> None:
    for path in (LEGACY_PROPOSAL, "skills/skills-codex/grant-proposal/SKILL.md"):
        text = read(path)
        lowered = text.lower()
        for artifact in ("DRAFT_ANALYSIS.md", "QUERY_PACK.md", "EVIDENCE_MATRIX.md"):
            assert artifact in text, f"{path} must preserve {artifact} handoff"
        assert "query pack:" in lowered
        assert "semantic_search" in text
        assert "unclear" in lowered
