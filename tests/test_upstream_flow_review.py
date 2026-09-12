import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from upstream_flow_review import CandidateError, classify_candidate  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "upstream_flow_review.py"


def candidate(**overrides):
    value = {
        "name": "zotero-branch-helper",
        "description": "Codex evidence branch helper for Zotero autoresearch",
        "entry_kind": "research",
        "sources": ["zotero", "local"],
        "host": "codex",
        "dependencies": ["research_state", "research_gate"],
        "tests": ["tests/test_zotero_branch_helper.py"],
        "fallback_policy": "none",
        "review_context": "not-applicable",
        "reviewed_commit": "0123456789abcdef0123456789abcdef01234567",
    }
    value.update(overrides)
    return value


def test_zotero_codex_candidate_is_mergeable():
    result = classify_candidate(candidate())
    assert result["decision"] == "MERGE"
    assert all(value == "pass" for value in result["checks"].values())


def test_multi_source_candidate_requires_adaptation():
    result = classify_candidate(candidate(sources=["zotero", "websearch"], fallback_policy="explicit"))
    assert result["decision"] == "ADAPT"
    assert "source set" in " ".join(result["reasons"])


def test_silent_external_fallback_is_rejected():
    result = classify_candidate(candidate(sources=["zotero", "arxiv"], fallback_policy="silent"))
    assert result["decision"] == "REJECT"


def test_silent_unknown_fallback_is_rejected():
    result = classify_candidate(candidate(sources=["zotero", "unknown-db"], fallback_policy="silent"))
    assert result["decision"] == "REJECT"


def test_duplicate_canonical_entry_is_rejected():
    result = classify_candidate(candidate(name="autoresearch-topic"))
    assert result["decision"] == "REJECT"
    assert result["checks"]["entry_overlap"] == "fail"


def test_unrelated_candidate_is_optional():
    result = classify_candidate(
        candidate(
            name="slide-theme-builder",
            description="A conference slide theme",
            entry_kind="other",
            sources=["none"],
            dependencies=[],
            tests=["tests/test_slide_theme.py"],
        )
    )
    assert result["decision"] == "OPTIONAL"


def test_same_context_audit_is_rejected():
    result = classify_candidate(
        candidate(
            name="upstream-audit",
            description="evidence audit",
            entry_kind="audit",
            sources=["local"],
            review_context="same-context",
        )
    )
    assert result["decision"] == "REJECT"


def test_malformed_candidate_is_rejected():
    with pytest.raises(CandidateError):
        classify_candidate({"name": "missing-fields"})


def test_cli_writes_stable_json_report(tmp_path: Path):
    candidate_path = tmp_path / "candidate.json"
    report_path = tmp_path / "review.json"
    candidate_path.write_text(json.dumps(candidate()), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(TOOL), "--candidate", str(candidate_path), "--out", str(report_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    report = json.loads(result.stdout)
    assert report == json.loads(report_path.read_text(encoding="utf-8"))
    assert report["decision"] == "MERGE"
