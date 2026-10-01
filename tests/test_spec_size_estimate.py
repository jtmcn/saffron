"""A spec declares its own size estimate, and `check` refuses one priced near
the `size` ceiling of its type (backlog item b-db95e1)."""

from __future__ import annotations

import argparse
import re
from typing import get_args

import pytest

from saffron.intake import Spec, SpecError, SpecType, parse_spec
from tests.test_spec_loop_driver import _cell, _spec, _StubLedger, driver

CLEAR = "check: ceilings clear this shape's history"


def _frontmatter(extra: str) -> str:
    return f"---\nid: SA-0001\ntitle: x\ntype: feature\n{extra}---\n"


def test_a_spec_declares_its_estimate_as_a_positive_integer_or_not_at_all():
    assert "estimated_lines" in Spec.model_fields
    assert parse_spec(_frontmatter("estimated_lines: 480\n")).estimated_lines == 480
    assert parse_spec(_frontmatter("")).estimated_lines is None
    assert parse_spec(_frontmatter("estimated_lines:\n")).estimated_lines is None
    for bad in ("0", "-3", "1.5", "many", "true"):
        with pytest.raises(SpecError):
            parse_spec(_frontmatter(f"estimated_lines: {bad}\n"))


def test_a_spec_marks_its_estimate_as_measured_or_leaves_it_a_hand_one():
    assert parse_spec(_frontmatter("")).estimate_measured is False
    assert parse_spec(_frontmatter("estimate_measured: true\n")).estimate_measured
    for bad in ("1", "yes please"):
        with pytest.raises(SpecError):
            parse_spec(_frontmatter(f"estimate_measured: {bad}\n"))


def _run(monkeypatch, capsys, target, rows, *, ratio=1, elevate_on=()):
    """`check` over `target`, the overrun pinned. The ratio defaults to 1 so
    the boundary tests read the ceiling arithmetic alone."""
    with monkeypatch.context() as m:  # undone, so the file-read run sees the real one
        m.setattr(driver, "_known_specs", lambda: {target.id: target})
        m.setattr(driver, "_ledger_and_repo", lambda: (_StubLedger(), 1, "url"))
        m.setattr(driver, "_past_cells", lambda *a, **k: rows)
        m.setattr(driver, "_overrun", lambda *a, **k: (ratio, "a pinned ratio"))
        m.setattr(driver, "_elevate_on", lambda: list(elevate_on))
        rc = driver.cmd_check(argparse.Namespace(spec_id=target.id))
    return rc, capsys.readouterr().out.splitlines()


def _words(line: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_.=]+", line))


def _has_numbers(line: str, lines: int, price: int, ceiling: int) -> bool:
    words = {w.split("=")[-1] for w in _words(line)}
    return {str(lines), str(price), str(ceiling)} <= words


def _boundary(ceiling: int, rate) -> int:
    """The fewest lines whose price reaches 80% of `ceiling`, rounded up."""
    return int(-(-4 * ceiling // (5 * rate)))


def _drive(monkeypatch, capsys, spec_type: str, *, row: bool) -> None:
    """The boundary in lines blocks and one line under it passes, each read
    from the size module as it stands when `check` runs."""
    from saffron.gates.core import size

    ceiling = size._CEILINGS.get(spec_type, size._DEFAULT_CEILING)
    rate = size._TOKENS_PER_LINE
    boundary = _boundary(ceiling, rate)
    rows = [_cell("SA-2000", spec_type, 2, 3)] if row else []
    for estimate, blocks in ((boundary, True), (boundary - 1, False)):
        target = _spec("SA-0009", spec_type=spec_type)
        target.max_turns = 100
        target.budget_usd = 100.0
        target.estimated_lines = estimate
        target.risk = "elevated"  # where `size` blocks, so the estimate does
        rc, out = _run(monkeypatch, capsys, target, rows)
        price = int(estimate * rate)  # a float rate would print `2400.0`
        blockers = [x for x in out if x.startswith("blocker: ")]
        if blocks:
            assert rc == 1, (spec_type, estimate, out)
            assert len(blockers) == 1, out
            assert _has_numbers(blockers[0], estimate, price, ceiling), out
            assert f"({price} tokens at {rate} a line)" in blockers[0], out
            assert "parent and children" in blockers[0]
            assert CLEAR not in out
        else:
            assert rc == 0, (spec_type, estimate, out)
            assert blockers == []
            sized = [x for x in out if x.startswith("size: ")]
            assert len(sized) == 1, out
            assert _has_numbers(sized[0], estimate, price, ceiling), out
            assert f"({price} tokens at {rate} a line)" in sized[0], out
            assert (CLEAR in out) is row, out


def test_check_blocks_an_estimate_at_80_percent_of_its_types_size_ceiling(
    monkeypatch, capsys, tmp_path
):
    from saffron.gates.core import size

    assert "estimated_lines" in Spec.model_fields
    for spec_type in get_args(SpecType):
        _drive(monkeypatch, capsys, spec_type, row=False)
        _drive(monkeypatch, capsys, spec_type, row=True)

    with monkeypatch.context() as m:
        m.setitem(size._CEILINGS, "feature", 3500)
        m.setattr(size, "_DEFAULT_CEILING", 5000)
        m.setattr(size, "_TOKENS_PER_LINE", 5)
        for spec_type in ("feature", "docs"):
            _drive(monkeypatch, capsys, spec_type, row=False)

    with monkeypatch.context() as m:
        # 12000 tokens over 35 is 342.86 lines, so 343 blocks and 342 passes.
        m.setitem(size._CEILINGS, "feature", 3000)
        m.setattr(size, "_TOKENS_PER_LINE", 7)
        _drive(monkeypatch, capsys, "feature", row=False)
        # 80% of 3001 is 2400.8 tokens, so 601 lines block and 600 pass.
        m.setitem(size._CEILINGS, "feature", 3001)
        m.setattr(size, "_TOKENS_PER_LINE", 4)
        _drive(monkeypatch, capsys, "feature", row=False)

    ceiling = size._CEILINGS["feature"]
    boundary = _boundary(ceiling, size._TOKENS_PER_LINE)
    specs_dir = tmp_path / ".saffron" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "SA-0009-x.md").write_text(
        _frontmatter(f"estimated_lines: {boundary}\nrisk: elevated\n").replace(
            "SA-0001", "SA-0009"
        )
    )
    monkeypatch.setattr(driver, "SPECS_DIR", specs_dir)
    monkeypatch.setattr(driver, "_ledger_and_repo", lambda: (_StubLedger(), 1, "url"))
    monkeypatch.setattr(driver, "_past_cells", lambda *a, **k: [])
    monkeypatch.setattr(driver, "_overrun", lambda *a, **k: (1, "a pinned ratio"))
    assert driver.cmd_check(argparse.Namespace(spec_id="SA-0009")) == 1
    assert any(x.startswith("blocker: ") for x in capsys.readouterr().out.splitlines())


def test_check_names_a_missing_estimate_and_blocks_nothing_for_it(monkeypatch, capsys):
    for rows in ([], [_cell("SA-2000", "bug", 2, 3)]):
        target = _spec("SA-0009")
        target.max_turns = 100
        target.budget_usd = 100.0
        rc, out = _run(monkeypatch, capsys, target, rows)
        assert rc == 0, out
        assert "size: no estimated_lines declared" in out
        assert not any(x.startswith("blocker: ") for x in out)
        assert (CLEAR in out) is bool(rows), out


def test_check_prints_a_size_blocker_beside_a_ceilings_blocker(monkeypatch, capsys):
    from saffron.gates.core import size

    assert "estimated_lines" in Spec.model_fields
    ceiling = size._CEILINGS.get("bug", size._DEFAULT_CEILING)
    boundary = _boundary(ceiling, size._TOKENS_PER_LINE)
    rows = [_cell("SA-2000", "bug", 2, 3)]  # peak 41
    for estimate, sized in ((boundary, True), (boundary - 1, False)):
        target = _spec("SA-0009")
        target.max_turns = 10
        target.budget_usd = 100.0
        target.estimated_lines = estimate
        target.risk = "elevated"
        rc, out = _run(monkeypatch, capsys, target, rows)
        assert rc == 1, out
        assert any(x.startswith("blocker: max_turns=10") for x in out), out
        size_blockers = [x for x in out if x.startswith("blocker: estimated_lines=")]
        assert len(size_blockers) == (1 if sized else 0), out


def _priced(monkeypatch, capsys, *, lines, ratio, risk="standard", touches=()):
    """`check` over one spec with no past cell, the overrun ratio pinned."""
    target = _spec("SA-0009", spec_type="feature")
    target.max_turns = 100
    target.budget_usd = 100.0
    target.estimated_lines = lines
    target.risk = risk
    target.touches = list(touches)
    return _run(
        monkeypatch, capsys, target, [], ratio=ratio, elevate_on=["saffron/ledger.py"]
    )


def test_check_prices_the_estimate_at_the_overrun_ratio_and_names_it(
    monkeypatch, capsys
):
    # 500 raw lines is 2000 tokens, 67% of 3000. At 1.4 it is 700 lines,
    # 2800 tokens, 93%: over the line only once the ratio is applied.
    rc, out = _priced(monkeypatch, capsys, lines=500, ratio=1.4, risk="elevated")
    blockers = [x for x in out if x.startswith("blocker: ")]
    assert rc == 1, out
    assert len(blockers) == 1, out
    assert "1.4" in blockers[0] and "700" in blockers[0] and "2800" in blockers[0]
    assert "a pinned ratio" in blockers[0], out

    rc, out = _priced(monkeypatch, capsys, lines=500, ratio=1.0, risk="elevated")
    assert rc == 0, out
    assert not any(x.startswith("blocker: ") for x in out), out


def test_check_prices_a_measured_estimate_at_one_and_says_so(monkeypatch, capsys):
    # b-b0a187: SA-0151's 478 lines came from a prototype `size_gate` measured,
    # and `check` blocked it at 478 x 1.4.
    target = _spec("SA-0009", spec_type="feature")
    target.max_turns = 100
    target.budget_usd = 100.0
    target.estimated_lines = 500
    target.estimate_measured = True
    target.risk = "elevated"
    rc, out = _run(monkeypatch, capsys, target, [], ratio=1.4)
    assert rc == 0, out
    [size] = [x for x in out if x.startswith("size: ")]
    assert "× 1.0 (measured" in size, size
    assert "a pinned ratio" not in size, size


def test_check_blocks_a_priced_estimate_only_where_size_blocks(monkeypatch, capsys):
    # Standard risk and no elevating touch: `size` is advisory in the cell,
    # so `check` prints a concern and exits 0.
    rc, out = _priced(monkeypatch, capsys, lines=700, ratio=1.4)
    assert rc == 0, out
    assert not any(x.startswith("blocker: ") for x in out), out
    concerns = [x for x in out if x.startswith("concern: estimated_lines=")]
    assert len(concerns) == 1, out
    assert "standard" in concerns[0], out

    # A touch `elevate_on` matches elevates it, and there it blocks.
    rc, out = _priced(
        monkeypatch, capsys, lines=700, ratio=1.4, touches=["saffron/ledger.py"]
    )
    assert rc == 1, out
    assert any(x.startswith("blocker: estimated_lines=") for x in out), out


class _LandedLedger:
    """`tasks_by_spec` and `queue_lines` rows for `_overrun`."""

    def __init__(self, landed):
        self._landed = landed  # (spec_id, state, added, removed), oldest first

    def tasks_by_spec(self, repo_id):
        grouped = {}
        for task_id, (spec_id, state, _a, _r) in enumerate(self._landed, 1):
            grouped.setdefault((spec_id, "sha"), []).append(
                {"task_id": task_id, "spec_id": spec_id, "state": state}
            )
        return grouped

    def queue_lines(self):
        return [
            {"task_id": task_id, "spec_id": s, "state": st, "added": a, "removed": r}
            for task_id, (s, st, a, r) in enumerate(self._landed, 1)
        ]


def _declaring(estimates):
    specs = {}
    for spec_id, lines in estimates.items():
        spec = _spec(spec_id)
        spec.estimated_lines = lines
        specs[spec_id] = spec
    return specs


def test_the_overrun_is_the_median_landed_ratio_once_three_specs_declare_one():
    specs = _declaring(
        {
            "SA-0147": 100,  # declared its estimate already times 1.4
            "SA-0150": 100,  # queued below SA-0184, and raw since #557
            "SA-0201": 100,
            "SA-0202": 100,
            "SA-0204": None,
        }
    )
    landed = [
        ("SA-0150", "MERGED", 110, 10),  # 1.2
        ("SA-0201", "READY_FOR_REVIEW", 200, 0),  # 2.0
        ("SA-0202", "APPROVED", 150, 0),  # 1.5
        ("SA-0202", "PLAN_REJECTED", 0, 0),  # the newest row, but never landed
        ("SA-0204", "MERGED", 900, 0),  # declares no estimate
        ("SA-0147", "MERGED", 900, 0),  # 9.0, and not counted
    ]
    ratio, basis = driver._overrun(_LandedLedger(landed), 1, specs)
    assert ratio == 1.5
    assert "3" in basis and "median" in basis

    # Two landed specs is too few to measure, so run 19's 1.4 stands.
    ratio, basis = driver._overrun(_LandedLedger(landed[:2]), 1, specs)
    assert ratio == 1.4
    assert "run 19" in basis


def test_the_overrun_counts_no_measured_estimate():
    # A measured estimate is priced at 1.0, so it says nothing about a hand one's overrun.
    specs = _declaring({"SA-0201": 100, "SA-0202": 100, "SA-0203": 100, "SA-0204": 100})
    specs["SA-0204"].estimate_measured = True
    landed = [
        ("SA-0201", "MERGED", 200, 0),
        ("SA-0202", "MERGED", 150, 0),
        ("SA-0204", "MERGED", 100, 0),
    ]
    ratio, basis = driver._overrun(_LandedLedger(landed), 1, specs)
    assert ratio == 1.4
    assert "run 19" in basis


class _TwoShaLedger(_LandedLedger):
    """One spec landed twice, at two spec shas. `tasks_by_spec` lists the
    newer sha's group first, as a dict keyed by first sight need not."""

    def tasks_by_spec(self, repo_id):
        return {
            ("SA-0201", "new"): [
                {"task_id": 2, "spec_id": "SA-0201", "state": "MERGED"}
            ],
            ("SA-0201", "old"): [
                {"task_id": 1, "spec_id": "SA-0201", "state": "MERGED"}
            ],
        }


def test_the_overrun_reads_each_specs_newest_landed_task_across_its_shas():
    specs = _declaring({"SA-0201": 100})
    landed = [("SA-0201", "MERGED", 900, 0), ("SA-0201", "MERGED", 150, 0)]
    with pytest.MonkeyPatch.context() as m:
        m.setattr(driver, "_OVERRUN_MIN_SPECS", 1)
        ratio, _basis = driver._overrun(_TwoShaLedger(landed), 1, specs)
    assert ratio == 1.5  # task 2's 150 lines, not task 1's 900
