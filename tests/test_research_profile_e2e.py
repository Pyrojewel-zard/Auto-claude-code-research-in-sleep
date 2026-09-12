import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from replay_research_fixture import run_fixture


FIXTURES = Path(__file__).parent / "fixtures" / "research"


def test_topic_fixture_reaches_synthesis_with_zotero_only():
    run = run_fixture(FIXTURES / "topic_complete", "ask")
    assert run["status"] == "WRITE_READY"
    assert run["external_calls"] == []


def test_proposal_fixture_excludes_only_failed_branch():
    run = run_fixture(FIXTURES / "proposal_branches", "ask")
    assert run["branches"]["unsupported"]["status"] == "NEEDS_WORK"
    assert run["branches"]["supported"]["status"] == "PROMOTABLE"
    assert "unsupported" not in run["synthesis_load_bearing_claims"]


def test_gap_fixture_asks_once():
    run = run_fixture(FIXTURES / "topic_gap", "ask")
    assert run["expansion_prompt_count"] == 1
