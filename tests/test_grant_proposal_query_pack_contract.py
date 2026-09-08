"""Contract tests for the proposal-draft evidence workflow skills.

These tests intentionally describe the behavior the skills must teach future
agents. They are red until the explicit query-pack workflow is documented.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


PROPOSAL_SKILLS = (
    "skills/grant-proposal/SKILL.md",
    "skills/skills-codex/grant-proposal/SKILL.md",
    "skills/skills-codex-gemini-review/grant-proposal/SKILL.md",
)

LITERATURE_SKILLS = (
    "skills/research-lit/SKILL.md",
    "skills/skills-codex/research-lit/SKILL.md",
)


def test_grant_proposal_requires_draft_analysis_query_pack_and_evidence_matrix() -> None:
    for path in PROPOSAL_SKILLS:
        text = read(path)
        for artifact in ("DRAFT_ANALYSIS.md", "QUERY_PACK.md", "EVIDENCE_MATRIX.md"):
            assert artifact in text, f"{path} must require {artifact}"
        assert "query pack:" in text.lower(), f"{path} must pass the query pack downstream"
        assert "semantic_search" in text, f"{path} must require semantic Zotero retrieval"
        assert "Query status = PENDING" in text, f"{path} must initialize query status before retrieval"
        assert "Phase 1 completion gate" in text, f"{path} must gate novelty checking on evidence completion"
        assert "all three artifacts exist" in text, f"{path} must gate Phase 1 on artifact existence"
        assert "unclear" in text, f"{path} must represent no-evidence cases honestly"


def test_research_lit_defines_per_query_zotero_semantic_search_contract() -> None:
    for path in LITERATURE_SKILLS:
        text = read(path)
        assert "QUERY_PACK.md" in text, f"{path} must consume QUERY_PACK.md"
        assert "EVIDENCE_MATRIX.md" in text, f"{path} must write EVIDENCE_MATRIX.md"
        assert "mcp__zotero_mcp__semantic_search" in text, (
            f"{path} must name the preferred Zotero semantic-search tool"
        )
        assert "for each query" in text.lower(), f"{path} must run one search per query"
        assert "NO_HIT" in text, f"{path} must record query misses instead of dropping them"
        assert "one coverage row for every Query ID" in text, (
            f"{path} must retain a row for queries with no retrieved paper"
        )
        assert "explicitly requested" in text and "not configured" in text, (
            f"{path} must surface a requested-but-missing Zotero MCP"
        )


def test_evidence_matrix_has_a_claim_to_evidence_shape() -> None:
    text = read("skills/research-lit/SKILL.md")
    for field in (
        "Draft claim",
        "Query ID",
        "Query status",
        "itemKey",
        "Matched chunk",
        "supports/contradicts/limits",
        "Verification status",
    ):
        assert field in text, f"evidence matrix is missing field: {field}"
