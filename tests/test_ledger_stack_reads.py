"""`Ledger.batch_tasks`, `batch_budget` and `end_reviews`: the three reads
`SA-0152`'s stack view calls, split out of it so `saffron/ledger.py` prices
on its own (backlog item b-792ab2).
"""

from __future__ import annotations

from saffron.ledger import Ledger


def test_a_batchs_tasks_budget_and_end_reviews_read_only_that_batch(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)

    batch_a = ledger.create_batch(budget_usd=50.0)
    batch_b = ledger.create_batch(budget_usd=100.0)

    run_te7 = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_b)
    run_shared = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_b)

    task_te5 = ledger.create_task(
        run_shared, spec_id="TE-5", spec_sha="s" * 64, branch="saffron/TE-5"
    )
    task_te7 = ledger.create_task(
        run_te7, spec_id="TE-7", spec_sha="s" * 64, branch="saffron/TE-7"
    )
    task_te3 = ledger.create_task(
        run_shared, spec_id="TE-3", spec_sha="s" * 64, branch="saffron/TE-3"
    )
    ledger.set_task_state(task_te5, "RATE_LIMITED")
    ledger.set_task_state(task_te7, "READY_FOR_REVIEW")
    ledger.set_task_state(task_te3, "GATE_ERROR")

    run_te2 = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_a)
    task_te2 = ledger.create_task(
        run_te2, spec_id="TE-2", spec_sha="s" * 64, branch="saffron/TE-2"
    )
    ledger.set_task_state(task_te2, "READY_FOR_REVIEW")

    run_te7b = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=None)
    task_te7b = ledger.create_task(
        run_te7b, spec_id="TE-7", spec_sha="s" * 64, branch="saffron/TE-7-b"
    )

    run_te9 = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_b)
    task_te9 = ledger.create_task(
        run_te9, spec_id="TE-9", spec_sha="s" * 64, branch="saffron/TE-9"
    )
    ledger.set_task_state(task_te9, "EXHAUSTED")

    ledger.record_stack_layer(
        task_te7, position=1, predecessor_task_id=None, generation=0
    )
    ledger.record_stack_layer(
        task_te2, position=1, predecessor_task_id=None, generation=0
    )

    ledger.record_end_review(
        task_te7, lens="spec", status="reviewed", cost_usd=1.0, error=None
    )
    ledger.record_end_review(
        task_te7, lens="join", status="error", cost_usd=1.0, error=None
    )
    ledger.record_end_review(
        task_te2, lens="spec", status="error", cost_usd=1.0, error=None
    )
    ledger.record_end_review(
        task_te3, lens="spec", status="reviewed", cost_usd=1.0, error=None
    )
    ledger.record_end_review(
        task_te7b, lens="standards", status="reviewed", cost_usd=1.0, error=None
    )

    unused_batch = batch_b + 1000

    def row(task_id, spec_id, state):
        return (task_id, spec_id, state, ledger.record_key(task_id))

    assert [tuple(r) for r in ledger.batch_tasks(batch_b)] == [
        row(task_te7, "TE-7", "READY_FOR_REVIEW"),
        row(task_te5, "TE-5", "RATE_LIMITED"),
        row(task_te3, "TE-3", "GATE_ERROR"),
        row(task_te9, "TE-9", "EXHAUSTED"),
    ]
    assert [tuple(r) for r in ledger.batch_tasks(batch_a)] == [
        row(task_te2, "TE-2", "READY_FOR_REVIEW")
    ]
    assert ledger.batch_tasks(unused_batch) == []

    assert ledger.batch_budget(batch_a) == 50.0
    assert ledger.batch_budget(batch_b) == 100.0
    assert ledger.batch_budget(unused_batch) is None

    te7_key = ledger.record_key(task_te7)
    te2_key = ledger.record_key(task_te2)
    assert sorted(tuple(r) for r in ledger.end_reviews(batch_b)) == sorted(
        [
            (te7_key, "spec", "reviewed"),
            (te7_key, "join", "error"),
        ]
    )
    assert [tuple(r) for r in ledger.end_reviews(batch_a)] == [
        (te2_key, "spec", "error")
    ]
    assert ledger.end_reviews(unused_batch) == []

    ledger.close()
