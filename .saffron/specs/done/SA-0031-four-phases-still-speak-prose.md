---
id: SA-0031
title: four phase modules still speak prose to a supervisor that speaks events
type: refactor
priority: 1
depends_on:
  - SA-0030
touches:
  - saffron/phases/implement.py
  - saffron/phases/package.py
  - saffron/phases/rebut.py
  - saffron/phases/review.py
  - saffron/cli.py
  - saffron/cell/session.py
  - tests/test_session.py
  - tests/test_events.py
  - tests/test_implement.py
  - tests/test_package.py
  - tests/test_package_cell.py
  - tests/test_rebut.py
  - tests/test_review.py
  - tests/test_agent_runner.py
  - tests/test_cli.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - tests/fixtures/watch-golden.txt
  - saffron/ledger.py
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/events.py
  - images/**
budget_usd: 18
max_attempts: 4
max_turns: 140
risk: elevated
---

## Status: superseded

Ran 2026-09-01 and ended `EXHAUSTED` at 141 turns of 140 and $19.17 of an
$18.00 budget, with six commits, red gates and no branch pushed. Superseded by
`SA-0041` (the agent stream and the supervisor's adapter) and `SA-0042`
(PACKAGE's events and the `cli.py` fan-out). Its exported patch is at
`~/.saffron/batches/v0/SA-0031/patch.diff` — 1174 lines, incomplete, applies
cleanly to `saffron/SA-0030` and leaves 15 failures. Kept as evidence for
`docs/superpowers/specs/2026-09-01-splitting-a-too-wide-spec-design.md`,
not as work to pick up.

## Context
`SA-0030` migrated the supervisor and left an adapter at the phase boundary:
`phases/` still receives a string-taking callable. **Fifteen `watch(...)` call
sites remain**, re-measured against `main` on 2026-09-01: `implement.py` **5**
(the agent stream and its raw-line quarantine), `package.py` **8** (re-verify,
conflict, refusal-to-push, the pull request URL), `rebut.py` **1**,
`review.py` **1**.

An earlier cut of this spec said thirty-three, split 8/11/9/5. It was wrong on
both the total and every part, and the correction matters because this number
*is* the spec's stated scope. The larger figures come from counting every
`watch` **token** — parameter declarations and `watch=watch` pass-throughs
included — which measures 6/12/14/7 and totals 39, not 33. `rebut.py` and
`review.py` have **one call site each**; the other tokens in those files are
the parameter and its forwarding. Renaming the parameter still touches all of
them, so the *edit* is wider than fifteen lines — but the migration proper is
fifteen sites, and a spec that promises thirty-three invites an agent to go
looking for eighteen that do not exist.

**And two more in `saffron/cli.py`, which this plan said would never be
touched.** `_resolve_stacked_on` takes `watch=print` and calls it twice, added
by `256e529` — a review fix on `SA-0026`, landed the day the design was
written, on a spec whose own `touches` named no `watch`. It is the last
`watch` outside `phases/`, so it is this spec's or nobody's.

`implement.py` is the interesting one. It already holds `_describe`, written
for the **cell's** events, and calls `watch(_describe(event))`. `SA-0040`
shipped a host-side `describe` alongside `_describe_agent_event`, a deliberate
copy of `implement._describe`, and a parity test asserting the two agree over
eleven event shapes. Two functions render events and only one should survive;
the parity test is what makes deleting the other safe, and it is the test that
must go with it.

**There is a second, unrelated `_describe` and it must not be touched.**
`review.py` defines `_describe(review: LensReview) -> str`, which renders a
lens review and has nothing to do with events. `grep -rn _describe saffron/`
returns both; only `implement.py`'s — the one taking an event `dict` — is this
spec's.

## Problem
- **The adapter is a seam with no owner.** It exists so `SA-0030` could land
  without touching four more files, and it is dead weight the moment those
  files move.
- **Two `describe` implementations will drift.** The host and the cell
  rendering the same event two ways is exactly the divergence structure-first
  exists to prevent. `SA-0040` already found one such drift — `_when(None)`
  returning `"unknown"` where the original reads `None` as *now* — in a copy
  whose docstring claimed to be identical.
- **PACKAGE's lines are the ones an unattended morning needs most** — a refused
  push, a conflict with the default branch, new failures against `main` — and
  they are strings.
- **The adapter and eight keyword sites live in `saffron/cell/session.py`.**
  Re-counted against `saffron/SA-0030` after that cell ran: `_drive_cell`
  (**4**), `plan_checkpoint` (**3**), `_repair` (**1**). It was eleven before,
  spread `_drive_cell` 6 / `plan_checkpoint` 3 / `run_one_cell` 1 / `_repair`
  1 — `SA-0030` consolidated three of them away, which is why this spec cites
  symbols and not the line numbers an earlier cut carried. `SA-0030` built
  **two** adapters, not one: `_phase_watch` is constructed separately inside
  `plan_checkpoint` and again in `_drive_cell` as `to_watch`. Both go. The
  adapter can live nowhere else, and renaming the phases' parameter forces
  edits there, so the file is in `touches` — an earlier cut of this spec
  `forbid` it and was unrunnable.
- **PACKAGE's events cannot reach the log while `emit` is built inside
  `run_one_cell`.** `package()` is called from `saffron/cli.py`, *outside*
  `run_one_cell`, so its eight call sites would fall back to `print` and none
  of the lines an unattended morning most needs would be recorded.
- **Seven test files call a migrated function with `watch=`**, re-measured
  2026-09-01 — `test_implement.py` (21 sites), `test_package.py` (7),
  `test_cli.py` (**7**, on `_resolve_stacked_on`), `test_package_cell.py` (2),
  `test_rebut.py` (1), `test_review.py` (1), `test_agent_runner.py` (1) — and
  `tests` is blocking. They are in `touches` because a migration that cannot
  repair its callers' tests cannot pass its own gates. `tests/test_session.py`
  carries a further 18 and is `SA-0030`'s; whatever that spec left there is
  what this one inherits.

## Acceptance criteria
- [ ] Every `watch(...)` in the four phase modules **and in
      `cli._resolve_stacked_on`** is an `emit(<Event>)`, and no signature in
      `saffron/` still carries a `watch` parameter — a test greps the package
      and asserts none remains. `saffron/cli.py` is in `touches` precisely so
      this criterion can be discharged rather than worked around
- [ ] **`saffron/cli.py` constructs the `emit` fan-out once and passes it to
      both `run_one_cell` and `package()`**, so a task's PACKAGE events land in
      the same `events.jsonl` as the rest of its run. A test drives a task
      through PACKAGE and asserts the pull-request line is in the log, not only
      on the terminal
- [ ] `run_one_cell` **keeps a working default** for callers that pass no
      `emit` — the one `SA-0030` built — and a test calls it with none and
      asserts it still prints. Hoisting a fan-out in `cli.py` must not make the
      supervisor uncallable without one
- [ ] The keyword call sites in `saffron/cell/session.py` pass `emit` instead,
      and **both** `_phase_watch` constructions go — `plan_checkpoint`'s and
      `_drive_cell`'s `to_watch`. Count them yourself: it was eleven before
      `SA-0030` and eight after, and it may move again
- [ ] The seven test files in `touches` are migrated with their callees and the
      suite is green — no `watch=` remains anywhere under `tests/`
- [ ] The adapter `SA-0030` left at the phase boundary is **deleted**
- [ ] **The terminal output does not change**, asserted against
      `tests/fixtures/watch-golden.txt` as in `SA-0030`. That file is
      `forbidden` here for the reason it was there: a repair loop's cheapest
      escape from a failing golden assertion is to re-capture the recording,
      and `SA-0024` makes editing it a gate failure rather than a broken
      promise. The harness in `tests/test_session.py` is fair game; the
      recording is not
- [ ] `implement.py`'s `_describe` is gone and its behaviour is served by
      `events.describe`; a test asserts a cell event renders identically to
      the line `_describe` produced. `SA-0040`'s parity test in
      `tests/test_events.py` is that assertion's ancestor and must be retired
      *with* the function rather than left importing a symbol that no longer
      exists
- [ ] **`Agent.event` carries the parsed cell event again.** `SA-0030`'s
      contract lens raised this as a concern and it is correct: `_phase_watch`
      receives a string `implement._consume` has *already* rendered with
      `_describe`, so every per-turn agent line lands in `Agent.detail` as
      opaque prose and `Agent.event` is permanently `None` — the opposite of
      what `events.Agent`'s docstring promises, which reserves `detail` for a
      host-authored fact with no cell event behind it. The dict cannot be
      recovered downstream of `_describe`, which is why this is `SA-0031`'s to
      fix and not `SA-0030`'s: emit `Agent(event=...)` at the call site in
      `implement.py`. A test asserts a driven agent turn leaves a log entry
      whose `event` is the dict, not its rendering
- [ ] An `Agent` event wraps the cell's event dict verbatim, and the
      `agent: (raw)` path — a line that is not an event, from a process sharing
      the runner's stdout — is still shown to the operator and still never
      parsed as one
- [ ] A test asserts an unknown cell event kind reaches the log and the
      terminal without raising
- [ ] Every new test runs with no network and no cell, and the golden-output
      test is **not** `cell`-marked, for the reason `SA-0030` gives: `addopts`
      would exclude it and the migration would verify against a skipped
      assertion. **Two of the seven test files in `touches` are cell-marked,
      not one** — `tests/test_package_cell.py` and `tests/test_agent_runner.py`
      — so their `watch=` sites are excluded from `make check` and the suite
      will not catch a migration that breaks them. Migrate both, run
      `uv run pytest -m cell` against them explicitly, and say in the pull
      request body that you did. Nothing new joins them

## Out of scope
**Everything in `saffron/cell/session.py` except the adapter and the eleven
call sites that feed it.** `SA-0030` migrated that file's own `watch` lines and
this spec must not revisit them. It is in `touches` to *delete the adapter*,
nothing more — the rest of `saffron/cell/**` stays `forbidden`.

**Everything in `saffron/cli.py` except `_resolve_stacked_on`'s three lines and
the `emit` fan-out.** The file is in `touches` to finish the seam, not to be
refactored. `SA-0026` and `SA-0027` have both merged, so nothing is racing for
it — which is exactly why a wider edit here would be unforced.

**Changing any message**, for the reason `SA-0030` gives.

**The scheduler and `reconcile`.** Neither has a `watch` today.

**Any renderer.** Part 3.

## Notes for the agent
**Delete `_describe`; do not leave it wrapping the new one.** A one-line
delegation is how two renderers survive a refactor meant to end them.

**`cli.py` is in `touches`, and the design document says it never would be.**
That claim was true when the design was written and false one commit later.
Where the two disagree, the code is the authority: `grep -rn watch
saffron/cli.py` settles it, and this spec was cut after that grep was run.

**Hoisting the fan-out into `cli.py` reverses a constraint this plan argued
for, deliberately.** The design's reason for keeping the seam out of `cli.py`
was a collision with in-flight stacking work, and that expired when `SA-0026`
merged. The reason it now has to move is structural and does not expire:
PACKAGE runs outside `run_one_cell`, so a fan-out built inside the supervisor
can never see it. Building it one level up is the smaller of the two changes —
the alternative is moving PACKAGE inside `run_one_cell`, which is a different
spec and probably a worse design.

**`implement.py`'s raw-line branch is a security boundary, not a formatting
case.** A line that is not JSON came from a process sharing the runner's
stdout inside an untrusted cell. It is shown, truncated, and never read as an
event. Preserve that exactly.

**`package.py` runs after the money is spent.** Its events are what an
unattended morning reads about a task that got all the way to PACKAGE and
still produced nothing mergeable. Do not economise on them.

**Read `SA-0030`'s diff before planning.** Every figure above was measured
before it ran. The fifteen phase call sites and the two in `cli.py` are in
files `SA-0030` was forbidden to touch and cannot have moved; the eleven
keyword sites and the adapter are in a file it rewrote, so find them by symbol
and re-count rather than trusting the number.

Commit after each coherent step. Uncommitted work dies with the cell.
