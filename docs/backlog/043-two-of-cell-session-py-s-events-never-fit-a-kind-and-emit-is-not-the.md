---
id: 43
title: Two of `cell/session.py`'s events never fit a kind, and `emit` is not the whole output seam
status: partial
tier: 2
specs: [SA-0029, SA-0030, SA-0031, SA-0041, SA-0042]
prs: []
commits: []
cites: []
related: []
---

## Problem

`SA-0030` migrated all 47 `watch(...)` call sites in `cell/session.py` to
`emit(<Event>)`, against `events.FAMILIES`. Two did not, by design —
`events.FINDINGS[0]` names them: the task's own terminal announcement
(`f"{outcome}: ${spent:.2f} spent, session {session_id}"`) and the rate-limit
rejection line. Neither `Terminal` (scoped to the five zero-commit IMPLEMENT
endings) nor `Budget` (a ceiling/value/limit triple) fits an arbitrary outcome
word and a session id without a tenth kind, which this spec's own out-of-scope
section forbids. Both stay direct `print()` calls in `_drive_cell`, which means
`events.jsonl` never carries them — `read_log` plus `describe` reproduces every
other printed line in order, but not these two. A future report reading
"what did this task's own log say happened" has to fall back to the ledger's
`tasks.state` for the outcome word, which is already there and already typed;
the gap is real but has a working substitute, which is presumably why `SA-0029`
scoped a tenth kind out from the start.

**The second half of that gap has no substitute and was not disclosed until
review found it: `emit` is no longer the supervisor's total output seam.**
Those two `print()` calls go to process stdout whatever the caller passed.
A caller supplying its own `emit` — which is exactly what `SA-0042` is
specified to do from `cli.py`, and what any batch or headless consumer would
do — still gets two lines it cannot redirect, and the one it most wants is the
task's own terminal announcement. Measured on `saffron/SA-0030`: driving
`run_one_cell(..., emit=seen.append)` without the test harness's
`session.print` double leaks `READY_FOR_REVIEW: $0.40 spent, session sess-1`
to stdout; at base, `watch=` captured 100% of output. Note the harness hides
this — `tests/test_session.py` patches `session.print` with `raising=False`,
so the double silently no-ops if those calls ever move. Done looks like the
tenth kind `SA-0029` scoped out, or an `emit`-shaped sink for lines no kind
carries; not a third `print`.

The eighth did not migrate, and it is the mirror image of
`events.FINDINGS[0]` above: `reverify`'s `"re-verify: {label} suite at {sha}"`
is `events.FINDINGS[1]`'s own named exception — no `PhaseStart` label fits a
lower-case, hyphenated step without widening `LineLabel`, which needs the
forbidden `events.py` — so it stays a direct, unconditional `print()`.

That leaves the second half of this item worse, not better, and review is what
said so. `session.py`'s two `print`s are untouched (forbidden here), and
`package.py` now adds a **third** — precisely the shape the done condition
above rules out. It is also a small regression in kind: before, a caller could
pass `package(watch=…)` and capture or silence the `re-verify:` line, and no
caller can redirect it now. Done is unchanged: the tenth kind, or an
`emit`-shaped sink for lines no kind carries. Three prints, not two.

**A tenth kind now exists, and it is not this one.** `saffron/task.py` added
`events.Ceilings` for the per-task ceilings line, so "the tenth kind
`SA-0029` scoped out" is no longer an unbuilt thing and this item's done
condition must not be read as met. The three prints above are a *terminal
announcement*, a *rate-limit rejection* and `reverify`'s `re-verify:` step;
`Ceilings` carries none of them, and none of the ten kinds does. What did change
is the precedent — `events.py` is no longer a file
nothing may add to, and the cost of adding a kind is now measured: the
dataclass, the union, `_KINDS`, one `describe` branch, one `FAMILIES` row,
two counts in `tests/test_events.py` and one render case.

Two stale docstrings for whoever takes that on, both in `session.py` and so
both unrepairable here. `_default_emit`'s says `cli.py` "never passes `emit`",
and `run_one_cell`'s says the default "lives here, not in `cli.py` (forbidden
to this spec)". `cli.py` is no longer forbidden, is the only production caller
of `run_one_cell`, and now builds exactly that fan-out — so the `emit is None`
branch is reached from tests alone.

## Done looks like

Done is
unchanged: an eleventh kind for the two `session.py` lines and a `LineLabel`
that fits a lower-case step, or an `emit`-shaped sink for lines no kind
carries.

## Record

**Closed by `SA-0041`, 2026-09-02.** `phases/implement.py`, `phases/review.py`
and `phases/rebut.py` were `forbidden` to `SA-0030` and called a plain
`watch(str)` with a line they had already fully formatted — `agent: `,
`agent: (raw) `, `REVIEW: ` or `REBUT: ` were the only four prefixes those
three files ever handed it. `session._phase_watch` recovered the event those
strings were always going to be by matching on that prefix and slicing it
off, which was correct only because no other prefix reached it. `SA-0041`
migrated those three files to construct `Agent`/`PhaseStart` events directly
and call `describe()` themselves — `implement.run_agent` gained a required
`spec_id` and now emits `Agent(event=<dict>)` at the point the cell's own
dict is still available, instead of flattening it to prose first — which is
what let `_phase_watch` itself, both constructions, be deleted outright.
`SA-0031`'s plan to migrate `cli.py`/`phases/package.py` in the same spec is
what died at 141 turns; `SA-0042` carries that half forward on its own, since
`package()` runs outside `run_one_cell` and never received the supervisor's
`emit` in the first place.

**The first half closed by `SA-0042`, 2026-09-02; the second half is still
open and this spec moved against it.** `cli.py` now builds one `emit` fan-out
— print plus a task-scoped `EventLog`, the same shape `session._default_emit`
already used — and hands the identical object to both `run_one_cell` and
`package()`, so PACKAGE's events finally reach `events.jsonl` too. **Seven** of
`package.py`'s eight `watch(str)` call sites and `cli._resolve_stacked_on`'s
two are now `emit(<Event>)`, against existing kinds and with no message change.
