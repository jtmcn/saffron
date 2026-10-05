"""The morning queue's stack section (backlog item b-792ab2 step 9, ADR 7)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from saffron.gates.contract import GateResult
from saffron.intake import Spec
from saffron.ledger import Ledger
from saffron.report.index import PLACEHOLDER, QueueLine, _row, append_queue_line

SIZE_900 = "900 changed tokens within the feature ceiling of 3000"
SIZE_2410 = "2410 changed tokens within the feature ceiling of 3000"
SIZE_1180 = "1180 changed tokens within the feature ceiling of 3000 <a>"
SIZE_300 = "300 changed tokens within the feature ceiling of 3000"
P = PLACEHOLDER

REPO_URL = "https://github.com/o/r.git"


def _size(summary: str) -> GateResult:
    return GateResult(gate="size", status="pass", tool="size 1.0", summary=summary)


def _tests(summary: str) -> GateResult:
    return GateResult(gate="tests", status="pass", tool="pytest 8.0", summary=summary)


def _attempt(
    ledger: Ledger,
    task_id: int,
    turns: int,
    cost: float,
    results,
    phase: str = "IMPLEMENTING",
) -> None:
    attempt_id = ledger.open_attempt(task_id, phase=phase)
    for result in results:
        ledger.record_gate_result(result, attempt_id=attempt_id)
    ledger.close_attempt(
        attempt_id,
        session_id="s",
        subtype="success",
        terminal_reason=None,
        num_turns=turns,
        cost_usd_est=cost,
    )


# One row per run of batch B, in run order. A `READY_FOR_REVIEW` end packages
# the task with its sha and pull request. Any other end sets the state alone.
B_ROWS = [
    ("TE-6", 9, [(8, 0.40, [])], "RATE_LIMITED", None, None),
    ("TE-3", 11, [(12, 1.25, [])], "GATE_ERROR", None, None),
    (
        "TE-7",
        18,
        [(44, 5.50, [_size(SIZE_900)]), (3, 0.00, [])],
        "READY_FOR_REVIEW",
        "7" * 40,
        "https://github.com/o/r/pull/207",
    ),
    ("TE-5", 13, [(20, 4.00, [])], "EXHAUSTED", None, None),
    (
        "TE-9",
        20,
        [
            (50, 3.00, [_size(SIZE_2410)]),
            (30, 2.00, [_size(SIZE_1180), _tests("412 passed")]),
        ],
        "READY_FOR_REVIEW",
        "9" * 40,
        "https://github.com/o/r/pull/209",
    ),
    (
        "TE-6",
        16,
        [(20, 1.00, []), (61, 5.10, [])],
        "READY_FOR_REVIEW",
        "6" * 40,
        "https://github.com/o/r/pull/206",
    ),
    (
        "TE-4",
        12,
        [(10, 0.75, [_size(SIZE_300)])],
        "READY_FOR_REVIEW",
        "4" * 40,
        "https://github.com/o/r/pull/204",
    ),
]


def _build_batches(tmp_path: Path):
    """Batches A and B, as the spec's notes lay them out. Shared by every
    witness below that reads a real ledger, so no two witnesses build their
    own copy of this arrangement."""
    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("r", REPO_URL, "/m.git", policy_sha=None)

    specs = {
        "TE-7": Spec(
            id="TE-7", title="Seven", type="chore", budget_usd=25, max_turns=90
        ),
        "TE-9": Spec(
            id="TE-9",
            title="Nine",
            type="chore",
            budget_usd=24,
            max_turns=140,
            depends_on=["TE-3"],
        ),
        "TE-6": Spec(id="TE-6", title="Six", type="chore", budget_usd=22, max_turns=70),
        "TE-3": Spec(
            id="TE-3", title="Three", type="chore", budget_usd=11, max_turns=60
        ),
        "TE-5": Spec(
            id="TE-5", title="Five", type="chore", budget_usd=13, max_turns=60
        ),
    }

    batch_a = ledger.create_batch(50.0)
    run_a = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_a)
    te2 = ledger.create_task(
        run_a, spec_id="TE-2", spec_sha="s" * 64, branch="saffron/TE-2", budget_usd=10.0
    )
    _attempt(ledger, te2, 5, 2.00, [])
    ledger.set_task_package(
        te2,
        "READY_FOR_REVIEW",
        "saffron/TE-2",
        "2" * 40,
        "https://github.com/o/r/pull/2",
    )
    ledger.record_stack_layer(te2, position=1, predecessor_task_id=None, generation=0)

    batch_b = ledger.create_batch(100.0)
    created = []
    for spec_id, budget, attempts, end, sha, pr in B_ROWS:
        run_id = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_b)
        task_id = ledger.create_task(
            run_id,
            spec_id=spec_id,
            spec_sha="s" * 64,
            branch=f"saffron/{spec_id}",
            budget_usd=float(budget),
        )
        # TE-4's one batch B attempt is opened in REPAIRING rather than the
        # default IMPLEMENTING, so its IMPLEMENT line reads absent.
        attempt_phase = "REPAIRING" if spec_id == "TE-4" else "IMPLEMENTING"
        for turns, cost, results in attempts:
            _attempt(ledger, task_id, turns, cost, results, phase=attempt_phase)
        if end == "READY_FOR_REVIEW":
            assert sha is not None and pr is not None
            ledger.set_task_package(task_id, end, f"saffron/{spec_id}", sha, pr)
        else:
            ledger.set_task_state(task_id, end)
        created.append(task_id)
    te6_1, te3, te7, te5, te9, te6_2, te4_1 = created

    ledger.record_stack_layer(te6_2, position=3, predecessor_task_id=te9, generation=0)
    ledger.record_stack_layer(te4_1, position=4, predecessor_task_id=te7, generation=1)
    ledger.record_stack_layer(te7, position=1, predecessor_task_id=None, generation=0)
    ledger.record_stack_layer(te9, position=2, predecessor_task_id=te7, generation=0)

    # Neither read live: baked into `TE-9`'s and `TE-4`'s layers already.
    ledger.record_push(te7, "e" * 40)

    # Phase-tagged attempts the turns witnesses read (see the spec's table).
    _attempt(ledger, te7, 150, 0.0, [], phase="SPEC_REVIEW")
    _attempt(ledger, te7, 200, 0.0, [], phase="REPLAY")
    _attempt(ledger, te9, 12, 0.0, [], phase="SPEC_REVIEW")
    _attempt(ledger, te9, 31, 0.0, [], phase="SPEC_REVIEW")
    _attempt(ledger, te9, 7, 0.0, [], phase="SPEC_REVIEW")
    _attempt(ledger, te9, 0, 0.0, [], phase="SPEC_WRITING")
    _attempt(ledger, te9, 27, 0.0, [], phase="REPAIRING")
    _attempt(ledger, te9, 38, 0.0, [], phase="REVIEWING")
    _attempt(ledger, te9, 45, 0.0, [], phase="REBUTTING")
    _attempt(ledger, te4_1, 9, 0.0, [], phase="SPEC_WRITING")
    ledger.open_attempt(te6_2, phase="REBUTTING")

    ledger.set_task_state(te9, "REJECTED")

    run8 = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_b)
    te4_2 = ledger.create_task(
        run8, spec_id="TE-4", spec_sha="s" * 64, branch="saffron/TE-4", budget_usd=5.0
    )
    _attempt(ledger, te4_2, 4, 0.20, [])
    ledger.set_task_state(te4_2, "RATE_LIMITED")

    # A later `saffron cell`, outside any batch: no layer, no order entry.
    run_outside = ledger.create_run(repo_id, base_sha="a" * 40)
    te7_second = ledger.create_task(
        run_outside, spec_id="TE-7", spec_sha="s" * 64, branch="saffron/TE-7-later"
    )
    ledger.set_task_package(
        te7_second,
        "READY_FOR_REVIEW",
        "saffron/TE-7-later",
        "8" * 40,
        "https://github.com/o/r/pull/300",
    )

    for task_id, lens, status, cost, error in [
        (te4_1, "spec", "reviewed", 0.0, None),
        (te4_1, "standards", "reviewed", 0.0, None),
        (te4_1, "join", "error", 0.0, "join broke"),
        (te6_2, "spec", "error", 0.25, "spec broke"),
        (te6_2, "standards", "reviewed", 0.0, None),
        (te9, "spec", "reviewed", 0.0, None),
        (te7, "spec", "reviewed", 0.0, None),
        (te7, "standards", "error", 0.0, "standards broke"),
    ]:
        ledger.record_end_review(
            task_id, lens=lens, status=status, cost_usd=cost, error=error
        )

    return ledger, specs, batch_a, batch_b


def _make_layerless_batch(ledger: Ledger) -> int:
    """A batch with one task and no `stack_layers` row, built fresh by each
    witness that needs one so batch order never shifts another's view."""
    repo_id = ledger.upsert_repo("r", REPO_URL, "/m.git", policy_sha=None)
    batch_id = ledger.create_batch(20.0)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_id)
    task_id = ledger.create_task(
        run_id, spec_id="TE-11", spec_sha="s" * 64, branch="saffron/TE-11"
    )
    _attempt(ledger, task_id, 10, 1.0, [])
    ledger.set_task_state(task_id, "EXHAUSTED")
    return batch_id


def _assert_layer(actual, expected: tuple) -> None:
    fields = (
        "position",
        "spec_id",
        "title",
        "state",
        "spent_usd",
        "budget_usd",
        "pr_url",
        "size",
        "generation",
        "predecessor",
        "predecessor_head",
        "end_review",
    )
    for name, value in zip(fields, expected, strict=True):
        got = getattr(actual, name)
        if isinstance(value, float):
            assert got == pytest.approx(value), name
        else:
            assert got == value, name


def test_the_stack_view_reads_each_layer_of_one_batch_in_position_order(tmp_path):
    from saffron.report.stack import stack_view

    ledger, specs, batch_a, batch_b = _build_batches(tmp_path)

    view = stack_view(ledger, batch_b, specs)
    assert view is not None

    assert view.order == [
        ("TE-6", "RATE_LIMITED", None),
        ("TE-3", "GATE_ERROR", None),
        ("TE-7", "READY_FOR_REVIEW", 1),
        ("TE-5", "EXHAUSTED", None),
        ("TE-9", "REJECTED", 2),
        ("TE-6", "READY_FOR_REVIEW", 3),
        ("TE-4", "READY_FOR_REVIEW", 4),
        ("TE-4", "RATE_LIMITED", None),
    ]
    assert view.spent_usd == pytest.approx(23.45)
    assert view.budget_usd == pytest.approx(100.0)
    assert view.outcomes == {
        "RATE_LIMITED": 2,
        "GATE_ERROR": 1,
        "READY_FOR_REVIEW": 3,
        "EXHAUSTED": 1,
        "REJECTED": 1,
    }

    expected_layers = [
        (
            1,
            "TE-7",
            "Seven",
            "READY_FOR_REVIEW",
            5.50,
            18.0,
            "https://github.com/o/r/pull/207",
            SIZE_900,
            0,
            None,
            None,
            "error",
        ),
        (
            2,
            "TE-9",
            "Nine",
            "REJECTED",
            5.00,
            20.0,
            "https://github.com/o/r/pull/209",
            SIZE_1180,
            0,
            "TE-7",
            "7" * 40,
            "not_reached",
        ),
        (
            3,
            "TE-6",
            "Six",
            "READY_FOR_REVIEW",
            6.10,
            16.0,
            "https://github.com/o/r/pull/206",
            None,
            0,
            "TE-9",
            "9" * 40,
            "error",
        ),
        (
            4,
            "TE-4",
            None,
            "READY_FOR_REVIEW",
            0.75,
            12.0,
            "https://github.com/o/r/pull/204",
            SIZE_300,
            1,
            "TE-7",
            "7" * 40,
            "reviewed",
        ),
    ]
    assert len(view.layers) == len(expected_layers)
    for actual, expected in zip(view.layers, expected_layers, strict=True):
        _assert_layer(actual, expected)

    view_a = stack_view(ledger, batch_a, specs)
    assert view_a is not None
    assert len(view_a.layers) == 1
    assert view_a.layers[0].spec_id == "TE-2"
    assert view_a.layers[0].end_review == "not_reached"

    batch_c = _make_layerless_batch(ledger)
    assert stack_view(ledger, batch_c, specs) is None


def test_the_stack_view_renders_a_section_for_the_batch_and_each_layer():
    from saffron.report.stack import StackLayer, StackView, render_stack

    nine = StackLayer(
        position=1,
        spec_id="TE-9",
        title="<b>Nine</b>",
        state="READY_FOR_REVIEW",
        spent_usd=7.25,
        budget_usd=20.00,
        turns=(("IMPLEMENT", 44, 140, False),),
        pr_url="https://github.com/o/r/pull/209",
        size=SIZE_1180,
        generation=1,
        predecessor="TE-7",
        predecessor_head="7" * 40,
        end_review="error",
    )
    four = StackLayer(
        # 5 matches no index into the order and no count of its layers, so
        # a layer number taken from either reads wrong.
        position=5,
        spec_id="TE-4",
        title=None,
        state="READY_FOR_REVIEW",
        spent_usd=0.0,
        budget_usd=None,
        turns=(("IMPLEMENT", None, None, False),),
        pr_url=None,
        size=None,
        generation=0,
        predecessor=None,
        predecessor_head=None,
        end_review="not_reached",
    )
    view = StackView(
        batch_id=9,
        order=[
            ("TE-3", "GATE_ERROR", None),
            ("TE-9", "READY_FOR_REVIEW", 1),
            ("TE-5", "EXHAUSTED", None),
            ("TE-4", "READY_FOR_REVIEW", 5),
        ],
        spent_usd=12.25,
        budget_usd=100.0,
        outcomes={"GATE_ERROR": 1, "READY_FOR_REVIEW": 2, "EXHAUSTED": 1},
        layers=[nine, four],
    )

    rendered = render_stack(view)
    sections = rendered.split("<section")
    assert len(sections) == 4
    _, batch_section, nine_section, four_section = sections

    assert "batch 9" in batch_section
    assert "$12.25 of $100.00" in batch_section
    entries = [
        "TE-3 <code>GATE_ERROR</code> no layer",
        "TE-9 <code>READY_FOR_REVIEW</code> layer 1",
        "TE-5 <code>EXHAUSTED</code> no layer",
        "TE-4 <code>READY_FOR_REVIEW</code> layer 5",
    ]
    for entry in entries:
        assert entry in batch_section
    positions = [batch_section.index(entry) for entry in entries]
    assert positions == sorted(positions)
    assert "<code>GATE_ERROR</code> 1" in batch_section
    assert "<code>READY_FOR_REVIEW</code> 2" in batch_section
    assert "<code>EXHAUSTED</code> 1" in batch_section

    assert "TE-9" in nine_section
    assert "<code>READY_FOR_REVIEW</code> layer 1" in nine_section
    assert "&lt;b&gt;Nine&lt;/b&gt;" in nine_section
    assert "<b>Nine</b>" not in nine_section
    assert "$7.25 of $20.00" in nine_section
    assert "IMPLEMENT 44 of 140 turns" in nine_section
    assert "generation 1" in nine_section
    assert f"on TE-7 at {'7' * 40}" in nine_section
    assert "end review <code>error</code>" in nine_section
    assert (
        "1180 changed tokens within the feature ceiling of 3000 &lt;a&gt;"
        in nine_section
    )
    assert "<a>" not in nine_section

    assert "TE-4" in four_section
    assert "<code>READY_FOR_REVIEW</code> layer 5" in four_section
    assert four_section.count(P) >= 7
    assert f"of {P}" in four_section
    assert f"IMPLEMENT {P} of {P} turns" in four_section
    assert f"on {P}" in four_section
    assert "end review <code>not_reached</code>" in four_section
    assert "None" not in rendered


def test_the_queue_page_carries_the_newest_batchs_stack_view_and_only_that(tmp_path):
    from saffron.report.stack import render_stack, stack_view, write_stack_view

    ledger, specs, _batch_a, batch_b = _build_batches(tmp_path)
    out_dir = tmp_path / "page"

    te7_line = QueueLine(
        repo="r",
        spec_id="TE-7",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=5.50,
        concerns=0,
        added=10,
        removed=2,
        link="",
    )
    te9_line = QueueLine(
        repo="r",
        spec_id="TE-9",
        state="REJECTED",
        attempts=1,
        cost_usd_est=5.00,
        concerns=0,
        added=4,
        removed=1,
        link="",
    )
    append_queue_line(out_dir, te7_line)
    append_queue_line(out_dir, te9_line)

    store = out_dir / "queue.json"
    before_bytes = store.read_bytes()
    before_inode = store.stat().st_ino

    page = out_dir / "index.html"
    assert "</header>\n<table>" in page.read_text()

    written = write_stack_view(out_dir, ledger, specs)
    assert written == page

    view = stack_view(ledger, batch_b, specs)
    assert view is not None
    rendered = render_stack(view)

    after_write = page.read_text()
    assert f"</header>\n{rendered}<table>" in after_write
    assert "TE-2" not in after_write
    assert "tasks <strong>2</strong>" in after_write
    assert "spend <strong>$10.50</strong>" in after_write
    assert _row(te7_line) in after_write

    assert store.read_bytes() == before_bytes
    assert store.stat().st_ino == before_inode

    batch_c = _make_layerless_batch(ledger)
    assert batch_c > batch_b
    append_queue_line(
        out_dir,
        QueueLine(
            repo="r",
            spec_id="TE-11",
            state="EXHAUSTED",
            attempts=1,
            cost_usd_est=1.0,
            concerns=0,
            added=0,
            removed=0,
            link="",
        ),
    )
    after_append = page.read_bytes()
    assert b"</header>\n<table>" in after_append

    assert write_stack_view(out_dir, ledger, specs) is None
    assert page.read_bytes() == after_append

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert write_stack_view(empty_dir, ledger, specs) is None
    assert list(empty_dir.iterdir()) == []


def _layer_section_text(rendered: str, spec_id: str) -> str:
    marker = f"<h2>{spec_id}</h2>"
    for section in rendered.split("<section"):
        if marker in section:
            return section
    raise AssertionError(f"no layer section for {spec_id}")


def _turn_lines(section: str) -> list[str]:
    """Each `<p>` line holding ' turns', in order, `P` for `PLACEHOLDER` and
    `X` for 'turns, extraction turns included,'."""
    lines = re.findall(r"<p>([^<]*)</p>", section)
    return [
        line.replace(PLACEHOLDER, "P").replace("turns, extraction turns included,", "X")
        for line in lines
        if " turns" in line
    ]


def test_each_phase_reads_its_own_peak_beside_its_own_bound(tmp_path, monkeypatch):
    from saffron import spec_review
    from saffron.report.stack import render_stack, stack_view

    monkeypatch.setattr(spec_review, "SPEC_REVIEW_MAX_TURNS", 77)
    monkeypatch.setattr(spec_review, "SPEC_WRITER_MAX_TURNS", 133)

    ledger, specs, _batch_a, batch_b = _build_batches(tmp_path)
    view = stack_view(ledger, batch_b, specs)
    assert view is not None
    rendered = render_stack(view)

    assert _turn_lines(_layer_section_text(rendered, "TE-7")) == [
        "SPEC_REVIEW 150 X 77 each",
        "SPEC_WRITING P X 133 each",
        "IMPLEMENT 44 of 90 turns",
        "GATE ⇄ REPAIR P of 90 turns",
        "REVIEW P of 90 turns",
        "REBUT P of 90 turns",
    ]
    assert _turn_lines(_layer_section_text(rendered, "TE-9")) == [
        "SPEC_REVIEW 31 X 77 each",
        "SPEC_WRITING 0 X 133 each",
        "IMPLEMENT 50 of 140 turns",
        "GATE ⇄ REPAIR 27 of 140 turns",
        "REVIEW 38 of 140 turns",
        "REBUT 45 of 140 turns",
    ]


def test_a_phase_with_no_closed_attempt_reads_absent_never_zero(tmp_path, monkeypatch):
    from saffron import spec_review
    from saffron.report.stack import render_stack, stack_view

    monkeypatch.setattr(spec_review, "SPEC_REVIEW_MAX_TURNS", 77)
    monkeypatch.setattr(spec_review, "SPEC_WRITER_MAX_TURNS", 133)

    ledger, specs, _batch_a, batch_b = _build_batches(tmp_path)
    view = stack_view(ledger, batch_b, specs)
    assert view is not None
    rendered = render_stack(view)

    assert _turn_lines(_layer_section_text(rendered, "TE-6")) == [
        "SPEC_REVIEW P X 77 each",
        "SPEC_WRITING P X 133 each",
        "IMPLEMENT 61 of 70 turns",
        "GATE ⇄ REPAIR P of 70 turns",
        "REVIEW P of 70 turns",
        "REBUT P of 70 turns",
    ]
    assert _turn_lines(_layer_section_text(rendered, "TE-4")) == [
        "SPEC_REVIEW P X 77 each",
        "SPEC_WRITING 9 X 133 each",
        "IMPLEMENT P of P turns",
        "GATE ⇄ REPAIR 10 of P turns",
        "REVIEW P of P turns",
        "REBUT P of P turns",
    ]

    te9_lines = _turn_lines(_layer_section_text(rendered, "TE-9"))
    assert "SPEC_WRITING 0 X 133 each" in te9_lines

    te7_lines = _turn_lines(_layer_section_text(rendered, "TE-7"))
    assert not any("200" in line for line in te7_lines)
