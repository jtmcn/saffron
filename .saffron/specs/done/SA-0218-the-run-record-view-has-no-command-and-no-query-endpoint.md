---
id: SA-0218
title: The run record view has no command that serves it, no query endpoint that refuses a write or a fetch, and no task page that shows findings
type: feature
priority: 2
depends_on: [SA-0217]
consumes:
  - saffron/view/server.py:make_server
estimated_lines: 365
estimate_measured: true
touches:
  - saffron/view/server.py
  - saffron/cli.py
  - tests/test_view_server.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/view/graph.py
  - saffron/projection.py
  - saffron/ledger.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - tests/test_view_graph.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 24
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      The query endpoint, `GET /sparql?query=<text>`, runs a `SELECT` or an
      `ASK` over the graph `make_server` loaded. It answers 200 with the
      result in SPARQL JSON, and its `Content-Type` is exactly the SPARQL
      JSON results media type. The witness drives a `SELECT` of every task's `rdfs:label` over two tasks,
      an `ASK` that holds and an `ASK` that does not.
    witness: tests/test_view_server.py::test_sparql_answers_a_select
    wrong_versions:
      - The answer is labelled `application/json`.
      - Only a `SELECT` is answered, so an `ASK` gets 400.
      - The result is serialized as SPARQL XML.
      - The query runs over a new empty `pyoxigraph.Store`, not the one `make_server` loaded.
      - The route matches the whole request path, so `/sparql?query=…` reads as an unknown page and gets 404.
      - The `query` parameter is read from the raw query string, still percent-encoded.
  - claim: >-
      The query endpoint answers 400 to an `INSERT DATA`, a `DELETE WHERE`, a
      `CONSTRUCT`, a `DESCRIBE`, a query that does not parse, and a request
      with no `query` parameter. The answer to the query that does not parse
      carries `pyoxigraph`'s own message for it. The graph is unchanged after
      the update, so the inserted triple is absent and the tasks are still
      there.
    witness: tests/test_view_server.py::test_sparql_refuses_an_update_and_a_construct
    wrong_versions:
      - A `CONSTRUCT` or a `DESCRIBE` is answered 200 as N-Triples.
      - A query that does not parse is retried as an update, so `INSERT DATA` writes its triple.
      - The parser's message is replaced by a fixed text.
      - A request with no `query` parameter raises inside the handler.
      - The parser's `SyntaxError` is not caught, so the handler dies.
      - "`DESCRIBE` is answered, since only `CONSTRUCT` is checked."
  - claim: >-
      Before it runs anything, the query endpoint decodes each `\uXXXX` and
      `\UXXXXXXXX` escape in the query text. It then answers 400 to any text
      matching the word `SERVICE` in any letter case. That refusal has one
      fixed body, whatever the spelling. It fails closed, so the word inside
      a string literal is refused too. An escape above U+10FFFF answers 400.
      No connection reaches the `SERVICE` endpoint. The witness drives
      `SERVICE`, `service` and `SeRvIcE` in a `SELECT`, `SERVICE` in an
      `ASK`, `\u0053ERVICE`, `SERV\U00000049CE`, the word inside a string
      literal, and `\UFFFFFFFF`, each against a loopback listener.
    witness: tests/test_view_server.py::test_sparql_refuses_a_service_clause_however_spelled
    wrong_versions:
      - No `SERVICE` check, so `pyoxigraph` fetches the endpoint.
      - The match is case-sensitive.
      - Only `SERVICE` and `service` are matched, so `SeRvIcE` is fetched.
      - The escapes are not decoded, so an escaped spelling gets the parser's message rather than the refusal.
      - Only the four-digit `\u` escape is decoded.
      - Only the eight-digit `\U` escape is decoded.
      - The check runs after `Store.query`, so the fetch has already happened.
      - String literals are stripped before the match, so the literal is answered 200.
      - An escape above U+10FFFF raises inside the handler.
      - The refusal body quotes the spelling it matched, so the bodies differ.
  - claim: >-
      A `POST` to any path answers 405 with an `Allow: GET` header. The
      witness posts a body to the index, to the query endpoint with and
      without a `query` parameter, to a task page, to a batch page and to an
      unknown path, and reads the status and the header of each.
    witness: tests/test_view_server.py::test_a_post_is_405
    wrong_versions:
      - No `POST` handler, so `http.server` answers 501.
      - Only `/sparql` answers 405, and every other path 404.
      - A `POST` is served as a `GET`.
      - A `POST` answers 403.
      - The 405 carries no `Allow` header.
  - claim: >-
      `make_server` raises `ValueError` unless `host` is `localhost` or an
      IPv4 loopback address. The witness drives `0.0.0.0`, the empty
      string, `10.1.2.3`, `192.168.0.7`, `::1`, `::`, `example.com` and
      `127.0.0.1.example`, each raising. It drives `127.0.0.1`, `localhost`
      and `127.0.0.2`, none raising `ValueError`.
    witness: tests/test_view_server.py::test_a_non_loopback_host_raises
    wrong_versions:
      - Any loopback address passes, so `::1` reaches a bind that cannot take it.
      - Only `127.0.0.1` and `localhost` pass.
      - Any host starting `127.` passes, so a hostname reaches the bind.
      - No check at all.
      - The empty string passes, so the bind takes every interface.
  - claim: >-
      `saffron serve` exits 2 and prints `ViewGraphError`'s report to stdout
      on a ledger whose graph fails the shapes. The witness gives a finding
      a severity outside the closed set and asserts the report's
      `Conforms: False` and that value are both printed.
    witness: tests/test_view_server.py::test_serve_exits_2_and_prints_the_report_when_the_graph_fails_the_shapes
    wrong_versions:
      - A fixed line is printed without the report.
      - "`ViewGraphError` is not caught."
      - The command exits 1.
      - The report goes to stderr.
  - claim: >-
      `saffron serve` exits 2 with one line naming the full path of
      `ledger.db` under its home when that file is absent, and creates
      nothing. The witness drives a home
      directory that exists and is empty, and one that does not exist. The
      first stays empty and the second is not created. Importing
      `saffron.cli` in a fresh interpreter loads no `saffron.view` module.
    witness: tests/test_view_server.py::test_serve_exits_2_when_there_is_no_ledger
    wrong_versions:
      - "`serve` dispatches after the home `Ledger` is constructed, which writes a schema into a new file."
      - There is no existence check, so the read-only open raises.
      - The message spans two lines.
      - The command exits 1.
      - "`saffron.cli` imports `saffron.view.server` at module scope."
      - The line does not name the path.
      - The home directory is created before the check.
  - claim: >-
      `saffron serve --port N` binds `127.0.0.1:N`, serves until
      `KeyboardInterrupt`, closes its server and exits 0. With no `--port`
      it passes `port=8765` to `make_server`. The witness drives a free port
      it chose, then no `--port` at all.
    witness: tests/test_view_server.py::test_serve_binds_the_given_port_and_exits_0_when_interrupted
    wrong_versions:
      - "`--port` is parsed and not passed, so the server binds 8765."
      - The default port is 8000.
      - The server is not closed on interrupt.
      - "`KeyboardInterrupt` is not caught."
      - The command exits 130 on interrupt.
  - claim: >-
      The task page lists `V4` bound on `?task`, one row per finding, whose
      cells are exactly the lens name, the severity's local name, the claim
      and the verdict, empty when the verdict is null. A finding's claim and
      verdict pass through `html.escape`. The page links its pull request,
      read from `V2` bound on `?task`, or from `V5` bound on `?task` when
      `V2` returns no row, with the URL escaped in the `href`. The witness
      drives two batched and two unbatched tasks. Each has its own pull
      request, its own lens, a gated attempt and one finding with no
      verdict. One URL carries an `&`. It adds markup in a claim and a
      verdict.
    witness: tests/test_view_server.py::test_a_task_page_shows_its_findings_and_links_its_pull_request
    wrong_versions:
      - The link is read from `V2` alone, so the unbatched task has no link.
      - The link is read from `V5` alone, so the batched task has no link.
      - "`V2` is read unbound, so a page links another batched task's pull request."
      - "`V5` is read unbound, so a page links another unbatched task's pull request."
      - "`V4` runs unbound, so another task's findings are listed."
      - The lens cell shows the whole IRI.
      - The severity cell shows its whole IRI.
      - The URL is not escaped in the `href`.
      - A null verdict is shown as `None`.
      - The claim is not escaped.
      - The verdict is not escaped.
---

## Context

Backlog item **b-a1d649**, which cites `DESIGN.md` §6 and §6.2, with ADR 9
(`docs/adr/0009-a-read-only-view-renders-the-run-record-from-the-graph.md`).
§6.2 (`DESIGN.md:1315-1321`) says `saffron serve` renders the view and "the
page writes nothing". ADR 9 (`:29-33`) opens the ledger read-only and keeps
every page out of any scheduler, gate or state change. The design
(`docs/superpowers/specs/2026-10-05-run-record-view-design.md:105-114`)
binds `127.0.0.1` only and accepts `SELECT` and `ASK` alone on `/sparql`.
Its error handling stops `serve` at start with the SHACL report
(`docs/superpowers/specs/2026-10-05-run-record-view-design.md:129`).

The plan's Task 4 (`docs/superpowers/plans/2026-10-05-run-record-view.md:662-689`)
was prototyped whole and measured at 2983 changed tokens, against the
`feature` ceiling of 3000. It was split in two. `SA-0217` is the parent and
serves the pages. This spec is the child. It adds `/sparql`, the `POST`
refusal, the loopback check and the `saffron serve` command. It also adds a
task's findings and its pull request link, which `SA-0217` moved here when
its own size crossed the line.

Line numbers below were read at `0996b3de`.

**What `SA-0217` gives this spec.** Its `saffron/view/server.py` has
`FAILURE_LINE_CAP` and `make_server(ledger_path, *, host="127.0.0.1",
port=8765)`, which returns an unstarted `ThreadingHTTPServer`. That builds
the graph once with `SA-0215`'s `build` and loads it into an in-memory
`pyoxigraph.Store`. It serves `GET /`, `/batch/<id>` and `/task/<id>`, and
404 elsewhere, `/sparql` included. It raises `ViewGraphError` from `build`
when the graph fails the shapes. It has no host check and no `POST`
handler, so a `POST` gets `http.server`'s 501. Its task page heads with the
spec id, read from `V2` bound on `?task` or else `V5`, and then lists the
attempts. It reads no `V4` and links no pull request. Its page contract
says "The task page holds no other rows". It does not touch
`saffron/cli.py`. Read the merged file before you edit it, and keep every
name and every page it has.

**The command line.** The last subcommand `saffron/cli.py` adds is
`chains` (`saffron/cli.py:208-212`). The arguments are parsed after it
(`:214`). The `fold` dispatch returns at `:223-230`. The home ledger is
constructed after it, at `:232`. `Ledger.__init__`
(`saffron/ledger.py:338-345`) creates the parent directory, connects, and
writes its schema, so a ledger opened there is a ledger created.
`_chains` defers its graph import into the function body (`:1916-1917`).

**What `pyoxigraph` 0.5.9 does**, measured on the host with the version
`uv.lock:272-273` pins. `Store.query` raises the builtin `SyntaxError` on
an update and on a query that does not parse. A `CONSTRUCT` or a
`DESCRIBE` returns `QueryTriples`. `serialize(format=QueryResultsFormat.JSON)`
works on `QuerySolutions` and on `QueryBoolean`. A `SERVICE` clause in a
`SELECT` or an `ASK` is fetched over HTTP, `SERVICE SILENT` included, and
`Store.query` has no option to turn that off. It does not decode a `\u`
escape in a keyword. So an escaped `SERVICE` is a parse error to it today,
and the decoding guards whatever a later parser does.

## Problem

1. **`/sparql`.** Route `GET /sparql` before the pages. Read `query` from
   the decoded query string. With no `query`, answer 400. Otherwise decode
   the escapes and refuse `SERVICE` as criterion 3 says. Run the original
   text with `Store.query`. A `SyntaxError` is 400 with its message. A
   `QuerySolutions` or `QueryBoolean` is 200 in SPARQL JSON. Anything else
   is 400.
2. **`POST`.** Answer 405 on every path, with `Allow: GET`, which HTTP
   requires of a 405. First read and discard the body, up to its
   `Content-Length` and at most 64 KiB.
3. **The loopback check.** In `make_server`, before the graph is built,
   raise `ValueError` unless `host` is `localhost` or parses with
   `ipaddress.ip_address` as an IPv4 loopback address.
   `ThreadingHTTPServer` binds IPv4 alone, so `::1` passes `is_loopback`
   and cannot bind. The empty string binds every interface.
4. **`saffron serve [--port N]`.** Add the subparser after `chains`, with
   `--port` an `int` defaulting to 8765. Dispatch it beside `fold`, before
   the home `Ledger` is constructed. Import `saffron.view.server` inside
   the dispatch function, as `_chains` defers its import. With no
   `<home>/ledger.db`, print one line naming it and exit 2. On
   `ViewGraphError`, print its report and exit 2. Otherwise serve until
   `KeyboardInterrupt`, close the server and exit 0. The module
   docstring lists the commands (`saffron/cli.py:1-2`). Add the two it
   lacks, `fold` and `serve`.
5. **Findings and the pull request link.** On the task page, take the
   row that already gives the heading its spec id. Link its pull request
   as an `<a href>`, with the URL escaped. After the attempts table, add a
   findings table from `V4` bound on `?task`, one row each, as criterion 9
   says. The lens cell is its name, so strip the `lens-` prefix from the
   lens IRI as the gate cell strips `gate-`. The severity cell is the
   severity's local name. This amends `SA-0217`'s page contract. The task
   page holds its gate-result and failure rows and, after them, finding
   rows. A finding row is the lens name, the severity's local name, the
   claim and the verdict. The page holds no other rows.

## Out of scope

- The pages, the failure lines and the 404s, apart from criterion 9's
  rows and link. `SA-0217` serves them. Change none of its tests.
- The `view-is-cli-only` rule, which forbids importing `saffron.view`
  outside `saffron/cli.py`. It lands by hand later. The code obeys it
  already, since only `cli.py` imports the view.
- A `SPARQL` protocol `POST`, a write path, and any other HTTP method.
  `PUT` and `DELETE` keep `http.server`'s 501.
- An IPv6 loopback bind. It needs a server class with `AF_INET6`, and no
  caller asks for one.
- A live overlay that rebuilds the graph as the ledger changes. ADR 9
  leaves it to a later item.
- Exempting a word `SERVICE` inside a string literal. The check fails
  closed, and the known cost is that such a query is refused.

## Notes for the agent

**This change is new code.** Four of the five parts do not exist at
base. Part 5 edits `SA-0217`'s task page, which exists at the cell's base,
but its spelling is unknown until `SA-0217` merges. So no text fixes a
spelling. Each criterion declares a witness and no mutant, and the
`witness` gate reports `skip` for all nine. The wrong versions under each
criterion are what its witness must kill. Do not run them yourself.

**Commit as each witness passes.** Nine witnesses, nine commits at
least. A turn cut by a bound then loses one witness's work.

**Every witness must fail without this change.** The parent answers
`/sparql` with 404 and a `POST` with 501. It binds every host, and `serve`
is no subcommand. Its task page shows no finding and no link. Import `saffron.view.server` inside each test
body, never at module scope.

**Fixtures.** Reuse `SA-0217`'s helpers in `tests/test_view_server.py`
for the ledger, a served instance on port 0 and a `GET`. Offset the ids
as its tests do, with spare rows made first, so no id equals its
position. Build every expected IRI from the ids the ledger returned.

**Criterion 1.** The media type is `application/sparql-results+json`.
Compare `Content-Type` with `==`, and the labels as a
sorted list. Two tasks with their own labels catch a query run over an
empty store.

**Criterion 2.** Get the parser's message by running the same text
through a fresh `pyoxigraph.Store` in the test, and assert the answer
carries it. Then send an `ASK` for the inserted triple, which must be
false, and an `ASK` for a task, which must hold.

**Criterion 3.** Bind a listener on `127.0.0.1` port 0 in a thread. It
records and closes each connection, so a fetch fails fast rather than
hanging. Point every `SERVICE` at it and assert it recorded none. Assert
the seven refusal bodies are one value, and that each escaped spelling's
body differs from `pyoxigraph`'s message for the same text. Close with a
plain `ASK`, answered 200, so the server is still up. The fetch was
measured on the host only. Whether a fetch reaches the listener under the
cell's proxy is unmeasured. So the 400 and the one refusal body kill a late
check, and the zero-connection assertion does not. On the host, a late
check fails the witness with that assertion removed. It fails again with
the listener answering 403, as a refusing proxy would. Write each
backslash so the query text carries it, as a raw string or a doubled
backslash.

**Criterion 5.** On macOS only `127.0.0.1` is configured on `lo0`, so
binding `127.0.0.2` raises `OSError` there. The cell's Linux binds it.
Accept an `OSError` for that one host and nothing else, with
`contextlib.suppress(OSError)`. A `ValueError` still fails the test.
`127.0.0.1.example` and `example.com` fail to resolve, which is an
`OSError` and not a `ValueError`.

**Criteria 6 to 8 call `cli.main`.** Stub
`socketserver.BaseServer.serve_forever` to raise `KeyboardInterrupt` in
each, so a wrong version that serves cannot hang the suite. Criterion 6
sets a finding's severity with a raw `UPDATE`, since `SA-0216`'s `build`
raises `ViewGraphError` on a value outside the closed set. `build` states a
finding only for a task with a gated attempt. So give the finding's task an
attempt with a recorded gate result, or the graph conforms and nothing
raises. Use an IRI-safe value such as `critical`, since the severity
becomes `factory:<severity>`. Criterion 7
runs `python -c "import saffron.cli, sys; print('saffron.view' in
sys.modules)"` with `sys.executable`. Criterion 8 picks a free port with a
bound and closed socket, records `server_address` in the stub, and wraps
`socketserver.TCPServer.server_close` to count calls. For the default
port it replaces `saffron.view.server.make_server` with a wrapper that
records its `port` keyword and calls the real one with `port=0`.
`make_server` takes `port` by keyword only, so the command passes it that
way.

**Criterion 9.** Make two batched and two unbatched tasks. Give each a
`pr_url`, a lens of its own, and an attempt with a recorded gate result.
Give each one finding with its own claim and no verdict. `SA-0216` states
a finding only for a task with a gated attempt. Put an `&` in one URL.
Read each page with the parent's `html.parser` helper. Assert its own URL
is among the links, and that `html.escape` of it appears in the body.
Assert its finding row equals the four cells exactly. Assert no other
task's URL or lens appears. Two tasks on each side of the `V2` and `V5`
split are what show a query read unbound. Give one task a second finding
whose claim and verdict carry markup, and set the verdict with a raw
`UPDATE`. Assert its row reads the markup as text, and that no raw tag
from it reaches the page.

**The `POST` body.** An unread body can make Linux reset the connection
before the client reads the 405, so `do_POST` drains it first.

**The `dead` gate.** `http.server` dispatches `do_POST` by name, so
vulture sees no caller. `.saffron/deadcode-allow.py` lists `do_POST` for
this spec. Name the method exactly that.

**The `types` gate.** `serialize` with no output is typed `bytes | None`,
so narrow it before it becomes a body. `server_address` is typed wider
than a tuple, so narrow it before you slice it in a test.

**Measured on a prototype at `8a0ad38f`.** A prototype of this half sat
over the revised parent. It passed all nine witnesses, and each failed against the
parent alone. Each of the 59 wrong versions above was applied to it as an
edit, and each failed its own criterion's witness.
