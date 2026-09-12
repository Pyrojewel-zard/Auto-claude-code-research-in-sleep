#!/usr/bin/env python3
"""Classify an upstream workflow candidate before ARIS adopts it.

This tool is deliberately advisory and offline.  It validates a small
candidate manifest and produces a stable review record; it never fetches,
merges, installs, or changes the default profile.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CANONICAL_ENTRIES = frozenset(
    {
        "autoresearch-topic",
        "autoresearch-proposal",
        "research-write",
        "research-audit",
    }
)
ENTRY_KINDS = frozenset({"research", "write", "audit", "other"})
DECISIONS = frozenset({"MERGE", "ADAPT", "OPTIONAL", "REJECT"})
ALLOWED_SOURCES = frozenset({"zotero", "local", "anti-vendored", "internal", "none"})
FORBIDDEN_SOURCES = frozenset(
    {"web", "websearch", "webfetch", "arxiv", "openalex", "semantic-scholar", "exa", "gemini"}
)
ALLOWED_HOSTS = frozenset({"codex", "codex-primary"})
ALLOWED_INTERNAL_DEPENDENCIES = frozenset(
    {"research_state", "research_gate", "forensics_gate", "zotero", "anti-vendored", "shared-references"}
)
REQUIRED_FIELDS = {"name", "description", "entry_kind", "sources", "host", "dependencies", "tests"}


class CandidateError(ValueError):
    """Raised when a candidate manifest is malformed."""


def _string(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise CandidateError(f"{field} must be a non-empty string")
    return value.strip()


def _strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise CandidateError(f"{field} must be a list of non-empty strings")
    return [item.strip().lower() for item in value]


def _validate_candidate(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise CandidateError("candidate must be a JSON object")
    missing = sorted(REQUIRED_FIELDS - set(candidate))
    if missing:
        raise CandidateError(f"candidate is missing required fields: {', '.join(missing)}")

    result = dict(candidate)
    result["name"] = _string(candidate["name"], "name")
    result["description"] = _string(candidate["description"], "description")
    result["entry_kind"] = _string(candidate["entry_kind"], "entry_kind").lower()
    if result["entry_kind"] not in ENTRY_KINDS:
        raise CandidateError(f"entry_kind must be one of {sorted(ENTRY_KINDS)}")
    result["sources"] = _strings(candidate["sources"], "sources")
    result["host"] = _string(candidate["host"], "host").lower()
    result["dependencies"] = _strings(candidate["dependencies"], "dependencies")
    result["tests"] = _strings(candidate["tests"], "tests")
    result["fallback_policy"] = _string(
        candidate.get("fallback_policy", "none"), "fallback_policy"
    ).lower()
    if result["fallback_policy"] not in {"none", "explicit", "silent"}:
        raise CandidateError("fallback_policy must be one of ['explicit', 'none', 'silent']")
    result["review_context"] = _string(
        candidate.get("review_context", "not-applicable"), "review_context"
    ).lower()
    if result["review_context"] not in {"not-applicable", "isolated", "same-family-isolated", "same-context"}:
        raise CandidateError("review_context has an unsupported value")
    result["reviewed_commit"] = _string(
        candidate.get("reviewed_commit", "unreviewed"), "reviewed_commit"
    )
    return result


def classify_candidate(
    candidate: dict[str, Any], canonical_entries: set[str] | frozenset[str] | None = None
) -> dict[str, Any]:
    """Return a deterministic upstream adoption decision.

    The function intentionally does not judge scientific usefulness.  It only
    identifies whether a candidate is structurally safe to merge, needs an
    explicit adaptation, belongs outside the core, or violates a hard policy.
    """

    item = _validate_candidate(candidate)
    canonical = set(CANONICAL_ENTRIES if canonical_entries is None else canonical_entries)
    name = item["name"]
    description = f"{name} {item['description']}".lower()
    sources = set(item["sources"])
    forbidden = sorted(sources & FORBIDDEN_SOURCES)
    unknown_sources = sorted(sources - ALLOWED_SOURCES - FORBIDDEN_SOURCES)
    overlap = name in canonical
    relevant = item["entry_kind"] != "other" or any(
        token in description
        for token in ("research", "autoresearch", "proposal", "zotero", "evidence", "audit", "write")
    )
    dependency_issues = sorted(
        dependency
        for dependency in item["dependencies"]
        if dependency not in ALLOWED_INTERNAL_DEPENDENCIES
    )

    checks: dict[str, str] = {
        "entry_overlap": "fail" if overlap else "pass",
        "relevance": "pass" if relevant else "review",
        "source_policy": "pass" if not forbidden and not unknown_sources else "warn",
        "codex_compatibility": "pass" if item["host"] in ALLOWED_HOSTS else "warn",
        "review_independence": (
            "fail" if item["review_context"] == "same-context" else "pass"
        ),
        "dependency_fanout": "warn" if dependency_issues or len(item["dependencies"]) > 3 else "pass",
        "test_evidence": "pass" if item["tests"] else "warn",
    }
    reasons: list[str] = []

    if overlap:
        decision = "REJECT"
        reasons.append("candidate name overlaps a canonical ARIS entry")
    elif item["fallback_policy"] == "silent" and (forbidden or unknown_sources):
        decision = "REJECT"
        reasons.append("silent fallback to external scholarly sources violates the Zotero boundary")
    elif item["review_context"] == "same-context":
        decision = "REJECT"
        reasons.append("same-context review cannot establish reviewer independence")
    elif not relevant:
        decision = "OPTIONAL"
        reasons.append("candidate does not match the four-entry research product")
    else:
        adaptation_reasons: list[str] = []
        if forbidden or unknown_sources:
            adaptation_reasons.append("source set needs an explicit Zotero-compatible adapter")
        if item["host"] not in ALLOWED_HOSTS:
            adaptation_reasons.append("host contract needs Codex-primary adaptation")
        if dependency_issues or len(item["dependencies"]) > 3:
            adaptation_reasons.append("dependency fan-out exceeds the reduced profile boundary")
        if not item["tests"]:
            adaptation_reasons.append("candidate has no focused regression evidence")
        if item["entry_kind"] == "audit" and item["review_context"] == "not-applicable":
            adaptation_reasons.append("audit flow must declare an isolated reviewer context")
        if adaptation_reasons:
            decision = "ADAPT"
            reasons.extend(adaptation_reasons)
        else:
            decision = "MERGE"
            reasons.append("candidate satisfies the structural default-profile checks")

    return {
        "candidate": {
            "name": name,
            "entry_kind": item["entry_kind"],
            "reviewed_commit": item["reviewed_commit"],
        },
        "decision": decision,
        "checks": checks,
        "reasons": reasons,
        "adoption": "manual-review-required; this tool never merges or changes the default profile",
    }


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CandidateError(f"cannot read candidate: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CandidateError(f"candidate is not valid JSON: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    try:
        report = classify_candidate(_load_json(args.candidate))
    except CandidateError as exc:
        print(f"upstream-flow-review: {exc}", file=sys.stderr)
        return 2

    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
