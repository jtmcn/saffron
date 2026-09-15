---
id: 10
title: Small, measured, cheap
status: partial
tier: 3
specs: [SA-0002]
prs: []
commits: []
cites: [§5.1]
related: []
---

## Problem

**Status:** **done bar one bullet.** Three of the four carry their own dated
closures below. The open one is `implement.md` doing double duty — it still
emits a plan block when told to implement, and `session.py:391` still always
sends `PLAN_PROMPT` first, so it stays harmless and stays untidy.

- `rebut.py` numbers blockers from 0 in the prompt. **Done, 2026-08-21:**
  numbered from 1 in both places they are produced. Not cosmetic —
  `run_verdict` requires the verdict set to match the blockers exactly, so a
  critic answering "1." for the first of one blocker failed the check, and
  the phase discarded both lens sessions, both rebuttal turns and every
  verdict session over the numbering.
- `implement.md` is non-deterministic on the first turn — 2 of 3 live sessions
  emitted a plan block when told to implement. Harmless today because
  `session.py` always sends `PLAN_PROMPT` first, but the template is doing double
  duty.
- `uv run` inside a cell rebuilds and reinstalls the project on every invocation,
  and would fail outright if it ever needed the network — the proxy allows one
  host. Agents work around it with `python -m`, at the cost of a turn.
  **Done, 2026-08-24.** It does need the network, and the cost is three turns,
  not one: `SA-0002`'s implementer took four `403`s from the proxy on
  `pypi.org` before reaching `python3 -m pytest`. `UV_NO_SYNC=1` in
  `.saffron/Dockerfile` runs it out of the venv the image already baked. The
  general form is an onboarding requirement rather than a Saffron fix, and
  §5.1 now carries it: a repo's image pins its runner to the baked
  environment, because the workaround leaves the run green and bills the
  difference to the task.
- `image_exists` was deleted as dead; if PACKAGE wants a stale-image check it
  comes back.
