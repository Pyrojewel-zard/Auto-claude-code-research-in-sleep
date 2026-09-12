import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

from research_state import (  # noqa: E402
    EXPANSION_POLICIES,
    QUERY_TERMINAL,
    InvalidTransition,
    coverage_decision,
    transition,
)


def _state(status="BRANCH_PLANNED", policy="ask"):
    return {
        "mode": "topic",
        "external_expansion": policy,
        "branches": {"b1": {"status": status}},
    }


def _researched_state(policy="ask", queries=None):
    branch = {"status": "ZOTERO_RESEARCHING", "queries": queries or {}}
    return {
        "mode": "topic",
        "external_expansion": policy,
        "branches": {"b1": branch},
    }


def _coverage_branch(policy, prompt_count=0, report_hash="coverage-v1"):
    return {
        "status": "BRANCH_RESEARCHED",
        "external_expansion": policy,
        "coverage_report": {
            "hash": report_hash,
            "gaps": [{"claim": "unresolved mechanism"}],
        },
        "coverage_prompt_count": prompt_count,
    }


def test_status_chain_requires_research_before_audit():
    state = _state()

    with pytest.raises(InvalidTransition):
        transition(state, "AUDIT_COMPLETE", branch_id="b1")

    state = transition(state, "ZOTERO_RESEARCHING", branch_id="b1")
    state["branches"]["b1"]["queries"] = {
        "q1": {"status": "SEARCHED"},
        "q2": {"status": "NO_HIT"},
    }
    state = transition(state, "BRANCH_RESEARCHED", branch_id="b1")
    assert state["branches"]["b1"]["status"] == "BRANCH_RESEARCHED"

    state = transition(state, "AUDIT_COMPLETE", branch_id="b1")
    assert state["branches"]["b1"]["status"] == "EVIDENCE_AUDITED"


def test_research_completion_rejects_non_terminal_query_status():
    state = _researched_state(queries={"q1": {"status": "SEARCHING"}})

    with pytest.raises(InvalidTransition):
        transition(state, "BRANCH_RESEARCHED", branch_id="b1")


@pytest.mark.parametrize("status", sorted(QUERY_TERMINAL))
def test_all_query_terminal_statuses_are_accepted(status):
    state = _researched_state(queries={"q1": {"status": status}})
    state = transition(state, "BRANCH_RESEARCHED", branch_id="b1")
    assert state["branches"]["b1"]["status"] == "BRANCH_RESEARCHED"


def test_unknown_query_status_is_rejected():
    state = _researched_state(queries={"q1": {"status": "MAYBE"}})

    with pytest.raises(InvalidTransition):
        transition(state, "BRANCH_RESEARCHED", branch_id="b1")


@pytest.mark.parametrize(
    ("query_key", "query_value"),
    [
        ("queries", {"q1": {"status": "PENDING"}}),
        ("query_results", {"q1": "PENDING"}),
        ("query_statuses", [{"query_id": "q1", "status": "PENDING"}]),
    ],
)
def test_terminal_query_event_updates_the_unique_query_record(
    query_key, query_value
):
    state = {
        "branches": {
            "b1": {
                "status": "ZOTERO_RESEARCHING",
                query_key: query_value,
            }
        }
    }

    transition(state, "SEARCHED", branch_id="b1")

    branch = state["branches"]["b1"]
    assert "query_status" not in branch
    if query_key == "queries":
        assert branch[query_key]["q1"]["status"] == "SEARCHED"
    elif query_key == "query_results":
        assert branch[query_key]["q1"] == "SEARCHED"
    else:
        assert branch[query_key][0]["status"] == "SEARCHED"


def test_terminal_query_event_requires_a_real_unique_query_record():
    state = {"branches": {"b1": {"status": "ZOTERO_RESEARCHING"}}}

    with pytest.raises(InvalidTransition):
        transition(state, "SEARCHED", branch_id="b1")

    assert "query_status" not in state["branches"]["b1"]


@pytest.mark.parametrize(
    "status", ["EVIDENCE_AUDITED", "PROMOTABLE", "PROMOTABLE_WITH_OBLIGATIONS", "NEEDS_WORK"]
)
def test_frozen_branch_rejects_research_state_mutations(status):
    state = {
        "branches": {
            "b1": {
                "status": status,
                "queries": {"q1": {"status": "SEARCHED"}},
                "coverage_gaps": [{"claim": "gap"}],
            }
        }
    }

    for event in ("SEARCHED", "QUERY_COMPLETE", "COVERAGE_COMPLETE"):
        with pytest.raises(InvalidTransition):
            transition(state, event, branch_id="b1")

    assert state["branches"]["b1"]["status"] == status
    assert state["branches"]["b1"]["queries"]["q1"]["status"] == "SEARCHED"
    assert "query_status" not in state["branches"]["b1"]


def test_frozen_branch_rejects_branch_scoped_expansion_events():
    state = {
        "external_expansion": "ask",
        "branches": {
            "b1": {
                "status": "EVIDENCE_AUDITED",
                "queries": {"q1": {"status": "SEARCHED"}},
            }
        },
    }

    with pytest.raises(InvalidTransition):
        transition(state, "EXPANSION_PROMPTED", branch_id="b1")

    assert "expansion_prompted" not in state["branches"]["b1"]


def test_expansion_policy_is_limited_to_ask_never_allow():
    assert EXPANSION_POLICIES == {"ask", "never", "allow"}
    for policy in ("ASK", "web", ""):
        with pytest.raises(ValueError):
            coverage_decision(_coverage_branch(policy))


def test_ask_policy_requests_external_expansion_once_per_report():
    first = coverage_decision(_coverage_branch("ask"))
    assert len(first) == 1
    assert first[0]["action"] == "ASK_EXTERNAL_EXPANSION"

    already_asked = _coverage_branch("ask", prompt_count=1)
    already_asked["coverage_prompted_report_hash"] = "coverage-v1"
    assert coverage_decision(already_asked) == []


def test_never_policy_preserves_gaps_without_external_call():
    decisions = coverage_decision(_coverage_branch("never"))
    assert len(decisions) == 1
    assert decisions[0]["action"] == "PRESERVE_GAPS"
    assert decisions[0]["policy"] == "never"
    assert decisions[0]["external_call"] is False


def test_allow_policy_authorizes_targeted_external_expansion():
    decisions = coverage_decision(_coverage_branch("allow"))
    assert len(decisions) == 1
    assert decisions[0]["action"] == "ALLOW_EXTERNAL_EXPANSION"
    assert decisions[0]["policy"] == "allow"
    assert decisions[0]["external_call"] is True


def test_coverage_without_gaps_has_no_expansion_decision():
    branch = _coverage_branch("ask")
    branch["coverage_report"]["gaps"] = []
    assert coverage_decision(branch) == []


def test_run_never_policy_is_inherited_by_branch_coverage():
    branch = _coverage_branch("ask")
    branch.pop("external_expansion")
    state = {
        "external_expansion": "never",
        "branches": {"b1": branch},
    }

    transition(state, "COVERAGE_COMPLETE", branch_id="b1")

    assert branch["coverage_gaps_preserved"] is True
    assert "expansion_prompted" not in branch
    assert "coverage_prompted_report_hash" not in branch


def test_ask_prompt_with_no_coverage_hash_binding_fails_closed():
    branch = _coverage_branch("ask")
    branch["expansion_prompted"] = True

    with pytest.raises(InvalidTransition):
        coverage_decision(branch)


def test_same_completed_coverage_report_cannot_prompt_twice():
    branch = _coverage_branch("ask", report_hash="coverage-v1")
    first = coverage_decision(branch)
    second = coverage_decision(branch)

    assert len(first) == 1
    assert second == []
    assert branch["expansion_prompt_count"] == 1


def test_new_coverage_report_may_prompt_again():
    branch = _coverage_branch("ask", report_hash="coverage-v1")
    first = coverage_decision(branch)
    assert first[0]["action"] == "ASK_EXTERNAL_EXPANSION"
    branch["coverage_report"] = {
        "hash": "coverage-v1",
        "gaps": [{"claim": "gap one"}],
    }
    branch["coverage_report"] = {
        "hash": "coverage-v2",
        "gaps": [{"claim": "gap two"}],
    }
    second = coverage_decision(branch)

    assert second[0]["action"] == "ASK_EXTERNAL_EXPANSION"
    assert branch["expansion_prompt_count"] == 2


def test_repeated_branch_planned_transition_is_not_idempotent():
    state = _state(status="INPUT")
    transition(state, "BRANCH_PLANNED", branch_id="b1")

    with pytest.raises(InvalidTransition):
        transition(state, "BRANCH_PLANNED", branch_id="b1")


def test_repeated_zotero_researching_transition_is_not_idempotent():
    state = _state()
    transition(state, "ZOTERO_RESEARCHING", branch_id="b1")

    with pytest.raises(InvalidTransition):
        transition(state, "ZOTERO_RESEARCHING", branch_id="b1")


def test_repeated_branch_researched_transition_is_not_idempotent():
    state = _researched_state(queries={"q1": {"status": "SEARCHED"}})
    transition(state, "BRANCH_RESEARCHED", branch_id="b1")

    with pytest.raises(InvalidTransition):
        transition(state, "BRANCH_RESEARCHED", branch_id="b1")


def test_repeated_promotion_transition_is_not_idempotent():
    state = {
        "branches": {
            "b1": {
                "status": "EVIDENCE_AUDITED",
                "queries": {"q1": {"status": "SEARCHED"}},
            }
        }
    }
    transition(state, "PROMOTABLE", branch_id="b1")

    with pytest.raises(InvalidTransition):
        transition(state, "PROMOTABLE", branch_id="b1")
