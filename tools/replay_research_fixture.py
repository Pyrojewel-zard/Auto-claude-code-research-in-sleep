#!/usr/bin/env python3
"""Replay deterministic ARIS research fixtures without live integrations.

The fixture runner is intentionally small: it exercises the same state and
branch-gate libraries used by the public skills while replacing Zotero,
reviewer agents, and external search with checked-in JSON inputs.  It is a
regression harness, not a production orchestrator.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

try:
    from research_gate import evaluate_branch
    from research_state import (
        InvalidState,
        coverage_decision,
        transition,
        validate_expansion_policy,
    )
except ImportError:  # package import: ``from tools.replay_research_fixture``
    from tools.research_gate import evaluate_branch
    from tools.research_state import (
        InvalidState,
        coverage_decision,
        transition,
        validate_expansion_policy,
    )


_TERMINAL_EVENTS = {
    "BRANCH_PLANNED",
    "ZOTERO_RESEARCHING",
    "BRANCH_RESEARCHED",
    "COVERAGE_COMPLETE",
    "AUDIT_COMPLETE",
    "PROMOTABLE",
    "PROMOTABLE_WITH_OBLIGATIONS",
    "NEEDS_WORK",
    "SYNTHESIZED",
    "WRITE_READY",
}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidState(f"cannot read fixture JSON: {path}") from exc


def _inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise InvalidState("fixture path must be a non-empty relative string")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise InvalidState(f"fixture path escapes fixture root: {relative!r}") from exc
    return candidate


def _coverage_decisions(state: dict[str, Any], branch_id: str) -> list[dict[str, Any]]:
    branch = state["branches"][branch_id]
    # Capture the decision before transition records the checkpoint.  The
    # transition calls the same pure policy boundary again and sees the prompt
    # hash as already recorded, so replay remains idempotent at the boundary.
    return coverage_decision(branch, state=state)


def _synthesis_claims(state: dict[str, Any]) -> list[Any]:
    claims: list[Any] = []
    for branch_id, branch in state.get("branches", {}).items():
        if branch.get("status") not in {
            "PROMOTABLE",
            "PROMOTABLE_WITH_OBLIGATIONS",
        }:
            continue
        values = branch.get("load_bearing_claims", branch.get("synthesis_load_bearing_claims", []))
        if isinstance(values, list):
            claims.extend(copy.deepcopy(values))
        elif values not in (None, ""):
            claims.append(copy.deepcopy(values))
    return claims


def run_fixture(fixture_dir: Path, expansion_policy: str) -> dict[str, Any]:
    """Replay one fixture and return its final JSON-compatible run state.

    ``fixture_dir`` contains ``state.json``, ``events.json``, and any report
    files referenced by an ``EVALUATE_BRANCH`` event.  No network, MCP, shell,
    or reviewer call is made.
    """

    root = Path(fixture_dir).resolve()
    if not root.is_dir():
        raise InvalidState(f"fixture directory does not exist: {root}")
    state = _read_json(_inside(root, "state.json"))
    events = _read_json(_inside(root, "events.json"))
    if not isinstance(state, dict) or not isinstance(events, list):
        raise InvalidState("fixture state must be an object and events must be a list")
    validate_expansion_policy(expansion_policy)
    state = copy.deepcopy(state)
    state["external_expansion"] = expansion_policy
    decisions: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []

    for index, record in enumerate(events):
        if not isinstance(record, dict):
            raise InvalidState(f"events[{index}] must be an object")
        raw_event = record.get("event")
        if not isinstance(raw_event, str) or not raw_event.strip():
            raise InvalidState(f"events[{index}] has no event")
        event = raw_event.strip().upper()
        if event == "EVALUATE_BRANCH":
            branch_id = record.get("branch_id")
            report_path = _inside(root, record.get("report", ""))
            report = _read_json(report_path)
            if not isinstance(report, dict):
                raise InvalidState(f"report for events[{index}] must be an object")
            evaluate_branch(report, state, branch_id)
            reports.append({"branch_id": branch_id, "verdict": report.get("overall_verdict")})
            continue
        if event == "COVERAGE_COMPLETE":
            branch_id = record.get("branch_id")
            decisions.extend(_coverage_decisions(state, branch_id))
            transition(state, event, branch_id=branch_id)
            continue
        if event not in _TERMINAL_EVENTS:
            raise InvalidState(f"unsupported fixture event {event!r}")
        branch_id = record.get("branch_id")
        transition(state, event, branch_id=branch_id)

    state["external_calls"] = [
        decision
        for decision in decisions
        if decision.get("external_call") is True
    ]
    state["expansion_prompt_count"] = sum(
        int(branch.get("coverage_prompt_count", 0))
        for branch in state.get("branches", {}).values()
        if isinstance(branch, dict)
    )
    state["synthesis_load_bearing_claims"] = _synthesis_claims(state)
    state["replayed_reports"] = reports
    return state


if __name__ == "__main__":  # pragma: no cover - convenience CLI
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture_dir", type=Path)
    parser.add_argument("--expansion-policy", default="ask")
    args = parser.parse_args()
    print(json.dumps(run_fixture(args.fixture_dir, args.expansion_policy), ensure_ascii=False, indent=2))
