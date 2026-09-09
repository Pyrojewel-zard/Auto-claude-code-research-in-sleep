#!/usr/bin/env python3
"""Deterministic state and coverage policy for Zotero-first research runs.

The research orchestrator owns the work, but this module owns the small set of
facts that must be true before work can advance: query results have terminal
statuses, a branch is researched before it is audited, expansion follows the
declared policy, and an audit is bound to the artifacts it inspected.

This module deliberately does not inspect the quality of evidence or compute an
Anti-Autoresearch verdict.  It only validates state and records transitions.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


QUERY_TERMINAL = {"SEARCHED", "NO_HIT", "UNVERIFIED", "UNSEARCHABLE", "ERROR"}
EXPANSION_POLICIES = {"ask", "never", "allow"}
PROMOTION_STATES = {
    "PROMOTABLE",
    "PROMOTABLE_WITH_OBLIGATIONS",
    "NEEDS_WORK",
}

QUERY_IN_PROGRESS = {"PENDING", "SEARCHING", "RUNNING", "IN_PROGRESS"}
QUERY_STATUSES = QUERY_TERMINAL | QUERY_IN_PROGRESS

BRANCH_STATUSES = {
    "INPUT",
    "BRANCH_PLANNED",
    "ZOTERO_RESEARCHING",
    "BRANCH_RESEARCHED",
    "EVIDENCE_AUDITED",
} | PROMOTION_STATES
RUN_STATUSES = {"INPUT", "SYNTHESIZED", "WRITE_READY"}


class InvalidTransition(ValueError):
    """The requested event is not legal from the current state."""


class InvalidState(InvalidTransition):
    """The supplied state is malformed or uses an unknown policy/status."""


class StaleAudit(InvalidTransition):
    """An audit does not describe the current branch artifact hashes."""


def _as_nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidState(f"{field} must be a non-empty string")
    return value.strip()


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _normalise_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def validate_query_status(status: Any) -> str:
    """Validate and return one known query status.

    ``QUERY_TERMINAL`` is the public completion contract.  The in-progress
    values are accepted while a branch is researching, but never satisfy a
    ``BRANCH_RESEARCHED`` transition.
    """

    if not isinstance(status, str) or status not in QUERY_STATUSES:
        raise InvalidState(
            f"unknown query status {status!r}; expected one of "
            f"{sorted(QUERY_STATUSES)}"
        )
    return status


def _query_records(branch: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return query records from the supported state-file representations."""

    for key in ("queries", "query_results", "query_statuses"):
        if key not in branch:
            continue
        raw = branch[key]
        records: list[dict[str, Any]] = []
        if isinstance(raw, Mapping):
            iterable = raw.items()
            for query_id, item in iterable:
                if isinstance(item, Mapping):
                    record = dict(item)
                    record.setdefault("query_id", query_id)
                else:
                    record = {"query_id": query_id, "status": item}
                records.append(record)
        elif isinstance(raw, list):
            for index, item in enumerate(raw):
                if isinstance(item, Mapping):
                    records.append(dict(item))
                elif isinstance(item, str):
                    records.append({"query_id": f"Q{index + 1}", "status": item})
                else:
                    raise InvalidState(f"{key}[{index}] must be an object")
        else:
            raise InvalidState(f"{key} must be a list or object")
        return records

    # A compact one-query state is useful for small fixtures and is still
    # unambiguous because there can be only one implicit query.
    if "query_status" in branch:
        return [{"query_id": "Q1", "status": branch["query_status"]}]
    return []


def validate_query_statuses(
    branch: Mapping[str, Any], *, require_terminal: bool = False
) -> list[dict[str, Any]]:
    """Validate every recorded query and optionally require completion."""

    records = _query_records(branch)
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):  # defensive for custom mappings
            raise InvalidState(f"query[{index}] must be an object")
        if "status" not in record:
            raise InvalidState(f"query[{index}] has no status")
        status = validate_query_status(record["status"])
        if require_terminal and status not in QUERY_TERMINAL:
            raise InvalidTransition(
                f"query {record.get('query_id', index)!r} is {status}; "
                "all queries must have terminal statuses before branch research completes"
            )
    return records


def _policy_from(
    state: Mapping[str, Any] | None, branch: Mapping[str, Any] | None
) -> str:
    """Resolve a policy, allowing branch-local overrides over run policy."""

    value: Any = None
    if branch is not None:
        for key in ("external_expansion", "expansion_policy"):
            if key in branch:
                value = branch[key]
                break
    if value is None and state is not None:
        for key in ("external_expansion", "expansion_policy"):
            if key in state:
                value = state[key]
                break
    if isinstance(value, Mapping):
        value = value.get("policy")
    if value is None:
        value = "ask"
    if value not in EXPANSION_POLICIES:
        raise InvalidState(
            f"unknown external expansion policy {value!r}; expected one of "
            f"{sorted(EXPANSION_POLICIES)}"
        )
    return value


def validate_expansion_policy(policy: Any) -> str:
    """Validate a standalone expansion policy."""

    if policy not in EXPANSION_POLICIES:
        raise InvalidState(
            f"unknown external expansion policy {policy!r}; expected one of "
            f"{sorted(EXPANSION_POLICIES)}"
        )
    return policy


def _hash_value(value: Any) -> Any:
    """Extract hash-shaped values without confusing artifact path metadata."""

    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return None


def _branch_scoped_value(
    state: Mapping[str, Any], key: str, branch_id: str
) -> Any:
    value = state.get(key)
    if not isinstance(value, Mapping):
        return value
    if branch_id in value:
        return value[branch_id]
    # A mapping whose values are all strings is itself an artifact hash map;
    # otherwise it is more likely a branch-id -> value map.
    if value and all(isinstance(item, str) for item in value.values()):
        return value
    return None


def _first_hash(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping:
            candidate = _hash_value(mapping[key])
            if candidate is not None:
                return candidate
    return None


def _expected_artifact_hashes(
    state: Mapping[str, Any], branch: Mapping[str, Any], branch_id: str
) -> Any:
    value = _first_hash(
        branch,
        (
            "artifact_hashes",
            "research_artifact_hashes",
            "input_hashes",
            "artifact_hash",
            "research_hash",
        ),
    )
    if value is not None:
        return value
    artifacts = branch.get("artifacts")
    if isinstance(artifacts, Mapping) and artifacts:
        # ``artifacts`` is only a hash source when all values are hash-like
        # strings; a list of artifact descriptors is deliberately ignored.
        if all(isinstance(item, str) for item in artifacts.values()):
            return dict(artifacts)
    for key in (
        "artifact_hashes",
        "research_artifact_hashes",
        "input_hashes",
    ):
        value = _branch_scoped_value(state, key, branch_id)
        if value is not None:
            return _hash_value(value)
    return None


def _audit_artifact_hashes(branch: Mapping[str, Any]) -> Any:
    audit = branch.get("audit")
    if isinstance(audit, Mapping):
        value = _first_hash(
            audit,
            (
                "artifact_hashes",
                "audited_artifact_hashes",
                "input_hashes",
                "source_hashes",
                "artifact_hash",
                "input_hash",
                "audit_artifact_hash",
                "audit_input_hash",
            ),
        )
        if value is not None:
            return value
    return _first_hash(
        branch,
        (
            "audit_artifact_hashes",
            "audited_artifact_hashes",
            "audit_hashes",
            "audit_hash",
            "audit_artifact_hash",
            "audit_input_hash",
        ),
    )


def _report_artifact_hashes(report: Mapping[str, Any]) -> Any:
    return _first_hash(
        report,
        (
            "artifact_hashes",
            "audited_artifact_hashes",
            "audit_artifact_hashes",
            "input_hashes",
            "source_hashes",
            "artifact_hash",
            "audit_hash",
            "audit_artifact_hash",
            "audit_input_hash",
        ),
    )


def _hashes_equal(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return False
    if _canonical(expected) == _canonical(actual):
        return True
    # A one-artifact state often stores the expected value as a map while the
    # report stores the single hash as a scalar.  Both are the same binding.
    if isinstance(expected, Mapping) and len(expected) == 1 and isinstance(actual, str):
        if actual in expected.values():
            return True
    if isinstance(actual, Mapping) and len(actual) == 1 and isinstance(expected, str):
        if expected in actual.values():
            return True
    # Permit an explicit combined hash over a map when the producer records
    # that digest instead of reproducing the map.
    if isinstance(actual, str):
        digest = hashlib.sha256(_canonical(expected).encode("utf-8")).hexdigest()
        return actual == digest
    return False


def _assert_hash_match(expected: Any, actual: Any, label: str) -> None:
    if expected is None:
        return
    if actual is None:
        raise StaleAudit(f"{label} is not bound to the current artifact hashes")
    if not _hashes_equal(expected, actual):
        raise StaleAudit(f"stale {label}: artifact hashes do not match")


def validate_audit_hashes(
    state: Mapping[str, Any], branch_id: str, report: Mapping[str, Any] | None = None
) -> None:
    """Reject audit metadata that is missing or differs from branch inputs.

    Hash metadata is optional for the tiny state fixtures used by the first
    contract.  Once a state records input hashes, however, every audit binding
    supplied by the branch or report must match them; a missing binding fails
    closed rather than silently accepting a stale audit.
    """

    branch = _get_branch(state, branch_id)
    expected = _expected_artifact_hashes(state, branch, branch_id)
    branch_audit = _audit_artifact_hashes(branch)
    if expected is not None and (
        isinstance(branch.get("audit"), Mapping) or branch_audit is not None
    ):
        _assert_hash_match(expected, branch_audit, "branch audit")
    if report is not None:
        report_hashes = _report_artifact_hashes(report)
        if expected is not None:
            _assert_hash_match(expected, report_hashes, "audit report")
        if branch_audit is not None and report_hashes is not None:
            _assert_hash_match(branch_audit, report_hashes, "audit report")
        # A state may carry both a named artifact-hash map and a compact
        # single-artifact hash.  Validate each explicit binding instead of
        # allowing the first representation to hide a mismatch in the other.
        for key in ("artifact_hash", "research_hash"):
            if key in branch and key in report:
                _assert_hash_match(branch[key], report[key], f"audit report {key}")
        audit = branch.get("audit")
        if isinstance(audit, Mapping):
            for key in ("artifact_hash", "input_hash", "audit_hash"):
                if key in audit and key in report:
                    _assert_hash_match(audit[key], report[key], f"audit report {key}")


def _coverage_gaps(branch: Mapping[str, Any]) -> list[Any]:
    raw: Any = None
    for key in ("coverage_gaps", "gaps", "unresolved_gaps", "external_gaps"):
        if key in branch:
            raw = branch[key]
            break
    if raw is None and isinstance(branch.get("coverage_report"), Mapping):
        report = branch["coverage_report"]
        for key in ("gaps", "coverage_gaps", "unresolved_gaps", "external_gaps"):
            if key in report:
                raw = report[key]
                break
    if raw is None:
        return []
    if isinstance(raw, (str, Mapping)):
        raw = [raw]
    if not isinstance(raw, list):
        raise InvalidState("coverage gaps must be a list, string, or object")
    return [gap for gap in raw if gap not in (None, "")]


def _coverage_hash(branch: Mapping[str, Any], gaps: list[Any]) -> str:
    report = branch.get("coverage_report")
    if isinstance(report, Mapping):
        value = report.get("hash")
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("coverage_report_hash", "coverage_hash"):
        value = branch.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if report is not None:
        return hashlib.sha256(_canonical(report).encode("utf-8")).hexdigest()
    return hashlib.sha256(_canonical(gaps).encode("utf-8")).hexdigest()


def _preserve_gap_decisions(
    gaps: list[Any], policy: str, coverage_hash: str
) -> list[dict[str, Any]]:
    return [
        {
            "action": "preserve_gap",
            "gap": gap,
            "policy": policy,
            "coverage_hash": coverage_hash,
        }
        for gap in gaps
    ]


def _expand_decisions(
    gaps: list[Any], policy: str, coverage_hash: str
) -> list[dict[str, Any]]:
    return [
        {
            "action": "expand",
            "gap": gap,
            "policy": policy,
            "coverage_hash": coverage_hash,
        }
        for gap in gaps
    ]


def coverage_decision(branch: dict) -> list[dict]:
    """Return the policy decision for the gaps in one completed coverage report.

    ``ask`` emits one prompt for a coverage-report hash and records that prompt
    on the branch.  ``never`` emits one durable preserve-gap decision per gap;
    ``allow`` emits one targeted expansion decision per gap.  Calling the
    function again for the same report never creates a second prompt.
    """

    if not isinstance(branch, dict):
        raise InvalidState("branch must be an object")
    status = branch.get("status")
    if status is not None and status not in {
        "BRANCH_RESEARCHED",
        "EVIDENCE_AUDITED",
        *PROMOTION_STATES,
    }:
        raise InvalidTransition(
            f"coverage decision requires a completed branch, got {status!r}"
        )
    if branch.get("coverage_report_complete") is False:
        raise InvalidTransition("coverage decision requires a completed coverage report")

    policy = _policy_from(None, branch)
    gaps = _coverage_gaps(branch)
    if not gaps:
        return []
    coverage_hash = _coverage_hash(branch, gaps)

    prior_decision = branch.get("external_expansion_decision")
    if prior_decision in {"declined", "never", "preserve"}:
        return [
            {
                "action": "PRESERVE_GAPS",
                "gaps": list(gaps),
                "policy": "never",
                "external_call": False,
                "coverage_report_hash": coverage_hash,
            }
        ]
    if prior_decision in {"approved", "allow", "authorized"}:
        return [
            {
                "action": "ALLOW_EXTERNAL_EXPANSION",
                "gaps": list(gaps),
                "policy": "allow",
                "external_call": True,
                "coverage_report_hash": coverage_hash,
            }
        ]

    if policy == "never":
        branch["coverage_gaps_preserved"] = True
        return [
            {
                "action": "PRESERVE_GAPS",
                "gaps": list(gaps),
                "policy": policy,
                "external_call": False,
                "coverage_report_hash": coverage_hash,
            }
        ]
    if policy == "allow":
        return [
            {
                "action": "ALLOW_EXTERNAL_EXPANSION",
                "gaps": list(gaps),
                "policy": policy,
                "external_call": True,
                "coverage_report_hash": coverage_hash,
            }
        ]

    prompted_for = branch.get(
        "coverage_prompted_report_hash", branch.get("expansion_prompted_for")
    )
    if prompted_for == coverage_hash or (
        branch.get("expansion_prompted") is True and prompted_for is None
    ):
        return []

    branch["coverage_prompted_report_hash"] = coverage_hash
    branch["expansion_prompted_for"] = coverage_hash
    branch["expansion_prompted"] = True
    branch["coverage_prompt_count"] = int(
        branch.get("coverage_prompt_count", branch.get("expansion_prompt_count", 0))
    ) + 1
    branch["expansion_prompt_count"] = branch["coverage_prompt_count"]
    return [
        {
            "action": "ASK_EXTERNAL_EXPANSION",
            "gaps": list(gaps),
            "policy": policy,
            "external_call": False,
            "coverage_hash": coverage_hash,
            "coverage_report_hash": coverage_hash,
            "prompt": "Coverage has explicit gaps. Authorize targeted external expansion?",
        }
    ]


def _get_branch(state: Mapping[str, Any], branch_id: str) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        raise InvalidState("state must be an object")
    branches = state.get("branches")
    if not isinstance(branches, Mapping):
        raise InvalidState("state.branches must be an object")
    if not isinstance(branch_id, str) or not branch_id.strip():
        raise InvalidState("branch_id must be a non-empty string")
    branch = branches.get(branch_id)
    if not isinstance(branch, dict):
        raise InvalidState(f"unknown or malformed branch {branch_id!r}")
    return branch


def _validate_state(state: Mapping[str, Any]) -> None:
    if not isinstance(state, Mapping):
        raise InvalidState("state must be an object")
    policy = state.get("external_expansion", state.get("expansion_policy"))
    if policy is not None:
        _policy_from(state, None)
    status = state.get("status")
    if status is not None and status not in RUN_STATUSES:
        raise InvalidState(f"unknown run status {status!r}")
    branches = state.get("branches")
    if not isinstance(branches, Mapping):
        raise InvalidState("state.branches must be an object")
    for branch_id, branch in branches.items():
        if not isinstance(branch_id, str) or not branch_id.strip():
            raise InvalidState("branch ids must be non-empty strings")
        if not isinstance(branch, dict):
            raise InvalidState(f"branch {branch_id!r} must be an object")
        branch_status = branch.get("status")
        if branch_status is not None and branch_status not in BRANCH_STATUSES:
            raise InvalidState(
                f"unknown status {branch_status!r} for branch {branch_id!r}"
            )
        _policy_from(state, branch)
        validate_query_statuses(
            branch,
            require_terminal=branch_status
            in {
                "BRANCH_RESEARCHED",
                "EVIDENCE_AUDITED",
                *PROMOTION_STATES,
            },
        )


def _require_branch_id(branch_id: str | None) -> str:
    if not isinstance(branch_id, str) or not branch_id.strip():
        raise InvalidTransition("this event requires a non-empty branch_id")
    return branch_id


def _record_expansion_event(
    state: dict, event: str, branch_id: str | None
) -> dict:
    branch = _get_branch(state, branch_id) if branch_id is not None else None
    policy = _policy_from(state, branch)
    holder = branch if branch is not None else state
    if event in {"EXPANSION_PROMPTED", "EXTERNAL_EXPANSION_PROMPTED"}:
        if policy != "ask":
            raise InvalidTransition(
                f"EXPANSION_PROMPTED is only valid for ask policy, got {policy!r}"
            )
        if holder.get("expansion_prompted") is True:
            raise InvalidTransition("external expansion was already prompted")
        holder["expansion_prompted"] = True
        holder["expansion_prompt_count"] = int(
            holder.get("expansion_prompt_count", 0)
        ) + 1
        return state
    if event in {"EXPANSION_APPROVED", "EXTERNAL_EXPANSION_APPROVED"}:
        if policy == "never":
            raise InvalidTransition("external expansion is forbidden by never policy")
        if policy == "ask" and holder.get("expansion_prompted") is not True:
            raise InvalidTransition("ask policy requires a prompt before approval")
        holder["external_expansion_decision"] = "approved"
        holder["expansion_authorized"] = True
        return state
    if event in {"EXPANSION_DECLINED", "EXTERNAL_EXPANSION_DECLINED"}:
        if policy != "ask":
            raise InvalidTransition(
                f"only ask policy can decline a prompt, got {policy!r}"
            )
        if holder.get("expansion_prompted") is not True:
            raise InvalidTransition("cannot decline an expansion that was not prompted")
        holder["external_expansion_decision"] = "declined"
        holder["expansion_authorized"] = False
        return state
    if event in {"EXPANSION_REQUESTED", "EXTERNAL_EXPANSION_REQUESTED", "EXPAND"}:
        if policy == "never":
            raise InvalidTransition("external expansion is forbidden by never policy")
        if policy == "ask" and holder.get("expansion_prompted") is not True:
            raise InvalidTransition("ask policy requires a prompt before expansion")
        holder["expansion_requested"] = True
        return state
    raise InvalidTransition(f"unknown expansion event {event!r}")


def _transition_branch(state: dict, event: str, branch_id: str) -> dict:
    branch = _get_branch(state, branch_id)
    current = branch.get("status", "INPUT")

    if event == "BRANCH_PLANNED":
        if current not in {"INPUT", "BRANCH_PLANNED"}:
            raise InvalidTransition(
                f"branch {branch_id!r} is {current!r}; cannot plan it"
            )
        branch["status"] = "BRANCH_PLANNED"
        return state

    if event == "ZOTERO_RESEARCHING":
        if current == event:
            return state
        if current != "BRANCH_PLANNED":
            raise InvalidTransition(
                f"branch {branch_id!r} is {current!r}; expected BRANCH_PLANNED"
            )
        branch["status"] = event
        return state

    if event in {"QUERY_COMPLETE", "QUERIES_COMPLETE", "RESEARCH_COMPLETE"}:
        if current not in {"ZOTERO_RESEARCHING", "BRANCH_RESEARCHED"}:
            raise InvalidTransition(
                f"query completion is not valid from branch status {current!r}"
            )
        validate_query_statuses(branch, require_terminal=True)
        branch["queries_complete"] = True
        branch["status"] = "BRANCH_RESEARCHED"
        return state

    if event == "COVERAGE_COMPLETE":
        if current not in {
            "BRANCH_RESEARCHED",
            "EVIDENCE_AUDITED",
            *PROMOTION_STATES,
        }:
            raise InvalidTransition(
                f"coverage completion requires a researched branch, got {current!r}"
            )
        # Coverage is a report-level checkpoint, not a branch-status change.
        # Calling it repeatedly is intentionally idempotent for one report;
        # coverage_decision records the report hash and asks at most once.
        coverage_decision(branch)
        branch["coverage_complete"] = True
        return state

    if event in QUERY_TERMINAL:
        # A terminal event is a compact one-query update.  Multi-query callers
        # should write the query record first and use BRANCH_RESEARCHED; this
        # guard avoids pretending that one event completed every query.
        records = _query_records(branch)
        if len(records) > 1:
            raise InvalidTransition(
                "terminal query events are only unambiguous for one query; "
                "record each query and transition BRANCH_RESEARCHED"
            )
        if "queries" in branch and isinstance(branch["queries"], list) and branch["queries"]:
            if not isinstance(branch["queries"][0], dict):
                raise InvalidState("queries[0] must be an object")
            branch["queries"][0]["status"] = event
        else:
            branch["query_status"] = event
        validate_query_statuses(branch)
        return state

    if event == "BRANCH_RESEARCHED":
        if current == event:
            return state
        if current != "ZOTERO_RESEARCHING":
            raise InvalidTransition(
                f"branch {branch_id!r} is {current!r}; expected ZOTERO_RESEARCHING"
            )
        validate_query_statuses(branch, require_terminal=True)
        branch["status"] = event
        return state

    if event == "AUDIT_COMPLETE":
        if current != "BRANCH_RESEARCHED":
            raise InvalidTransition(
                f"audit requires BRANCH_RESEARCHED, got {current!r} for {branch_id!r}"
            )
        validate_audit_hashes(state, branch_id)
        branch["status"] = "EVIDENCE_AUDITED"
        audit = branch.get("audit")
        if not isinstance(audit, dict):
            audit = {}
            branch["audit"] = audit
        audit["status"] = "COMPLETE"
        return state

    if event in PROMOTION_STATES:
        if current == event:
            return state
        if current != "EVIDENCE_AUDITED":
            raise InvalidTransition(
                f"promotion requires EVIDENCE_AUDITED, got {current!r} for {branch_id!r}"
            )
        # A researched artifact may be edited after the audit.  Re-check the
        # binding at promotion time so a stale EVIDENCE_AUDITED status cannot
        # be hand-carried into synthesis.
        validate_audit_hashes(state, branch_id)
        branch["status"] = event
        return state

    raise InvalidTransition(f"unknown branch event {event!r}")


def _transition_run(state: dict, event: str) -> dict:
    current = state.get("status", "INPUT")
    if event == "INPUT":
        if current not in {"INPUT"}:
            raise InvalidTransition(f"run is already {current!r}")
        state["status"] = event
        return state
    if event == "SYNTHESIZED":
        if current == event:
            return state
        if current not in {"INPUT", "SYNTHESIZED"}:
            raise InvalidTransition(f"cannot synthesize from run status {current!r}")
        branches = state["branches"]
        if not branches:
            raise InvalidTransition("cannot synthesize without research branches")
        not_promoted = {
            branch_id: branch.get("status")
            for branch_id, branch in branches.items()
            if branch.get("status") not in PROMOTION_STATES
        }
        if not_promoted:
            raise InvalidTransition(
                f"branches are not promotion-terminal: {not_promoted!r}"
            )
        if not any(
            branch.get("status")
            in {"PROMOTABLE", "PROMOTABLE_WITH_OBLIGATIONS"}
            for branch in branches.values()
        ):
            raise InvalidTransition(
                "cannot synthesize when every branch is blocked or unresolved"
            )
        state["status"] = event
        return state
    if event == "WRITE_READY":
        if current != "SYNTHESIZED":
            raise InvalidTransition(
                f"WRITE_READY requires SYNTHESIZED, got {current!r}"
            )
        state["status"] = event
        return state
    raise InvalidTransition(f"unknown run event {event!r}")


def transition(
    state: dict, event: str, branch_id: str | None = None
) -> dict:
    """Validate and apply one monotonic research state transition.

    The input dictionary is updated in place and returned for convenient
    orchestration.  Validation occurs before the corresponding status change,
    so failed transitions do not leave a partially advanced branch.
    """

    if not isinstance(state, dict):
        raise InvalidState("state must be a dictionary")
    if not isinstance(event, str) or not event.strip():
        raise InvalidTransition("event must be a non-empty string")
    event = event.strip().upper()
    event = {
        "RESEARCH_START": "ZOTERO_RESEARCHING",
        "RESEARCHING": "ZOTERO_RESEARCHING",
        "RESEARCH_COMPLETE": "BRANCH_RESEARCHED",
    }.get(event, event)
    _validate_state(state)

    expansion_events = {
        "EXPANSION_PROMPTED",
        "EXTERNAL_EXPANSION_PROMPTED",
        "EXPANSION_APPROVED",
        "EXTERNAL_EXPANSION_APPROVED",
        "EXPANSION_DECLINED",
        "EXTERNAL_EXPANSION_DECLINED",
        "EXPANSION_REQUESTED",
        "EXTERNAL_EXPANSION_REQUESTED",
        "EXPAND",
    }
    if event in expansion_events:
        return _record_expansion_event(state, event, branch_id)

    if branch_id is None:
        return _transition_run(state, event)
    return _transition_branch(state, event, _require_branch_id(branch_id))


if __name__ == "__main__":  # pragma: no cover - a small importable policy tool
    raise SystemExit("research_state.py is a library; call transition() from the orchestrator")
