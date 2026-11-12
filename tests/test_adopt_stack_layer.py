"""Witnesses for `saffron adopt` placing a stack batch's own top layer
(b-323c97, `CONTEXT.md`'s Layer entry)."""

import json

from saffron import cli
from saffron.ledger import Ledger
from saffron.record.fold import fold
from saffron.record.memory import MemoryRecord
from tests.test_cli import (
    _checkout_with_origin,
    _fake_gh_names_a_pull_request,
    _FakeRegate,
    _routed_ledger,
    _seed_repo,
    _seed_task,
    _task_state,
)


def _seed_stack_task(ledger, repo_id, batch_id, *, spec_id, state, follow_up=False):
    """A task of a stack batch: its own run, attached to `batch_id`, with
    the one `spec_reviews` row every stack-batch task carries, the order's
    own and a follow-up's alike (`Ledger.stack_batch_of`). `follow_up`
    also files a `follow_up` spec text, the mark `batch_follow_ups` reads."""
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    ledger.attach_run_to_batch(run_id, batch_id)
    task_id = ledger.create_task(
        run_id, spec_id=spec_id, spec_sha="s" * 40, branch=f"saffron/{spec_id}"
    )
    ledger.record_spec_review(
        task_id, route="run", block=None, block_sha256=None, error=None, findings=[]
    )
    if follow_up:
        ledger.record_spec_text(
            task_id,
            origin="follow_up",
            spec_id=spec_id,
            path=f".saffron/specs/{spec_id}-fix.md",
            text="placeholder",
        )
    ledger.set_task_state(task_id, state)
    return task_id


def _adopt_green(monkeypatch, repo, home, *, spec_id, task_id, number, head_sha):
    """One `saffron adopt` call whose `gh` and re-gate both answer green."""
    branch = f"saffron/{spec_id}"
    url = f"https://github.com/owner/repo/pull/{number}"
    monkeypatch.setattr(
        cli,
        "run_gh",
        _fake_gh_names_a_pull_request(
            url, head_branch=branch, number=number, head_sha=head_sha
        ),
    )
    monkeypatch.setattr(cli.regate, "run_regate", _FakeRegate({task_id: (head_sha, 0)}))
    return cli.main(
        ["--home", str(home), "adopt", spec_id, number, "--repo", str(repo)]
    )


def test_an_adopted_task_that_ran_after_every_layer_becomes_its_batchs_top_layer(
    tmp_path, monkeypatch, capsys
):
    """Adopt places an `EXHAUSTED` task that ran after every layer a stack
    batch holds as its own new top layer: position one past the current
    top, predecessor the current top task and its head, generation 0. A
    batch with no layer at all gets position 1 and no predecessor.
    `saffron finish` refuses the empty batch with `holds no layer` before
    the adopt, and passes that check once the layer lands. The new
    layer is a fact as well as a row: a fold of the record alone, with
    no SQL row to lean on, rebuilds it."""
    repo = _checkout_with_origin(tmp_path, "https://github.com/owner/repo.git")
    home = tmp_path / "home"
    home.mkdir()
    record = MemoryRecord()
    monkeypatch.setattr(cli, "Ledger", lambda path, **_: Ledger(path, record=record))
    ledger = Ledger(home / "ledger.db", record=record)
    repo_id = _seed_repo(tmp_path, ledger, "https://github.com/owner/repo.git")
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

    # A batch holding no layer at all, the shape batches 59, 66 and 79 held.
    empty_batch = ledger.create_batch(100.0)
    bare_task = _seed_stack_task(
        ledger, repo_id, empty_batch, spec_id="SY-BARE", state="EXHAUSTED"
    )
    ledger.close_batch(empty_batch, "DRAINED")
    finish_dir = home / "batches" / "v0" / "finish" / str(empty_batch)
    finish_dir.mkdir(parents=True)
    (finish_dir / "deferred.json").write_text(
        json.dumps({"batch_id": empty_batch, "repo": str(repo.resolve())})
    )

    # A batch whose two layers both ran before the newly adopted task.
    full_batch = ledger.create_batch(100.0)
    layer_one = _seed_stack_task(
        ledger, repo_id, full_batch, spec_id="SY-ONE", state="READY_FOR_REVIEW"
    )
    ledger.record_stack_layer(
        layer_one, position=1, predecessor_task_id=None, generation=0
    )
    layer_two = _seed_stack_task(
        ledger, repo_id, full_batch, spec_id="SY-TWO", state="READY_FOR_REVIEW"
    )
    ledger.record_push(layer_two, "2" * 40)
    ledger.record_stack_layer(
        layer_two, position=2, predecessor_task_id=layer_one, generation=0
    )
    layer_two_key = ledger.record_key(layer_two)
    newest_task = _seed_stack_task(
        ledger, repo_id, full_batch, spec_id="SY-NEWEST", state="EXHAUSTED"
    )
    ledger.close()

    assert (
        cli.main(["--home", str(home), "finish", str(empty_batch), "--repo", str(repo)])
        == 2
    )
    assert "holds no layer" in capsys.readouterr().out

    adopted_head = "c" * 40
    assert (
        _adopt_green(
            monkeypatch,
            repo,
            home,
            spec_id="SY-BARE",
            task_id=bare_task,
            number="71",
            head_sha=adopted_head,
        )
        == 0
    )
    assert f"layer 1 of batch {empty_batch}" in capsys.readouterr().out

    assert (
        _adopt_green(
            monkeypatch,
            repo,
            home,
            spec_id="SY-NEWEST",
            task_id=newest_task,
            number="72",
            head_sha=adopted_head,
        )
        == 0
    )
    assert f"layer 3 of batch {full_batch}" in capsys.readouterr().out

    direct = Ledger(home / "ledger.db")
    bare_layers = direct.stack_layers(empty_batch)
    assert len(bare_layers) == 1
    assert bare_layers[0]["position"] == 1
    assert bare_layers[0]["predecessor_key"] is None
    assert bare_layers[0]["predecessor_head"] is None
    assert bare_layers[0]["generation"] == 0

    full_layers = direct.stack_layers(full_batch)
    assert len(full_layers) == 3
    assert full_layers[-1]["task_id"] == newest_task
    assert full_layers[-1]["position"] == 3
    assert full_layers[-1]["predecessor_key"] == direct.record_key(layer_two)
    assert full_layers[-1]["predecessor_head"] == "2" * 40
    assert full_layers[-1]["generation"] == 0
    direct.close()

    # The fact is what a fold rebuilds from, not the row `_apply` leaves
    # behind: a write that skips the record would still read back above.
    folded = Ledger(tmp_path / "folded.db")
    outcome = fold(record, folded)
    assert outcome.skipped == []
    folded_bare = folded.stack_layers(empty_batch)
    assert len(folded_bare) == 1
    assert folded_bare[0]["spec_id"] == "SY-BARE"
    folded_full = folded.stack_layers(full_batch)
    assert [row["spec_id"] for row in folded_full] == ["SY-ONE", "SY-TWO", "SY-NEWEST"]
    assert folded_full[-1]["position"] == 3
    assert folded_full[-1]["predecessor_key"] == layer_two_key
    assert folded_full[-1]["predecessor_head"] == "2" * 40
    assert folded_full[-1]["generation"] == 0
    folded.close()

    assert (
        cli.main(["--home", str(home), "finish", str(empty_batch), "--repo", str(repo)])
        == 2
    )
    out = capsys.readouterr().out
    assert "holds no layer" not in out
    assert "CLAUDE_CODE_OAUTH_TOKEN is unset" in out


def test_an_adopted_follow_up_becomes_a_layer_at_generation_one(
    tmp_path, monkeypatch, capsys
):
    """A follow-up `Ledger.batch_follow_ups` names is placed at generation
    1, the generation it ran in, never the order layer's own 0."""
    repo = _checkout_with_origin(tmp_path, "https://github.com/owner/repo.git")
    home = tmp_path / "home"
    home.mkdir()
    ledger = _routed_ledger(home / "ledger.db")
    repo_id = _seed_repo(tmp_path, ledger, "https://github.com/owner/repo.git")

    batch_id = ledger.create_batch(100.0)
    order_layer = _seed_stack_task(
        ledger, repo_id, batch_id, spec_id="SY-ORDER", state="READY_FOR_REVIEW"
    )
    ledger.record_stack_layer(
        order_layer, position=1, predecessor_task_id=None, generation=0
    )
    follow_up_task = _seed_stack_task(
        ledger,
        repo_id,
        batch_id,
        spec_id="SY-FOLLOW",
        state="EXHAUSTED",
        follow_up=True,
    )
    ledger.close()

    assert (
        _adopt_green(
            monkeypatch,
            repo,
            home,
            spec_id="SY-FOLLOW",
            task_id=follow_up_task,
            number="73",
            head_sha="c" * 40,
        )
        == 0
    )
    assert f"layer 2 of batch {batch_id}" in capsys.readouterr().out

    direct = Ledger(home / "ledger.db")
    layers = direct.stack_layers(batch_id)
    assert len(layers) == 2
    assert layers[-1]["task_id"] == follow_up_task
    assert layers[-1]["generation"] == 1
    direct.close()


def test_an_adopted_task_a_layer_ran_after_gets_no_layer_and_a_no_end_review_line(
    tmp_path, monkeypatch, capsys
):
    """When any layer of the batch ran after the adopted task, adopt
    records no layer. It still moves the task to `READY_FOR_REVIEW`,
    and prints a line holding `no end review` and the batch id. Driven
    once with the batch's only layer after the task, and once with one
    layer before it and one after, `SA-0353`'s batch 73 shape."""
    repo = _checkout_with_origin(tmp_path, "https://github.com/owner/repo.git")
    home = tmp_path / "home"
    home.mkdir()
    ledger = _routed_ledger(home / "ledger.db")
    repo_id = _seed_repo(tmp_path, ledger, "https://github.com/owner/repo.git")

    # The batch's only layer ran after the adopted task.
    only_after_batch = ledger.create_batch(100.0)
    only_after_task = _seed_stack_task(
        ledger, repo_id, only_after_batch, spec_id="SY-MISSED", state="EXHAUSTED"
    )
    later_layer = _seed_stack_task(
        ledger, repo_id, only_after_batch, spec_id="SY-LATER", state="READY_FOR_REVIEW"
    )
    ledger.record_stack_layer(
        later_layer, position=1, predecessor_task_id=None, generation=0
    )

    # One layer before the task, one after it (batch 73's own shape).
    mixed_batch = ledger.create_batch(100.0)
    before_layer = _seed_stack_task(
        ledger, repo_id, mixed_batch, spec_id="SY-353", state="READY_FOR_REVIEW"
    )
    ledger.record_stack_layer(
        before_layer, position=1, predecessor_task_id=None, generation=0
    )
    mixed_task = _seed_stack_task(
        ledger, repo_id, mixed_batch, spec_id="SY-353B", state="EXHAUSTED"
    )
    after_layer = _seed_stack_task(
        ledger, repo_id, mixed_batch, spec_id="SY-354", state="READY_FOR_REVIEW"
    )
    ledger.record_stack_layer(
        after_layer, position=2, predecessor_task_id=before_layer, generation=0
    )
    ledger.close()

    adopted_head = "c" * 40
    for spec_id, task_id, number, batch_id in (
        ("SY-MISSED", only_after_task, "81", only_after_batch),
        ("SY-353B", mixed_task, "82", mixed_batch),
    ):
        assert (
            _adopt_green(
                monkeypatch,
                repo,
                home,
                spec_id=spec_id,
                task_id=task_id,
                number=number,
                head_sha=adopted_head,
            )
            == 0
        )
        out = capsys.readouterr().out
        assert "no end review" in out
        assert f"batch {batch_id}" in out
        assert _task_state(home, task_id) == "READY_FOR_REVIEW"

    direct = Ledger(home / "ledger.db")
    assert len(direct.stack_layers(only_after_batch)) == 1
    assert len(direct.stack_layers(mixed_batch)) == 2
    direct.close()


def test_adopt_outside_a_stack_batch_or_of_a_layer_records_nothing_and_prints_no_line(
    tmp_path, monkeypatch, capsys
):
    """Adopt records no layer for a task on a plain batch, a task whose
    run names no batch, or a task that already holds one. Each still
    reaches `READY_FOR_REVIEW` with no extra line. The same witness then
    adopts a stack batch's own task with no layer yet and sees it
    placed, with its line."""
    repo = _checkout_with_origin(tmp_path, "https://github.com/owner/repo.git")
    home = tmp_path / "home"
    home.mkdir()
    ledger = _routed_ledger(home / "ledger.db")
    repo_id = _seed_repo(tmp_path, ledger, "https://github.com/owner/repo.git")

    # A task on a plain batch: its run names a batch, but it was never
    # reviewed, so `stack_batch_of` reads no stack batch for it.
    plain_batch = ledger.create_batch(100.0)
    plain_run = ledger.create_run(repo_id, base_sha="a" * 40)
    ledger.attach_run_to_batch(plain_run, plain_batch)
    plain_task = ledger.create_task(
        plain_run, spec_id="SY-PLAIN", spec_sha="s" * 40, branch="saffron/SY-PLAIN"
    )
    ledger.set_task_state(plain_task, "EXHAUSTED")

    # A reviewed task whose run names no batch, the shape `saffron draft` leaves.
    orphan_task = _seed_task(ledger, repo_id, spec_id="SY-ORPHAN", state="EXHAUSTED")
    ledger.record_spec_review(
        orphan_task, route="run", block=None, block_sha256=None, error=None, findings=[]
    )

    # A task already a layer of its own stack batch, seeded `EXHAUSTED`
    # to reach the already-a-layer check through the re-gate path.
    layer_batch = ledger.create_batch(100.0)
    already_task = _seed_stack_task(
        ledger, repo_id, layer_batch, spec_id="SY-ALREADY", state="EXHAUSTED"
    )
    ledger.record_stack_layer(
        already_task, position=1, predecessor_task_id=None, generation=0
    )

    # A genuine stack-batch task that holds no layer yet.
    placed_batch = ledger.create_batch(100.0)
    placed_task = _seed_stack_task(
        ledger, repo_id, placed_batch, spec_id="SY-PLACED", state="EXHAUSTED"
    )
    ledger.close()

    adopted_head = "c" * 40
    for spec_id, task_id, number in (
        ("SY-PLAIN", plain_task, "91"),
        ("SY-ORPHAN", orphan_task, "92"),
        ("SY-ALREADY", already_task, "93"),
    ):
        assert (
            _adopt_green(
                monkeypatch,
                repo,
                home,
                spec_id=spec_id,
                task_id=task_id,
                number=number,
                head_sha=adopted_head,
            )
            == 0
        )
        out = capsys.readouterr().out
        adopt_lines = [line for line in out.splitlines() if line.startswith("adopt:")]
        assert len(adopt_lines) == 1
        assert "layer" not in out
        assert "no end review" not in out
        assert _task_state(home, task_id) == "READY_FOR_REVIEW"

    assert (
        _adopt_green(
            monkeypatch,
            repo,
            home,
            spec_id="SY-PLACED",
            task_id=placed_task,
            number="94",
            head_sha=adopted_head,
        )
        == 0
    )
    out = capsys.readouterr().out
    assert f"layer 1 of batch {placed_batch}" in out
    assert _task_state(home, placed_task) == "READY_FOR_REVIEW"

    direct = Ledger(home / "ledger.db")
    assert direct.stack_layers(plain_batch) == []
    assert len(direct.stack_layers(layer_batch)) == 1
    assert len(direct.stack_layers(placed_batch)) == 1
    assert direct.stack_layers(placed_batch)[0]["task_id"] == placed_task
    direct.close()


def test_adopt_records_a_layer_only_when_its_regate_moves_the_task_to_ready_for_review(
    tmp_path, monkeypatch, capsys
):
    """A red re-gate, a declined one and a task already
    `READY_FOR_REVIEW` record no layer and print neither line. The same
    red task, adopted again on a green re-gate, is placed."""
    repo = _checkout_with_origin(tmp_path, "https://github.com/owner/repo.git")
    home = tmp_path / "home"
    home.mkdir()
    ledger = _routed_ledger(home / "ledger.db")
    repo_id = _seed_repo(tmp_path, ledger, "https://github.com/owner/repo.git")

    batch_id = ledger.create_batch(100.0)
    red_task = _seed_stack_task(
        ledger, repo_id, batch_id, spec_id="SY-RED", state="EXHAUSTED"
    )
    declined_task = _seed_stack_task(
        ledger, repo_id, batch_id, spec_id="SY-DECLINED", state="NOT_IMPLEMENTED"
    )
    already_ready = _seed_stack_task(
        ledger, repo_id, batch_id, spec_id="SY-READY", state="DIAGNOSING"
    )
    ledger.record_push(already_ready, "5" * 40)
    ledger.set_task_state(already_ready, "READY_FOR_REVIEW")
    ledger.close()

    red_head = "a" * 40
    declined_head = "b" * 40
    ready_head = "5" * 40

    monkeypatch.setattr(
        cli.regate,
        "run_regate",
        _FakeRegate({red_task: (red_head, 5), declined_task: 1}),
    )
    for spec_id, _task_id, number, head_sha in (
        ("SY-RED", red_task, "61", red_head),
        ("SY-DECLINED", declined_task, "62", declined_head),
        ("SY-READY", already_ready, "63", ready_head),
    ):
        branch = f"saffron/{spec_id}"
        url = f"https://github.com/owner/repo/pull/{number}"
        monkeypatch.setattr(
            cli,
            "run_gh",
            _fake_gh_names_a_pull_request(
                url, head_branch=branch, number=number, head_sha=head_sha
            ),
        )
        assert (
            cli.main(
                ["--home", str(home), "adopt", spec_id, number, "--repo", str(repo)]
            )
            == 0
        )
        assert "layer" not in capsys.readouterr().out

    direct = Ledger(home / "ledger.db")
    assert direct.stack_layers(batch_id) == []
    direct.close()

    green_head = "9" * 40
    assert (
        _adopt_green(
            monkeypatch,
            repo,
            home,
            spec_id="SY-RED",
            task_id=red_task,
            number="61",
            head_sha=green_head,
        )
        == 0
    )
    assert f"layer 1 of batch {batch_id}" in capsys.readouterr().out

    direct = Ledger(home / "ledger.db")
    layers = direct.stack_layers(batch_id)
    assert len(layers) == 1
    assert layers[0]["task_id"] == red_task
    direct.close()
