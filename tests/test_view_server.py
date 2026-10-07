"""Tests for `saffron.view.server`.

Every test imports `saffron.view.server` inside its own body, never at
module scope. A reverted run's missing module then reads as a `skip` for
this file, rather than a collection error (`DESIGN.md` Appendix H).
"""

from __future__ import annotations

import contextlib
import html
import json
import socket
import socketserver
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

import pyoxigraph as ox
import pytest

from saffron.agents.findings import Finding, Severity
from saffron.gates.contract import Failure, GateResult, GateStatus
from saffron.ledger import Ledger
from saffron.projection import DATA_NS

_SPARE = "spare-failure"


@dataclass(frozen=True)
class _Spares:
    batches: list[int]
    task: int


def _ledger(tmp_path: Path) -> tuple[Ledger, int, _Spares]:
    """A ledger whose tables number from different offsets.

    An id read from the wrong table, or by position, then reads wrong."""
    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("r", "origin", str(tmp_path / "mirror"), None)
    batches = [ledger.create_batch(1.0) for _ in range(3)]
    runs = [ledger.create_run(repo_id, f"spare{i}") for i in range(4)]
    for gate in ("lint", "types"):
        ledger.record_gate_result(
            _gate(
                gate,
                "fail",
                failures=[Failure(file="s.py", line=1, code="E", message=_SPARE)],
            ),
            run_id=runs[0],
        )
    task = ledger.create_task(runs[1], "SA-SPARE", "ss", "bs")
    for phase in ("IMPLEMENTING", "REPAIRING", "REPAIRING", "REPAIRING"):
        ledger.open_attempt(task, phase)
    ledger.record_findings(task, [_finding("concern", _SPARE)] * 2)
    return ledger, repo_id, _Spares(batches, task)


def _close(ledger: Ledger, spares: _Spares) -> None:
    """Drops the spare rows only now, since a table without `AUTOINCREMENT`
    hands a deleted id out again."""
    db = ledger._db
    for table in ("findings", "attempts", "tasks"):
        db.execute(f"DELETE FROM {table} WHERE task_id = ?", (spares.task,))
    db.executemany(
        "DELETE FROM batches WHERE batch_id = ?", [(b,) for b in spares.batches]
    )
    db.commit()
    ledger.close()


def _set_task(ledger: Ledger, task_id: int, **columns: object) -> None:
    names = ", ".join(f"{name} = ?" for name in columns)
    ledger._db.execute(
        f"UPDATE tasks SET {names} WHERE task_id = ?",
        (*columns.values(), task_id),
    )
    ledger._db.commit()


def _set_attempt(ledger: Ledger, attempt_id: int, **columns: object) -> None:
    """Sets an attempt's times, turns and cost directly. `close_attempt`
    always stamps `ended_at` from the clock, so a fixture wanting a chosen
    value, or an attempt never closed at all, writes the row itself."""
    names = ", ".join(f"{name} = ?" for name in columns)
    ledger._db.execute(
        f"UPDATE attempts SET {names} WHERE attempt_id = ?",
        (*columns.values(), attempt_id),
    )
    ledger._db.commit()


def _set_batch(ledger: Ledger, batch_id: int, **columns: object) -> None:
    names = ", ".join(f"{name} = ?" for name in columns)
    ledger._db.execute(
        f"UPDATE batches SET {names} WHERE batch_id = ?",
        (*columns.values(), batch_id),
    )
    ledger._db.commit()


def _dt(ledger_time: str) -> str:
    """`V3`'s own spelling of a ledger timestamp: `%Y-%m-%d %H:%M:%S`
    becomes `...THH:MM:SSZ`, measured on the host at `cc3f4622`."""
    return ledger_time.replace(" ", "T") + "Z"


def _gate(
    gate: str, status: GateStatus, *, failures: list[Failure] | None = None
) -> GateResult:
    return GateResult(gate=gate, status=status, tool="t", failures=failures or [])


def _finding(severity: Severity, claim: str) -> Finding:
    return Finding(lens="style", severity=severity, file="f.py", line=1, claim=claim)


class _PageParser(HTMLParser):
    """Every `<tr>`'s `<td>` texts, grouped by its enclosing `<table id>`,
    apart from each table's own `<th>` header row, kept in `header_rows`
    by the same id. `row_kinds` holds `True` for a header row and
    `False` for a data row, by table id, in the document's row order.
    `table_ids` lists every table id in the order its `<table>` tag
    appears. `headings3` maps a table id to the `<h3>` text right before
    it, when there is one. `summary` maps each `<dl id="summary">` term's
    `<dt>` text to its `<dd>` text and the `href` of its `<a>`, if any.
    Also every `<a href>`, the first `<h1>`'s text, the `<title>`'s text,
    and `text`: the page's own data, untagged, without the stylesheet."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: dict[str, list[list[str]]] = {}
        self.header_rows: dict[str, list[str]] = {}
        self.row_kinds: dict[str, list[bool]] = {}
        self.table_ids: list[str] = []
        self.headings3: dict[str, str] = {}
        self.summary: dict[str, tuple[str, str | None]] = {}
        self.hrefs: list[str] = []
        self.heading = ""
        self.title = ""
        self.text = ""

        self._table_stack: list[str] = []
        self._row: list[str] | None = None
        self._row_is_header = False
        self._cell: list[str] | None = None
        self._in_h1 = False
        self._in_title = False
        self._in_h3 = False
        self._h3_buffer = ""
        self._pending_h3: str | None = None
        self._in_dl_summary = False
        self._in_dt = False
        self._in_dd = False
        self._dt_buffer = ""
        self._dd_buffer = ""
        self._dd_href: str | None = None
        self._current_term: str | None = None
        self._in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "table":
            table_id = attr_map.get("id")
            assert table_id is not None, "every table now carries an id"
            self._table_stack.append(table_id)
            self.table_ids.append(table_id)
            self.tables.setdefault(table_id, [])
            if self._pending_h3 is not None:
                self.headings3[table_id] = self._pending_h3
                self._pending_h3 = None
        elif tag == "tr":
            self._row = []
            self._row_is_header = False
        elif tag == "th":
            self._row_is_header = True
            self._cell = []
        elif tag == "td":
            self._cell = []
        elif tag == "a":
            href = attr_map.get("href")
            if href is not None:
                self.hrefs.append(href)
                if self._in_dd:
                    self._dd_href = href
        elif tag == "h1":
            self._in_h1 = True
        elif tag == "title":
            self._in_title = True
        elif tag == "style":
            self._in_style = True
        elif tag == "h3":
            self._in_h3 = True
            self._h3_buffer = ""
        elif tag == "dl":
            self._in_dl_summary = attr_map.get("id") == "summary"
        elif tag == "dt" and self._in_dl_summary:
            self._in_dt = True
            self._dt_buffer = ""
        elif tag == "dd" and self._in_dl_summary:
            self._in_dd = True
            self._dd_buffer = ""
            self._dd_href = None

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._table_stack:
            self._table_stack.pop()
        elif tag == "tr" and self._row is not None:
            table_id = self._table_stack[-1] if self._table_stack else None
            if table_id is not None:
                self.row_kinds.setdefault(table_id, []).append(self._row_is_header)
                if self._row_is_header:
                    self.header_rows[table_id] = self._row
                else:
                    self.tables[table_id].append(self._row)
            self._row = None
        elif tag in ("td", "th") and self._cell is not None:
            if self._row is not None:
                self._row.append("".join(self._cell))
            self._cell = None
        elif tag == "h1":
            self._in_h1 = False
        elif tag == "title":
            self._in_title = False
        elif tag == "style":
            self._in_style = False
        elif tag == "h3":
            self._in_h3 = False
            self._pending_h3 = self._h3_buffer
        elif tag == "dl":
            self._in_dl_summary = False
        elif tag == "dt" and self._in_dt:
            self._in_dt = False
            self._current_term = self._dt_buffer.strip()
        elif tag == "dd" and self._in_dd:
            self._in_dd = False
            if self._current_term is not None:
                self.summary[self._current_term] = (self._dd_buffer, self._dd_href)
            self._current_term = None

    def handle_data(self, data: str) -> None:
        if self._in_style:
            return
        self.text += data
        if self._cell is not None:
            self._cell.append(data)
        if self._in_h1:
            self.heading += data
        if self._in_title:
            self.title += data
        if self._in_h3:
            self._h3_buffer += data
        if self._in_dt:
            self._dt_buffer += data
        if self._in_dd:
            self._dd_buffer += data


def _parse(body: str) -> _PageParser:
    parser = _PageParser()
    parser.feed(body)
    return parser


@contextmanager
def _running(ledger_path: Path) -> Iterator[str]:
    from saffron.view.server import make_server

    server = make_server(ledger_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        address = server.server_address
        yield f"http://{address[0]}:{address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _get(base: str, path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(base + path) as resp:
            status, body = resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        status, body = exc.code, exc.read().decode()
    assert _SPARE not in body, path
    return status, body


def _sparql(base: str, query: str) -> tuple[int, str, str]:
    """`GET /sparql?query=<query>`, percent-encoded here so the caller's own
    text, backslashes included, reaches the server untouched."""
    url = f"{base}/sparql?query={urllib.parse.quote(query, safe='')}"
    try:
        with urllib.request.urlopen(url) as resp:
            return (
                resp.status,
                resp.read().decode(),
                resp.headers.get("Content-Type", ""),
            )
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(), exc.headers.get("Content-Type", "")


def _post(base: str, path: str) -> tuple[int, str | None]:
    request = urllib.request.Request(base + path, data=b"x", method="POST")
    try:
        with urllib.request.urlopen(request) as resp:
            return resp.status, resp.headers.get("Allow")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Allow")


@contextmanager
def _closing_listener() -> Iterator[tuple[int, list[bool]]]:
    """A loopback listener that records and closes each connection, so a
    `SERVICE` fetch that reaches it fails fast rather than hanging the
    suite."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    port = sock.getsockname()[1]
    connections: list[bool] = []

    def serve() -> None:
        while True:
            try:
                conn, _addr = sock.accept()
            except OSError:
                return
            connections.append(True)
            conn.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield port, connections
    finally:
        sock.close()
        thread.join(timeout=1)


def test_the_index_lists_each_batch_and_the_tasks_with_no_batch(
    tmp_path: Path,
) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)

    until_batch = ledger.create_batch(5.0)
    run_a = ledger.create_run(repo_id, "ba", batch_id=until_batch)
    run_b = ledger.create_run(repo_id, "bb", batch_id=until_batch)
    for i, run in enumerate([run_a, run_a, run_b, run_b]):
        task_id = ledger.create_task(run, f"SA-U{i:04d}", f"u{i}", f"ub{i}")
        _set_task(ledger, task_id, state="READY_FOR_REVIEW")
    ledger.close_batch(until_batch, "UNTIL")

    open_batch = ledger.create_batch(3.0)
    run_c = ledger.create_run(repo_id, "bc", batch_id=open_batch)
    open_task = ledger.create_task(run_c, "SA-OPEN", "o1", "ob1")
    _set_task(ledger, open_task, state="DRAFT")

    no_batch_run = ledger.create_run(repo_id, "nb")
    unbatched = []
    for i in range(2):
        task_id = ledger.create_task(no_batch_run, f"SA-N{i:04d}", f"n{i}", f"nb{i}")
        _set_task(ledger, task_id, state="DRAFT")
        unbatched.append(task_id)
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, "/")
    assert status == 200
    page = _parse(body)

    batch_rows = {row[0]: row for row in page.tables.get("batches", [])}
    assert set(batch_rows) == {str(until_batch), str(open_batch)}

    until_row = batch_rows[str(until_batch)]
    assert until_row[2] != ""  # window end, present once closed
    assert until_row[3] == "UNTIL"
    assert float(until_row[4]) == 5.0
    assert until_row[6] == "4"

    open_row = batch_rows[str(open_batch)]
    assert open_row[2] == ""  # window end, absent while running
    assert open_row[3] == ""  # stop reason, absent while running
    assert open_row[5] == ""  # spend, absent while running
    assert float(open_row[4]) == 3.0
    assert open_row[6] == "1"

    no_batch_rows = {row[0]: row for row in page.tables.get("no-batch", [])}
    assert set(no_batch_rows) == {str(t) for t in unbatched}

    batch_links = {href for href in page.hrefs if href.startswith("/batch/")}
    assert batch_links == {f"/batch/{until_batch}", f"/batch/{open_batch}"}
    task_links = {href for href in page.hrefs if href.startswith("/task/")}
    assert task_links == {f"/task/{t}" for t in unbatched}


def test_the_index_lists_each_left_out_task_with_its_reason(tmp_path: Path) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    batch_id = ledger.create_batch(10.0)
    run_id = ledger.create_run(repo_id, "base", batch_id=batch_id)

    unknown_state = ledger.create_task(run_id, "SA-STATE", "s1", "bs1")
    _set_task(ledger, unknown_state, state="PAUSED")

    unknown_risk = ledger.create_task(run_id, "SA-RISK", "s2", "bs2")
    _set_task(ledger, unknown_risk, risk="reckless")

    kept = ledger.create_task(run_id, "SA-KEPT", "s3", "bs3")
    _set_task(ledger, kept, state="REVIEWING")
    ledger.open_attempt(kept, "REVIEWING")
    ledger.record_findings(kept, [_finding("concern", "a claim")])
    ledger.close_batch(batch_id, "DRAINED")
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, "/")
        kept_status, kept_body = _get(base, f"/task/{kept}")
    assert status == 200
    page = _parse(body)

    left_rows = {row[0]: row for row in page.tables.get("left-out", [])}
    assert len(left_rows) == 3

    state_row = next(r for r in left_rows.values() if r[1] == "SA-STATE")
    assert state_row[2] == "unknown_state"
    risk_row = next(r for r in left_rows.values() if r[1] == "SA-RISK")
    assert risk_row[2] == "unknown_risk"
    kept_row = next(r for r in left_rows.values() if r[1] == "SA-KEPT")
    assert kept_row[2] == "findings_without_diff"
    assert kept_row[0] == str(kept)

    left_links = {href for href in page.hrefs if href.startswith("/task/")}
    assert left_links == {f"/task/{kept}"}

    assert kept_status == 200
    kept_page = _parse(kept_body)
    rows = kept_page.tables.get("attempts", [])
    (kept_attempt_row,) = [row for row in rows if row[0] == "REVIEWING"]
    assert kept_attempt_row[1] == "1"
    assert kept_attempt_row[2] != ""  # started
    assert kept_attempt_row[3:] == ["", "", ""]  # ended, turns, cost


def test_a_batch_page_lists_only_that_batchs_tasks(tmp_path: Path) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)

    batch_one = ledger.create_batch(10.0)
    run_a = ledger.create_run(repo_id, "a", batch_id=batch_one)
    run_b = ledger.create_run(repo_id, "b", batch_id=batch_one)
    task_a = ledger.create_task(run_a, "SA-A", "sa", "ba")
    _set_task(ledger, task_a, state="DRAFT")
    task_b = ledger.create_task(run_b, "SA-B", "sb", "bb")
    _set_task(ledger, task_b, state="DRAFT")

    batch_two = ledger.create_batch(5.0)
    run_c = ledger.create_run(repo_id, "c", batch_id=batch_two)
    task_c = ledger.create_task(run_c, "SA-C", "sc", "bc")
    _set_task(ledger, task_c, state="DRAFT")

    run_d = ledger.create_run(repo_id, "d")
    task_d = ledger.create_task(run_d, "SA-D", "sd", "bd")
    _set_task(ledger, task_d, state="DRAFT")
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, f"/batch/{batch_one}")
    assert status == 200
    page = _parse(body)

    rows = page.tables.get("tasks", [])
    ids = {row[0] for row in rows}
    assert ids == {str(task_a), str(task_b)}

    task_links = {href for href in page.hrefs if href.startswith("/task/")}
    assert task_links == {f"/task/{task_a}", f"/task/{task_b}"}


def test_a_task_page_shows_each_attempts_gate_outcomes_with_error_apart_from_fail(
    tmp_path: Path,
) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base")

    task_id = ledger.create_task(run_id, "SA-MAIN", "sm", "bm")
    _set_task(ledger, task_id, state="REPAIRING")
    implementing = ledger.open_attempt(task_id, "IMPLEMENTING")
    ledger.record_gate_result(_gate("scope", "pass"), attempt_id=implementing)
    ledger.record_gate_result(_gate("lint", "fail"), attempt_id=implementing)
    ledger.record_gate_result(_gate("no-network", "error"), attempt_id=implementing)
    ledger.record_gate_result(_gate("custom-check", "skip"), attempt_id=implementing)

    repair_one = ledger.open_attempt(task_id, "REPAIRING")
    ledger.record_gate_result(_gate("lint", "error"), attempt_id=repair_one)
    ledger.record_gate_result(_gate("no-network", "fail"), attempt_id=repair_one)

    repair_two = ledger.open_attempt(task_id, "REPAIRING")
    ledger.record_gate_result(_gate("lint", "pass"), attempt_id=repair_two)

    other_task = ledger.create_task(run_id, "SA-OTHER", "so", "bo")
    _set_task(ledger, other_task, state="DRAFT")
    other_attempt = ledger.open_attempt(other_task, "IMPLEMENTING")
    ledger.record_gate_result(_gate("scope", "pass"), attempt_id=other_attempt)
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, f"/task/{task_id}")
    assert status == 200
    page = _parse(body)

    rows = page.tables.get("gate-results", [])
    first_four = sorted(row[:4] for row in rows)
    expected = sorted(
        [
            ["IMPLEMENTING", "1", "scope", "passed"],
            ["IMPLEMENTING", "1", "lint", "failed"],
            ["IMPLEMENTING", "1", "no-network", "cantTell"],
            ["IMPLEMENTING", "1", "custom-check", "inapplicable"],
            ["REPAIRING", "1", "lint", "cantTell"],
            ["REPAIRING", "1", "no-network", "failed"],
            ["REPAIRING", "2", "lint", "passed"],
        ]
    )
    assert first_four == expected
    assert "urn:" not in body
    assert "gate-" not in page.text


def _failures(tag: str, count: int) -> list[Failure]:
    """`count` failures, messaged by position but filed with files and lines
    running the opposite way, so an order keyed on anything but `failure_id`
    reads wrong.

    `tag` names the owning gate result in every message.

    A query that reaches into a sibling result's rows then reads wrong
    too, instead of matching it by coincidence."""
    return [
        Failure(
            file=f"f{count - 1 - i}.py",
            line=count - 1 - i,
            code="E",
            message=f"{tag}-msg{i}",
        )
        for i in range(count)
    ]


def test_a_task_page_shows_failure_lines_capped_with_a_count_of_the_rest(
    tmp_path: Path,
) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base")
    task_id = ledger.create_task(run_id, "SA-CAP", "sc", "bc")
    _set_task(ledger, task_id, state="REPAIRING")

    gating = ledger.open_attempt(task_id, "GATING")
    lint_result_id = ledger.record_gate_result(
        _gate("lint", "fail", failures=_failures("lint", 205)), attempt_id=gating
    )
    types_result_id = ledger.record_gate_result(
        _gate("types", "fail", failures=_failures("types", 200)), attempt_id=gating
    )
    repairing = ledger.open_attempt(task_id, "REPAIRING")
    tests_result_id = ledger.record_gate_result(
        _gate("tests", "fail", failures=_failures("tests", 3)), attempt_id=repairing
    )
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, f"/task/{task_id}")
    assert status == 200
    page = _parse(body)

    # `lint` and `types` share an attempt. `lint`'s own 205 rows outrun the
    # cap, so its table alone cannot catch a wrong attempt-wide query.
    lint_rows = page.tables[f"failures-{lint_result_id}"]
    assert [row[3] for row in lint_rows[:-1]] == [f"lint-msg{i}" for i in range(200)]
    assert lint_rows[-1] == ["5 more"]

    # `types`'s own 200 rows start only after `lint`'s 205. Borrowing the
    # attempt's earliest 200 instead reads as 200 `lint-msg*` rows here.
    types_rows = page.tables[f"failures-{types_result_id}"]
    assert [row[3] for row in types_rows] == [f"types-msg{i}" for i in range(200)]

    tests_rows = page.tables[f"failures-{tests_result_id}"]
    assert [row[3] for row in tests_rows] == [f"tests-msg{i}" for i in range(3)]

    more_cells = [
        cell
        for rows in page.tables.values()
        for row in rows
        for cell in row
        if cell.endswith(" more")
    ]
    assert more_cells == ["5 more"]


def test_markup_in_a_stored_value_renders_as_text(tmp_path: Path) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    tag = "<markup>"

    batch_id = ledger.create_batch(10.0)
    run_batched = ledger.create_run(repo_id, "batched", batch_id=batch_id)
    spec_b1 = "<markup>B1</markup>"
    task_b1 = ledger.create_task(run_batched, spec_b1, "sb1", "bb1")
    _set_task(ledger, task_b1, state="DRAFT")
    spec_b2 = "<markup>B2</markup>"
    task_b2 = ledger.create_task(run_batched, spec_b2, "sb2", "bb2")
    _set_task(ledger, task_b2, state="DRAFT")
    attempt = ledger.open_attempt(task_b1, "GATING")
    lint_result_id = ledger.record_gate_result(
        _gate(
            "lint",
            "fail",
            failures=[
                Failure(
                    file="<markup>f</markup>.py",
                    line=1,
                    code="<markup>C</markup>",
                    message="<markup>m</markup>",
                )
            ],
        ),
        attempt_id=attempt,
    )

    run_unbatched = ledger.create_run(repo_id, "unbatched")
    spec_u1 = "<markup>U1</markup>"
    task_u1 = ledger.create_task(run_unbatched, spec_u1, "su1", "bu1")
    _set_task(ledger, task_u1, state="DRAFT")
    spec_u2 = "<markup>U2</markup>"
    task_u2 = ledger.create_task(run_unbatched, spec_u2, "su2", "bu2")
    _set_task(ledger, task_u2, state="DRAFT")

    spec_x = "<markup>X</markup>"
    left_out_task = ledger.create_task(run_batched, spec_x, "sx", "bx")
    _set_task(ledger, left_out_task, state="PAUSED")
    _close(ledger, spares)

    pages = [
        (task_b1, spec_b1),
        (task_b2, spec_b2),
        (task_u1, spec_u1),
        (task_u2, spec_u2),
    ]
    with _running(tmp_path / "ledger.db") as base:
        for task_id, spec_id in pages:
            status, body = _get(base, f"/task/{task_id}")
            assert status == 200
            assert tag not in body
            page = _parse(body)
            assert page.heading.endswith(spec_id)
            assert page.title.endswith(spec_id)

        status, b1_body = _get(base, f"/task/{task_b1}")
        b1_page = _parse(b1_body)
        (failure_row,) = b1_page.tables[f"failures-{lint_result_id}"]
        assert failure_row == [
            "<markup>f</markup>.py",
            "1",
            "<markup>C</markup>",
            "<markup>m</markup>",
        ]

        index_status, index_body = _get(base, "/")
        assert index_status == 200
        assert tag not in index_body
        index_page = _parse(index_body)
        left_row = next(
            row for row in index_page.tables.get("left-out", []) if row[1] == spec_x
        )
        assert left_row[1] == spec_x
        no_batch_specs = {row[1] for row in index_page.tables.get("no-batch", [])}
        assert no_batch_specs == {spec_u1, spec_u2}

        batch_status, batch_body = _get(base, f"/batch/{batch_id}")
        assert batch_status == 200
        assert tag not in batch_body
        batch_specs = {row[1] for row in _parse(batch_body).tables.get("tasks", [])}
        assert batch_specs == {spec_b1, spec_b2}


def _status_line(host: str, port: int, raw_target: bytes, headers: bytes = b"") -> str:
    """One raw HTTP/1.0 request, with `raw_target` sent byte for byte.

    The vehicle for a path byte `urllib` cannot encode, or a forged `Host`."""
    with socket.create_connection((host, port)) as sock:
        sock.sendall(b"GET " + raw_target + b" HTTP/1.0\r\n" + headers + b"\r\n")
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
    return response.split(b"\r\n", 1)[0].decode("iso-8859-1")


def test_an_unknown_or_malformed_id_is_404(tmp_path: Path) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)

    main_batch = ledger.create_batch(5.0)
    main_run = ledger.create_run(repo_id, "m", batch_id=main_batch)

    # Consumes a task id, so the real task below never shares main_batch's id.
    throwaway = ledger.create_task(main_run, "SA-THROW", "st", "bt")
    _set_task(ledger, throwaway, state="DRAFT")

    main_task = ledger.create_task(main_run, "SA-REAL", "sr", "br")
    _set_task(ledger, main_task, state="READY_FOR_REVIEW")

    unknown_task = ledger.create_task(main_run, "SA-UNK", "su", "bu")
    _set_task(ledger, unknown_task, state="PAUSED")

    # A run id that names no task: created only after every task above, with
    # enough throwaway runs ahead of it that its own id outruns both.
    highest_task_id = max(main_task, unknown_task)
    for n in range(highest_task_id):
        ledger.create_run(repo_id, f"dummy{n}")
    runs_only_id = ledger.create_run(repo_id, "runs-only")
    assert runs_only_id > highest_task_id
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        for path in [
            "/task/99999",
            "/task/abc",
            "/task/-1",
            "/task/1.5",
            f"/task/+{main_task}",
            f"/task/{unknown_task}",
            f"/task/{runs_only_id}",
            "/batch/99999",
            "/batch/abc",
            "/batch/-1",
            f"/batch/+{main_batch}",
            f"/batch/{main_task}",
            "/nowhere",
            f"/task/{main_task}/x",
        ]:
            status, _ = _get(base, path)
            assert status == 404, path

        status, _ = _get(base, f"/task/{main_task}")
        assert status == 200
        status, _ = _get(base, f"/batch/{main_batch}")
        assert status == 200

        split = urllib.parse.urlsplit(base)
        assert split.hostname is not None
        assert split.port is not None
        line = _status_line(split.hostname, split.port, b"/task/\xb2")
        assert " 404 " in line


def test_sparql_answers_a_select(tmp_path: Path) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base")
    task_a = ledger.create_task(run_id, "SA-SEL1", "sa", "ba")
    _set_task(ledger, task_a, state="DRAFT")
    task_b = ledger.create_task(run_id, "SA-SEL2", "sb", "bb")
    _set_task(ledger, task_b, state="DRAFT")
    _close(ledger, spares)

    select = (
        "SELECT ?label WHERE { "
        "?task a <urn:software-factory:ns#Task> ; "
        "<http://www.w3.org/2000/01/rdf-schema#label> ?label . }"
    )
    ask_true = "ASK { ?s a <urn:software-factory:ns#Task> }"
    ask_false = f"ASK {{ <{DATA_NS}task-999999> a <urn:software-factory:ns#Task> }}"

    with _running(tmp_path / "ledger.db") as base:
        status, body, content_type = _sparql(base, select)
        assert status == 200
        assert content_type == "application/sparql-results+json"
        parsed = json.loads(body)
        labels = sorted(row["label"]["value"] for row in parsed["results"]["bindings"])
        assert labels == sorted(["SA-SEL1", "SA-SEL2"])

        status, body, content_type = _sparql(base, ask_true)
        assert status == 200
        assert content_type == "application/sparql-results+json"
        assert json.loads(body)["boolean"] is True

        status, body, _ = _sparql(base, ask_false)
        assert status == 200
        assert json.loads(body)["boolean"] is False


def test_sparql_refuses_an_update_and_a_construct(tmp_path: Path) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base")
    task_id = ledger.create_task(run_id, "SA-UPD", "su", "bu")
    _set_task(ledger, task_id, state="DRAFT")
    _close(ledger, spares)

    fresh = ox.Store()

    def parser_message(text: str) -> str:
        try:
            fresh.query(text)
        except SyntaxError as broke:
            return str(broke)
        raise AssertionError(f"expected a parse error for {text!r}")

    insert = "INSERT DATA { <urn:test:s> <urn:test:p> <urn:test:o> . }"
    delete = "DELETE WHERE { ?s ?p ?o }"
    unparseable = "SELECT ?x WHERE {"

    with _running(tmp_path / "ledger.db") as base:
        status, _ = _get(base, "/sparql")
        assert status == 400

        status, body, _ = _sparql(base, insert)
        assert status == 400
        assert body == parser_message(insert)

        status, body, _ = _sparql(base, delete)
        assert status == 400
        assert body == parser_message(delete)

        status, _, _ = _sparql(base, "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
        assert status == 400

        status, _, _ = _sparql(base, "DESCRIBE <urn:software-factory:ns#Task>")
        assert status == 400

        status, body, _ = _sparql(base, unparseable)
        assert status == 400
        assert body == parser_message(unparseable)

        status, body, _ = _sparql(
            base, "ASK { <urn:test:s> <urn:test:p> <urn:test:o> }"
        )
        assert status == 200
        assert json.loads(body)["boolean"] is False

        status, body, _ = _sparql(base, "ASK { ?s a <urn:software-factory:ns#Task> }")
        assert status == 200
        assert json.loads(body)["boolean"] is True


def test_sparql_refuses_a_service_clause_however_spelled(tmp_path: Path) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base")
    task_id = ledger.create_task(run_id, "SA-SVC", "ss", "bs")
    _set_task(ledger, task_id, state="DRAFT")
    _close(ledger, spares)

    with _closing_listener() as (port, connections):
        endpoint = f"<http://127.0.0.1:{port}/>"
        escaped_4 = (
            "SELECT ?x WHERE { " + "\\u0053ERVICE " + endpoint + " { ?x ?y ?z } }"
        )
        escaped_8 = (
            r"SELECT ?x WHERE { SERV\U00000049CE " + endpoint + " { ?x ?y ?z } }"
        )
        queries = [
            f"SELECT ?x WHERE {{ SERVICE {endpoint} {{ ?x ?y ?z }} }}",
            f"SELECT ?x WHERE {{ service {endpoint} {{ ?x ?y ?z }} }}",
            f"SELECT ?x WHERE {{ SeRvIcE {endpoint} {{ ?x ?y ?z }} }}",
            f"ASK {{ SERVICE {endpoint} {{ ?x ?y ?z }} }}",
            escaped_4,
            escaped_8,
            'ASK { FILTER("SERVICE" = "SERVICE") }',
        ]

        fresh = ox.Store()

        def parser_message(text: str) -> str:
            try:
                fresh.query(text)
            except SyntaxError as broke:
                return str(broke)
            raise AssertionError(f"expected a parse error for {text!r}")

        bodies: set[str] = set()
        with _running(tmp_path / "ledger.db") as base:
            for query in queries:
                status, body, _ = _sparql(base, query)
                assert status == 400, query
                bodies.add(body)

            assert len(bodies) == 1
            (one_body,) = bodies
            assert parser_message(escaped_4) != one_body
            assert parser_message(escaped_8) != one_body

            assert connections == []

            # An escape above U+10FFFF must answer 400, not crash the
            # handler.
            status, body, _ = _sparql(base, "\\UFFFFFFFF")
            assert status == 400

            status, body, _ = _sparql(
                base, "ASK { ?s a <urn:software-factory:ns#Task> }"
            )
            assert status == 200
            assert json.loads(body)["boolean"] is True


def test_a_post_is_405(tmp_path: Path) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base")
    task_id = ledger.create_task(run_id, "SA-POST", "sp", "bp")
    _set_task(ledger, task_id, state="DRAFT")
    batch_id = ledger.create_batch(5.0)
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        for path in [
            "/",
            "/sparql?query=ASK%20%7B%20%3Fs%20%3Fp%20%3Fo%20%7D",
            "/sparql",
            f"/task/{task_id}",
            f"/batch/{batch_id}",
            "/nowhere",
        ]:
            status, allow = _post(base, path)
            assert status == 405, path
            assert allow == "GET", path


def test_a_non_loopback_host_raises(tmp_path: Path) -> None:
    from saffron.view.server import make_server

    ledger, repo_id, spares = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base")
    task_id = ledger.create_task(run_id, "SA-HOST", "sh", "bh")
    _set_task(ledger, task_id, state="DRAFT")
    _close(ledger, spares)
    ledger_path = tmp_path / "ledger.db"

    for bad_host in [
        "0.0.0.0",
        "",
        "10.1.2.3",
        "192.168.0.7",
        "::1",
        "::",
        "example.com",
        "127.0.0.1.example",
    ]:
        with pytest.raises(ValueError):
            make_server(ledger_path, host=bad_host, port=0)

    for good_host in ["127.0.0.1", "localhost"]:
        server = make_server(ledger_path, host=good_host, port=0)
        server.server_close()

    with contextlib.suppress(OSError):
        server = make_server(ledger_path, host="127.0.0.2", port=0)
        server.server_close()


def test_serve_exits_2_and_prints_the_report_when_the_graph_fails_the_shapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from saffron import cli

    monkeypatch.setattr(
        socketserver.BaseServer,
        "serve_forever",
        lambda self: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    home = tmp_path
    ledger, repo_id, spares = _ledger(home)
    run_id = ledger.create_run(repo_id, "base")
    task_id = ledger.create_task(run_id, "SA-BAD", "sb", "bb")
    _set_task(ledger, task_id, state="DRAFT")
    attempt = ledger.open_attempt(task_id, "GATING")
    ledger.record_gate_result(_gate("lint", "pass"), attempt_id=attempt)
    [finding_id] = ledger.record_findings(task_id, [_finding("concern", "a claim")])
    ledger._db.execute(
        "UPDATE findings SET severity = 'critical' WHERE finding_id = ?",
        (finding_id,),
    )
    ledger._db.commit()
    _close(ledger, spares)

    assert cli.main(["--home", str(home), "serve"]) == 2
    out = capsys.readouterr().out
    assert "Conforms: False" in out


def test_serve_exits_2_when_there_is_no_ledger(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from saffron import cli

    existing_empty = tmp_path / "existing"
    existing_empty.mkdir()
    missing = tmp_path / "missing"

    for home in (existing_empty, missing):
        assert cli.main(["--home", str(home), "serve"]) == 2
        out = capsys.readouterr().out
        lines = out.splitlines()
        assert len(lines) == 1
        assert str(home / "ledger.db") in lines[0]

    assert list(existing_empty.iterdir()) == []
    assert not missing.exists()

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import saffron.cli, sys; print('saffron.view' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert result.stdout.strip() == "False"


def test_serve_binds_the_given_port_and_exits_0_when_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import saffron.view.server as view_server
    from saffron import cli

    home = tmp_path
    ledger, repo_id, spares = _ledger(home)
    _close(ledger, spares)

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    free_port = probe.getsockname()[1]
    probe.close()

    recorded_addresses: list[tuple[str, int] | str] = []
    close_calls = {"n": 0}
    real_close = socketserver.TCPServer.server_close

    def fake_serve_forever(self: socketserver.BaseServer) -> None:
        address = self.server_address
        assert isinstance(address, tuple)
        recorded_addresses.append(address)
        raise KeyboardInterrupt

    def fake_server_close(self: socketserver.TCPServer) -> None:
        close_calls["n"] += 1
        real_close(self)

    monkeypatch.setattr(socketserver.BaseServer, "serve_forever", fake_serve_forever)
    monkeypatch.setattr(socketserver.TCPServer, "server_close", fake_server_close)

    assert cli.main(["--home", str(home), "serve", "--port", str(free_port)]) == 0
    assert len(recorded_addresses) == 1
    address = recorded_addresses[0]
    assert isinstance(address, tuple)
    host, port = address
    assert port == free_port
    assert close_calls["n"] == 1

    recorded_ports: list[int] = []
    real_make_server = view_server.make_server

    def fake_make_server(
        ledger_path: Path, *, host: str = "127.0.0.1", port: int = 8765
    ) -> socketserver.TCPServer:
        recorded_ports.append(port)
        return real_make_server(ledger_path, host=host, port=0)

    monkeypatch.setattr(view_server, "make_server", fake_make_server)
    assert cli.main(["--home", str(home), "serve"]) == 0
    assert recorded_ports == [8765]
    assert close_calls["n"] == 2

    # Any other raise must still close the server before it propagates.
    def fake_serve_forever_raises(self: socketserver.BaseServer) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        socketserver.BaseServer, "serve_forever", fake_serve_forever_raises
    )
    with pytest.raises(RuntimeError):
        cli.main(["--home", str(home), "serve"])
    assert close_calls["n"] == 3


def test_a_task_page_shows_its_findings_and_links_its_pull_request(
    tmp_path: Path,
) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)

    batch_id = ledger.create_batch(10.0)
    run_batched = ledger.create_run(repo_id, "batched", batch_id=batch_id)
    run_unbatched = ledger.create_run(repo_id, "unbatched")

    def make_task(run_id: int, spec_id: str, pr_url: str, lens: str, claim: str) -> int:
        task_id = ledger.create_task(run_id, spec_id, f"s-{spec_id}", f"b-{spec_id}")
        _set_task(ledger, task_id, state="DRAFT", pr_url=pr_url)
        attempt = ledger.open_attempt(task_id, "GATING")
        ledger.record_gate_result(_gate("lint", "pass"), attempt_id=attempt)
        ledger.record_findings(
            task_id,
            [Finding(lens=lens, severity="concern", file="f.py", line=1, claim=claim)],
        )
        return task_id

    pr_amp = "https://example.com/pulls/1?x=1&y=2"
    pr_b2 = "https://example.com/pulls/2"
    pr_u1 = "https://example.com/pulls/3"
    pr_u2 = "https://example.com/pulls/4"

    task_b1 = make_task(run_batched, "SA-B1", pr_amp, "style", "claim-b1")
    task_b2 = make_task(run_batched, "SA-B2", pr_b2, "security", "claim-b2")
    task_u1 = make_task(run_unbatched, "SA-U1", pr_u1, "docs", "claim-u1")
    task_u2 = make_task(run_unbatched, "SA-U2", pr_u2, "perf", "claim-u2")

    markup_claim = "<b>markup claim</b>"
    markup_verdict = "<i>markup verdict</i>"
    [markup_finding_id] = ledger.record_findings(
        task_b1,
        [
            Finding(
                lens="style", severity="note", file="f.py", line=2, claim=markup_claim
            )
        ],
    )
    ledger._db.execute(
        "UPDATE findings SET verdict = ? WHERE finding_id = ?",
        (markup_verdict, markup_finding_id),
    )
    ledger._db.commit()
    _close(ledger, spares)

    tasks = {
        task_b1: (pr_amp, "style", "claim-b1"),
        task_b2: (pr_b2, "security", "claim-b2"),
        task_u1: (pr_u1, "docs", "claim-u1"),
        task_u2: (pr_u2, "perf", "claim-u2"),
    }

    with _running(tmp_path / "ledger.db") as base:
        bodies = {}
        pages = {}
        for task_id in tasks:
            status, body = _get(base, f"/task/{task_id}")
            assert status == 200
            bodies[task_id] = body
            pages[task_id] = _parse(body)

    for task_id, (pr_url, _lens, _claim) in tasks.items():
        assert pr_url in pages[task_id].hrefs
        # In the `href` attribute, not only somewhere in the body.
        assert f'href="{html.escape(pr_url)}"' in bodies[task_id]
        for other_id, (other_pr, other_lens, _other_claim) in tasks.items():
            if other_id == task_id:
                continue
            assert other_pr not in bodies[task_id]
            assert other_lens not in pages[task_id].text

    finding_rows = pages[task_b1].tables.get("findings", [])
    assert ["style", "concern", "claim-b1", ""] in finding_rows
    assert ["style", "note", markup_claim, markup_verdict] in finding_rows
    assert len(finding_rows) == 2

    for task_id, (_pr_url, lens, claim) in tasks.items():
        if task_id == task_b1:
            continue
        findings = pages[task_id].tables.get("findings", [])
        assert findings == [[lens, "concern", claim, ""]]


def _one_batched_task(tmp_path: Path) -> tuple[int, int]:
    ledger, repo_id, spares = _ledger(tmp_path)
    batch = ledger.create_batch(5.0)
    run = ledger.create_run(repo_id, "m", batch_id=batch)
    task = ledger.create_task(run, "SA-REAL", "sr", "br")
    _set_task(ledger, task, state="READY_FOR_REVIEW")
    _close(ledger, spares)
    return batch, task


def test_a_request_naming_another_host_is_refused(tmp_path: Path) -> None:
    # A DNS-rebinding page reaches loopback with its own name in Host.
    _, task = _one_batched_task(tmp_path)
    with _running(tmp_path / "ledger.db") as base:
        split = urllib.parse.urlsplit(base)
        assert split.hostname is not None
        assert split.port is not None
        host, port = split.hostname, split.port
        targets = [b"/", f"/task/{task}".encode(), b"/sparql?query=ASK%7B%7D"]
        for target in targets:
            for forged in [b"evil.example", b"localhost.evil.example", b"10.0.0.5"]:
                line = _status_line(host, port, target, b"Host: " + forged + b"\r\n")
                assert " 421 " in line, (target, forged)
            for own in [f"127.0.0.1:{port}", f"localhost:{port}", "localhost"]:
                line = _status_line(host, port, target, f"Host: {own}\r\n".encode())
                assert " 200 " in line, (target, own)


def test_an_overlong_digit_id_is_404_and_a_query_string_keeps_its_page(
    tmp_path: Path,
) -> None:
    batch, task = _one_batched_task(tmp_path)
    with _running(tmp_path / "ledger.db") as base:
        status, _ = _get(base, "/task/" + "9" * 5000)
        assert status == 404
        for path in ["/?x=1", f"/batch/{batch}?x=1", f"/task/{task}?x=1"]:
            status, _ = _get(base, path)
            assert status == 200, path


def test_a_task_page_heads_with_its_state_risk_batch_pull_request_and_cost(
    tmp_path: Path,
) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)

    # `_ledger` hands out batch ids from 4 and task ids from 2. Spare
    # batches here push the counter past every task id this fixture mints.
    for _ in range(6):
        ledger.create_batch(1.0)

    main_batch = ledger.create_batch(9.0)
    main_run = ledger.create_run(repo_id, "main", batch_id=main_batch)
    main_task = ledger.create_task(main_run, "SA-MAIN", "sm", "bm")
    main_pr = "https://example.com/pulls/9"
    _set_task(
        ledger, main_task, state="READY_FOR_REVIEW", risk="elevated", pr_url=main_pr
    )

    three_results = ledger.open_attempt(main_task, "GATING")
    for gate in ("lint", "types", "tests"):
        ledger.record_gate_result(_gate(gate, "pass"), attempt_id=three_results)
    _set_attempt(ledger, three_results, cost_usd_est=1.234)

    no_gate_result = ledger.open_attempt(main_task, "IMPLEMENTING")
    _set_attempt(ledger, no_gate_result, cost_usd_est=2.004)

    one_gate_result = ledger.open_attempt(main_task, "REPAIRING")
    ledger.record_gate_result(_gate("lint", "pass"), attempt_id=one_gate_result)
    _set_attempt(ledger, one_gate_result, cost_usd_est=0.459)

    ledger.open_attempt(main_task, "REPAIRING")  # no cost at all

    duplicate_cost = ledger.open_attempt(main_task, "REPAIRING")
    _set_attempt(ledger, duplicate_cost, cost_usd_est=0.459)

    unbatched_run = ledger.create_run(repo_id, "unbatched")
    unbatched_task = ledger.create_task(unbatched_run, "SA-UNB", "su", "bu")
    _set_task(ledger, unbatched_task, state="GATING", risk="standard")
    unbatched_attempt_one = ledger.open_attempt(unbatched_task, "GATING")
    _set_attempt(ledger, unbatched_attempt_one, cost_usd_est=0.415)
    unbatched_attempt_two = ledger.open_attempt(unbatched_task, "REPAIRING")
    _set_attempt(ledger, unbatched_attempt_two, cost_usd_est=0.237)

    decoy_batch = ledger.create_batch(2.0)
    decoy_run = ledger.create_run(repo_id, "decoy", batch_id=decoy_batch)
    batched_decoy = ledger.create_task(decoy_run, "SA-DECOY-B", "sdb", "bdb")
    decoy_pr = "https://example.com/pulls/404"
    _set_task(ledger, batched_decoy, state="DRAFT", risk="standard", pr_url=decoy_pr)
    decoy_attempt = ledger.open_attempt(batched_decoy, "GATING")
    _set_attempt(ledger, decoy_attempt, cost_usd_est=99.99)

    unbatched_decoy = ledger.create_task(unbatched_run, "SA-DECOY-U", "sdu", "bdu")
    unbatched_decoy_pr = "https://example.com/pulls/405"
    _set_task(
        ledger,
        unbatched_decoy,
        state="REVIEWING",
        risk="elevated",
        pr_url=unbatched_decoy_pr,
    )
    unbatched_decoy_attempt = ledger.open_attempt(unbatched_decoy, "REVIEWING")
    _set_attempt(ledger, unbatched_decoy_attempt, cost_usd_est=50.0)
    assert unbatched_decoy > unbatched_task

    fixture_task_ids = {main_task, unbatched_task, batched_decoy, unbatched_decoy}
    assert main_batch not in fixture_task_ids
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        main_status, main_body = _get(base, f"/task/{main_task}")
        unbatched_status, unbatched_body = _get(base, f"/task/{unbatched_task}")
    assert main_status == 200
    assert unbatched_status == 200

    main_page = _parse(main_body)
    assert main_page.summary["state"] == ("READY_FOR_REVIEW", None)
    assert main_page.summary["risk"] == ("elevated", None)
    assert main_page.summary["batch"] == (str(main_batch), f"/batch/{main_batch}")
    assert main_page.summary["pull request"] == (main_pr, main_pr)
    assert main_page.summary["cost"] == ("4.16", None)
    assert decoy_pr not in main_body
    assert str(decoy_batch) not in main_page.summary["batch"][0]

    unbatched_page = _parse(unbatched_body)
    assert unbatched_page.summary["state"] == ("GATING", None)
    assert unbatched_page.summary["risk"] == ("standard", None)
    assert unbatched_page.summary["batch"] == ("none", None)
    assert unbatched_page.summary["pull request"] == ("none", None)
    assert unbatched_page.summary["cost"] == ("0.65", None)
    assert unbatched_decoy_pr not in unbatched_body


def test_a_task_page_lists_each_attempt_once_with_its_times_turns_and_cost(
    tmp_path: Path,
) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base")
    task_id = ledger.create_task(run_id, "SA-ATTEMPTS", "sa", "ba")
    _set_task(ledger, task_id, state="REPAIRING")

    implementing = ledger.open_attempt(task_id, "IMPLEMENTING")
    for gate in ("lint", "types", "tests"):
        ledger.record_gate_result(_gate(gate, "pass"), attempt_id=implementing)
    _set_attempt(
        ledger,
        implementing,
        started_at="2026-01-02 03:00:00",
        ended_at="2026-01-02 03:10:00",
        num_turns=7,
        cost_usd_est=1.50,
    )

    gating = ledger.open_attempt(task_id, "GATING")
    _set_attempt(
        ledger,
        gating,
        started_at="2026-01-02 01:00:00",
        ended_at="2026-01-02 01:05:00",
        num_turns=2,
        cost_usd_est=0.30,
    )

    repairing = ledger.open_attempt(task_id, "REPAIRING")
    ledger.record_gate_result(_gate("lint", "fail"), attempt_id=repairing)
    _set_attempt(
        ledger,
        repairing,
        started_at="2026-01-02 05:00:00",
        ended_at="2026-01-02 05:20:00",
        num_turns=11,
        cost_usd_est=0.75,
    )

    reviewing = ledger.open_attempt(task_id, "REVIEWING")
    _set_attempt(ledger, reviewing, started_at="2026-01-02 02:00:00")
    # Never closed: ended_at, num_turns and cost_usd_est stay NULL.

    rebutting = ledger.open_attempt(task_id, "REBUTTING")
    _set_attempt(
        ledger,
        rebutting,
        started_at="2026-01-02 04:00:00",
        ended_at="2026-01-02 04:15:00",
        num_turns=4,
        cost_usd_est=1.50,  # equal to `implementing`'s cost
    )
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, f"/task/{task_id}")
    assert status == 200
    page = _parse(body)

    assert page.tables["attempts"] == [
        [
            "GATING",
            "1",
            _dt("2026-01-02 01:00:00"),
            _dt("2026-01-02 01:05:00"),
            "2",
            "0.30",
        ],
        ["REVIEWING", "1", _dt("2026-01-02 02:00:00"), "", "", ""],
        [
            "IMPLEMENTING",
            "1",
            _dt("2026-01-02 03:00:00"),
            _dt("2026-01-02 03:10:00"),
            "7",
            "1.50",
        ],
        [
            "REBUTTING",
            "1",
            _dt("2026-01-02 04:00:00"),
            _dt("2026-01-02 04:15:00"),
            "4",
            "1.50",
        ],
        [
            "REPAIRING",
            "1",
            _dt("2026-01-02 05:00:00"),
            _dt("2026-01-02 05:20:00"),
            "11",
            "0.75",
        ],
    ]


def test_a_task_with_no_attempts_shows_its_summary_and_no_table(
    tmp_path: Path,
) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    batch_id = ledger.create_batch(5.0)
    run_id = ledger.create_run(repo_id, "base", batch_id=batch_id)
    task_id = ledger.create_task(run_id, "SA-EMPTY", "se", "be")
    _set_task(ledger, task_id, state="GATE_ERROR")

    other_task = ledger.create_task(run_id, "SA-OTHER", "so", "bo")
    _set_task(ledger, other_task, state="DRAFT")
    ledger.open_attempt(other_task, "GATING")
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, f"/task/{task_id}")
        other_status, other_body = _get(base, f"/task/{other_task}")
    assert status == 200
    assert other_status == 200

    assert "<table" not in body
    page = _parse(body)
    assert page.summary["state"] == ("GATE_ERROR", None)
    assert page.summary["cost"] == ("0.00", None)
    assert "no attempts" in body

    assert "no attempts" not in other_body


def test_gate_results_failure_lines_and_findings_sit_in_separate_tables(
    tmp_path: Path,
) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base")
    task_id = ledger.create_task(run_id, "SA-SPLIT", "ss", "bs")
    _set_task(ledger, task_id, state="REPAIRING")

    gating = ledger.open_attempt(task_id, "GATING")
    # Filed out of file order, so a table sorted by `file` instead of as
    # recorded would read `a.py` first and fail this test.
    gating_lint_id = ledger.record_gate_result(
        _gate(
            "lint",
            "fail",
            failures=[
                Failure(file="b.py", line=1, code="E1", message="first"),
                Failure(file="a.py", line=2, code="E2", message="second"),
            ],
        ),
        attempt_id=gating,
    )
    ledger.record_gate_result(_gate("types", "pass"), attempt_id=gating)
    ledger.record_gate_result(_gate("no-network", "error"), attempt_id=gating)

    # Opened before the `REPAIRING` attempt with `lint`, with no gate result
    # of its own, so that one becomes `REPAIRING` attempt 2.
    ledger.open_attempt(task_id, "REPAIRING")

    repair_with_lint = ledger.open_attempt(task_id, "REPAIRING")
    repair_lint_id = ledger.record_gate_result(
        _gate(
            "lint",
            "fail",
            failures=[Failure(file="c.py", line=3, code="E3", message="third")],
        ),
        attempt_id=repair_with_lint,
    )

    ledger.record_findings(
        task_id,
        [
            Finding(
                lens="style", severity="concern", file="f.py", line=1, claim="claim-one"
            ),
            Finding(
                lens="security",
                severity="blocker",
                file="g.py",
                line=2,
                claim="claim-two",
            ),
        ],
    )
    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, f"/task/{task_id}")
    assert status == 200
    page = _parse(body)

    gate_rows = page.tables["gate-results"]
    assert sorted(row[:4] for row in gate_rows) == sorted(
        [
            ["GATING", "1", "lint", "failed"],
            ["GATING", "1", "types", "passed"],
            ["GATING", "1", "no-network", "cantTell"],
            ["REPAIRING", "2", "lint", "failed"],
        ]
    )
    assert len(gate_rows) == 4  # the no-result `REPAIRING` attempt adds none

    gating_heading = "lint in GATING attempt 1"
    repair_heading = "lint in REPAIRING attempt 2"
    assert page.headings3[f"failures-{gating_lint_id}"] == gating_heading
    assert page.headings3[f"failures-{repair_lint_id}"] == repair_heading

    assert page.tables[f"failures-{gating_lint_id}"] == [
        ["b.py", "1", "E1", "first"],
        ["a.py", "2", "E2", "second"],
    ]
    assert page.tables[f"failures-{repair_lint_id}"] == [["c.py", "3", "E3", "third"]]

    failures_table_ids = [tid for tid in page.table_ids if tid.startswith("failures-")]
    assert failures_table_ids == [
        f"failures-{gating_lint_id}",
        f"failures-{repair_lint_id}",
    ]

    findings = page.tables["findings"]
    assert sorted(findings) == sorted(
        [
            ["style", "concern", "claim-one", ""],
            ["security", "blocker", "claim-two", ""],
        ]
    )


def test_every_table_on_every_page_has_a_header_row_naming_its_columns(
    tmp_path: Path,
) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)
    batch_id = ledger.create_batch(5.0)
    run_id = ledger.create_run(repo_id, "base", batch_id=batch_id)

    task_id = ledger.create_task(run_id, "SA-HEADERS", "sh", "bh")
    _set_task(ledger, task_id, state="REPAIRING")
    attempt = ledger.open_attempt(task_id, "GATING")
    result_id = ledger.record_gate_result(
        _gate(
            "lint",
            "fail",
            failures=[Failure(file="a.py", line=1, code="E", message="m")],
        ),
        attempt_id=attempt,
    )
    ledger.record_findings(task_id, [_finding("concern", "a claim")])

    unbatched_run = ledger.create_run(repo_id, "unbatched")
    unbatched_task = ledger.create_task(unbatched_run, "SA-UNB", "su", "bu")
    _set_task(ledger, unbatched_task, state="DRAFT")

    left_out_task = ledger.create_task(run_id, "SA-LEFT", "sl", "bl")
    _set_task(ledger, left_out_task, state="PAUSED")

    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        index_status, index_body = _get(base, "/")
        batch_status, batch_body = _get(base, f"/batch/{batch_id}")
        task_status, task_body = _get(base, f"/task/{task_id}")
    assert index_status == 200
    assert batch_status == 200
    assert task_status == 200

    def _assert_headers_and_widths(
        page: _PageParser, expected: dict[str, list[str]]
    ) -> None:
        for table_id, columns in expected.items():
            assert page.header_rows[table_id] == columns, table_id
            # The header row is the table's first row, and its only one.
            kinds = page.row_kinds[table_id]
            assert kinds[0] is True, table_id
            assert kinds.count(True) == 1, table_id
            rows = page.tables[table_id]
            assert len(rows) >= 1, table_id
            for row in rows:
                if row and row[0].endswith(" more"):
                    continue
                assert len(row) == len(columns), (table_id, row)

    index_page = _parse(index_body)
    assert index_page.table_ids == ["batches", "no-batch", "left-out"]
    _assert_headers_and_widths(
        index_page,
        {
            "batches": [
                "batch",
                "started",
                "ended",
                "ended because",
                "budget",
                "spent",
                "tasks",
            ],
            "no-batch": ["task", "spec", "state", "risk"],
            "left-out": ["task", "spec", "reason"],
        },
    )

    batch_page = _parse(batch_body)
    assert batch_page.table_ids == ["tasks"]
    _assert_headers_and_widths(batch_page, {"tasks": ["task", "spec", "state", "risk"]})

    task_page = _parse(task_body)
    failures_table_id = f"failures-{result_id}"
    assert task_page.table_ids == [
        "attempts",
        "gate-results",
        failures_table_id,
        "findings",
    ]
    _assert_headers_and_widths(
        task_page,
        {
            "attempts": ["phase", "n", "started", "ended", "turns", "cost"],
            "gate-results": ["phase", "n", "gate", "outcome", "failures"],
            failures_table_id: ["file", "line", "code", "message"],
            "findings": ["lens", "severity", "claim", "verdict"],
        },
    )


def test_task_lists_run_newest_first_by_id_as_a_number(tmp_path: Path) -> None:
    ledger, repo_id, spares = _ledger(tmp_path)

    # A throwaway batch and run advance the task id counter past 7, so each
    # group below crosses the single-to-double-digit boundary on its own.
    throwaway_batch = ledger.create_batch(1.0)
    throwaway_run = ledger.create_run(repo_id, "throwaway", batch_id=throwaway_batch)
    for i in range(6):
        throwaway = ledger.create_task(throwaway_run, f"SA-THROW{i}", f"t{i}", f"bt{i}")
        _set_task(ledger, throwaway, state="DRAFT")

    main_batch = ledger.create_batch(20.0)
    main_run = ledger.create_run(repo_id, "main", batch_id=main_batch)
    unbatched_run = ledger.create_run(repo_id, "unbatched")

    # Interleaved, so each group's own ids cross the 9/10 boundary rather
    # than only the combined set of both groups.
    batched_1 = ledger.create_task(main_run, "SA-QUX", "sq", "bq")
    _set_task(ledger, batched_1, state="DRAFT")
    unbatched_1 = ledger.create_task(unbatched_run, "SA-FOO", "sf", "bf")
    _set_task(ledger, unbatched_1, state="DRAFT")
    batched_2 = ledger.create_task(main_run, "SA-BAR", "sb", "bb")
    _set_task(ledger, batched_2, state="DRAFT")
    unbatched_2 = ledger.create_task(unbatched_run, "SA-ZAP", "sz", "bz")
    _set_task(ledger, unbatched_2, state="DRAFT")
    batched_3 = ledger.create_task(main_run, "SA-MOO", "sm", "bm")
    _set_task(ledger, batched_3, state="DRAFT")
    unbatched_3 = ledger.create_task(unbatched_run, "SA-EEK", "se", "be")
    _set_task(ledger, unbatched_3, state="DRAFT")
    unbatched_4 = ledger.create_task(unbatched_run, "SA-ARG", "sa", "ba")
    _set_task(ledger, unbatched_4, state="DRAFT")

    assert (
        min(batched_1, batched_2, batched_3)
        < 10
        <= max(batched_1, batched_2, batched_3)
    )
    assert (
        min(unbatched_1, unbatched_2, unbatched_3, unbatched_4)
        < 10
        <= max(unbatched_1, unbatched_2, unbatched_3, unbatched_4)
    )

    # Three batches here start in an order that differs from their id
    # order both ways. The index keeps `V1`'s own order, not one by id.
    batch_x = ledger.create_batch(1.0)
    batch_y = ledger.create_batch(1.0)
    _set_batch(ledger, throwaway_batch, started_at="2026-01-01 00:00:00")
    _set_batch(ledger, batch_x, started_at="2026-01-03 00:00:00")
    _set_batch(ledger, batch_y, started_at="2026-01-02 00:00:00")

    _close(ledger, spares)

    with _running(tmp_path / "ledger.db") as base:
        index_status, index_body = _get(base, "/")
        batch_status, batch_body = _get(base, f"/batch/{main_batch}")
    assert index_status == 200
    assert batch_status == 200

    index_page = _parse(index_body)
    no_batch_ids = [row[0] for row in index_page.tables["no-batch"]]
    expected_unbatched_order = [
        str(t)
        for t in sorted(
            [unbatched_1, unbatched_2, unbatched_3, unbatched_4], reverse=True
        )
    ]
    assert no_batch_ids == expected_unbatched_order

    batch_page = _parse(batch_body)
    tasks_ids = [row[0] for row in batch_page.tables["tasks"]]
    expected_batched_order = [
        str(t) for t in sorted([batched_1, batched_2, batched_3], reverse=True)
    ]
    assert tasks_ids == expected_batched_order

    batch_ids_in_order = [row[0] for row in index_page.tables["batches"]]
    expected_chronological = [str(batch_x), str(batch_y), str(throwaway_batch)]
    ours_batches = [b for b in batch_ids_in_order if b in set(expected_chronological)]
    assert ours_batches == expected_chronological


def test_every_page_carries_one_stylesheet_with_a_dark_scheme(tmp_path: Path) -> None:
    batch, task = _one_batched_task(tmp_path)
    with _running(tmp_path / "ledger.db") as base:
        for path in ["/", f"/batch/{batch}", f"/task/{task}"]:
            status, body = _get(base, path)
            assert status == 200, path
            assert body.count("<style>") == 1, path
            assert "prefers-color-scheme: dark" in body, path
