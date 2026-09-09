import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

from research_gate import (  # noqa: E402
    InvalidReport,
    append_obligations,
    evaluate_branch,
    obligation_fingerprint,
)


def _state(*branch_ids):
    return {
        "branches": {
            branch_id: {
                "status": "BRANCH_RESEARCHED",
                "artifact_hashes": {"evidence": "evidence-v1"},
            }
            for branch_id in branch_ids
        }
    }


def _report(verdict, artifact_hash="evidence-v1", findings=None):
    return {
        "overall_verdict": verdict,
        "artifact_hashes": {"evidence": artifact_hash},
        "findings": list(findings or []),
    }


def _finding(span="claim span"):
    return {
        "skill": "claim-audit",
        "pattern": "missing-support",
        "claim": "C1",
        "span": span,
        "severity": "major",
    }


def test_anti_verdicts_map_to_branch_promotion_states():
    assert evaluate_branch(_report("HARD_FLAGS"), _state("b1"), "b1") == "NEEDS_WORK"
    assert evaluate_branch(_report("SOFT_FLAGS"), _state("b1"), "b1") == (
        "PROMOTABLE_WITH_OBLIGATIONS"
    )
    assert evaluate_branch(
        _report("CLEAN_GIVEN_EVIDENCE"), _state("b1"), "b1"
    ) == "PROMOTABLE"


def test_hard_flags_block_only_the_reported_branch():
    state = _state("b1", "b2")

    assert evaluate_branch(_report("HARD_FLAGS"), state, "b1") == "NEEDS_WORK"
    assert state["branches"]["b1"]["status"] == "NEEDS_WORK"
    assert state["branches"]["b2"]["status"] == "BRANCH_RESEARCHED"


def test_unknown_verdict_is_rejected():
    with pytest.raises(InvalidReport):
        evaluate_branch(_report("UNKNOWN"), _state("b1"), "b1")


def test_stale_audit_hash_is_rejected():
    state = _state("b1")
    report = _report("CLEAN_GIVEN_EVIDENCE", artifact_hash="old-evidence")

    with pytest.raises(InvalidReport, match="hash"):
        evaluate_branch(report, state, "b1")


def test_artifact_hash_mismatch_is_rejected_even_for_clean_report():
    state = {
        "branches": {
            "b1": {"status": "BRANCH_RESEARCHED", "artifact_hash": "artifact-v2"}
        }
    }
    report = {
        "overall_verdict": "CLEAN_GIVEN_EVIDENCE",
        "artifact_hash": "artifact-v1",
        "findings": [],
    }

    with pytest.raises(InvalidReport, match="hash"):
        evaluate_branch(report, state, "b1")


def test_obligation_fingerprint_is_stable_and_branch_scoped():
    finding = _finding("a   span")
    same_finding = dict(finding, span="a span", finding_id="different")

    assert obligation_fingerprint("b1", finding) == obligation_fingerprint(
        "b1", same_finding
    )
    assert obligation_fingerprint("b1", finding) != obligation_fingerprint("b2", finding)
    assert obligation_fingerprint("b1", finding) != obligation_fingerprint(
        "b1", _finding("another span")
    )


def test_append_obligations_is_append_only_and_deduplicates(tmp_path):
    path = Path(tmp_path) / "OBLIGATIONS.json"
    first = _finding()
    second = _finding("second span")

    append_obligations(path, [first], "b1")
    append_obligations(path, [first, second], "b1")
    append_obligations(path, [], "b1")

    ledger = json.loads(path.read_text(encoding="utf-8"))
    assert len(ledger["obligations"]) == 2
    assert ledger["obligations"][0]["branch"] == "b1"
    assert ledger["obligations"][0]["status"] == "OPEN"


def test_append_obligations_keeps_same_claim_separate_per_branch(tmp_path):
    path = Path(tmp_path) / "obligations.json"
    finding = _finding()

    append_obligations(path, [finding], "b1")
    append_obligations(path, [finding], "b2")

    ledger = json.loads(path.read_text(encoding="utf-8"))
    assert len(ledger["obligations"]) == 2
    assert {row["branch"] for row in ledger["obligations"]} == {"b1", "b2"}
