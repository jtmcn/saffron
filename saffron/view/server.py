"""The run record's read-only pages (`DESIGN.md` §6.2, ADR 9).

`make_server` builds the view graph once (`saffron.view.graph.build`) and
serves it over stdlib `http.server`. `SA-0218` adds `/sparql`, the loopback
check on `host`, the 405 on a write and the `saffron serve` command. This
module takes `host` as given and serves `/`, `/batch/<id>` and `/task/<id>`
only.
"""

from __future__ import annotations

import html
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

import pyoxigraph as ox

from saffron.projection import DATA_NS, NS, VOCABULARY
from saffron.view.graph import LeftOut, ViewGraph, build, open_read_only

FAILURE_LINE_CAP = 200

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

    Never a bare split on the last hyphen: a hyphenated gate name like
    `no-network` would break it (Problem item 4 of `SA-0217`)."""
    if iri.startswith(NS):
        return iri[len(NS) :]
    gate_prefix = f"{DATA_NS}gate-"
    if iri.startswith(gate_prefix):
        return iri[len(gate_prefix) :]
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


def _node_exists(store: ox.Store, iri: str, cls: ox.NamedNode) -> bool:
    return bool(list(store.quads_for_pattern(ox.NamedNode(iri), _RDF_TYPE, cls)))


class _ViewServer(ThreadingHTTPServer):
    """A plain `ThreadingHTTPServer` with the view's own state attached, typed
    rather than stashed as bare attributes on the stdlib class."""

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
    from `build`, propagated here with no socket touched."""
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
        path = self.path
        if path == "/":
            self._respond(200, _render_index(server.store, server.left_out))
            return
        parts = path.split("/")
        if len(parts) != 3 or parts[0] != "":
            self._respond(404, "")
            return
        kind, raw_id = parts[1], parts[2]
        if kind not in ("batch", "task") or not (raw_id.isascii() and raw_id.isdigit()):
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

    def log_message(self, format: str, *args: object) -> None:
        """Silence the default per-request access log."""

    def _respond(self, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
    because = sol["because"]
    return [
        _link(f"/batch/{batch_id}", str(batch_id)),
        html.escape(_text(sol["started"])),
        html.escape(_text(sol["ended"])),
        html.escape(_local_name(because.value) if because is not None else ""),
        html.escape(_text(sol["budget"])),
        html.escape(_text(sol["spent"])),
        html.escape(_text(sol["tasks"])),
    ]


def _task_row(sol: ox.QuerySolution) -> list[str]:
    task_id = _id_from(_TASK_IRI, cast(str, sol["task"].value))
    assert task_id is not None
    state = sol["state"]
    risk = sol["risk"]
    return [
        _link(f"/task/{task_id}", str(task_id)),
        html.escape(_text(sol["spec"])),
        html.escape(_local_name(state.value) if state is not None else ""),
        html.escape(_local_name(risk.value) if risk is not None else ""),
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


def _task_spec_id(store: ox.Store, task_id: int) -> str:
    substitutions: _Substitutions = {
        ox.Variable("task"): ox.NamedNode(_task_iri(task_id))
    }
    for sol in _query(store, _V2, substitutions):
        spec = sol["spec"]
        if spec is not None:
            return cast(str, spec.value)
    for sol in _query(store, _V5, substitutions):
        spec = sol["spec"]
        if spec is not None:
            return cast(str, spec.value)
    return ""


def _failure_rows(conn: sqlite3.Connection, gate_result_id: int) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """SELECT file, line, code, message FROM failures
                WHERE gate_result_id = ? ORDER BY failure_id LIMIT ?""",
            (gate_result_id, FAILURE_LINE_CAP),
        )
    )


def _gate_result_rows(
    store: ox.Store, ledger_path: Path, task_id: int
) -> list[list[str]]:
    substitutions: _Substitutions = {
        ox.Variable("task"): ox.NamedNode(_task_iri(task_id))
    }
    rows: list[list[str]] = []
    for sol in _query(store, _V3, substitutions):
        phase_name = sol["phaseName"]
        n = sol["n"]
        gate = sol["gate"]
        outcome = sol["outcome"]
        failures = sol["failures"]
        rows.append(
            [
                html.escape(_text(phase_name)),
                html.escape(_text(n)),
                html.escape(_local_name(gate.value) if gate is not None else ""),
                html.escape(_local_name(outcome.value) if outcome is not None else ""),
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
        conn = open_read_only(ledger_path)
        try:
            lines = _failure_rows(conn, gate_result_id)
        finally:
            conn.close()
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
    spec_id = html.escape(_task_spec_id(store, task_id))
    rows = _gate_result_rows(store, ledger_path, task_id)
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Saffron — {spec_id}</title>
<h1>Task {task_id} — {spec_id}</h1>
{_table(rows)}
"""
