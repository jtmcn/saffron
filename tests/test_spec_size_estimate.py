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


def _run(monkeypatch, capsys, target, rows):
    with monkeypatch.context() as m:  # undone, so the file-read run sees the real one
        m.setattr(driver, "_known_specs", lambda: {target.id: target})
        m.setattr(driver, "_ledger_and_repo", lambda: (_StubLedger(), 1, "url"))
        m.setattr(driver, "_past_cells", lambda *a, **k: rows)
        rc = driver.cmd_check(argparse.Namespace(spec_id=target.id))
    return rc, capsys.readouterr().out.splitlines()


def _words(line: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_.=]+", line))


def _has_numbers(line: str, lines: int, price: int, ceiling: int) -> bool:
    words = {w.split("=")[-1] for w in _words(line)}
    return {str(lines), str(price), str(ceiling)} <= words


def _drive(monkeypatch, capsys, spec_type: str, *, row: bool) -> None:
    """The boundary in lines blocks and one line under it passes, each read
    from the size module as it stands when `check` runs."""
    from saffron.gates.core import size

    ceiling = size._CEILINGS.get(spec_type, size._DEFAULT_CEILING)
    rate = size._TOKENS_PER_LINE
    boundary = int(-(-4 * ceiling // (5 * rate)))
    rows = [_cell("SA-2000", spec_type, 2, 3)] if row else []
    for estimate, blocks in ((boundary, True), (boundary - 1, False)):
        target = _spec("SA-0009", spec_type=spec_type)
        target.max_turns = 100
        target.budget_usd = 100.0
        target.estimated_lines = estimate
        rc, out = _run(monkeypatch, capsys, target, rows)
        price = int(estimate * rate)  # a float rate would print `2400.0`
        blockers = [x for x in out if x.startswith("blocker: ")]
        if blocks:
            assert rc == 1, (spec_type, estimate, out)
            assert len(blockers) == 1, out
            assert _has_numbers(blockers[0], estimate, price, ceiling), out
            assert "parent and children" in blockers[0]
            assert CLEAR not in out
        else:
            assert rc == 0, (spec_type, estimate, out)
            assert blockers == []
            sized = [x for x in out if x.startswith("size: ")]
            assert len(sized) == 1, out
            assert _has_numbers(sized[0], estimate, price, ceiling), out
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
    boundary = -(-4 * ceiling // (5 * size._TOKENS_PER_LINE))
    specs_dir = tmp_path / ".saffron" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "SA-0009-x.md").write_text(
        _frontmatter(f"estimated_lines: {boundary}\n").replace("SA-0001", "SA-0009")
    )
    monkeypatch.setattr(driver, "SPECS_DIR", specs_dir)
    monkeypatch.setattr(driver, "_ledger_and_repo", lambda: (_StubLedger(), 1, "url"))
    monkeypatch.setattr(driver, "_past_cells", lambda *a, **k: [])
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
    boundary = -(-4 * ceiling // (5 * size._TOKENS_PER_LINE))
    rows = [_cell("SA-2000", "bug", 2, 3)]  # peak 41
    for estimate, sized in ((boundary, True), (boundary - 1, False)):
        target = _spec("SA-0009")
        target.max_turns = 10
        target.budget_usd = 100.0
        target.estimated_lines = estimate
        rc, out = _run(monkeypatch, capsys, target, rows)
        assert rc == 1, out
        assert any(x.startswith("blocker: max_turns=10") for x in out), out
        size_blockers = [x for x in out if x.startswith("blocker: estimated_lines=")]
        assert len(size_blockers) == (1 if sized else 0), out
