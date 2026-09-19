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

# Every fixture diff below carries a non-ASCII character: `_diff_length`
# reads UTF-8, and an ASCII-only suite can't catch a byte/character miscount.


def test_the_checked_walk_needs_the_rows_and_the_files_and_nothing_else(tmp_path):
    from saffron.chain_walk import checked_walk
    from tests.test_projection import T, build, spec_text

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

    assert checked_walk(ledger, out_dir, a) is False
    assert checked_walk(ledger, out_dir, b) is False  # its null pr_url is the ledger's
    assert checked_walk(ledger, out_dir, c) is False
    assert checked_walk(ledger, out_dir, d) is False

    # An unrelated stored file (the event log) missing does not break the walk.
    (out_dir / "SA-9005" / "events.jsonl").unlink()
    assert checked_walk(ledger, out_dir, e) is True


def _ten_task_fixture(tmp_path, ledger=None):
    """The second criterion's fixture: one break (an overwritten diff sharing
    a `pr_url` with a whole sibling), two merged-and-kept tasks the walk calls
    broken (no gate result; no `pr_url`) — Q4 drops them too, so no break —
    three merged-and-left-out tasks by three different reasons, and two
    never-merged tasks (kept and left out alike) that never reach the
    comparison."""
    from tests.test_projection import T, build, spec_text

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
    no_pr = T(
        "SA-9109",
        "MERGED",
        spec_text=spec_text("SA-9109"),
        pr_url=None,
        plan_line=True,
        plan_file=plan,
        diff_line=True,
        diff_file="diff --git a/n b/n\n+café\n",
        gate_result=True,
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
            no_pr,
        ],
        ledger=ledger,
    )


def test_the_output_names_only_breaks_the_checked_walk_calls_whole(tmp_path):
    from saffron.chain_walk import compare_chains
    from saffron.projection import materialize

    ledger, out_dir, ids = _ten_task_fixture(tmp_path)
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
        no_pr_id,
    ) = ids

    output_path = tmp_path / "projection.ttl"
    result = materialize(ledger, out_dir, output_path)
    comparison = compare_chains(ledger, out_dir, result, output_path)

    # whole, overwritten, sibling, no_gate_result, no_pr
    assert comparison.compared == 5
    assert [(b.task_id, b.spec_id) for b in comparison.breaks] == [
        (overwritten_id, "SA-9102")
    ]
    assert no_pr_id not in {b.task_id for b in comparison.breaks}
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
    ledger, out_dir, ids = _ten_task_fixture(tmp_path, ledger=ledger)
    overwritten_id = ids[1]
    ledger.close()

    (home / "batches").mkdir()
    shutil.move(str(out_dir), str(home / "batches" / "v0"))

    exit_code = cli.main(["--home", str(home), "chains"])
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert f"chains: break task {overwritten_id} SA-9102" in lines
    for reason in ("missing_artifact", "spec_not_found", "unattributable"):
        assert f"chains: 1 merged task(s) left out ({reason})" in lines
    assert "unsupported_end_state" not in out
    assert "chains: 5 merged task(s) compared, 1 break(s)" in lines
    assert lines.count(cli._DIFF_LENGTH_CAVEAT) == 1
    assert exit_code == 0

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(projection_module, "materialize", _raise)

    exit_code = cli.main(["--home", str(home), "chains"])
    out = capsys.readouterr().out
    assert "RuntimeError" in out
    assert "boom" in out
    assert exit_code == 2
