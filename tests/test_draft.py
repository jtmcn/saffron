"""`saffron.draft` (backlog b-98a3be, `DESIGN.md` §3.4): running the spec
chain as a task.

`saffron.draft` is imported inside each test body, so a reverted tree
fails each test and not collection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from saffron import intake
from saffron.agents.artifacts import hash_artifact
from saffron.follow_up import _slug
from saffron.ledger import Ledger
from saffron.record.memory import MemoryRecord
from saffron.spec_review import (
    SpecReviewSession,
    SpecWriterSession,
    read_spec_review,
    spec_review_route,
)


def _declares_other(text: str, spec_id: str) -> bool:
    """The oracle's own check, through `intake.parse_spec` alone, so it
    cannot share a wrong answer with `saffron.draft`."""
    try:
        parsed = intake.parse_spec(text)
    except intake.SpecError:
        return False
    return parsed.id != spec_id


def _slug_of(text: str) -> str:
    """The oracle's own slug, from `intake.parse_spec` and `_slug`,
    never from `saffron.draft._slug_for_text`."""
    try:
        parsed = intake.parse_spec(text)
    except intake.SpecError:
        return "draft"
    return _slug(parsed.title)


_SPEC_ID = "SA-0001"
_DRAFT_PATH = f".saffron/specs/{_SPEC_ID}-draft.md"


def _task(ledger: Ledger, spec_id: str = _SPEC_ID) -> int:
    repo_id = ledger.upsert_repo("t", f"https://{spec_id}", "/m", policy_sha="p")
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    return ledger.create_task(run_id, spec_id=spec_id, spec_sha="s" * 64, branch="b")


def _state(ledger: Ledger, task_id: int) -> str:
    row = ledger._db.execute(
        "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    return row["state"]


def _review_rows(ledger: Ledger, task_id: int) -> list[dict]:
    key = ledger.record_key(task_id)
    return [
        dict(r)
        for r in ledger._db.execute(
            "SELECT route, block, error FROM spec_reviews "
            "WHERE task_key = ? ORDER BY n",
            (key,),
        )
    ]


def _routes(ledger: Ledger, task_id: int) -> list[str]:
    return [r["route"] for r in _review_rows(ledger, task_id)]


def _texts(ledger: Ledger, task_id: int) -> list[tuple[str, str, str]]:
    key = ledger.record_key(task_id)
    return [
        (r["origin"], r["path"], r["text"])
        for r in ledger._db.execute(
            "SELECT origin, path, text FROM spec_texts WHERE task_key = ? ORDER BY n",
            (key,),
        )
    ]


def _findings(ledger: Ledger, task_id: int) -> list[tuple]:
    key = ledger.record_key(task_id)
    return [
        (r["n"], r["position"], r["severity"], r["fixes"], r["claim"])
        for r in ledger._db.execute(
            "SELECT n, position, severity, fixes, claim FROM spec_findings "
            "WHERE task_key = ? ORDER BY n, position",
            (key,),
        )
    ]


class _Double:
    """Pops items off a list in call order. An item that is an exception
    instance is raised instead of returned. Records every call's own
    arguments, so a test can assert both what each adapter was handed and
    how many times it ran."""

    def __init__(self, items):
        self._items = list(items)
        self.calls: list[tuple] = []

    def __call__(self, *args):
        self.calls.append(args)
        item = self._items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


_N = iter(range(1, 1_000_000))


def _writer(
    text: str = "unparsed draft reply",
    *,
    error: str | None = None,
    resets_at: int | None = None,
) -> SpecWriterSession:
    n = next(_N)
    return SpecWriterSession(
        text=text,
        cost_usd=0.01 * n,
        error=error,
        resets_at=resets_at,
        session_id=f"w{n}",
        num_turns=n,
        spec_sha=hash_artifact(text) if text else None,
        model=f"wmodel{n}",
    )


def _block(findings: list[dict]) -> str:
    return "```json\n" + json.dumps({"findings": findings}, indent=2) + "\n```\n"


def _reviewer(
    findings: list[dict] | None = None,
    *,
    error: str | None = None,
    resets_at: int | None = None,
    text: str | None = None,
) -> SpecReviewSession:
    n = next(_N)
    if text is None:
        text = _block(findings) if findings else ""
    return SpecReviewSession(
        text=text,
        cost_usd=0.02 * n,
        error=error,
        resets_at=resets_at,
        session_id=f"r{n}",
        num_turns=n,
        model=f"rmodel{n}",
    )


def _finding(severity: str, claim: str, fixes: str | None = None) -> dict:
    return {
        "severity": severity,
        "claim": claim,
        "fixes": fixes,
        "criterion": None,
        "file": None,
        "line": None,
    }


_NOTE = [_finding("note", "note claim")]
_ESCALATE = [_finding("blocker", "blocker scope claim", fixes="scope")]
_REVISE = [
    _finding("concern", "concern claim"),
    _finding("blocker", "blocker build claim", fixes="build"),
    _finding("note", "note claim"),
]


def _parsing_text(spec_id: str, title: str = "Something") -> str:
    return f"---\nid: {spec_id}\ntitle: {title}\ntype: feature\n---\nbody\n"


def _unparsed_id_text(spec_id: str) -> str:
    return f"---\nid: {spec_id}\ntype: feature\n---\nbody\n"


@dataclass
class Case:
    """One arrangement: what each adapter returns or raises, in call order."""

    name: str
    write: SpecWriterSession | BaseException
    review: list
    revise: list


@dataclass
class Expected:
    """What `_expect` derives from one `Case`, read back from the ledger
    or asserted against `draft_spec`'s own return value."""

    state: str
    path: str | None
    text: str | None
    raises: bool
    raised: tuple[int, str] | None
    routes: list[str]
    texts: list[tuple[str, str, str]]
    review_calls: list[tuple[str, str]]
    revise_calls: list[tuple[str, str, str]]
    attempts: list[tuple[str, object]]
    findings: list[list]


# A route's state, once no further round follows it.
_ROUTE_STATE = {
    "wait": "RATE_LIMITED",
    "error": "GATE_ERROR",
    "run": "SPEC_DRAFTED",
    "escalate": "SPEC_WITHHELD",
}


def _expect(
    write: SpecWriterSession | BaseException,
    review: list,
    revise: list,
    spec_id: str,
    *,
    slug_for_text,
    declares_other_id,
) -> Expected:
    """The same chain `draft_spec` walks, built from the primitives it
    calls, never from its own code. A divergence shows as a failed
    assertion."""
    routes: list[str] = []
    texts: list[tuple[str, str, str]] = []
    review_calls: list[tuple[str, str]] = []
    revise_calls: list[tuple[str, str, str]] = []
    attempts: list[tuple[str, object]] = []
    findings: list[list] = []

    def done(state: str, path: str | None, text: str | None, **extra) -> Expected:
        return Expected(
            state,
            path,
            text,
            extra.get("raises", False),
            extra.get("raised"),
            routes,
            texts,
            review_calls,
            revise_calls,
            attempts,
            findings,
        )

    def one_round(idx: int, item, path: str, text: str, *, force_escalate: bool):
        review_calls.append((path, text))
        if isinstance(item, BaseException):
            routes.append("error")
            return None, (idx, f"RuntimeError: {item}")
        attempts.append(("SPEC_REVIEW", item))
        read = read_spec_review(item)
        findings.append(read.findings)
        route = spec_review_route(read)
        if force_escalate and route == "revise":
            route = "escalate"
        routes.append(route)
        return route, None

    if isinstance(write, BaseException):
        return done("GATE_ERROR", None, None, raises=True)
    attempts.append(("SPEC_WRITING", write))
    if write.resets_at is not None:
        return done("RATE_LIMITED", None, None)
    if write.error is not None:
        return done("GATE_ERROR", None, None)

    path = f".saffron/specs/{spec_id}-{slug_for_text(write.text)}.md"
    text = write.text
    texts.append(("draft", path, text))
    if declares_other_id(text, spec_id):
        return done("SPEC_WITHHELD", path, text)

    route1, raised = one_round(0, review[0], path, text, force_escalate=False)
    if raised is not None:
        return done("GATE_ERROR", path, text, raises=True, raised=raised)
    if route1 != "revise":
        return done(_ROUTE_STATE[route1], path, text)

    revise_calls.append((path, text, review[0].text))
    rv = revise[0]
    if isinstance(rv, BaseException):
        return done("GATE_ERROR", path, text, raises=True)
    attempts.append(("SPEC_WRITING", rv))
    if rv.resets_at is not None:
        return done("RATE_LIMITED", path, text)
    if rv.error is not None:
        return done("GATE_ERROR", path, text)

    text = rv.text
    texts.append(("revision", path, text))
    if declares_other_id(text, spec_id):
        return done("SPEC_WITHHELD", path, text)

    route2, raised = one_round(1, review[1], path, text, force_escalate=True)
    if raised is not None:
        return done("GATE_ERROR", path, text, raises=True, raised=raised)
    return done(_ROUTE_STATE[route2], path, text)


def _build_cases() -> list[Case]:
    oid = _parsing_text("SA-0043")
    no_t = _unparsed_id_text("SA-0043")
    rev = [_reviewer(_REVISE)]  # the round-1 review that starts a revision
    cases = [
        Case("run", _writer(), [_reviewer(_NOTE)], []),
        Case("escalate", _writer(), [_reviewer(_ESCALATE)], []),
        Case("wait1", _writer(), [_reviewer(resets_at=42, text="")], []),
        Case("wait2", _writer(), [_reviewer(_NOTE, resets_at=99)], []),
        Case("err1", _writer(), [_reviewer(text="not json")], []),
        Case("err2", _writer(), [_reviewer(_NOTE, error="x")], []),
        Case("rev_run", _writer(), [*rev, _reviewer(_NOTE)], [_writer()]),
        Case("rev_wait", _writer(), [*rev, _reviewer(_NOTE, resets_at=7)], [_writer()]),
        Case("rev_esc", _writer(), [*rev, _reviewer(_ESCALATE)], [_writer()]),
        Case("rev_err", _writer(), [*rev, _reviewer(error="x")], [_writer()]),
        Case("rev_rev", _writer(), [*rev, _reviewer(_REVISE)], [_writer()]),
        Case("draft_oid", _writer(text=oid), [], []),
        Case("rev_oid", _writer(), rev, [_writer(text=oid)]),
        Case("draft_no_t", _writer(text=no_t), [_reviewer(_NOTE)], []),
        Case("rev_no_t", _writer(), [*rev, _reviewer(_NOTE)], [_writer(text=no_t)]),
        Case("w_err", _writer(error="x"), [], []),
        Case("w_wait", _writer(resets_at=11), [], []),
        Case("rv_err", _writer(), rev, [_writer(error="x")]),
        Case("rv_wait", _writer(), rev, [_writer(resets_at=13)]),
        Case("raise_w", RuntimeError("x"), [], []),
        Case("raise_r1", _writer(), [RuntimeError("review boom")], []),
        Case(
            "raise_r2",
            _writer(),
            [*rev, RuntimeError("review2 boom")],
            [_writer()],
        ),
        Case("raise_rv", _writer(), rev, [RuntimeError("x")]),
    ]
    assert len(cases) == 23
    return cases


def _run(tmp_path: Path, case: Case):
    """Run one `Case`. Returns its `Expected`, the ledger and task,
    the review and revise doubles, and the `Drafted` (or `None` for a
    raise, already checked here)."""
    from saffron.draft import draft_spec

    expected = _expect(
        case.write,
        case.review,
        case.revise,
        _SPEC_ID,
        slug_for_text=_slug_of,
        declares_other_id=_declares_other,
    )
    ledger = Ledger(tmp_path / f"{case.name}.db", record=MemoryRecord())
    task_id = _task(ledger)
    review_d = _Double(case.review)
    revise_d = _Double(case.revise)
    write_d = _Double([case.write])
    if expected.raises:
        with pytest.raises(RuntimeError):
            draft_spec(
                ledger,
                task_id,
                spec_id=_SPEC_ID,
                item="the item",
                write=write_d,
                review=review_d,
                revise=revise_d,
            )
        drafted = None
    else:
        drafted = draft_spec(
            ledger,
            task_id,
            spec_id=_SPEC_ID,
            item="the item",
            write=write_d,
            review=review_d,
            revise=revise_d,
        )
    return expected, ledger, task_id, review_d, revise_d, drafted


def test_each_route_and_each_writer_stop_ends_the_draft_in_its_own_state(tmp_path):
    for case in _build_cases():
        expected, ledger, task_id, review_d, revise_d, drafted = _run(tmp_path, case)
        if drafted is not None:
            assert (drafted.state, drafted.path, drafted.text) == (
                expected.state,
                expected.path,
                expected.text,
            ), case.name
        assert _state(ledger, task_id) == expected.state, case.name
        assert _routes(ledger, task_id) == expected.routes, case.name
        assert _texts(ledger, task_id) == expected.texts, case.name
        assert review_d.calls == expected.review_calls, case.name
        assert revise_d.calls == expected.revise_calls, case.name
        ledger.close()


def test_each_session_is_one_attempt_and_each_round_records_its_own_findings(
    tmp_path,
):
    for case in _build_cases():
        expected, ledger, task_id, _rd, _vd, _drafted = _run(tmp_path, case)

        rows = ledger.attempts(task_id)
        assert len(rows) == len(expected.attempts), case.name
        counts: dict[str, int] = {}
        for row, (phase, s) in zip(rows, expected.attempts, strict=True):
            counts[phase] = counts.get(phase, 0) + 1
            got = (
                row["phase"],
                row["n"],
                row["session_id"],
                row["model"],
                row["subtype"],
                row["num_turns"],
                row["cost_usd_est"],
            )
            want = (
                phase,
                counts[phase],
                s.session_id,
                s.model,
                "error" if s.error is not None else "success",
                s.num_turns,
                s.cost_usd,
            )
            assert got == want, case.name

        want = [
            (n, position, f.severity, f.fixes, f.claim)
            for n, flist in enumerate(expected.findings, start=1)
            for position, f in enumerate(flist, start=1)
        ]
        assert _findings(ledger, task_id) == want, case.name

        if expected.raised is not None:
            index, message = expected.raised
            row = _review_rows(ledger, task_id)[index]
            assert row["route"] == "error", case.name
            assert row["block"] is None, case.name
            assert row["error"] == message, case.name

        ledger.close()


def test_a_draft_spec_text_records_only_under_its_own_ids_path(tmp_path):
    """A `draft` text is checked by `_FOLLOW_UP_PATH` for the task's own
    spec id, exactly as a `follow_up` text is. Never `_REVISION_PATH`."""
    ledger = Ledger(tmp_path / "ledger.db", record=MemoryRecord())
    task_id = _task(ledger)
    accepted = f".saffron/specs/{_SPEC_ID}-draft.md"

    assert (
        ledger.record_spec_text(
            task_id, origin="draft", spec_id=_SPEC_ID, path=accepted, text="x"
        )
        == 1
    )
    row = ledger.spec_text(task_id)
    assert row is not None
    assert (row["origin"], row["spec_id"], row["path"], row["text"]) == (
        "draft",
        _SPEC_ID,
        accepted,
        "x",
    )

    bad = [
        ".saffron/specs/SA-0002-draft.md",  # another id
        ".saffron/specs/SA-00001-draft.md",  # one more digit
        ".saffron/specs/other.md",  # no id
        f".saffron/specs/{_SPEC_ID}.md",  # bare id, no slug
        f".saffron/specs/done/{_SPEC_ID}-draft.md",  # under done/
    ]
    for path in bad:
        with pytest.raises(ValueError):
            ledger.record_spec_text(
                task_id, origin="draft", spec_id=_SPEC_ID, path=path, text="x"
            )
    ledger.close()


def test_the_draft_prompt_quotes_the_item_and_names_the_draft_for_its_title(
    tmp_path,
):
    from saffron.draft import draft_spec

    items = [
        "an item ending in a newline\nsecond line\n",
        "an item with no trailing newline",
        "\nleading blank line, trailing spaces   \n\n\n",
        "line one\r\nnon-ascii: é\r\n",
    ]
    for i, item in enumerate(items):
        for parses in (False, True):
            ledger = Ledger(tmp_path / f"{i}-{parses}.db", record=MemoryRecord())
            task_id = _task(ledger)
            reply = _parsing_text(_SPEC_ID, "A New Thing") if parses else "no spec"
            path = (
                f".saffron/specs/{_SPEC_ID}-{_slug('A New Thing')}.md"
                if parses
                else _DRAFT_PATH
            )
            writer = _Double([_writer(text=reply)])
            reviewer = _Double([_reviewer(_NOTE)])
            draft_spec(
                ledger,
                task_id,
                spec_id=_SPEC_ID,
                item=item,
                write=writer,
                review=reviewer,
                revise=_Double([]),
            )

            (prompt,) = writer.calls[0]
            assert prompt.splitlines()[0].startswith("context:")
            assert f"id: {_SPEC_ID}" in prompt.splitlines()
            marker = "<item>\n"
            rest = prompt[prompt.index(marker) + len(marker) :]
            assert rest.endswith("</item>")
            want_body = item if item.endswith("\n") else item + "\n"
            assert rest[: -len("</item>")] == want_body

            assert _texts(ledger, task_id) == [("draft", path, reply)]
            assert reviewer.calls == [(path, reply)]
            ledger.close()


def test_the_seed_id_is_the_highest_file_id_of_the_one_prefix(tmp_path):
    from saffron.draft import seed_spec_id

    def _write(dir_: Path, name: str) -> None:
        dir_.mkdir(parents=True, exist_ok=True)
        (dir_ / name).write_text("x")

    # top, done, want: want is the expected id, or None for a raise.
    cases = [
        (["SA-0001-x.md", "SA-0003-y.md"], [], "SA-0003"),  # specs_dir alone
        ([], ["SA-0005-x.md"], "SA-0005"),  # done/ alone
        (["SA-0002-x.md"], ["SA-0009-x.md"], "SA-0009"),  # both, highest in done/
        (["SA-42-x.md"], ["SA-0042-x.md"], "SA-0042"),  # tied, longer spelling wins
        (["SA-0042-x.md"], ["SA-42-x.md"], "SA-0042"),  # tied, either way round
        (["SA-42-x.md", "SA-0042-y.md"], [], "SA-0042"),  # tied, one directory
        (["SA-9-x.md", "SA-10-y.md"], [], "SA-10"),  # numbers, not digit strings
        (["SA-9999-x.md"], ["SA-10000-y.md"], "SA-10000"),  # past four places
        (
            ["SA-0001-x.md", "notes.md", "SA-0999.txt", "TE-0001.txt"],
            ["README.md"],
            "SA-0001",
        ),
        ([], [], None),  # no file at all
        (["README.md"], [], None),  # README.md alone
        (["SA-0001-x.md"], ["TE-0002-y.md"], None),  # two prefixes, two dirs
        (["SA-0001-x.md", "TE-0002-y.md"], [], None),  # two prefixes, one dir
    ]
    for i, (top, done, want) in enumerate(cases):
        d = tmp_path / str(i)
        d.mkdir()
        for name in top:
            _write(d, name)
        for name in done:
            _write(d / "done", name)
        if want is None:
            with pytest.raises(ValueError):
                seed_spec_id(d)
        else:
            assert seed_spec_id(d) == want

    with pytest.raises(ValueError):
        seed_spec_id(tmp_path / "missing")
