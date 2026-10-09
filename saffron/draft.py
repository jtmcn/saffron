"""Running the spec chain as a task (`DESIGN.md` §3.4, backlog b-98a3be).

`draft_spec` drives one spec-writer session and up to two spec-review
rounds, with at most one revision between them. Its caller mints the
task first, with its own `spec_id`. It opens no cell and calls no
model. `write`, `review` and `revise` are the caller's own adapters,
each a thin wrapper around a host-invoked session
(`saffron/spec_review.py`). `SA-0229` builds those over cells, mints
the task, and writes the file into the tree. Nothing here does that.

`seed_spec_id` gives a draft the other half of what `next_spec_id`
(`saffron/follow_up.py`) needs. A draft has no origin spec to read a
prefix and digit width from.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from saffron import follow_up, intake, spec_review
from saffron.ledger import Ledger
from saffron.scheduler import RETIRED_DIRNAME

# A file's name as `<prefix>-<digits>`, with an optional `-slug` before `.md`.
_FILE_ID = re.compile(r"^([A-Za-z0-9]+)-([0-9]+)(?:-.*)?$")

# The two clean-round states, beside `RATE_LIMITED` and `GATE_ERROR`.
DraftState = Literal["SPEC_DRAFTED", "SPEC_WITHHELD", "RATE_LIMITED", "GATE_ERROR"]

# A route's state, once no further round follows it.
_ROUTE_STATE: dict[str, DraftState] = {
    "wait": "RATE_LIMITED",
    "error": "GATE_ERROR",
    "run": "SPEC_DRAFTED",
    "escalate": "SPEC_WITHHELD",
}

# `draft_spec`'s three adapters, each a thin wrapper over a session.
WriteFn = Callable[[str], spec_review.SpecWriterSession]
ReviewFn = Callable[[str, str], spec_review.SpecReviewSession]
ReviseFn = Callable[[str, str, str], spec_review.SpecWriterSession]


@dataclass(frozen=True)
class Drafted:
    """`path`/`text` name the last spec text recorded, or `None`/`None`."""

    state: DraftState
    path: str | None
    text: str | None


def seed_spec_id(specs_dir: Path) -> str:
    """The spec id of the highest-numbered `*.md` file directly in
    `specs_dir` or in its `done/` (`RETIRED_DIRNAME`).

    A draft task has no `depends_on` parent, so its caller passes this
    id to `follow_up.next_spec_id` in its place. On an equal number the
    longer digit spelling wins (`SA-0042` over `SA-42`). Raises
    `ValueError` for files found with no prefix, or more than one.
    """
    best: tuple[int, str, str] | None = None
    prefixes: set[str] = set()
    for directory in (specs_dir, specs_dir / RETIRED_DIRNAME):
        if not directory.is_dir():
            continue
        for path in directory.glob("*.md"):
            match = _FILE_ID.match(path.stem)
            if match is None:
                continue
            prefix, digits = match.group(1), match.group(2)
            prefixes.add(prefix)
            value = int(digits)
            if best is None or (value, len(digits)) > (best[0], len(best[1])):
                best = (value, digits, prefix)
    if not prefixes:
        raise ValueError(f"no spec id under {specs_dir}")
    if len(prefixes) > 1:
        raise ValueError(f"not one prefix under {specs_dir}: {sorted(prefixes)}")
    assert best is not None
    return f"{best[2]}-{best[1]}"


def _prompt(spec_id: str, item: str) -> str:
    """The write session's own prompt: a `context:` line, an `id:` line,
    then `item` quoted whole between `<item>` and `</item>` lines.

    `item` is never stripped or rejoined. A newline is added before the
    closing tag only when `item` lacks one, so the tag is always its
    own line.
    """
    body = item if item.endswith("\n") else item + "\n"
    return (
        "context: this session drafts a new spec from the item quoted below, "
        "for this task's own review (DESIGN.md §3.4).\n"
        f"id: {spec_id}\n"
        "<item>\n"
        f"{body}"
        "</item>"
    )


def _slug_for_text(text: str) -> str:
    """`follow_up._slug` of `text`'s parsed title, or the literal
    `draft` when `text` does not parse. Never `follow_up._slug("")`."""
    try:
        parsed = intake.parse_spec(text)
    except intake.SpecError:
        return "draft"
    return follow_up._slug(parsed.title)


def _declares_other_id(text: str, spec_id: str) -> bool:
    """`True` only when `text` parses and declares an id other than
    `spec_id`. An unparsed `text` is reviewed whatever its `id:` line
    says, read through `intake.parse_spec` alone."""
    try:
        parsed = intake.parse_spec(text)
    except intake.SpecError:
        return False
    return parsed.id != spec_id


def _charge(
    ledger: Ledger,
    task_id: int,
    phase: str,
    session: spec_review.SpecWriterSession | spec_review.SpecReviewSession,
) -> None:
    """Charge one session as one attempt, the shape `saffron/batch.py`
    and `saffron/follow_up.py` already use."""
    attempt_id = ledger.open_attempt(task_id, phase=phase)
    ledger.close_attempt(
        attempt_id,
        session_id=session.session_id,
        model=session.model,
        subtype="error" if session.error is not None else "success",
        terminal_reason=None,
        num_turns=session.num_turns,
        cost_usd_est=session.cost_usd,
    )


def _stop(
    ledger: Ledger,
    task_id: int,
    session: spec_review.SpecWriterSession,
    path: str | None,
    text: str | None,
) -> Drafted | None:
    """`None` for a session that wrote cleanly. Otherwise ends the task
    `RATE_LIMITED` or `GATE_ERROR` and returns that `Drafted`."""
    if session.resets_at is not None:
        ledger.set_task_state(task_id, "RATE_LIMITED")
        return Drafted(state="RATE_LIMITED", path=path, text=text)
    if session.error is not None:
        ledger.set_task_state(task_id, "GATE_ERROR")
        return Drafted(state="GATE_ERROR", path=path, text=text)
    return None


def _end(ledger: Ledger, task_id: int, route: str, path: str, text: str) -> Drafted:
    """End the task in the state `route` names, and return that `Drafted`."""
    state = _ROUTE_STATE[route]
    ledger.set_task_state(task_id, state)
    return Drafted(state=state, path=path, text=text)


def _review_round(
    ledger: Ledger,
    task_id: int,
    *,
    review: ReviewFn,
    path: str,
    text: str,
) -> tuple[spec_review.SpecReview, str]:
    """Run one review call, charged and recorded.

    A raise records an `error` round, sets `GATE_ERROR`, and propagates.
    A clean call is charged as one `SPEC_REVIEW` attempt, and its read
    is recorded under whatever route it reads. Returns the read
    alongside the session's own whole text, which `revise` is handed
    unchanged, never the read's fenced block alone.
    """
    try:
        session = review(path, text)
    except Exception as exc:
        ledger.record_spec_review(
            task_id,
            route="error",
            block=None,
            block_sha256=None,
            error=f"{type(exc).__name__}: {exc}",
            findings=[],
        )
        ledger.set_task_state(task_id, "GATE_ERROR")
        raise
    _charge(ledger, task_id, "SPEC_REVIEW", session)
    read = spec_review.read_spec_review(session)
    return read, session.text


def draft_spec(
    ledger: Ledger,
    task_id: int,
    *,
    spec_id: str,
    item: str,
    write: WriteFn,
    review: ReviewFn,
    revise: ReviseFn,
) -> Drafted:
    """Drive one draft's writing chain on `task_id`, minted with `spec_id`.

    `write(prompt)` and `revise(path, text, review_text)` return a
    `SpecWriterSession`. `review(path, text)` returns a
    `SpecReviewSession`. Ends the task `SPEC_DRAFTED`, `SPEC_WITHHELD`,
    `RATE_LIMITED` or `GATE_ERROR`, with the last spec text recorded.

    A raise from any adapter sets `GATE_ERROR` and propagates.
    """
    try:
        writer_session = write(_prompt(spec_id, item))
    except Exception:
        ledger.set_task_state(task_id, "GATE_ERROR")
        raise
    _charge(ledger, task_id, spec_review.WRITING_PHASE, writer_session)
    stopped = _stop(ledger, task_id, writer_session, None, None)
    if stopped is not None:
        return stopped

    path = f".saffron/specs/{spec_id}-{_slug_for_text(writer_session.text)}.md"
    ledger.record_spec_text(
        task_id, origin="draft", spec_id=spec_id, path=path, text=writer_session.text
    )
    last_path, last_text = path, writer_session.text

    if _declares_other_id(last_text, spec_id):
        return _end(ledger, task_id, "escalate", last_path, last_text)

    read, review_text = _review_round(
        ledger, task_id, review=review, path=last_path, text=last_text
    )
    route = spec_review.spec_review_route(read)
    ledger.record_spec_review(
        task_id,
        route=route,
        block=read.block,
        block_sha256=read.block_sha256,
        error=read.error,
        findings=read.findings,
    )
    if route != "revise":
        return _end(ledger, task_id, route, last_path, last_text)

    # One revision, then one more review round at most (`DESIGN.md` §3.4).
    try:
        writer_session = revise(last_path, last_text, review_text)
    except Exception:
        ledger.set_task_state(task_id, "GATE_ERROR")
        raise
    _charge(ledger, task_id, spec_review.WRITING_PHASE, writer_session)
    stopped = _stop(ledger, task_id, writer_session, last_path, last_text)
    if stopped is not None:
        return stopped

    ledger.record_spec_text(
        task_id,
        origin="revision",
        spec_id=spec_id,
        path=last_path,
        text=writer_session.text,
    )
    last_text = writer_session.text

    if _declares_other_id(last_text, spec_id):
        return _end(ledger, task_id, "escalate", last_path, last_text)

    read2, _ = _review_round(
        ledger, task_id, review=review, path=last_path, text=last_text
    )
    route2 = spec_review.spec_review_route(read2)
    recorded_route = "escalate" if route2 == "revise" else route2
    ledger.record_spec_review(
        task_id,
        route=recorded_route,
        block=read2.block,
        block_sha256=read2.block_sha256,
        error=read2.error,
        findings=read2.findings,
    )
    return _end(ledger, task_id, recorded_route, last_path, last_text)
