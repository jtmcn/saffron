"""Saffron's own event vocabulary — the host side of DESIGN.md §4.1.

`agent_runner.py` already does this one level down: it emits Saffron's own
typed events as JSON lines out of the cell, and `implement._consume` renders
them for the operator. Host-side the arrangement is inverted — 64 call sites
across `cell/session.py`, `phases/*.py` and `cli.py` author prose straight into
`watch()`, and the structure behind each line dies with the terminal scroll.

This module is the fix, and only the fix's first half: nine frozen dataclasses
— one per kind, never one class with a `type` string, so a future renderer
knows what it holds — an `Event` union naming all nine, and a tiny durable log.
Nothing here emits an `Event`; `SA-0030`/`SA-0031` migrate the call sites, and
`SA-0040` writes the renderer that turns these back into the prose above.

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
import typing
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Literal

from saffron.gates.contract import GateStatus

# CONTEXT.md is the authority and it names six: DIAGNOSE, IMPLEMENT,
# GATE <-> REPAIR, REVIEW, REBUT, PACKAGE. Imported nowhere from because the
# gate contract does not model phases; restated here, deliberately, as the only
# place the host's own event vocabulary needs them.
Phase = Literal["DIAGNOSE", "IMPLEMENT", "GATE", "REPAIR", "REVIEW", "REBUT", "PACKAGE"]

# The prefix a progress line actually carries, which is *not* the same set.
# `PLAN:` and `SALVAGE:` both print from inside IMPLEMENT and `SCOPE:` from
# inside DIAGNOSE, so labelling them phases would restate in code exactly the
# conflation CONTEXT.md exists to prevent — it lists "PLAN" on the plan
# checkpoint's own _Avoid_ line and says the checkpoint is deliberately not a
# phase. Both fields are carried: the phase for anything grouping by it, the
# label so `SA-0040` can reproduce the line verbatim.
LineLabel = Literal[
    "SCOPE", "PLAN", "IMPLEMENT", "SALVAGE", "REPAIR", "REVIEW", "REBUT", "PACKAGE"
]

Ceiling = Literal["budget_usd", "max_attempts", "max_turns"]

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
class Baseline:
    """The baseline gate suite finished. `aborted` names the gates that
    errored against `base_sha` — non-empty means the toolchain is broken and
    the task never reaches an agent (PREFLIGHT_FAILED)."""

    timestamp: float
    spec_id: str
    aborted: tuple[str, ...] = ()


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
    """One numbered execution that produced at least one commit and let the
    run continue — the GATE ⇄ REPAIR loop's own numbered attempt
    (`new_failures`/`decision` set), or an IMPLEMENT/SALVAGE turn that landed
    commits (left `None`). Cut off *and recovered* is this, not `Terminal`:
    that branch has commits and the run goes on."""

    timestamp: float
    spec_id: str
    attempt: int
    commits: int
    spent_usd: float
    new_failures: int | None = None
    decision: Literal["green", "no-progress", "exhausted", "repair"] | None = None


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
    # `None`, not `0` — the same absence-vs-zero rule `Attempt.new_failures`
    # already follows. A `skip` or `error` never had a count computed, and a
    # renderer that cannot tell that from a verified zero reports "0 new
    # failures" for a gate that never ran. That is `tool`'s defect (§5.4,
    # Appendix H) one layer out.
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
    stream. Exactly one of three shapes: `event` — a parsed cell event,
    verbatim, under one key, never re-typed (no Agent SDK type is imported
    here or anywhere outside `agent_runner.py`); `line` — a raw line that was
    not an event at all, from a process sharing the runner's stdout inside an
    untrusted cell, quarantined by `raw=True` rather than dropped; or
    `detail` — a host-authored fact with no cell event behind it at all (a
    reap outcome, a pipe closing). `raw` is the field that must survive the
    log: a raw line that loses its flag on round-trip is a quarantine that
    stopped being one."""

    timestamp: float
    spec_id: str
    raw: bool
    event: dict | None = None
    line: str | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class Terminal:
    """One of the five ways an IMPLEMENT turn ends with zero commits — the
    supervisor separates five, and a `cut_off: bool` would re-collapse exactly
    what SA-0028 pulled apart. `subtype`/`terminal_reason` are only meaningful
    on `ended_without_finishing`, where the runtime's own reason is what makes
    "an idle bound", "a provider wall" and "a crash" distinguishable at all.
    `detail` carries the rejection text on `plan_rejected` or a failure note
    on the salvage branches."""

    timestamp: float
    spec_id: str
    reason: TerminalReason
    spent_usd: float
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
    | Baseline
    | PhaseStart
    | Attempt
    | GateResult
    | Budget
    | Agent
    | Terminal
    | Teardown
)

_KINDS: dict[str, type] = {
    cls.__name__: cls
    for cls in (
        Preflight,
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

    def append(self, event: Event) -> None:
        """Write one line, flushed. Never raises: a cell that cannot write its
        own log is not a cell whose task should die on that account — the
        caller has nothing useful to do with the failure either way."""
        payload = {"kind": type(event).__name__, **asdict(event)}
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a") as handle:
                handle.write(json.dumps(payload) + "\n")
                handle.flush()
        except (OSError, TypeError, ValueError):
            # Not only OSError: `Agent.event` carries a cell-authored dict
            # verbatim, so a value that is not JSON-serialisable raises
            # TypeError from `json.dumps` and would cross the boundary this
            # method's whole contract is that nothing crosses. Untrusted input
            # reaching a host-side writer is exactly the case to swallow.
            return


def read_log(task_dir: Path) -> list[Event]:
    """Read back every whole event `EventLog` wrote for one task.

    Per-line tolerance, never a whole-file discard — the rule
    `saffron.report.index._existing_queue_rows` already applies, named there
    in a `ponytail:`. A line that fails to parse as JSON, is not an object, or
    is missing (or names an unknown) `kind`, or does not match its own kind's
    fields, is dropped in silence: this is what turns a truncated final line
    (the write a killed cell left mid-object) and a `kind` from a newer
    Saffron into "the earlier events survive" rather than a raised error.
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
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        cls = _KINDS.get(obj.pop("kind", None))
        if cls is None:
            continue
        expected = {f.name for f in fields(cls)}
        if set(obj) - expected:
            continue
        # JSON has no tuple, so a field declared `tuple[str, ...]` (Baseline's
        # `aborted`) comes back a list; coerced here rather than loosened on
        # the dataclass, or a round-trip's equality check reads a real
        # difference where the wire format has none.
        hints = typing.get_type_hints(cls)
        for name, value in list(obj.items()):
            if isinstance(value, list) and typing.get_origin(hints.get(name)) is tuple:
                obj[name] = tuple(value)
        try:
            events.append(cls(**obj))
        except TypeError:
            continue
    return events
