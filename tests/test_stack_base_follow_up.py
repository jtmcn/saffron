import dataclasses

import pytest

from saffron.ledger import Ledger
from saffron.scheduler import StackBase
from tests.test_batch import StackDoubles, _candidate, _ready


@pytest.fixture
def ledger(tmp_path):
    made = Ledger(tmp_path / "ledger.db")
    yield made
    made.close()


def test_a_follow_up_with_no_predecessor_on_a_gone_stack_base_is_refused(ledger):
    """b-7ee599: a follow-up offered with no predecessor asks whether the
    stack base's branch is there, as an order spec does (ADR 7). When it is
    gone, the follow-up is refused by name and never reaches the runner."""
    from saffron.batch import run_stack_batch

    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    stack_base = StackBase(spec_id="TE-9000", task_id=1, branch="saffron/TE-0")
    rows = {"TE-1": {"runner": "EXHAUSTED"}, "__follow_ups__": [{"id": "TE-5"}]}
    doubles = StackDoubles(ledger, repo_id, rows)
    answers = [True, False]
    asked: list[str] = []

    def alive(branch: str) -> bool:
        asked.append(branch)
        return answers.pop(0)

    lines: list[str] = []
    reason = run_stack_batch(
        [dataclasses.replace(_candidate("TE-1"), stack_base=stack_base)],
        ledger,
        30.0,
        None,
        doubles.runner,
        readiness_check=_ready,
        review=doubles.review,
        mint=doubles.mint,
        end_review=doubles.end_review,
        follow_ups=doubles.follow_ups,
        emit=lines.append,
        stack_base_alive=alive,
    )

    assert reason == "DRAINED"
    assert asked == ["saffron/TE-0", "saffron/TE-0"]
    assert doubles.runner_calls == [("TE-1", None)]
    refused = [line for line in lines if " refused " in line]
    assert [line.split()[0] for line in refused] == ["TE-5"]
    assert "TE-9000" in refused[0]
    assert "follow-ups unrun  TE-5" in lines
