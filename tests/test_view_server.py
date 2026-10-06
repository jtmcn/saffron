"""Tests for `saffron.view.server`.

Every test imports `saffron.view.server` inside its own body, never at
module scope. A reverted run's missing module then reads as a `skip` for
this file, rather than a collection error (`DESIGN.md` Appendix H).
"""

from __future__ import annotations

import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from html.parser import HTMLParser
from pathlib import Path

from saffron.agents.findings import Finding, Severity
from saffron.gates.contract import Failure, GateResult, GateStatus
from saffron.ledger import Ledger


def _ledger(tmp_path: Path) -> tuple[Ledger, int]:
    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("r", "origin", str(tmp_path / "mirror"), None)
    return ledger, repo_id


def _set_task(ledger: Ledger, task_id: int, **columns: object) -> None:
    names = ", ".join(f"{name} = ?" for name in columns)
    ledger._db.execute(
        f"UPDATE tasks SET {names} WHERE task_id = ?",
        (*columns.values(), task_id),
    )
    ledger._db.commit()


def _gate(
    gate: str, status: GateStatus, *, failures: list[Failure] | None = None
) -> GateResult:
    return GateResult(gate=gate, status=status, tool="t", failures=failures or [])


def _finding(severity: Severity, claim: str) -> Finding:
    return Finding(lens="style", severity=severity, file="f.py", line=1, claim=claim)


class _PageParser(HTMLParser):
    """Every `<tr>`'s `<td>` texts, grouped by its enclosing `<table id>`
    (`None` for an untagged table), every `<a href>`, the first `<h1>`'s text
    and the `<title>`'s text."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: dict[str | None, list[list[str]]] = {}
        self.hrefs: list[str] = []
        self.heading = ""
        self.title = ""
        self._table_stack: list[str | None] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_h1 = False
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "table":
            self._table_stack.append(attr_map.get("id"))
        elif tag == "tr":
            self._row = []
        elif tag == "td":
            self._cell = []
        elif tag == "a":
            href = attr_map.get("href")
            if href is not None:
                self.hrefs.append(href)
        elif tag == "h1":
            self._in_h1 = True
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._table_stack:
            self._table_stack.pop()
        elif tag == "tr" and self._row is not None:
            table_id = self._table_stack[-1] if self._table_stack else None
            self.tables.setdefault(table_id, []).append(self._row)
            self._row = None
        elif tag == "td" and self._cell is not None:
            if self._row is not None:
                self._row.append("".join(self._cell))
            self._cell = None
        elif tag == "h1":
            self._in_h1 = False
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)
        if self._in_h1:
            self.heading += data
        if self._in_title:
            self.title += data


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
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def test_the_index_lists_each_batch_and_the_tasks_with_no_batch(
    tmp_path: Path,
) -> None:
    ledger, repo_id = _ledger(tmp_path)

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
    ledger.close()

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
    ledger, repo_id = _ledger(tmp_path)
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
    ledger.close()

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
    rows = kept_page.tables.get(None, [])
    assert ["REVIEWING", "1", "", "", ""] in rows


def test_a_batch_page_lists_only_that_batchs_tasks(tmp_path: Path) -> None:
    ledger, repo_id = _ledger(tmp_path)

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
    ledger.close()

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, f"/batch/{batch_one}")
    assert status == 200
    page = _parse(body)

    rows = page.tables.get(None, [])
    ids = {row[0] for row in rows}
    assert ids == {str(task_a), str(task_b)}

    task_links = {href for href in page.hrefs if href.startswith("/task/")}
    assert task_links == {f"/task/{task_a}", f"/task/{task_b}"}


def test_a_task_page_shows_each_attempts_gate_outcomes_with_error_apart_from_fail(
    tmp_path: Path,
) -> None:
    ledger, repo_id = _ledger(tmp_path)
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
    ledger.close()

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, f"/task/{task_id}")
    assert status == 200
    page = _parse(body)

    rows = page.tables.get(None, [])
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
    assert "gate-" not in body


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


def _result_blocks(
    rows: list[list[str]],
) -> list[tuple[list[str], list[list[str]], str | None]]:
    """Groups a task page's flat row list back into one `(gate row, failure
    lines, more cell)` tuple per gate result, by each row's own cell count:
    5 for a gate result, 4 for a failure line, 1 for a `more` row."""
    blocks: list[tuple[list[str], list[list[str]], str | None]] = []
    i = 0
    while i < len(rows):
        row = rows[i]
        if len(row) != 5:
            i += 1
            continue
        i += 1
        lines: list[list[str]] = []
        while i < len(rows) and len(rows[i]) == 4:
            lines.append(rows[i])
            i += 1
        more = None
        if i < len(rows) and len(rows[i]) == 1:
            more = rows[i][0]
            i += 1
        blocks.append((row, lines, more))
    return blocks


def test_a_task_page_shows_failure_lines_capped_with_a_count_of_the_rest(
    tmp_path: Path,
) -> None:
    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base")
    task_id = ledger.create_task(run_id, "SA-CAP", "sc", "bc")
    _set_task(ledger, task_id, state="REPAIRING")

    gating = ledger.open_attempt(task_id, "GATING")
    ledger.record_gate_result(
        _gate("lint", "fail", failures=_failures("lint", 205)), attempt_id=gating
    )
    ledger.record_gate_result(
        _gate("types", "fail", failures=_failures("types", 200)), attempt_id=gating
    )
    repairing = ledger.open_attempt(task_id, "REPAIRING")
    ledger.record_gate_result(
        _gate("tests", "fail", failures=_failures("tests", 3)), attempt_id=repairing
    )
    ledger.close()

    with _running(tmp_path / "ledger.db") as base:
        status, body = _get(base, f"/task/{task_id}")
    assert status == 200
    page = _parse(body)
    blocks = _result_blocks(page.tables.get(None, []))

    # `lint` and `types` share an attempt, and `lint`'s own 205 rows outrun
    # the cap, so this block alone cannot catch a wrong attempt-wide query.
    lint_block = next(b for b in blocks if b[0][2] == "lint")
    assert [line[3] for line in lint_block[1]] == [f"lint-msg{i}" for i in range(200)]
    assert lint_block[2] == "5 more"

    # `types`'s own 200 rows start only after `lint`'s 205. Borrowing the
    # attempt's earliest 200 instead reads as 200 `lint-msg*` rows here.
    types_block = next(b for b in blocks if b[0][2] == "types")
    assert [line[3] for line in types_block[1]] == [f"types-msg{i}" for i in range(200)]
    assert types_block[2] is None

    tests_block = next(b for b in blocks if b[0][2] == "tests")
    assert [line[3] for line in tests_block[1]] == [f"tests-msg{i}" for i in range(3)]
    assert tests_block[2] is None

    more_cells = [
        cell
        for row in page.tables.get(None, [])
        for cell in row
        if cell.endswith(" more")
    ]
    assert more_cells == ["5 more"]


def test_markup_in_a_stored_value_renders_as_text(tmp_path: Path) -> None:
    ledger, repo_id = _ledger(tmp_path)
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
    ledger.record_gate_result(
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
    ledger.close()

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
        rows = b1_page.tables.get(None, [])
        failure_row = next(row for row in rows if len(row) == 4)
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


def _status_line(host: str, port: int, raw_target: bytes) -> str:
    """One raw HTTP/1.0 request, with `raw_target` sent byte for byte.

    The vehicle for a path byte `urllib` cannot encode."""
    with socket.create_connection((host, port)) as sock:
        sock.sendall(b"GET " + raw_target + b" HTTP/1.0\r\n\r\n")
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
    return response.split(b"\r\n", 1)[0].decode("iso-8859-1")


def test_an_unknown_or_malformed_id_is_404(tmp_path: Path) -> None:
    ledger, repo_id = _ledger(tmp_path)

    main_batch = ledger.create_batch(5.0)
    main_run = ledger.create_run(repo_id, "m", batch_id=main_batch)

    # Consumes task_id 1, so the real task below never shares main_batch's id.
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
    ledger.close()

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
