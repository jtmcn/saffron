"""The run record's read-only pages (`DESIGN.md` §6.2, ADR 9).

`make_server` builds the view graph once (`saffron.view.graph.build`) and
serves `/`, `/batch/<id>` and `/task/<id>` over stdlib `http.server`. It
also serves `GET /sparql` for a `SELECT` or an `ASK`, answers every `POST`
405, and binds a loopback host only.
"""

from __future__ import annotations

import html
import ipaddress
import re
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

import pyoxigraph as ox

from saffron.projection import DATA_NS, NS, VOCABULARY
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


def _link(path: str, label: str) -> str:
    return f'<a href="{html.escape(path)}">{html.escape(label)}</a>'


def _tr(cells: list[str]) -> str:
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


def _table(rows: list[list[str]], *, table_id: str | None = None) -> str:
    """`table_id` names which section a row belongs to on a page with more
    than one table.

    A reader cannot tell two tables apart by position alone."""
    open_tag = f'<table id="{table_id}">' if table_id is not None else "<table>"
    return open_tag + "\n" + "\n".join(_tr(row) for row in rows) + "\n</table>"


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


def _task_row(sol: ox.QuerySolution) -> list[str]:
    task_id = _id_from(_TASK_IRI, cast(str, sol["task"].value))
    assert task_id is not None
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


def _render_index(store: ox.Store, left_out: list[LeftOut]) -> str:
    batches = list(_query(store, _V1))
    rows = [_batch_row(sol) for sol in batches]
    unbatched = list(_query(store, _V5))
    task_rows = [_task_row(sol) for sol in unbatched]
    left_rows = [_left_out_row(store, entry) for entry in left_out]
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Saffron — run record</title>
<h1>Run record</h1>
<h2>Batches</h2>
{_table(rows, table_id="batches")}
<h2>No batch</h2>
{_table(task_rows, table_id="no-batch")}
<h2>Left out</h2>
{_table(left_rows, table_id="left-out")}
"""


def _render_batch(store: ox.Store, batch_id: int) -> str:
    substitutions: _Substitutions = {
        ox.Variable("batch"): ox.NamedNode(_batch_iri(batch_id))
    }
    rows = [_task_row(sol) for sol in _query(store, _V2, substitutions)]
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Saffron — batch {batch_id}</title>
<h1>Batch {batch_id}</h1>
{_table(rows)}
"""


def _task_spec_id_and_pr(store: ox.Store, task_id: int) -> tuple[str, str | None]:
    """The task's spec id and pull request URL.

    Read from `V2` bound on `?task`, or from `V5` bound on `?task` when
    `V2` returns no row. A batched task's own run reaches `V2`. An
    unbatched one reaches only `V5`."""
    substitutions: _Substitutions = {
        ox.Variable("task"): ox.NamedNode(_task_iri(task_id))
    }
    for query_text in (_V2, _V5):
        for sol in _query(store, query_text, substitutions):
            spec = sol["spec"]
            if spec is not None:
                pr = sol["pr"]
                return cast(str, spec.value), (
                    cast(str, pr.value) if pr is not None else None
                )
    return "", None


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


def _gate_result_rows(
    store: ox.Store, conn: sqlite3.Connection, task_id: int
) -> list[list[str]]:
    substitutions: _Substitutions = {
        ox.Variable("task"): ox.NamedNode(_task_iri(task_id))
    }
    rows: list[list[str]] = []
    for sol in _query(store, _V3, substitutions):
        phase_name = sol["phaseName"]
        failures = sol["failures"]
        rows.append(
            [
                html.escape(_text(phase_name)),
                html.escape(_text(sol["n"])),
                html.escape(_name(sol["gate"])),
                html.escape(_name(sol["outcome"])),
                html.escape(_text(failures)),
            ]
        )
        if failures is None:
            continue
        count = int(cast(str, failures.value))
        if count <= 0:
            continue
        result_iri = cast(str, sol["result"].value)
        gate_result_id = _id_from(_GATE_RESULT_IRI, result_iri)
        assert gate_result_id is not None
        lines = _failure_rows(conn, gate_result_id)
        for line in lines:
            rows.append(
                [
                    html.escape(str(line["file"])),
                    html.escape("" if line["line"] is None else str(line["line"])),
                    html.escape(str(line["code"])),
                    html.escape(str(line["message"] or "")),
                ]
            )
        if count > len(lines):
            rows.append([f"{count - len(lines)} more"])
    return rows


def _render_task(store: ox.Store, ledger_path: Path, task_id: int) -> str:
    spec_id, pr_url = _task_spec_id_and_pr(store, task_id)
    spec_id = html.escape(spec_id)
    pr_html = _link(pr_url, pr_url) if pr_url else ""
    conn = open_read_only(ledger_path)
    try:
        rows = _gate_result_rows(store, conn, task_id)
    finally:
        conn.close()
    rows = rows + _finding_rows(store, task_id)
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Saffron — {spec_id}</title>
<h1>Task {task_id} — {spec_id}</h1>
{pr_html}
{_table(rows)}
"""
