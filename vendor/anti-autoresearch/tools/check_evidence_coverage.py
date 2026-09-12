#!/usr/bin/env python3
"""Deterministic checks for research-claim evidence coverage.

This checker audits the evidence records already present in a Task 1 claims
ledger and query-coverage document. It does not retrieve sources or decide the
overall report verdict; it emits ordinary span-anchored ``evidence-audit``
findings for the deterministic adjudicator.
"""
import argparse
import json
import sys


RESEARCH_CLAIM_TYPES = {"research_claim", "evidence_statement", "hypothesis"}
VERIFIED_SUPPORT_BASES = {"quoted_span", "annotation", "metadata"}
UNVERIFIED_QUERY_STATES = {"UNVERIFIED", "UNSEARCHABLE", "ERROR"}


def _is_research_claim(claim):
    """Return whether a claim carries the Task 1 research-evidence fields."""
    if not isinstance(claim, dict):
        return False
    if claim.get("type") == "hypothesis":
        return False
    if claim.get("type") in RESEARCH_CLAIM_TYPES:
        return True
    return any(field in claim for field in (
        "query_ids", "evidence_direction", "verification_status",
        "load_bearing", "support_basis",
    ))


def _selected_queries(claim, queries, by_id, allow_branch_fallback):
    """Select a claim's coverage queries without inventing retrieval links.

    The Task 1 annotations make ``query_ids`` optional for compatibility. A
    branch-wide fallback is safe only when there is exactly one auditable
    claim and no claim of any type declares explicit query links. With any
    explicit linkage elsewhere, absent linkage is itself a coverage gap; no
    branch query is borrowed by the claim.
    """
    if "query_ids" not in claim:
        if allow_branch_fallback:
            return list(queries), [], False
        return [], [], True

    query_ids = claim.get("query_ids")
    if not isinstance(query_ids, list):
        return [], [], False

    selected, missing = [], []
    for query_id in query_ids:
        if query_id in by_id:
            selected.append(by_id[query_id])
        else:
            missing.append(query_id)
    return selected, missing, False


def _coverage_summary(queries, missing_query_ids, linkage_required=False):
    """Return deterministic, human-readable coverage metadata for a finding."""
    selected = sorted(
        ((q.get("query_id"), q) for q in queries),
        key=lambda pair: str(pair[0]),
    )
    statuses = {
        str(query_id): query.get("status")
        for query_id, query in selected
        if query_id is not None
    }
    item_keys = []
    seen = set()
    for _, query in selected:
        keys = query.get("evidence_item_keys", [])
        if not isinstance(keys, list):
            continue
        for key in keys:
            if key not in seen:
                seen.add(key)
                item_keys.append(key)
    return {
        "query_ids": [str(query_id) for query_id, _ in selected],
        "query_statuses": statuses,
        "evidence_item_keys": item_keys,
        "missing_query_ids": [str(query_id) for query_id in missing_query_ids],
        "explicit_query_linkage_required": linkage_required,
    }


def _has_valid_anchor(claim):
    """Return whether a claim can safely anchor an above-info finding."""
    return all(
        isinstance(claim.get(field), str) and bool(claim[field].strip())
        for field in ("claim_id", "text_span", "evidence_anchor")
    )


def _evidence(claim):
    """Build the required span-anchored evidence entry for a claim."""
    return {
        "claim_id": claim["claim_id"],
        "span": claim["text_span"],
        "location": claim.get("location", {}),
        "artifact_hash": claim["evidence_anchor"],
    }


def _finding(claim, pattern_id, title, description, severity, coverage, action):
    """Build one deterministic finding using the shared finding contract."""
    anchored = _has_valid_anchor(claim)
    final_severity = severity if anchored else "info"
    if not anchored:
        description += " The claim anchor is incomplete; this finding is informational only."
    return {
        "skill": "evidence-audit",
        "pattern_id": pattern_id,
        "title": title,
        "description": description,
        "severity": final_severity,
        "observability_level_required": 0,
        "evidence": [_evidence(claim)] if anchored else [],
        "verdict_local": "fail" if final_severity in {"critical", "major"} else "warn",
        "reviewer": {"deterministic": True},
        "false_positive_risk": "low",
        "recommended_reviewer_action": action,
        "coverage": coverage,
    }


def _has_supporting_item(query):
    """Return whether a searched query records support evidence items."""
    if query.get("status") != "SEARCHED":
        return False
    directions = query.get("evidence_directions", [])
    keys = query.get("evidence_item_keys", [])
    return isinstance(directions, list) and "supports" in directions \
        and isinstance(keys, list) and bool(keys)


def _has_provenance_gap(queries, artifact_hashes):
    """Return missing/empty artifact hashes for the selected evidence items."""
    missing = []
    for query in queries:
        keys = query.get("evidence_item_keys", [])
        if not isinstance(keys, list):
            continue
        for key in keys:
            value = artifact_hashes.get(key) if isinstance(artifact_hashes, dict) else None
            if not isinstance(value, str) or not value:
                if key not in missing:
                    missing.append(key)
    return missing


def check_coverage(claims_doc: dict, coverage_doc: dict) -> list[dict]:
    """Return deterministic, span-anchored evidence-audit findings.

    A searched query with an evidence item in the ``supports`` direction is
    recorded support. ``NO_HIT`` remains a distinct query state and therefore
    cannot establish support. Query states such as ``UNVERIFIED`` are reported
    as unverifiable support rather than upgraded to a hard unsupported claim.
    """
    claims = claims_doc.get("claims", []) if isinstance(claims_doc, dict) else []
    raw_queries = coverage_doc.get("queries", []) if isinstance(coverage_doc, dict) else []
    queries = [q for q in raw_queries if isinstance(q, dict)]
    by_id = {
        q.get("query_id"): q for q in queries
        if q.get("query_id") is not None
    }
    artifact_hashes = coverage_doc.get("artifact_hashes", {}) \
        if isinstance(coverage_doc, dict) else {}
    counter_query_missing = (isinstance(coverage_doc, dict)
                             and coverage_doc.get("counter_query_run") is False)

    research_claims = [
        (index, claim) for index, claim in enumerate(claims)
        if _is_research_claim(claim)
    ]
    research_claims.sort(key=lambda pair: (str(pair[1].get("claim_id", "")), pair[0]))
    has_explicit_query_links = any(
        isinstance(claim, dict) and "query_ids" in claim
        for claim in claims
    )
    allow_branch_fallback = len(research_claims) == 1 and not has_explicit_query_links

    findings = []
    for _, claim in research_claims:
        selected, missing_query_ids, linkage_required = _selected_queries(
            claim, queries, by_id, allow_branch_fallback
        )
        coverage = _coverage_summary(selected, missing_query_ids, linkage_required)
        claim_status = claim.get("verification_status")
        support_basis = claim.get("support_basis", "none")
        supporting = any(_has_supporting_item(query) for query in selected)
        query_states = {query.get("status") for query in selected}
        unverified = claim_status in {"UNVERIFIED", "VERIFY_PENDING"} \
            or bool(query_states & UNVERIFIED_QUERY_STATES) \
            or bool(missing_query_ids)
        has_claim_support = (
            claim_status == "VERIFIED" and support_basis in VERIFIED_SUPPORT_BASES
        )
        has_verified_support = supporting or has_claim_support

        if support_basis == "relevance_score":
            findings.append(_finding(
                claim,
                "HP-EVIDENCE-RELEVANCE-AS-SUPPORT",
                "Relevance score used as evidence support",
                "The claim records a relevance score as its support basis. A retrieval "
                "relevance score is not evidence that the claim is true; inspect the "
                "quoted source span or bounded metadata that should support it.",
                "critical",
                coverage,
                "Replace the relevance score with a recorded, claim-bearing evidence "
                "span or mark the claim as unverified.",
            ))
        elif unverified:
            states = sorted(str(state) for state in query_states if state is not None)
            if missing_query_ids:
                states.append("MISSING_QUERY")
            state_text = ", ".join(states) or str(claim_status)
            findings.append(_finding(
                claim,
                "HP-EVIDENCE-UNVERIFIED",
                "Claim support is not verified",
                f"The recorded support for this claim is not verified ({state_text}); "
                "the coverage record does not establish a verified evidence basis.",
                "major",
                coverage,
                "Verify the cited evidence item and update the claim and query status "
                "with the exact support relationship.",
            ))
        elif not has_verified_support:
            states = sorted(str(state) for state in query_states if state is not None)
            state_text = f" Query states: {', '.join(states)}." if states else ""
            linkage_text = (
                " No query_ids link this claim to branch coverage; explicit linkage is "
                "required when multiple research claims are present."
                if linkage_required else ""
            )
            findings.append(_finding(
                claim,
                "HP-EVIDENCE-UNSUPPORTED",
                "Claim lacks verified evidence support",
                "The claim has no recorded verified supporting evidence item."
                f"{state_text}{linkage_text} A NO_HIT query is preserved as no supporting hit, not "
                "as evidence for the claim.",
                "critical" if claim.get("load_bearing") is True else "minor",
                coverage,
                "Locate a claim-bearing source span, record its evidence item and "
                "provenance, or mark the claim as unverified.",
            ))

        missing_items = _has_provenance_gap(selected, artifact_hashes)
        if missing_items:
            findings.append(_finding(
                claim,
                "HP-EVIDENCE-PROVENANCE-GAP",
                "Evidence item provenance is incomplete",
                "Evidence item key(s) lack a recorded artifact hash: "
                + ", ".join(str(key) for key in missing_items) + ".",
                "minor",
                coverage,
                "Record the source artifact hash for every evidence item before "
                "relying on the item for audit support.",
            ))

        if counter_query_missing:
            findings.append(_finding(
                claim,
                "HP-EVIDENCE-NO-COUNTERSEARCH",
                "No counter-query was recorded",
                "The coverage record declares that no counter-query was run for this "
                "research branch, so the support claim has not been stress-tested "
                "against an opposing search direction.",
                "minor",
                coverage,
                "Run and record a counter-query with its terminal status and evidence "
                "items, or explain why a counter-query is not searchable.",
            ))

    for index, finding in enumerate(findings, 1):
        finding["finding_id"] = f"EVID{index:03d}"
    return findings


def main(argv: list[str] | None = None) -> int:
    """Read --ledger/--coverage and write a findings object to --out."""
    ap = argparse.ArgumentParser(description="Deterministic research evidence coverage checks.")
    ap.add_argument("--ledger", required=True, help="claims.json from the evidence ledger")
    ap.add_argument("--coverage", required=True, help="query_coverage.json from the research branch")
    ap.add_argument("--out", default="evidence-audit.deterministic.findings.json")
    args = ap.parse_args(argv)

    with open(args.ledger, "r", encoding="utf-8") as fh:
        claims_doc = json.load(fh)
    with open(args.coverage, "r", encoding="utf-8") as fh:
        coverage_doc = json.load(fh)

    findings = check_coverage(claims_doc, coverage_doc)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2, ensure_ascii=False)
    print(f"evidence coverage findings: {len(findings)} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
