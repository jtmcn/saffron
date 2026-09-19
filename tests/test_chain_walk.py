"""Tests for `saffron.chain_walk` — the checked walk `SA-0108` builds as the
other half of Q4's comparison (`DESIGN.md` Appendix T).

Every test imports `saffron.chain_walk` (and anything else this diff adds)
inside its own body, never at module scope: a module-scope import of a name
this change adds turns the `revert` gate's reverted run into a collection
error for the whole file, and `revert` reads a collection error as `skip`
(`DESIGN.md` §5.5.1).
"""

from __future__ import annotations

import hashlib
import shutil

from tests.test_projection import T, build, spec_text

# Every fixture diff below carries a non-ASCII character: `_diff_length`
# reads UTF-8, and an ASCII-only suite can't catch a byte/character miscount.


def test_the_checked_walk_needs_the_rows_and_the_files_and_nothing_else(tmp_path):
    from saffron.chain_walk import checked_walk

    plan = '{"café": true}'
    diff = "diff --git a/x b/x\n+café\n"

    # An attempt exists but holds no gate result — distinct from zero
    # attempts, which would satisfy a walk that only asked "any attempt".
    no_gate_result = T(
        "SA-9001",
        "MERGED",
        spec_text=spec_text("SA-9001"),
        pr_url="https://example/pr/9001",
        plan_line=True,
        plan_file=plan,
        diff_line=True,
        diff_file=diff,
        gate_result=False,
    )
    no_pr = T(
        "SA-9002",
        "MERGED",
        spec_text=spec_text("SA-9002"),
        pr_url=None,
        plan_line=True,
        plan_file=plan,
        diff_line=True,
        diff_file=diff,
        gate_result=True,
    )
    no_plan_file = T(
        "SA-9003",
        "MERGED",
        spec_text=spec_text("SA-9003"),
        pr_url="https://example/pr/9003",
        plan_line=True,
        plan_line_hash="0" * 12,
        diff_line=True,
        diff_file=diff,
        gate_result=True,
    )
    no_diff_file = T(
        "SA-9004",
        "MERGED",
        spec_text=spec_text("SA-9004"),
        pr_url="https://example/pr/9004",
        plan_line=True,
        plan_file=plan,
        diff_line=True,
        diff_line_length=123,
        gate_result=True,
    )
    whole_no_log = T(
        "SA-9005",
        "MERGED",
        spec_text=spec_text("SA-9005"),
        pr_url="https://example/pr/9005",
        plan_line=True,
        plan_file=plan,
        diff_line=True,
        diff_file=diff,
        gate_result=True,
    )

    ledger, out_dir, ids = build(
        tmp_path,
        [no_gate_result, no_pr, no_plan_file, no_diff_file, whole_no_log],
    )
    a, b, c, d, e = ids
    ledger.open_attempt(a, phase="IMPLEMENT")  # no gate result recorded on it

    assert (
        checked_walk(ledger, out_dir, a, "SA-9001", "https://example/pr/9001") is False
    )
    assert checked_walk(ledger, out_dir, b, "SA-9002", None) is False
    assert (
        checked_walk(ledger, out_dir, c, "SA-9003", "https://example/pr/9003") is False
    )
    assert (
        checked_walk(ledger, out_dir, d, "SA-9004", "https://example/pr/9004") is False
    )

    # An unrelated stored file (the event log) missing does not break the walk.
    (out_dir / "SA-9005" / "events.jsonl").unlink()
    assert (
        checked_walk(ledger, out_dir, e, "SA-9005", "https://example/pr/9005") is True
    )


def _nine_task_fixture(tmp_path, ledger=None):
    """The second criterion's fixture: three merged tasks the checked walk
    must judge, plus the reasons `Projection.left_out` already names for the
    rest — one break (an overwritten diff sharing a `pr_url` with a whole
    sibling), one merged-and-kept task with no gate result at all (walk
    broken, Q4 drops it too — not a break), three merged-and-left-out tasks
    by three different reasons, and two never-merged tasks (kept and left
    out alike) that must never reach the comparison."""
    plan = '{"v": "café"}'

    whole = T(
        "SA-9101",
        "MERGED",
        spec_text=spec_text("SA-9101"),
        pr_url="https://example/pr/9101",
        plan_line=True,
        plan_file=plan,
        diff_line=True,
        diff_file="diff --git a/x b/x\n+café\n",
        gate_result=True,
    )
    # Shared pr_url: the later task's plan and diff are what land on disk,
    # matching this task's own plan record but not its own diff record.
    overwritten = T(
        "SA-9102",
        "MERGED",
        spec_text=spec_text("SA-9102"),
        pr_url="https://example/pr/shared-9102",
        started_at="2026-03-01 00:00:00",
        plan_line=True,
        plan_line_hash=hashlib.sha256(plan.encode()).hexdigest()[:12],
        diff_line=True,
        diff_line_length=10,
        gate_result=True,
    )
    sibling = T(
        "SA-9102",
        "MERGED",
        spec_text=spec_text("SA-9102"),
        pr_url="https://example/pr/shared-9102",
        started_at="2026-03-01 00:05:00",
        plan_line=True,
        plan_file=plan,
        diff_line=True,
        diff_file="diff --git a/y b/y\n+café longer\n",
        gate_result=True,
    )
    no_gate_result = T(
        "SA-9103",
        "MERGED",
        spec_text=spec_text("SA-9103"),
        pr_url="https://example/pr/9103",
        plan_line=True,
        plan_file=plan,
        diff_line=True,
        diff_file="diff --git a/z b/z\n+café\n",
        gate_result=False,
    )
    diff_deleted = T(
        "SA-9104",
        "MERGED",
        spec_text=spec_text("SA-9104"),
        pr_url="https://example/pr/9104",
        plan_line=True,
        plan_file=plan,
        diff_line=True,
        diff_line_length=99,  # recorded, never written — deleted
        gate_result=True,
    )
    unattributable = T(
        "SA-9105",
        "MERGED",
        spec_text=spec_text("SA-9105"),
        pr_url="https://example/pr/9105",
        no_ceilings=True,
        plan_file=plan,
        diff_file="diff --git a/u b/u\n+café\n",
        gate_result=True,
    )
    spec_missing = T(
        "SA-9106",
        "MERGED",
        spec_sha="0" * 64,
        pr_url="https://example/pr/9106",
        plan_file=plan,
        diff_file="diff --git a/v b/v\n+café\n",
        gate_result=True,
    )
    rejected = T(
        "SA-9107",
        "REJECTED",
        spec_text=spec_text("SA-9107"),
        pr_url="https://example/pr/9107",
        plan_line=True,
        plan_file=plan,
        diff_line=True,
        diff_file="diff --git a/w b/w\n+café\n",
        gate_result=True,
    )
    running = T(
        "SA-9108",
        "RUNNING",
        spec_text=spec_text("SA-9108"),
    )

    return build(
        tmp_path,
        [
            whole,
            overwritten,
            sibling,
            no_gate_result,
            diff_deleted,
            unattributable,
            spec_missing,
            rejected,
            running,
        ],
        ledger=ledger,
    )


def test_the_output_names_only_breaks_the_checked_walk_calls_whole(tmp_path):
    from saffron.chain_walk import compare_chains
    from saffron.projection import materialize

    ledger, out_dir, ids = _nine_task_fixture(tmp_path)
    (
        whole_id,
        overwritten_id,
        sibling_id,
        no_gate_result_id,
        diff_deleted_id,
        unattributable_id,
        spec_missing_id,
        rejected_id,
        running_id,
    ) = ids

    output_path = tmp_path / "projection.ttl"
    result = materialize(ledger, out_dir, output_path)
    comparison = compare_chains(ledger, out_dir, result, output_path)

    assert comparison.compared == 4  # whole, overwritten, sibling, no_gate_result
    assert [(b.task_id, b.spec_id) for b in comparison.breaks] == [
        (overwritten_id, "SA-9102")
    ]
    assert comparison.left_out == {
        "missing_artifact": 1,
        "unattributable": 1,
        "spec_not_found": 1,
    }


def test_saffron_chains_prints_its_count_and_exits_0_or_2_on_a_raise(
    tmp_path, capsys, monkeypatch
):
    from saffron import cli
    from saffron import projection as projection_module
    from saffron.ledger import Ledger

    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")
    ledger, out_dir, ids = _nine_task_fixture(tmp_path, ledger=ledger)
    ledger.close()

    (home / "batches").mkdir()
    shutil.move(str(out_dir), str(home / "batches" / "v0"))

    exit_code = cli.main(["--home", str(home), "chains"])
    out = capsys.readouterr().out
    assert "chains: break task" in out
    assert "SA-9102" in out
    assert "4 merged task(s) compared, 1 break(s)" in out
    assert exit_code == 0

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(projection_module, "materialize", _raise)

    exit_code = cli.main(["--home", str(home), "chains"])
    out = capsys.readouterr().out
    assert "RuntimeError" in out
    assert "boom" in out
    assert exit_code == 2
