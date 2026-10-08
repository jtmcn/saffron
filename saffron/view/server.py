"""The run record's read-only pages (`DESIGN.md` §6.2, ADR 9).

`make_server` builds the view graph once (`saffron.view.graph.build`) and
serves `/`, `/batch/<id>` and `/task/<id>` over stdlib `http.server`. It
also serves `GET /sparql` for a `SELECT` or an `ASK`, answers every `POST`
405, and binds a loopback host only.
"""

from __future__ import annotations

import hashlib
import html
import ipaddress
import re
import sqlite3
import subprocess
import urllib.parse
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Literal, cast

import pyoxigraph as ox

from saffron.intake import DisclosedMutantError, SpecError, parse_spec
from saffron.projection import DATA_NS, NS, VOCABULARY
from saffron.report.pr_body import extract_problem
from saffron.view.graph import LeftOut, ViewGraph, build, open_read_only

FAILURE_LINE_CAP = 200

# The SPARQL JSON results media type. Compared with `==` by the caller, so
# no charset parameter rides along.
_SPARQL_RESULTS_JSON = "application/sparql-results+json"

# One fixed body, whatever spelling of SERVICE the query carried.
_SERVICE_REFUSED = "the query endpoint refuses a SERVICE clause"

_MAX_POST_BODY = 65536
_MAX_ID_DIGITS = 18

_SERVICE_WORD = re.compile(r"\bservice\b", re.IGNORECASE)
_UNICODE_ESCAPE = re.compile(r"\\u([0-9A-Fa-f]{4})|\\U([0-9A-Fa-f]{8})")

_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_TASK_CLASS = ox.NamedNode(f"{NS}Task")
_BATCH_CLASS = ox.NamedNode(f"{NS}Batch")

_QUERY_DIR = (
    Path(__file__).resolve().parent.parent.parent / "ontology" / "queries" / "view"
)


def _query_text(prefix: str) -> str:
    """The one `.rq` file whose name starts with `prefix`.

    Found by name, never by position, so a renamed or inserted query fails
    loudly instead of retargeting this."""
    (found,) = sorted(_QUERY_DIR.glob(f"{prefix}-*.rq"))
    return found.read_text()


_V1 = _query_text("V1")
_V2 = _query_text("V2")
_V3 = _query_text("V3")
_V4 = _query_text("V4")
_V5 = _query_text("V5")

_BATCH_IRI = re.compile(rf"^{re.escape(DATA_NS)}batch-(\d+)$")
_TASK_IRI = re.compile(rf"^{re.escape(DATA_NS)}task-(\d+)$")
_GATE_RESULT_IRI = re.compile(rf"^{re.escape(DATA_NS)}gate-result-(\d+)$")

_Subject = ox.NamedNode | ox.BlankNode | ox.Literal | ox.Triple
_Substitutions = dict[ox.Variable, _Subject]


def _batch_iri(batch_id: int) -> str:
    return f"{DATA_NS}batch-{batch_id}"


def _task_iri(task_id: int) -> str:
    return f"{DATA_NS}task-{task_id}"


def _id_from(pattern: re.Pattern[str], iri: str) -> int | None:
    m = pattern.match(iri)
    return int(m.group(1)) if m else None


def _local_name(iri: str) -> str:
    """What follows `factory:` or `data:gate-` in `iri`.

    Never a bare split on the last hyphen, which breaks a gate named
    `no-network`."""
    if iri.startswith(NS):
        return iri[len(NS) :]
    gate_prefix = f"{DATA_NS}gate-"
    if iri.startswith(gate_prefix):
        return iri[len(gate_prefix) :]
    lens_prefix = f"{DATA_NS}lens-"
    if iri.startswith(lens_prefix):
        return iri[len(lens_prefix) :]
    return iri.rsplit("#", 1)[-1]


def _query(
    store: ox.Store, text: str, substitutions: _Substitutions | None = None
) -> ox.QuerySolutions:
    result = store.query(text, substitutions=substitutions)
    assert isinstance(result, ox.QuerySolutions), type(result).__name__
    return result


_Term = ox.NamedNode | ox.BlankNode | ox.Literal


def _text(value: _Term | None) -> str:
    """A bound term's display text, or `""` for an unbound one (`None`)."""
    if value is None:
        return ""
    return value.value


def _name(value: _Term | None) -> str:
    """A bound IRI's local name, or `""` for an unbound one (`None`)."""
    if value is None:
        return ""
    return _local_name(value.value)


def _node_exists(store: ox.Store, iri: str, cls: ox.NamedNode) -> bool:
    return bool(list(store.quads_for_pattern(ox.NamedNode(iri), _RDF_TYPE, cls)))


def _decode_escapes(text: str) -> str:
    """Every `\\uXXXX` and `\\UXXXXXXXX` in `text`, decoded to its character.

    Raises `ValueError` for a code point above `U+10FFFF`, caught by the
    caller as a refusal rather than a crash."""

    def replace(match: re.Match[str]) -> str:
        digits = match.group(1) or match.group(2)
        code_point = int(digits, 16)
        if code_point > 0x10FFFF:
            raise ValueError(f"escape out of range: {match.group(0)}")
        return chr(code_point)

    return _UNICODE_ESCAPE.sub(replace, text)


def _mentions_service(text: str) -> bool:
    return _SERVICE_WORD.search(text) is not None


def _check_loopback(host: str) -> None:
    """Raises `ValueError` unless `host` is `localhost` or an IPv4 loopback
    address.

    `ThreadingHTTPServer` binds IPv4 only, so an IPv6 loopback address such
    as `::1` is refused along with everything else."""
    if host == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise ValueError(
            f"not localhost or an IPv4 loopback address: {host!r}"
        ) from None
    if not (isinstance(address, ipaddress.IPv4Address) and address.is_loopback):
        raise ValueError(f"not localhost or an IPv4 loopback address: {host!r}")


def _host_is_local(header: str | None) -> bool:
    """Whether a request's `Host` names this loopback server. A missing header
    passes, because a browser always sends one."""
    if header is None:
        return True
    name = header.rsplit(":", 1)[0] if ":" in header else header
    try:
        _check_loopback(name)
    except ValueError:
        return False
    return True


class _ViewServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        store: ox.Store,
        left_out: list[LeftOut],
        ledger_path: Path,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.store = store
        self.left_out = left_out
        self.ledger_path = ledger_path


def make_server(
    ledger_path: Path, *, host: str = "127.0.0.1", port: int = 8765
) -> ThreadingHTTPServer:
    """Builds the view graph once and returns an unstarted server on
    `(host, port)`. A graph that fails the shapes raises `ViewGraphError`
    from `build`, propagated here with no socket touched. `host` must be
    `localhost` or an IPv4 loopback address, checked before anything else."""
    _check_loopback(host)
    conn = open_read_only(ledger_path)
    try:
        view: ViewGraph = build(conn)
    finally:
        conn.close()
    store = ox.Store()
    store.load(input=view.turtle, format=ox.RdfFormat.TURTLE)
    store.load(path=str(VOCABULARY), format=ox.RdfFormat.TURTLE)
    return _ViewServer((host, port), _Handler, store, view.left_out, ledger_path)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        server = cast(_ViewServer, self.server)
        # A DNS-rebinding page reaches loopback carrying its own name in Host.
        if not _host_is_local(self.headers.get("Host")):
            self._respond(421, "")
            return
        if self.path == "/sparql" or self.path.startswith("/sparql?"):
            self._handle_sparql(server, self.path)
            return
        path = urllib.parse.urlsplit(self.path).path
        if path == "/":
            self._respond(200, _render_index(server.store, server.left_out))
            return
        parts = path.split("/")
        if len(parts) != 3 or parts[0] != "":
            self._respond(404, "")
            return
        kind, raw_id = parts[1], parts[2]
        # int() refuses a digit string past 4300 digits. No ledger id needs 19.
        digits = raw_id.isascii() and raw_id.isdigit() and len(raw_id) <= _MAX_ID_DIGITS
        if kind not in ("batch", "task") or not digits:
            self._respond(404, "")
            return
        node_id = int(raw_id)
        if kind == "batch":
            if not _node_exists(server.store, _batch_iri(node_id), _BATCH_CLASS):
                self._respond(404, "")
                return
            self._respond(200, _render_batch(server.store, node_id))
        else:
            if not _node_exists(server.store, _task_iri(node_id), _TASK_CLASS):
                self._respond(404, "")
                return
            self._respond(200, _render_task(server.store, server.ledger_path, node_id))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(min(length, _MAX_POST_BODY))
        self.send_response(405)
        self.send_header("Allow", "GET")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _handle_sparql(self, server: _ViewServer, path: str) -> None:
        query_string = path.partition("?")[2]
        values = urllib.parse.parse_qs(query_string, keep_blank_values=True).get(
            "query"
        )
        if not values:
            self._respond(400, "missing query parameter")
            return
        text = values[0]
        try:
            decoded = _decode_escapes(text)
        except ValueError as broke:
            self._respond(400, str(broke))
            return
        if _mentions_service(decoded):
            self._respond(400, _SERVICE_REFUSED)
            return
        try:
            result = server.store.query(text)
        except SyntaxError as broke:
            self._respond(400, str(broke))
            return
        if isinstance(result, (ox.QuerySolutions, ox.QueryBoolean)):
            payload = result.serialize(format=ox.QueryResultsFormat.JSON)
            assert isinstance(payload, bytes)
            self._respond(200, payload, content_type=_SPARQL_RESULTS_JSON)
            return
        self._respond(400, "the query is neither a SELECT nor an ASK")

    def log_message(self, format: str, *args: object) -> None:
        """Silence the default per-request access log."""

    def _respond(
        self,
        status: int,
        body: str | bytes,
        *,
        content_type: str = "text/html; charset=utf-8",
    ) -> None:
        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


_STYLESHEET = """<style>
  body { font: 14px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace;
         margin: 2rem auto; padding: 0 1rem; max-width: 72rem; color: #111; }
  h1 { font-size: 1.4rem; }
  h2 { font-size: 1.1rem; margin-top: 2rem; }
  h3 { font-size: 1rem; margin-top: 1.5rem; color: #444; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; }
  th { text-align: left; font-weight: 600; border-bottom: 2px solid #ccc; }
  th, td { padding: .35rem .6rem; vertical-align: top; }
  td { border-bottom: 1px solid #eee; }
  dl { display: grid; grid-template-columns: max-content 1fr; gap: .2rem 1.2rem; }
  dt { color: #555; }
  dd { margin: 0; }
  a { color: #0645ad; }
  @media (prefers-color-scheme: dark) {
    body { background: #111; color: #eee; }
    h3, dt { color: #aaa; }
    th { border-bottom-color: #444; }
    td { border-bottom-color: #262626; }
    a { color: #8ab4f8; }
  }
</style>"""


def _link(path: str, label: str) -> str:
    return f'<a href="{html.escape(path)}">{html.escape(label)}</a>'


def _tr(cells: list[str]) -> str:
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


def _th_row(columns: list[str]) -> str:
    return "<tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in columns) + "</tr>"


def _table(rows: list[list[str]], columns: list[str], *, table_id: str) -> str:
    """`table_id` names which section a row belongs to on a page with more
    than one table. A reader cannot tell two tables apart by position
    alone. The first row is the only `<th>` row, naming `columns`."""
    body_rows = [_th_row(columns), *(_tr(row) for row in rows)]
    return f'<table id="{table_id}">\n' + "\n".join(body_rows) + "\n</table>"


def _batch_row(sol: ox.QuerySolution) -> list[str]:
    batch_id = _id_from(_BATCH_IRI, cast(str, sol["batch"].value))
    assert batch_id is not None
    return [
        _link(f"/batch/{batch_id}", str(batch_id)),
        html.escape(_text(sol["started"])),
        html.escape(_text(sol["ended"])),
        html.escape(_name(sol["because"])),
        html.escape(_text(sol["budget"])),
        html.escape(_text(sol["spent"])),
        html.escape(_text(sol["tasks"])),
    ]


def _task_id_of(sol: ox.QuerySolution) -> int:
    task_id = _id_from(_TASK_IRI, cast(str, sol["task"].value))
    assert task_id is not None
    return task_id


def _task_row(sol: ox.QuerySolution) -> list[str]:
    task_id = _task_id_of(sol)
    return [
        _link(f"/task/{task_id}", str(task_id)),
        html.escape(_text(sol["spec"])),
        html.escape(_name(sol["state"])),
        html.escape(_name(sol["risk"])),
    ]


def _left_out_row(store: ox.Store, entry: LeftOut) -> list[str]:
    task_cell = (
        _link(f"/task/{entry.task_id}", str(entry.task_id))
        if _node_exists(store, _task_iri(entry.task_id), _TASK_CLASS)
        else html.escape(str(entry.task_id))
    )
    return [task_cell, html.escape(entry.spec_id), html.escape(entry.reason)]


_TASK_COLUMNS = ["task", "spec", "state", "risk"]
_BATCH_COLUMNS = [
    "batch",
    "started",
    "ended",
    "ended because",
    "budget",
    "spent",
    "tasks",
]
_LEFT_OUT_COLUMNS = ["task", "spec", "reason"]


def _render_index(store: ox.Store, left_out: list[LeftOut]) -> str:
    batches = list(_query(store, _V1))
    rows = [_batch_row(sol) for sol in batches]
    unbatched = sorted(_query(store, _V5), key=_task_id_of, reverse=True)
    task_rows = [_task_row(sol) for sol in unbatched]
    left_rows = [_left_out_row(store, entry) for entry in left_out]
    batches_table = _table(rows, _BATCH_COLUMNS, table_id="batches")
    no_batch_table = _table(task_rows, _TASK_COLUMNS, table_id="no-batch")
    left_out_table = _table(left_rows, _LEFT_OUT_COLUMNS, table_id="left-out")
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Saffron — run record</title>
{_STYLESHEET}
<h1>Run record</h1>
<h2>Batches</h2>
{batches_table}
<h2>No batch</h2>
{no_batch_table}
<h2>Left out</h2>
{left_out_table}
"""


def _render_batch(store: ox.Store, batch_id: int) -> str:
    substitutions: _Substitutions = {
        ox.Variable("batch"): ox.NamedNode(_batch_iri(batch_id))
    }
    solutions = sorted(_query(store, _V2, substitutions), key=_task_id_of, reverse=True)
    rows = [_task_row(sol) for sol in solutions]
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Saffron — batch {batch_id}</title>
{_STYLESHEET}
<h1>Batch {batch_id}</h1>
{_table(rows, _TASK_COLUMNS, table_id="tasks")}
"""


@dataclass(frozen=True)
class _TaskSummary:
    """One task's `<dl id="summary">` material, read from `V2` bound on
    `?task`, or from `V5` bound on `?task` when `V2` returns no row. A
    batched task's own run reaches `V2`. An unbatched one reaches only
    `V5`, which has no `?batch` to read."""

    spec_id: str
    state: str
    risk: str
    batch_id: int | None
    pr_url: str | None
    added: str | None
    removed: str | None


def _task_summary(store: ox.Store, task_id: int) -> _TaskSummary:
    substitutions: _Substitutions = {
        ox.Variable("task"): ox.NamedNode(_task_iri(task_id))
    }
    for query_text in (_V2, _V5):
        for sol in _query(store, query_text, substitutions):
            spec = sol["spec"]
            if spec is None:
                continue
            batch = sol["batch"]
            pr = sol["pr"]
            added = sol["added"]
            removed = sol["removed"]
            return _TaskSummary(
                spec_id=cast(str, spec.value),
                state=_name(sol["state"]),
                risk=_name(sol["risk"]),
                batch_id=(
                    _id_from(_BATCH_IRI, cast(str, batch.value))
                    if batch is not None
                    else None
                ),
                pr_url=cast(str, pr.value) if pr is not None else None,
                added=_text(added) if added is not None else None,
                removed=_text(removed) if removed is not None else None,
            )
    return _TaskSummary(
        spec_id="",
        state="",
        risk="",
        batch_id=None,
        pr_url=None,
        added=None,
        removed=None,
    )


_CENTS = Decimal("0.01")


def _round_cents(value: Decimal) -> str:
    return str(value.quantize(_CENTS, rounding=ROUND_HALF_UP))


def _attempt_solutions(store: ox.Store, task_id: int) -> list[ox.QuerySolution]:
    """One `V3` solution per distinct `?attempt`, the first in `V3`'s own
    order. `V3` has one row per gate result, so an attempt with several
    would otherwise be counted, and its cost summed, more than once."""
    substitutions: _Substitutions = {
        ox.Variable("task"): ox.NamedNode(_task_iri(task_id))
    }
    seen: set[str] = set()
    solutions: list[ox.QuerySolution] = []
    for sol in _query(store, _V3, substitutions):
        attempt_iri = cast(ox.NamedNode, sol["attempt"]).value
        if attempt_iri in seen:
            continue
        seen.add(attempt_iri)
        solutions.append(sol)
    return solutions


def _task_cost(store: ox.Store, task_id: int) -> str:
    """The task's attempts' `costUsdEst`, summed once per attempt however
    many gate results it has. A `Decimal` sum, so no float noise reaches
    the page."""
    total = Decimal(0)
    for sol in _attempt_solutions(store, task_id):
        cost = sol["cost"]
        if cost is not None:
            total += Decimal(cast(str, cost.value))
    return _round_cents(total)


_ATTEMPT_COLUMNS = ["phase", "n", "started", "ended", "turns", "cost", "model"]


def _attempts_rows(store: ox.Store, task_id: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for sol in _attempt_solutions(store, task_id):
        cost = sol["cost"]
        cost_text = (
            _round_cents(Decimal(cast(str, cost.value))) if cost is not None else ""
        )
        rows.append(
            [
                html.escape(_text(sol["phaseName"])),
                html.escape(_text(sol["n"])),
                html.escape(_text(sol["started"])),
                html.escape(_text(sol["ended"])),
                html.escape(_text(sol["turns"])),
                html.escape(cost_text),
                html.escape(_text(sol["model"])),
            ]
        )
    return rows


def _finding_rows(store: ox.Store, task_id: int) -> list[list[str]]:
    substitutions: _Substitutions = {
        ox.Variable("task"): ox.NamedNode(_task_iri(task_id))
    }
    rows: list[list[str]] = []
    for sol in _query(store, _V4, substitutions):
        rows.append(
            [
                html.escape(_name(sol["lens"])),
                html.escape(_name(sol["severity"])),
                html.escape(_text(sol["claim"])),
                html.escape(_text(sol["verdict"])),
            ]
        )
    return rows


def _failure_rows(conn: sqlite3.Connection, gate_result_id: int) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """SELECT file, line, code, message FROM failures
                WHERE gate_result_id = ? ORDER BY failure_id LIMIT ?""",
            (gate_result_id, FAILURE_LINE_CAP),
        )
    )


_GATE_RESULT_COLUMNS = ["phase", "n", "gate", "outcome", "failures"]
_FAILURE_COLUMNS = ["file", "line", "code", "message"]
_FINDING_COLUMNS = ["lens", "severity", "claim", "verdict"]


def _gate_result_rows(store: ox.Store, task_id: int) -> list[list[str]]:
    """The `V3` rows with `?result` bound. An attempt with no gate result
    adds no row. Its failure lines, if any, live in their own table."""
    substitutions: _Substitutions = {
        ox.Variable("task"): ox.NamedNode(_task_iri(task_id))
    }
    rows: list[list[str]] = []
    for sol in _query(store, _V3, substitutions):
        if sol["result"] is None:
            continue
        rows.append(
            [
                html.escape(_text(sol["phaseName"])),
                html.escape(_text(sol["n"])),
                html.escape(_name(sol["gate"])),
                html.escape(_name(sol["outcome"])),
                html.escape(_text(sol["failures"])),
            ]
        )
    return rows


@dataclass(frozen=True)
class _FailuresBlock:
    """One gate result's failure lines: the `<h3>` text that introduces
    them, the table id, and the rows (ending in an `N more` row when the
    ledger holds more than `FAILURE_LINE_CAP`)."""

    heading: str
    table_id: str
    rows: list[list[str]]


def _failures_blocks(
    store: ox.Store, conn: sqlite3.Connection, task_id: int
) -> list[_FailuresBlock]:
    substitutions: _Substitutions = {
        ox.Variable("task"): ox.NamedNode(_task_iri(task_id))
    }
    blocks: list[_FailuresBlock] = []
    for sol in _query(store, _V3, substitutions):
        failures = sol["failures"]
        if failures is None:
            continue
        count = int(cast(str, failures.value))
        if count <= 0:
            continue
        result_iri = cast(str, sol["result"].value)
        gate_result_id = _id_from(_GATE_RESULT_IRI, result_iri)
        assert gate_result_id is not None
        heading = (
            f"{_name(sol['gate'])} in {_text(sol['phaseName'])} "
            f"attempt {_text(sol['n'])}"
        )
        lines = _failure_rows(conn, gate_result_id)
        rows = [
            [
                html.escape(str(line["file"])),
                html.escape("" if line["line"] is None else str(line["line"])),
                html.escape(str(line["code"])),
                html.escape(str(line["message"] or "")),
            ]
            for line in lines
        ]
        if count > len(lines):
            rows.append([f"{count - len(lines)} more"])
        blocks.append(
            _FailuresBlock(
                heading=heading, table_id=f"failures-{gate_result_id}", rows=rows
            )
        )
    return blocks


_SPEC_DIR = ".saffron/specs/"
_REGULAR_FILE_MODES = frozenset({"100644", "100755"})

# Why a task's spec text could not be shown (§6.2). Never `str`: the four
# reasons are a closed set, named in full where `_render_spec_section` uses them.
SpecUnavailableReason = Literal["absent", "hash mismatch", "unparseable", "unreadable"]


@dataclass(frozen=True)
class _SpecInfo:
    """A task's own spec, read at its own run's `base_sha` from its own
    repo's mirror, and hash-checked against `spec_sha`. `problem` is `None`
    when the spec has no `## Problem` section."""

    title: str
    type: str
    problem: str | None


@dataclass(frozen=True)
class _SpecLocation:
    """One tree entry `_find_spec_entry` matched. `mode` is its git mode, a
    symlink's never `100644` or `100755`. `path` is relative to the tree root."""

    mode: str
    path: str


def _git_bytes(args: list[str]) -> subprocess.CompletedProcess[bytes] | None:
    """One git subprocess, run in bytes mode so a CRLF spec is hashed and
    decoded exactly as committed. Never `saffron.repos.mirror.file_at`,
    whose runner sets `text=True` and turns CRLF into LF first. `None` for
    an `OSError`, so a missing git binary reads as any other broken command."""
    try:
        return subprocess.run(args, capture_output=True, check=False)
    except OSError:
        return None


def _find_spec_entry(
    mirror_path: str, base_sha: str, spec_id: str
) -> _SpecLocation | Literal["absent", "unreadable"]:
    """The tree entry under `.saffron/specs/` at `base_sha` whose last path
    segment starts with `spec_id` and a hyphen.

    Found by listing that one directory, never by
    `saffron.projection._find_spec_version`'s walk over every blob
    `.saffron/specs` has ever held on any ref. `--` keeps `_SPEC_DIR` a
    pathspec rather than a tree object of its own. A `base_sha` whose tree
    has no such directory then lists nothing, read as `absent`, rather
    than making the command itself fail."""
    completed = _git_bytes(
        ["git", "-C", mirror_path, "ls-tree", "-z", base_sha, "--", _SPEC_DIR]
    )
    if completed is None or completed.returncode != 0:
        return "unreadable"
    prefix = f"{spec_id}-".encode()
    for entry in completed.stdout.split(b"\x00"):
        if not entry:
            continue
        header, _, path_bytes = entry.partition(b"\t")
        name = path_bytes.rsplit(b"/", 1)[-1]
        if not name.startswith(prefix):
            continue
        mode = header.split(b" ", 1)[0].decode("ascii")
        try:
            path = path_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return "unreadable"
        return _SpecLocation(mode=mode, path=path)
    return "absent"


def _read_spec_blob(mirror_path: str, base_sha: str, path: str) -> bytes | None:
    """The blob's raw bytes at `base_sha:path`, or `None` for a broken
    command."""
    completed = _git_bytes(
        ["git", "-C", mirror_path, "cat-file", "blob", f"{base_sha}:{path}"]
    )
    if completed is None or completed.returncode != 0:
        return None
    return completed.stdout


def _task_spec(
    conn: sqlite3.Connection, task_id: int
) -> _SpecInfo | SpecUnavailableReason:
    """§6.2: the task's own spec, read at its own run's `base_sha`, from its
    own run's own repo. Never the latest run, never the latest repo, and
    never a history-wide search."""
    row = conn.execute(
        """SELECT t.spec_id AS spec_id, t.spec_sha AS spec_sha,
                  r.base_sha AS base_sha, repo.mirror_path AS mirror_path
             FROM tasks t
             JOIN runs r ON r.run_id = t.run_id
             JOIN repos repo ON repo.repo_id = r.repo_id
            WHERE t.task_id = ?""",
        (task_id,),
    ).fetchone()
    assert row is not None, f"no task {task_id} to read a spec for"

    location = _find_spec_entry(row["mirror_path"], row["base_sha"], row["spec_id"])
    if location == "absent" or location == "unreadable":
        return location
    if location.mode not in _REGULAR_FILE_MODES:
        return "unreadable"

    raw = _read_spec_blob(row["mirror_path"], row["base_sha"], location.path)
    if raw is None:
        return "unreadable"
    if hashlib.sha256(raw).hexdigest() != row["spec_sha"]:
        return "hash mismatch"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "unreadable"

    try:
        spec = parse_spec(text)
    except DisclosedMutantError as exc:
        # The frontmatter validated and the id is trustworthy. The refusal
        # is about admitting the spec as a candidate, not about reading it.
        spec = exc.spec
    except SpecError:
        return "unparseable"

    return _SpecInfo(
        title=spec.title, type=spec.type, problem=extract_problem(spec.body) or None
    )


def _render_spec_section(conn: sqlite3.Connection, task_id: int) -> str:
    result = _task_spec(conn, task_id)
    if isinstance(result, str):
        return (
            f'<p id="spec-unavailable">spec text unavailable: {html.escape(result)}</p>'
        )
    lines = [
        '<dl id="spec">',
        f"<dt>title</dt><dd>{html.escape(result.title)}</dd>",
        f"<dt>type</dt><dd>{html.escape(result.type)}</dd>",
        "</dl>",
    ]
    if result.problem is not None:
        lines.append(f'<pre id="problem">{html.escape(result.problem)}</pre>')
    return "\n".join(lines)


def _render_task(store: ox.Store, ledger_path: Path, task_id: int) -> str:
    summary = _task_summary(store, task_id)
    spec_id = html.escape(summary.spec_id)
    batch_html = (
        _link(f"/batch/{summary.batch_id}", str(summary.batch_id))
        if summary.batch_id is not None
        else "none"
    )
    pr_html = _link(summary.pr_url, summary.pr_url) if summary.pr_url else "none"
    summary_terms = [
        f"<dt>state</dt><dd>{html.escape(summary.state)}</dd>",
        f"<dt>risk</dt><dd>{html.escape(summary.risk)}</dd>",
        f"<dt>batch</dt><dd>{batch_html}</dd>",
        f"<dt>pull request</dt><dd>{pr_html}</dd>",
        f"<dt>cost</dt><dd>{html.escape(_task_cost(store, task_id))}</dd>",
    ]
    if summary.added is not None:
        summary_terms.append(
            f"<dt>lines added</dt><dd>{html.escape(summary.added)}</dd>"
        )
    if summary.removed is not None:
        summary_terms.append(
            f"<dt>lines removed</dt><dd>{html.escape(summary.removed)}</dd>"
        )
    summary_html = '<dl id="summary">\n' + "\n".join(summary_terms) + "\n</dl>"

    conn = open_read_only(ledger_path)
    try:
        spec_html = _render_spec_section(conn, task_id)

        attempt_rows = _attempts_rows(store, task_id)
        if not attempt_rows:
            body = "no attempts"
        else:
            sections = [
                _table(attempt_rows, _ATTEMPT_COLUMNS, table_id="attempts"),
                _table(
                    _gate_result_rows(store, task_id),
                    _GATE_RESULT_COLUMNS,
                    table_id="gate-results",
                ),
            ]
            blocks = _failures_blocks(store, conn, task_id)
            for block in blocks:
                sections.append(f"<h3>{html.escape(block.heading)}</h3>")
                sections.append(
                    _table(block.rows, _FAILURE_COLUMNS, table_id=block.table_id)
                )
            findings_table = _table(
                _finding_rows(store, task_id), _FINDING_COLUMNS, table_id="findings"
            )
            sections.append(findings_table)
            body = "\n".join(sections)
    finally:
        conn.close()

    return f"""<!doctype html>
<meta charset="utf-8">
<title>Saffron — {spec_id}</title>
{_STYLESHEET}
<h1>Task {task_id} — {spec_id}</h1>
{summary_html}
{spec_html}
{body}
"""
