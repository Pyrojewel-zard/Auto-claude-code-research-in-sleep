#!/usr/bin/env python3
"""Focused tests for the deterministic research-evidence coverage checker."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_evidence_coverage import check_coverage, main  # noqa: E402


def claims_doc(load_bearing=False, support_basis="none"):
    return {"claims": [{"claim_id": "C001", "type": "research_claim",
            "text_span": "The proposed mechanism improves robustness.",
            "location": {"file": "EVIDENCE_MATRIX.md"}, "load_bearing": load_bearing,
            "support_basis": support_basis, "evidence_anchor": "a" * 64}]}


def coverage_doc(items=None, counter_query_run=True):
    return {"branch_id": "b1", "source_policy": "zotero",
            "counter_query_run": counter_query_run,
            "queries": [{"query_id": "Q1", "status": "SEARCHED",
                         "evidence_directions": ["supports"],
                         "source": "zotero", "evidence_item_keys": items or []}]}


def one(findings, pattern_id):
    return next(f for f in findings if f["pattern_id"] == pattern_id)


def for_claim(findings, claim_id):
    return [f for f in findings if f["evidence"]
            and f["evidence"][0].get("claim_id") == claim_id]


def test_load_bearing_claim_without_verified_support_is_critical():
    findings = check_coverage(claims_doc(load_bearing=True), coverage_doc(items=[]))
    assert one(findings, "HP-EVIDENCE-UNSUPPORTED")["severity"] == "critical"


def test_relevance_score_cannot_be_support():
    findings = check_coverage(
        claims_doc(load_bearing=True, support_basis="relevance_score"),
        coverage_doc(items=["Z1"]),
    )
    assert one(findings, "HP-EVIDENCE-RELEVANCE-AS-SUPPORT")["severity"] == "critical"


def test_missing_counter_query_is_soft():
    findings = check_coverage(claims_doc(), coverage_doc(counter_query_run=False))
    assert one(findings, "HP-EVIDENCE-NO-COUNTERSEARCH")["severity"] == "minor"


def test_no_hit_is_preserved_as_unavailable_support():
    coverage = coverage_doc(items=[])
    coverage["queries"][0]["status"] = "NO_HIT"
    findings = check_coverage(claims_doc(load_bearing=True), coverage)
    finding = one(findings, "HP-EVIDENCE-UNSUPPORTED")
    assert finding["severity"] == "critical"
    assert "NO_HIT" in finding["description"]
    assert finding["coverage"]["query_statuses"] == {"Q1": "NO_HIT"}


def test_unverified_evidence_is_major_not_critical():
    coverage = coverage_doc(items=["Z1"])
    coverage["queries"][0]["status"] = "UNVERIFIED"
    coverage["artifact_hashes"] = {"Z1": "z" * 64}
    findings = check_coverage(claims_doc(load_bearing=True), coverage)
    assert one(findings, "HP-EVIDENCE-UNVERIFIED")["severity"] == "major"
    assert not any(f["severity"] == "critical" for f in findings)


def test_missing_item_provenance_is_minor():
    coverage = coverage_doc(items=["Z1"])
    coverage["artifact_hashes"] = {"OTHER": "b" * 64}
    findings = check_coverage(claims_doc(load_bearing=True), coverage)
    finding = one(findings, "HP-EVIDENCE-PROVENANCE-GAP")
    assert finding["severity"] == "minor"
    assert "Z1" in finding["description"]


def test_query_linkage_is_per_claim_in_multi_claim_ledger():
    first = claims_doc(load_bearing=True)["claims"][0]
    first["query_ids"] = ["Q1"]
    second = claims_doc(load_bearing=True)["claims"][0]
    second.update({"claim_id": "C002", "text_span": "A second claim lacks support.",
                   "evidence_anchor": "b" * 64, "query_ids": ["Q2"]})
    coverage = {
        "branch_id": "b1",
        "source_policy": "zotero",
        "queries": [
            {"query_id": "Q1", "status": "SEARCHED", "evidence_directions": ["supports"],
             "source": "zotero", "evidence_item_keys": ["Z1"]},
            {"query_id": "Q2", "status": "SEARCHED", "evidence_directions": ["supports"],
             "source": "zotero", "evidence_item_keys": []},
        ],
        "artifact_hashes": {"Z1": "z" * 64},
    }

    findings = check_coverage({"claims": [first, second]}, coverage)
    assert not for_claim(findings, "C001")
    assert one(for_claim(findings, "C002"), "HP-EVIDENCE-UNSUPPORTED")["severity"] == "critical"


def test_unlinked_multi_claims_do_not_share_branch_support():
    first = claims_doc(load_bearing=True)["claims"][0]
    second = claims_doc(load_bearing=True)["claims"][0]
    second.update({"claim_id": "C002", "text_span": "A second claim lacks support.",
                   "evidence_anchor": "b" * 64})
    coverage = coverage_doc(items=["Z1"])
    coverage["artifact_hashes"] = {"Z1": "z" * 64}

    findings = check_coverage({"claims": [first, second]}, coverage)
    assert one(for_claim(findings, "C002"), "HP-EVIDENCE-UNSUPPORTED")["severity"] == "critical"


def test_hypothesis_is_not_treated_as_an_evidence_obligation():
    claim = claims_doc(load_bearing=True)["claims"][0]
    claim.update({"type": "hypothesis", "verification_status": "VERIFY_PENDING"})
    coverage = coverage_doc(items=["Z1"])
    coverage["queries"][0]["status"] = "UNVERIFIED"

    assert check_coverage({"claims": [claim]}, coverage) == []


def test_unlinked_research_claim_does_not_borrow_hypothesis_support():
    claim = claims_doc(load_bearing=True)["claims"][0]
    hypothesis = claims_doc()["claims"][0]
    hypothesis.update({
        "claim_id": "H001",
        "type": "hypothesis",
        "text_span": "The mechanism may generalize beyond the target task.",
        "evidence_anchor": "h" * 64,
        "query_ids": ["Q-HYPOTHESIS"],
    })
    coverage = coverage_doc(items=[])
    coverage["queries"] = [{
        "query_id": "Q-HYPOTHESIS",
        "status": "SEARCHED",
        "evidence_directions": ["supports"],
        "source": "zotero",
        "evidence_item_keys": ["Z-HYPOTHESIS"],
    }]
    coverage["artifact_hashes"] = {"Z-HYPOTHESIS": "z" * 64}

    findings = check_coverage({"claims": [claim, hypothesis]}, coverage)

    finding = one(for_claim(findings, "C001"), "HP-EVIDENCE-UNSUPPORTED")
    assert finding["severity"] == "critical"


def test_incomplete_claim_anchor_fails_closed_to_info():
    for field in ("claim_id", "text_span", "evidence_anchor"):
        claim = claims_doc(load_bearing=True)["claims"][0]
        claim.pop(field)
        findings = check_coverage({"claims": [claim]}, coverage_doc())
        assert findings
        assert all(f["severity"] == "info" for f in findings)
        assert all(f["evidence"] == [] for f in findings)


def test_findings_have_stable_unique_ids_and_copy_span_anchor():
    coverage = coverage_doc(items=["Z1"], counter_query_run=False)
    coverage["artifact_hashes"] = {"OTHER": "b" * 64}
    first = check_coverage(claims_doc(load_bearing=True), coverage)
    second = check_coverage(claims_doc(load_bearing=True), coverage)

    assert [f["finding_id"] for f in first] == [f["finding_id"] for f in second]
    assert len({f["finding_id"] for f in first}) == len(first)
    for finding in first:
        evidence = finding["evidence"][0]
        assert evidence["claim_id"] == "C001"
        assert evidence["span"] == claims_doc()["claims"][0]["text_span"]
        assert evidence["artifact_hash"] == "a" * 64


def test_cli_writes_findings_json(tmp_path):
    ledger_path = tmp_path / "claims.json"
    coverage_path = tmp_path / "coverage.json"
    output_path = tmp_path / "findings.json"
    ledger_path.write_text(json.dumps(claims_doc(load_bearing=True)), encoding="utf-8")
    coverage_path.write_text(json.dumps(coverage_doc()), encoding="utf-8")

    assert main(["--ledger", str(ledger_path), "--coverage", str(coverage_path),
                 "--out", str(output_path)]) == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert one(payload, "HP-EVIDENCE-UNSUPPORTED")["skill"] == "evidence-audit"
