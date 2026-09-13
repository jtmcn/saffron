"""Saffron's own event vocabulary — the host side of DESIGN.md §4.1.

`agent_runner.py` already does this one level down: it emits Saffron's own
typed events as JSON lines out of the cell, and `implement._consume` renders
them for the operator. Host-side the arrangement is inverted — 64 call sites
across `cell/session.py`, `phases/*.py` and `task.py` author prose straight into
`watch()`, and the structure behind each line dies with the terminal scroll.

This module is the fix: ten frozen dataclasses — one per kind, never one
class with a `type` string, so a future renderer knows what it holds — an
`Event` union naming all ten, a tiny durable log, and `describe()`, which
turns one back into the prose above. `FAMILIES` below is the proof that the
ten kinds are sufficient: one row per call-site shape, citing the file and
symbol it lives in (never a line number — DESIGN.md's own citation rule) and
the kind `describe()` renders it from. Two shapes resisted typing outright and
are named as `FINDINGS` instead of forced into a `message: str` — the escape
hatch this vocabulary exists to close.

Nothing here emits an `Event` yet; `SA-0030`/`SA-0031` migrate the 64 call
sites to construct one and call `describe()` in place of the f-string they
author today.

Every event carries `timestamp` (unix epoch seconds, `time.time()` — the one
documented representation; every reader and writer here agrees on it) and
`spec_id`, plus whatever is specific to its kind.

On disk, `EventLog` appends one JSON object per line to `events.jsonl`, tagged
with a `kind` field naming the dataclass — the wire needs a discriminator even
though the in-memory type does not. `read_log` reads it back, tolerating a
truncated final line and an unknown `kind` the way `saffron.report.index.
_existing_queue_rows` already tolerates a hand-edited queue row: per line, not
per file — one bad row should not cost every good one.

ponytail: one file per task, no rotation, no compression, no size cap — named
as a ceiling (tens of MB a night, by §4.1's own estimate) and not built. Reading
this log for a decision is not a thing this file, or anything else, ever does:
every control that matters lives outside the cell, and `events.jsonl` is a
record, not an input.
"""

from __future__ import annotations

import json
import types
import typing
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Literal

from saffron.gates.contract import GateStatus

# The one size bound feeding both paths a cell's stdout can reach the host's
# disk through — the raw-line quarantine (`implement._quarantined`, reachable
# as `implement.QUARANTINE_BYTES`) and the parsed-event bound below
# (`EventLog.append`). Backlog item 46 named "one value, both paths" as the
# open half after `implement.QUARANTINE_BYTES` shipped alone, because this
# module was forbidden to that spec. Counted in characters — the unit a raw
# stdout `line` is already sliced in, not bytes: JSON escaping can still
# multiply a character's cost once it is written, which is why the bound on
# disk is "a small constant multiple of this", never this exactly.
BOUND_CHARS = 8192

# CONTEXT.md names GATE <-> REPAIR as one phase; split here because a gate
# attempt and a repair turn render as different lines. Deliberate divergence,
# recorded as backlog item 38.
Phase = Literal["DIAGNOSE", "IMPLEMENT", "GATE", "REPAIR", "REVIEW", "REBUT", "PACKAGE"]

# The prefix a progress line actually carries, which is *not* the same set.
# `PLAN:` and `SALVAGE:` both print from inside IMPLEMENT and `SCOPE:` from
# inside DIAGNOSE, so labelling them phases would restate in code exactly the
# conflation CONTEXT.md exists to prevent — it lists "PLAN" on the plan
# checkpoint's own _Avoid_ line and says the checkpoint is deliberately not a
# phase. Both fields are carried: the phase for anything grouping by it, the
# label so `SA-0040` can reproduce the line verbatim.
LineLabel = Literal[
    "SCOPE",
    "SCOPE_REVIEW",
    "PLAN",
    "IMPLEMENT",
    "SALVAGE",
    "REPAIR",
    "REVIEW",
    "REBUT",
    "PACKAGE",
]

Ceiling = Literal["budget_usd", "max_attempts", "max_turns"]

# Where a ceiling's value came from. Three, not two: see `Ceilings`.
CeilingSource = Literal["flag", "spec", "default"]

TerminalReason = Literal[
    # Cut off at the turn ceiling with no budget left to attempt a salvage turn.
    "cut_off_no_salvage_room",
    # Cut off at the turn ceiling, a salvage turn ran, and nothing was recovered.
    "cut_off_salvage_failed",
    # Ended without finishing and produced nothing — an idle or wall-clock
    # bound, a provider wall, or a crash. `subtype`/`terminal_reason` carry
    # which. Not "cut off": the turn ceiling did not fire.
    "ended_without_finishing",
    # Finished on its own and produced nothing. Doneness is measured, never
    # argued with: this is a different fact from being cut off.
    "finished_empty",
    # The plan turn's own rejection — no IMPLEMENT turn ever ran.
    "plan_rejected",
]


@dataclass(frozen=True, slots=True)
class Preflight:
    """One step of standing the cell up, before any agent turn runs — the
    proxy, the image build, the port probe, the worktree coming online."""

    timestamp: float
    spec_id: str
    step: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class Ceilings:
    """What bounded this task, said on the way in — the three ceilings and
    where each came from.

    A tenth kind, and the reason is the one item 18 gives: `SA-0005` was
    stopped by the turn ceiling with more than half its budget left, and
    nothing on the way in had said what any of the three were. `Budget`
    is the other half of that story and not this one — it fires when a
    ceiling is *reached*, carrying only the one that fired, so a task that
    ends any other way leaves no trace of what it was allowed.

    `*_source` is three labels rather than two: calling a model default
    "spec" sends an operator to grep a spec file for a line that is not in
    it, which is the conflation `cli._ceilings` exists to end.
    """

    timestamp: float
    spec_id: str
    budget_usd: float
    max_attempts: int
    max_turns: int
    # Required, not defaulted, for `GateResult.against`'s reason one class up:
    # `"default"` is one of the three real labels, so a forgotten keyword would
    # file a declared or flag-overridden ceiling as a model default,
    # indistinguishably from an observed one — and send the operator to grep a
    # spec file for a line that *is* in it. That is the conflation this kind
    # exists to end, so it cannot be the thing a caller falls into by omission.
    budget_source: CeilingSource
    attempts_source: CeilingSource
    turns_source: CeilingSource


@dataclass(frozen=True, slots=True)
class Baseline:
    """The baseline gate suite finished. `gates`/`statuses` are every gate's
    status, always populated — two parallel tuples, not one of pairs:
    `read_log`'s tuple coercion is one level deep, and a nested
    `tuple[tuple[str, str], ...]` would round-trip as a tuple of *lists*.
    `aborted` names the ones that errored against `base_sha` — non-empty
    means the toolchain is broken and the task never reaches an agent
    (PREFLIGHT_FAILED). Both can be set on the same event: the real call site
    prints the joined `baseline: g=s, ...` line unconditionally and then, only
    when something errored, a second line naming it — `describe()` renders
    both, in that order, from the one event."""

    timestamp: float
    spec_id: str
    aborted: tuple[str, ...] = ()
    gates: tuple[str, ...] = ()
    statuses: tuple[GateStatus, ...] = ()


@dataclass(frozen=True, slots=True)
class PhaseStart:
    """A phase-scoped progress fact — roughly thirty of the 64 lines are this
    shape. `phase` is the phase it happened in and `label` is the prefix the
    line carries; they differ for `PLAN:`, `SALVAGE:` and `SCOPE:`, and
    collapsing them is the thing CONTEXT.md's plan-checkpoint entry forbids.

    ponytail: `detail` is a free string, and it is the one place in this
    vocabulary where prose survives. Typing the roughly thirty line families
    behind it is `SA-0040`'s mapping table, which either types them or names
    the ones that resist; until then this field is the ceiling, not the
    design."""

    timestamp: float
    spec_id: str
    phase: Phase
    label: LineLabel
    detail: str = ""


@dataclass(frozen=True, slots=True)
class Attempt:
    """One numbered execution that let the run continue: an IMPLEMENT/SALVAGE
    turn that landed commits, which measures `commits`/`spent_usd_est`, or a
    gate suite judged in GATE ⇄ REPAIR or re-run after REBUT
    (`new_failures`, and `decision` in the loop), which measures neither and
    leaves both `None`. Cut off *and recovered* is this, not `Terminal`: that
    branch has commits and the run goes on.

    `aborted`/`drift` are the loop's own two ways of distrusting a suite
    mid-attempt — `suite.aborted_gates`/`suite_drift`, both already
    `list[str]` at the call site. Named apart from `Baseline.aborted`: that one
    means the toolchain was already broken before an agent ran; these mean it
    broke, or moved, between two suites of the same attempt."""

    timestamp: float
    spec_id: str
    # CONTEXT.md: "'Attempt 3' without a phase is ambiguous — name both."
    phase: Phase
    # On a gate-suite line this counts gate suites in the task, so REBUT's
    # re-run continues the loop's count rather than restarting at 1 (item 47).
    attempt: int
    # `None`, never `0`, where nothing was measured: a GATE or REBUT line knows
    # neither the commits nor the spend (item 47).
    commits: int | None
    # `_est` travels with any stored figure (DESIGN.md §4.1).
    spent_usd_est: float | None
    new_failures: int | None = None
    decision: Literal["green", "no-progress", "exhausted", "repair"] | None = None
    aborted: tuple[str, ...] = ()
    drift: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GateResult:
    """One gate's host-observed status. All four statuses are representable,
    and `error` (the gate itself broke, charged to nobody) is a different
    value from `fail` (the repo's code is wrong) — never inferred from one
    another. Distinct from `saffron.gates.contract.GateResult`, which is the
    gate *contract*; this is the host's own typed record of the fact a watch
    line already carried a hundred times over."""

    timestamp: float
    spec_id: str
    gate: str
    status: GateStatus
    # Required, not defaulted: a forgotten keyword would file a baseline result
    # as an attempt's, indistinguishably from an observed one.
    against: Literal["baseline", "attempt", "rebuttal"]
    attempt: int | None = None
    # `None`, never `0`: a skipped or errored gate had no count computed.
    new_failures: int | None = None


@dataclass(frozen=True, slots=True)
class Budget:
    """Which of the task's three ceilings stopped it — a typed field over an
    enumeration, never a free string (SA-0005: died at the turn ceiling with
    56% of budget unspent, and nothing said which of the three had fired).
    `value`/`limit` are the reached figure and the declared one, in whatever
    unit `ceiling` names (dollars for `budget_usd`, a count for the other
    two)."""

    timestamp: float
    spec_id: str
    ceiling: Ceiling
    value: float
    limit: float


@dataclass(frozen=True, slots=True)
class Agent:
    """One line of the cell's stdout, or a host-authored fact about that
    stream. One of four shapes: `event` — a parsed cell event, verbatim,
    under one key, never re-typed (no Agent SDK type is imported here or
    anywhere outside `agent_runner.py`), and whose JSON serialization is at
    most `BOUND_CHARS` characters; `line` — a
    raw line that was not an event at all, from a process sharing the
    runner's stdout inside an untrusted cell, quarantined by `raw=True`
    rather than dropped; `line` again but for a different reason, when
    `bounded` is set instead — a parsed event whose own `json.dumps`
    serialization exceeded `BOUND_CHARS`, too large to keep as `event` (a
    dict truncated to a size budget is not a smaller version of the same
    event, so `event` is `None` here rather than a partial one), stored as
    that serialization sliced to `BOUND_CHARS` characters, with
    `original_chars` naming how large it really was; or `detail` — a
    host-authored fact with no cell event behind it at all (a reap outcome, a
    pipe closing). `raw` is the field that must survive the log: a raw line
    that loses its flag on round-trip is a quarantine that stopped being one.
    `bounded` is the same kind of fact for the fourth shape — a bounded event
    that loses its flag reads as a whole one, which is worse than the
    unbounded line it replaced (item 46). `describe()` renders a bounded
    event as `agent: (bounded, N chars) <line, cut again to 160 for the
    terminal>` — the same truncation the raw shape gets, on top of the one
    already applied for storage."""

    timestamp: float
    spec_id: str
    raw: bool
    event: dict | None = None
    line: str | None = None
    detail: str = ""
    bounded: bool = False
    original_chars: int | None = None


@dataclass(frozen=True, slots=True)
class Terminal:
    """One of the five ways an IMPLEMENT turn ends with zero commits — the
    supervisor separates five, and a `cut_off: bool` would re-collapse exactly
    what SA-0028 pulled apart. `subtype`/`terminal_reason` are only meaningful
    on `ended_without_finishing`, where the runtime's own reason is what makes
    "an idle bound", "a provider wall" and "a crash" distinguishable at all.
    `detail` carries the rejection text on `plan_rejected` or a failure note
    on the salvage branches.

    Not a `TerminalState`. CONTEXT.md reserves "terminal state" for the states
    that reach the operator; this kind is narrower, and two of the five map
    onto one, which makes the collision easy to miss. Renaming was deferred
    because SA-0029's own criteria and SA-0030/SA-0040 all cite the name — not
    because DESIGN.md does; it carries no event schema at all (backlog 36)."""

    timestamp: float
    spec_id: str
    reason: TerminalReason
    spent_usd_est: float
    subtype: str | None = None
    terminal_reason: str | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class Teardown:
    """One fact from the cell's teardown — the patch export, a proxy denial or
    failure, or a container/network/volume that would not go away."""

    timestamp: float
    spec_id: str
    step: str
    ok: bool
    detail: str = ""


Event = (
    Preflight
    | Ceilings
    | Baseline
    | PhaseStart
    | Attempt
    | GateResult
    | Budget
    | Agent
    | Terminal
    | Teardown
)

_KINDS: dict[str, type[Event]] = {
    cls.__name__: cls
    for cls in (
        Preflight,
        Ceilings,
        Baseline,
        PhaseStart,
        Attempt,
        GateResult,
        Budget,
        Agent,
        Terminal,
        Teardown,
    )
}


class EventLog:
    """Appends `Event`s to one task's `events.jsonl`, and nothing else.

    One file per task, no rotation (`ponytail:` above): the caller passes the
    task's own directory, matching every other per-task artifact
    (`plan.json`, `patch.diff`, `baseline.json`).
    """

    def __init__(self, task_dir: Path) -> None:
        self._path = Path(task_dir) / "events.jsonl"
        # A disk-full night must not render as a night in which nothing
        # happened. `append` never raises; this is how anyone can tell.
        self.failed = False

    def append(self, event: Event) -> None:
        """Write one line, flushed. Never raises: a cell that cannot write its
        own log is not a cell whose task should die on that account — the
        caller has nothing useful to do with the failure either way.

        An `Agent` event's own `event` dict is bounded here, at the size its
        `json.dumps` serialization reaches — never at the size of the whole
        written line, which would cut an already-bounded raw line a second
        time. Measured on one 5 MB stdout line wrapped in nine bytes of JSON:
        5 MB written before this bound; 16517 characters now for 5 MB of `"`,
        the worst case, since writing escapes each stored character once."""
        try:
            if isinstance(event, Agent) and event.event is not None:
                serialized = json.dumps(event.event)
                if len(serialized) > BOUND_CHARS:
                    event = replace(
                        event,
                        event=None,
                        line=serialized[:BOUND_CHARS],
                        bounded=True,
                        original_chars=len(serialized),
                    )
            # Both reads of the cell's dict sit in this try. `json.dumps` above
            # handles nesting 5000 deep; `asdict` raises RecursionError at 1000,
            # so an event too deep to copy is dropped — unless it was bounded,
            # in which case `asdict` copies a string and the cut event is kept.
            payload = {"kind": type(event).__name__, **asdict(event)}
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a") as handle:
                handle.write(json.dumps(payload) + "\n")
                handle.flush()
        except (OSError, RecursionError, TypeError, ValueError):
            # Everything reachable in the four statements above; narrower than
            # bare `Exception` so a programming error introduced when SA-0030
            # wires 64 producers still surfaces. `self.failed` is the
            # breadcrumb — silence here must not read as "nothing happened".
            self.failed = True
            return


def _shape_ok(value: object, hint: object) -> bool:
    """True if `value`, straight off the wire, is a legal instance of a
    dataclass field's annotated type — the check `read_log`'s own docstring
    claims and `cls(**obj)` never performs. `Agent(event='x')` round-trips
    today and `describe` raises `AttributeError` on it; this is what
    `read_log` needs to catch that at the line, not leave it for the reader.

    JSON is looser than Python, so this checks each hint's own rule rather
    than a blanket `isinstance`: a `float` field accepts a JSON integer
    (there is no float/int distinction on the wire), but neither an `int`
    field nor a `float` field accepts a `bool` (`bool` is an `int`
    subclass in Python, not in JSON). `tuple[str, ...]` is checked
    element-wise, after `read_log`'s own list coercion. `X | None` is
    matched as either `types.UnionType` or `typing.Union`: one object from
    Python 3.14, two before it.

    Never checks a `Literal`'s membership: a string that is the right
    shape carrying a value the enum does not (yet) list is the
    forward-compatible case `read_log` exists to allow.
    """
    origin = typing.get_origin(hint)
    if origin is Literal:
        return any(type(value) is type(choice) for choice in typing.get_args(hint))
    if origin is typing.Union or origin is types.UnionType:
        return any(_shape_ok(value, arg) for arg in typing.get_args(hint))
    if origin is tuple:
        args = typing.get_args(hint)
        elem_hint = args[0] if args else object
        return isinstance(value, (list, tuple)) and all(
            _shape_ok(item, elem_hint) for item in value
        )
    if hint is type(None):
        return value is None
    if hint is bool:
        return isinstance(value, bool)
    if hint is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if hint is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        # An int past float range is valid JSON, and raises at every `:.2f`
        # `describe` formats it with.
        try:
            float(value)
        except OverflowError:
            return False
        return True
    if hint is str:
        return isinstance(value, str)
    if hint is dict:
        return isinstance(value, dict)
    return True


def read_log(task_dir: Path) -> list[Event]:
    """Read back every whole event `EventLog` wrote for one task.

    Per-line tolerance, never a whole-file discard — the rule
    `saffron.report.index._existing_queue_rows` already applies, named there
    in a `ponytail:`. A line that fails to parse as JSON, is not an object,
    names no known `kind`, or is missing a field its kind requires, is dropped
    in silence: this is what turns a truncated final line (the write a killed
    cell left mid-object) and a `kind` from a newer Saffron into "the earlier
    events survive" rather than a raised error.

    An unknown *extra* field is dropped without dropping its event, which is
    the asymmetry that makes this forward-compatible in the direction it will
    actually be used: `SA-0030`, `SA-0031` and `SA-0040` add fields to these
    kinds, and a reader that rejected the line would delete every event of a
    kind rather than one line of it.
    """
    path = Path(task_dir) / "events.jsonl"
    if not path.is_file():
        return []
    events: list[Event] = []
    for line in path.read_text().split("\n"):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        # Not only `JSONDecodeError`: an integer past 4300 digits raises the
        # plain `ValueError`, which would take every other line down with it.
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        # `.get` raises TypeError on an unhashable key, which would take the
        # whole file down — the one thing per-line tolerance exists to prevent.
        kind = obj.pop("kind", None)
        cls = _KINDS.get(kind) if isinstance(kind, str) else None
        if cls is None:
            continue
        # Drop the unknown field, not the event carrying it: a newer Saffron
        # adds fields to existing kinds, and rejecting the line would delete
        # every event of that kind. A missing required field still goes below.
        expected = {f.name for f in fields(cls)}
        obj = {k: v for k, v in obj.items() if k in expected}
        # JSON has no tuple, so a field declared `tuple[str, ...]` (Baseline's
        # `aborted`) comes back a list; coerced here rather than loosened on
        # the dataclass, or a round-trip's equality check reads a real
        # difference where the wire format has none.
        hints = typing.get_type_hints(cls)
        for name, value in list(obj.items()):
            if isinstance(value, list) and typing.get_origin(hints.get(name)) is tuple:
                obj[name] = tuple(value)
        # A field present with the wrong shape drops its event, exactly like
        # one missing outright — `Agent(event='x')` round-tripped unchecked
        # before this, and `describe` raised on it (item 61).
        if any(not _shape_ok(value, hints[name]) for name, value in obj.items()):
            continue
        try:
            events.append(cls(**obj))
        except (TypeError, ValueError):
            continue
    return events


def when(stamp: int | None) -> str:
    """The one place a unix reset time becomes something an operator can act
    on: "when can I retry", in local time, the day dropped unless it isn't
    today. Its callers are the `except RateLimited` handler in
    `cell/session.py` and `describe()`'s `rate_limit` branch below; item 104
    deleted the unguarded copy in `phases.implement`.

    `stamp` arrives from an untrusted cell's `resets_at`, unchecked by any
    shape gate — it is a value, not a shape, so `read_log` would not refuse
    it either. A string, a list, an integer past `time_t`'s range, and NaN
    are all measured to reach here (`SA-0070`, then item 104's own table for
    the `session.py` call site) and must render `"unknown"`, never raise.

    `None` also renders `"unknown"` here, rather than `time.localtime`'s own
    reading of it as *now* — which would print a reset time already past.
    Both callers guard with a truthiness check before calling this, so the
    branch is not reachable through either today; it is still handled
    deliberately, not left to accident, since a caller that stops guarding is
    a caller this function must not silently mislead."""
    import time

    if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
        return "unknown"
    try:
        local = time.localtime(stamp)
        today = time.localtime()
    except (OverflowError, OSError, ValueError):
        return "unknown"
    same_day = (local.tm_year, local.tm_yday) == (today.tm_year, today.tm_yday)
    return time.strftime("%H:%M local" if same_day else "%a %d %b %H:%M local", local)


# Every C0 control character and DEL, mapped to a space — the one place
# cell-authored content is made safe for a terminal, so no caller has to
# remember to do it itself.
_CONTROL_TRANSLATION = str.maketrans({chr(code): " " for code in (*range(0x20), 0x7F)})


def _clean(value: object, limit: int) -> str:
    """One cell-authored field, made safe to print: every control character
    replaced with a space, then clipped to `limit` characters. An error
    event carrying an escape sequence used to clear the operator's screen
    and retitle their terminal — and `saffron watch` can replay that into a
    fresh terminal long after the run — so the strip happens once, here,
    rather than in each branch below. Host-authored text (the `, resets …`
    suffix, `Agent.detail`) never passes through this."""
    return str(value).translate(_CONTROL_TRANSLATION)[:limit]


def _describe_agent_event(event: dict) -> str:
    """The one place a raw Claude Agent SDK event dict becomes a line;
    `phases.implement` renders through `describe` rather than keeping a copy."""
    kind = event.get("type")
    if kind == "text":
        text = " ".join(str(event.get("text", "")).split())
        return f"agent: {_clean(text, 160)}"
    if kind == "tool_use":
        name = _clean(event.get("name"), 160)
        arg = _clean(json.dumps(event.get("input")), 120)
        return f"agent: {name} {arg}"
    if kind == "tool_result":
        return "agent: tool " + ("error" if event.get("is_error") else "ok")
    if kind == "result":
        subtype = _clean(event.get("subtype"), 160)
        terminal_reason = _clean(event.get("terminal_reason"), 160)
        # Numbers from the SDK, but the cell writes them: a string here is as
        # able to carry an escape sequence as `subtype` is.
        turns = _clean(event.get("num_turns"), 160)
        cost = _clean(event.get("total_cost_usd"), 160)
        return f"agent: {subtype} in {turns} turns, ${cost} ({terminal_reason})"
    if kind == "rate_limit":
        used = event.get("utilization")
        status = _clean(event.get("status"), 160)
        try:
            share = f"{used:.0%}" if isinstance(used, int | float) else ""
        except (OverflowError, ValueError):
            # An int past float range, from a live cell's own event.
            share = ""
        return (
            f"agent: rate limit {status}"
            + (f", {_clean(share, 160)} used" if share else "")
            + (
                f", resets {when(event.get('resets_at'))}"
                if event.get("resets_at")
                else ""
            )
        )
    if kind == "error":
        return f"agent: error {_clean(event.get('error'), 160)}"
    rest = _clean(event.get("subtype") or event.get("kind") or "", 160)
    return f"agent: {_clean(kind, 160)} {rest}".rstrip()


def describe(event: Event) -> str:
    """One line per event — `implement._describe`'s shape, widened to the
    whole vocabulary. Returns the exact line today's `watch(...)` call site
    would have printed, so `SA-0030`/`SA-0031` can replace that call site with
    `watch(describe(event))` and change nothing an operator sees.

    Dispatches on `type(event)`, never a `type` string field — the module's
    own rule (line 9 above) applies here too. `FAMILIES` below is the table
    proving every one of the 64 call sites this exists to replace reaches a
    branch here; `FINDINGS` names the two that do not.
    """
    if isinstance(event, Preflight):
        if event.step == "cell_up":
            return f"cell: {event.detail}"
        if event.step == "unstacked":
            return f"unstacked: {event.detail}"
        return f"preflight: {event.detail}"

    if isinstance(event, Ceilings):
        # The line `cli._run_cell` printed verbatim before this kind existed:
        # `_ceilings` formatted it there and the unattended path had none.
        return "ceilings: " + ", ".join(
            (
                f"budget_usd={event.budget_usd} ({event.budget_source})",
                f"max_attempts={event.max_attempts} ({event.attempts_source})",
                f"max_turns={event.max_turns} ({event.turns_source})",
            )
        )

    if isinstance(event, Baseline):
        # The real call site (`_drive_cell`) prints the joined gate-status
        # line unconditionally, then — only on a broken toolchain — a second
        # line naming what errored. Both facts can live on one `Baseline`, so
        # both must render: an if/else here would silently drop whichever
        # line lost, and on PREFLIGHT_FAILED the per-gate line is the one
        # diagnosis needs most.
        lines = []
        if event.gates or event.statuses:
            # Not `strict=True`: a `Baseline` whose two lists differ in
            # length is a value, not a shape, so `read_log` does not refuse
            # it — this renders the overlap it has rather than raising.
            joined = ", ".join(
                f"{gate}={status}"
                for gate, status in zip(event.gates, event.statuses, strict=False)
            )
            lines.append(f"baseline: {joined}")
        if event.aborted:
            lines.append(
                f"baseline errored in {list(event.aborted)} — the toolchain "
                "is broken, not the code"
            )
        return "\n".join(lines)

    if isinstance(event, PhaseStart):
        return f"{event.label}: {event.detail}"

    if isinstance(event, Attempt):
        if event.aborted:
            return (
                f"gates: {list(event.aborted)} errored — infrastructure, not the task"
            )
        if event.drift:
            return f"gates: {list(event.drift)} — distrusting the subtraction"
        if event.new_failures is not None and event.decision is not None:
            return (
                f"gates: attempt {event.attempt}, {event.new_failures} new "
                f"failures -> {event.decision}"
            )
        if event.new_failures is not None:
            return f"gates: {event.new_failures} new failures after the rebuttal"
        if event.commits is None or event.spent_usd_est is None:
            return f"{event.phase}: attempt {event.attempt}"
        return f"IMPLEMENT: {event.commits} commit(s), ${event.spent_usd_est:.2f} spent"

    if isinstance(event, GateResult):
        # No call site prints one alone today — every printed line joins
        # several (`Baseline`) or reports only a count (`Attempt`). Still
        # rendered: a future consumer (a report page, `SA-0036`) reads one
        # `GateResult` at a time, and "the ten kinds render" cannot mean
        # "eight of them."
        return f"gates: {event.gate}={event.status}"

    if isinstance(event, Budget):
        return f"budget: ${event.value:.2f} of ${event.limit:.2f} — stopping"

    if isinstance(event, Agent):
        if event.bounded:
            return (
                f"agent: (bounded, {event.original_chars} chars) "
                f"{_clean(event.line or '', 160)}"
            )
        if event.raw:
            return f"agent: (raw) {_clean(event.line or '', 160)}"
        if event.event is not None:
            return _describe_agent_event(event.event)
        return f"agent: {event.detail}"

    if isinstance(event, Terminal):
        if event.reason == "cut_off_no_salvage_room":
            return (
                f"budget: {event.detail} — cut off at the turn ceiling with "
                "nothing committed, no room left to salvage"
            )
        if event.reason == "cut_off_salvage_failed":
            return (
                "SALVAGE: cut off and could not be salvaged, "
                f"${event.spent_usd_est:.2f} spent"
            )
        if event.reason == "ended_without_finishing":
            return (
                "IMPLEMENT: the turn ended without finishing and produced "
                f"nothing ({event.subtype}/{event.terminal_reason})"
            )
        if event.reason == "finished_empty":
            return "IMPLEMENT: finished and produced nothing"
        return f"PLAN: rejected, ${event.spent_usd_est:.2f} spent — {event.detail}"

    if isinstance(event, Teardown):
        if event.step == "start":
            return "teardown"
        return f"teardown: {event.detail}"

    raise TypeError(f"describe() has no branch for {type(event).__name__}")


@dataclass(frozen=True, slots=True)
class _Family:
    """One row: a call-site shape, where it lives (file and symbol — never a
    line number, DESIGN.md's own citation rule), and the kind `describe()`
    renders it from. `tests/test_events.py` pairs every row with a concrete
    event and the literal line it must produce."""

    prefix: str
    where: str
    kind: type


# The proof this vocabulary's ten kinds are sufficient for the 64 call sites across
# `cell/session.py`, `phases/{implement,package,review,rebut}.py` and
# `task.py`. Grouped by rendered shape, not by literal call site: two call
# sites that print the same shape (both `SALVAGE: the session failed — …`
# branches, both `agent: (raw) …` guards) are one row. Two rows can still
# share a prefix and differ in kind — `budget:` is `Budget` when the ceiling
# is merely reached and `Terminal` when it is reached with nothing committed
# and no salvage room left; `IMPLEMENT:` spans `PhaseStart`, `Attempt` and
# `Terminal` depending on which of the three it is. That is not an
# inconsistency to fix; it is `describe()` reading the *fields*, never the
# prefix, to decide what happened.
# Short aliases so a row is one line: the citation, not its length, is the
# point. `_S` covers every branch of `_drive_cell` itself.
_S = "cell/session.py:_drive_cell"
_PC = "cell/session.py:plan_checkpoint"
_RL = "cell/session.py:repair_loop"
_EP = "cell/session.py:export_patch"
_IA = "phases/implement.py:run_agent"
_IC = "phases/implement.py:_consume"
_PKG = "phases/package.py:package"
_TASK = "task.py:_resolve_stacked_on"
_RT = "task.py:run_task"

FAMILIES: tuple[_Family, ...] = (
    _Family("preflight: starting the proxy", _S, Preflight),
    _Family("preflight: proxy at", _S, Preflight),
    _Family("preflight: proxy reaches", _S, Preflight),
    _Family("preflight: building", _S, Preflight),
    _Family("preflight: probing", _S, Preflight),
    _Family("cell:", _S, Preflight),
    _Family("unstacked:", _TASK, Preflight),
    _Family("ceilings:", _RT, Ceilings),
    _Family("baseline: (joined gate=status)", _S, Baseline),
    _Family("baseline errored in", _S, Baseline),
    _Family("SCOPE: proposal refused", _PC, PhaseStart),
    _Family("SCOPE_REVIEW: proposed", _S, PhaseStart),
    _Family("PLAN: not the schema", _PC, PhaseStart),
    _Family("PLAN: the session failed", _S, PhaseStart),
    _Family("PLAN: accepted", _S, PhaseStart),
    _Family("PLAN: rejected", _S, Terminal),
    _Family("IMPLEMENT: system prompt", _S, PhaseStart),
    _Family("IMPLEMENT: the session failed", _S, PhaseStart),
    _Family("IMPLEMENT: cut off … spending one turn", _S, PhaseStart),
    _Family("IMPLEMENT: N commit(s)", _S, Attempt),
    _Family("IMPLEMENT: the turn ended without finishing", _S, Terminal),
    _Family("IMPLEMENT: finished and produced nothing", _S, Terminal),
    _Family("budget: … stopping", _S, Budget),
    _Family("budget: … cut off … no room left to salvage", _S, Terminal),
    _Family("SALVAGE: the session failed", _S, PhaseStart),
    _Family("SALVAGE: uncommitted work checkpointed", _S, PhaseStart),
    _Family("SALVAGE: the host checkpoint failed", _S, PhaseStart),
    _Family("SALVAGE: recovered N commit(s)", _S, PhaseStart),
    _Family("SALVAGE: cut off and could not be salvaged", _S, Terminal),
    _Family("gates: attempt N, K new failures -> decision", _RL, Attempt),
    _Family("gates: … errored — infrastructure", _RL, Attempt),
    _Family("gates: … distrusting the subtraction", _RL, Attempt),
    _Family("gates: N new failures after the rebuttal", _S, Attempt),
    _Family("REPAIR: the session failed", _S, PhaseStart),
    _Family("REPAIR: uncommitted work checkpointed", _S, PhaseStart),
    _Family("REVIEW:", _S, PhaseStart),
    # Two of the three `REVIEW:` lines in the captured fixture come from
    # `run_review`, not the supervisor, and `SA-0031` migrates `phases/*.py`
    # by reading this table — so the file it has to edit has to appear in it.
    _Family("REVIEW: (per-lens)", "phases/review.py:run_review", PhaseStart),
    # A lens's own re-prompt line, not the supervisor's or `run_review`'s: it
    # fires from inside `run_lens`, one turn before the per-lens line above.
    _Family("REVIEW: not the schema", "phases/review.py:run_lens", PhaseStart),
    _Family("REBUT:", _S, PhaseStart),
    _Family("REBUT: (verdict)", "phases/rebut.py:run_rebut", PhaseStart),
    _Family("teardown", _S, Teardown),
    _Family("teardown: commit subjects unreadable", _EP, Teardown),
    _Family("teardown: no commits, nothing to export", _EP, Teardown),
    _Family("teardown: exported N bytes", _EP, Teardown),
    _Family("teardown: patch export FAILED", _EP, Teardown),
    _Family("teardown: proxy DENIED", _S, Teardown),
    _Family("teardown: proxy FAILED", _S, Teardown),
    _Family("teardown: … survived", _S, Teardown),
    _Family("agent: (raw)", _IA, Agent),
    _Family("agent: (event dict rendering)", _IC, Agent),
    _Family("agent: reaped/would not reap", _IA, Agent),
    _Family("agent: result seen, then a child held stdout open", _IA, Agent),
    _Family("PACKAGE: (ParentGone)", _PKG, PhaseStart),
    _Family("PACKAGE: conflicts with", _PKG, PhaseStart),
    _Family("PACKAGE: refusing to push", _PKG, PhaseStart),
    _Family("PACKAGE: N new failures against", _PKG, PhaseStart),
    _Family("PACKAGE: (LeaseRejected)", _PKG, PhaseStart),
    _Family("PACKAGE: (pr_url)", _PKG, PhaseStart),
    _Family("PACKAGE: could not remove", _PKG, PhaseStart),
)

# The two call-site shapes `FAMILIES` above could not fit into the ten kinds
# without a `message: str` standing in for a shape of its own — named here
# rather than forced, per this spec's own acceptance criteria.
FINDINGS: tuple[tuple[str, str, str], ...] = (
    (
        "{outcome}: $N spent, session … / rate limit: rejected — not exhausted",
        _S,
        "Both are the task's own terminal announcement, not a kind's. "
        "`Terminal` is scoped to the five zero-commit ways one IMPLEMENT turn "
        "ends (backlog item 37); `Budget` carries a ceiling/value/limit triple, "
        "not an arbitrary outcome word and a session id. Typing this needs a "
        "eleventh kind, out of scope here.",
    ),
    (
        "re-verify: {label} suite at {sha}",
        "phases/package.py:reverify",
        "Every other `PhaseStart` prefix is a phase name in bare caps; "
        "`re-verify` is lower-case with a hyphen and names a step inside "
        "PACKAGE re-running the gate suite, not a phase transition. Widening "
        "`LineLabel`'s casing for one call site would carry no more than a "
        "free string does.",
    ),
)
