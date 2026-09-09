#!/usr/bin/env python3
"""Branch promotion adapter for Anti-Autoresearch evidence reports.

Anti-Autoresearch owns the report verdict.  This module only validates that a
report carries a known verdict, binds it to the researched branch, maps the
verbatim token to ARIS's promotion state, and records branch-local obligations.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from research_state import (
        PROMOTION_STATES,
        InvalidState,
        InvalidTransition,
        StaleAudit,
        transition,
        validate_audit_hashes,
        validate_query_statuses,
    )
except ImportError:  # package import: ``from tools import research_gate``
    from tools.research_state import (
        PROMOTION_STATES,
        InvalidState,
        InvalidTransition,
        StaleAudit,
        transition,
        validate_audit_hashes,
        validate_query_statuses,
    )


class InvalidReport(InvalidState):
    """The supplied Anti report cannot be used by the branch gate."""


# REVIEW_UNAVAILABLE is part of the existing Anti report contract.  It is a
# known, fail-closed report state, not a new verdict computed by this adapter.
ANTI_VERDICTS = {
    "HARD_FLAGS",
    "SOFT_FLAGS",
    "CLEAN_GIVEN_EVIDENCE",
    "REVIEW_UNAVAILABLE",
}
VERDICT_TO_PROMOTION = {
    "HARD_FLAGS": "NEEDS_WORK",
    "SOFT_FLAGS": "PROMOTABLE_WITH_OBLIGATIONS",
    "CLEAN_GIVEN_EVIDENCE": "PROMOTABLE",
    "REVIEW_UNAVAILABLE": "NEEDS_WORK",
}

_FINGERPRINT_RE = re.compile(
    r"(?:aris-obligation|obligation-fingerprint)\s*[:=]\s*([0-9a-f]{64})",
    re.IGNORECASE,
)


def _normalise_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _unique_sorted(values: Sequence[Any]) -> list[str]:
    return sorted({item for item in (_normalise_text(value) for value in values) if item})


def _finding_identity_parts(finding: Mapping[str, Any]) -> dict[str, Any]:
    evidence = finding.get("evidence")
    evidence_items = evidence if isinstance(evidence, list) else []

    claims: list[Any] = []
    spans: list[Any] = []
    if finding.get("claim_id") is not None:
        claims.append(finding.get("claim_id"))
    for key in ("claim", "claim_text", "claim_span"):
        if finding.get(key) is not None:
            claims.append(finding.get(key))
            break
    if finding.get("span") is not None:
        spans.append(finding.get("span"))

    for item in evidence_items:
        if not isinstance(item, Mapping):
            continue
        for key in ("claim_id", "claim", "claim_text"):
            if item.get(key) is not None:
                claims.append(item.get(key))
                break
        if item.get("span") is not None:
            spans.append(item.get("span"))

    return {
        "skill": _normalise_text(finding.get("skill")),
        "pattern": _normalise_text(
            finding.get("pattern_id") or finding.get("pattern")
        ),
        "claim": _unique_sorted(claims),
        "span": _unique_sorted(spans),
    }


def obligation_fingerprint(
    finding: Mapping[str, Any] | str, branch_id: str | Mapping[str, Any]
) -> str:
    """Return a stable identity over branch, skill, pattern, claim, and span.

    Positional finding IDs and mutable artifact hashes are intentionally absent:
    changing either must not duplicate the same unresolved obligation.
    """

    # Keep the natural ``(finding, branch_id)`` order used internally while
    # accepting the brief's human-readable ``(branch_id, finding)`` spelling.
    if isinstance(finding, str) and isinstance(branch_id, Mapping):
        finding, branch_id = branch_id, finding
    if not isinstance(finding, Mapping):
        raise InvalidState("finding must be an object")
    if not isinstance(branch_id, str) or not branch_id.strip():
        raise InvalidState("branch_id must be a non-empty string")
    basis = _finding_identity_parts(finding)
    basis["branch"] = _normalise_text(branch_id)
    return hashlib.sha256(
        json.dumps(basis, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        .encode("utf-8")
    ).hexdigest()


# Shorter alias for callers familiar with the existing forensics gate API.
fingerprint = obligation_fingerprint


def _eligible_finding(finding: Mapping[str, Any]) -> bool:
    weight = finding.get("_verdict_weight", 1)
    if weight == 0:
        return False
    severity = finding.get("_severity_final", finding.get("severity"))
    return severity != "info"


def _obligation_record(finding: Mapping[str, Any], branch_id: str) -> dict[str, Any]:
    identity = _finding_identity_parts(finding)
    obligation_id = obligation_fingerprint(finding, branch_id)
    record = {
        "obligation_id": obligation_id,
        "fingerprint": obligation_id,
        "branch": _normalise_text(branch_id),
        "branch_id": _normalise_text(branch_id),
        "skill": identity["skill"],
        "pattern": identity["pattern"],
        "pattern_id": identity["pattern"],
        "claim": identity["claim"],
        "span": identity["span"],
        "status": "OPEN",
        "finding": copy.deepcopy(dict(finding)),
    }
    return record


def _records_from_findings(
    findings: Sequence[Mapping[str, Any]], branch_id: str
) -> list[dict[str, Any]]:
    if isinstance(findings, (str, bytes)) or not isinstance(findings, Sequence):
        raise InvalidState("findings must be a list")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, finding in enumerate(findings):
        if not isinstance(finding, Mapping):
            raise InvalidState(f"finding[{index}] must be an object")
        if not _eligible_finding(finding):
            continue
        record = _obligation_record(finding, branch_id)
        if record["obligation_id"] not in seen:
            seen.add(record["obligation_id"])
            records.append(record)
    return records


def _load_json_ledger(path: Path) -> tuple[dict[str, Any], set[str]]:
    if not path.exists():
        return {"ledger_version": "1", "obligations": []}, set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidState(f"cannot read obligations ledger {path}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("obligations"), list):
        raise InvalidState(f"{path} is not an obligations ledger")
    existing: set[str] = set()
    for index, item in enumerate(data["obligations"]):
        if not isinstance(item, Mapping):
            raise InvalidState(f"obligations[{index}] must be an object")
        value = item.get("fingerprint", item.get("obligation_id"))
        if isinstance(value, str):
            existing.add(value)
    return data, existing


def _append_json_obligations(
    path: Path, records: list[dict[str, Any]]
) -> None:
    data, existing = _load_json_ledger(path)
    new_records = [
        record for record in records if record["obligation_id"] not in existing
    ]
    if not new_records:
        return
    data["obligations"].extend(new_records)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _markdown_fingerprints(text: str) -> set[str]:
    return set(_FINGERPRINT_RE.findall(text))


def _markdown_record(record: Mapping[str, Any]) -> str:
    def display(value: Any) -> str:
        return _normalise_text(value).replace("`", "'") or "(none)"

    claims = "; ".join(record["claim"]) or "(none)"
    spans = "; ".join(record["span"]) or "(none)"
    return (
        f"<!-- aris-obligation:{record['obligation_id']} -->\n"
        f"- [ ] branch `{display(record['branch_id'])}` | "
        f"skill `{display(record['skill'])}` | "
        f"pattern `{display(record['pattern'])}`\n"
        f"  - claim: {display(claims)}\n"
        f"  - span: {display(spans)}\n"
    )


def _append_markdown_obligations(
    path: Path, records: list[dict[str, Any]]
) -> None:
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise InvalidState(f"cannot read obligations file {path}") from exc
    else:
        text = ""
    existing = _markdown_fingerprints(text)
    new_records = [
        record for record in records if record["obligation_id"] not in existing
    ]
    if not new_records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = ""
    if not text:
        prefix = "# Research Obligations\n\n"
    elif not text.endswith("\n"):
        prefix = "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(prefix)
        for record in new_records:
            handle.write(_markdown_record(record))
            handle.write("\n")


def append_obligations(path: Path, findings: list[dict], branch_id: str) -> None:
    """Append new findings to an obligations ledger without pruning old ones.

    ``OBLIGATIONS.md`` is the normal branch-workspace format.  A JSON path is
    also accepted for machine consumers and keeps the same stable record shape.
    Repeated findings, reordered evidence, and changed positional finding IDs
    are deduplicated by :func:`obligation_fingerprint`; vanished findings are
    never removed or auto-closed.
    """

    if not isinstance(path, Path):
        path = Path(path)
    if not isinstance(branch_id, str) or not branch_id.strip():
        raise InvalidState("branch_id must be a non-empty string")
    records = _records_from_findings(findings, branch_id)
    if not records:
        return

    if path.suffix.lower() == ".json":
        _append_json_obligations(path, records)
    else:
        _append_markdown_obligations(path, records)


def _report_verdict(report: Mapping[str, Any]) -> str:
    if not isinstance(report, Mapping):
        raise InvalidReport("Anti report must be an object")
    verdict = report.get("overall_verdict")
    if not isinstance(verdict, str) or verdict not in ANTI_VERDICTS:
        raise InvalidReport(
            f"unknown Anti overall_verdict {verdict!r}; expected one of "
            f"{sorted(ANTI_VERDICTS)}"
        )
    findings = report.get("findings", [])
    if findings is not None and not isinstance(findings, list):
        raise InvalidReport("Anti report findings must be a list")
    return verdict


def evaluate_branch(report: dict, state: dict, branch_id: str) -> str:
    """Map one already-completed branch audit to an ARIS promotion state.

    The branch must be ``BRANCH_RESEARCHED`` (or the intermediate
    ``EVIDENCE_AUDITED`` state if the caller recorded ``AUDIT_COMPLETE``
    separately).  Hash bindings are checked before any status mutation.  Only
    the named branch is changed; a hard finding cannot block sibling branches.
    """

    verdict = _report_verdict(report)
    if not isinstance(state, dict):
        raise InvalidState("state must be a dictionary")
    if not isinstance(branch_id, str) or not branch_id.strip():
        raise InvalidState("branch_id must be a non-empty string")
    branches = state.get("branches")
    if not isinstance(branches, Mapping) or branch_id not in branches:
        raise InvalidState(f"unknown branch {branch_id!r}")
    branch = branches[branch_id]
    if not isinstance(branch, dict):
        raise InvalidState(f"branch {branch_id!r} must be an object")
    if branch.get("status") not in {"BRANCH_RESEARCHED", "EVIDENCE_AUDITED"}:
        raise InvalidTransition(
            f"branch audit requires BRANCH_RESEARCHED, got {branch.get('status')!r}"
        )
    validate_query_statuses(branch, require_terminal=True)

    # Do not derive a verdict from findings here.  Anti's deterministic
    # adjudicator is the sole owner of overall_verdict.
    try:
        validate_audit_hashes(state, branch_id, report)
    except (InvalidState, InvalidTransition) as exc:
        raise InvalidReport(str(exc)) from exc
    branch_audit = branch.get("audit")
    if not isinstance(branch_audit, dict):
        branch_audit = {}
        branch["audit"] = branch_audit
    branch_audit["status"] = "COMPLETE"
    branch_audit["overall_verdict"] = verdict  # preserve the upstream token
    for key in (
        "artifact_hashes",
        "audited_artifact_hashes",
        "audit_artifact_hashes",
        "input_hashes",
        "source_hashes",
        "artifact_hash",
        "audit_hash",
        "audit_artifact_hash",
        "audit_input_hash",
    ):
        if key in report:
            branch_audit[key] = copy.deepcopy(report[key])
    branch["status"] = "EVIDENCE_AUDITED"

    promotion = VERDICT_TO_PROMOTION[verdict]
    transition(state, promotion, branch_id=branch_id)
    return promotion


if __name__ == "__main__":  # pragma: no cover - library by contract
    raise SystemExit("research_gate.py is a library; call evaluate_branch() from the orchestrator")
