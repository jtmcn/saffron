---
id: 4
title: Three of five supervisor bounds are missing
status: done
tier: null
closed: 2026-08-20
specs: []
prs: []
commits: [293f558]
cites: [§4.3]
related: []
---

## Problem

§4.3 wants turns, spend, idle, completion and wall clock. v0.5 has turns, spend
(host-side, per task) and a wall clock on `exec_stream`. **Idle and completion do
not exist**, and the wall clock defaults to 3600s that `run_one_cell` never
overrides — so an "attended" operator can watch nothing happen for an hour.

§4.3 is emphatic that splitting idle from completion matters: silence *before* an
agent claims to be done is a stall, silence *after* is a lingering child process,
and collapsing them makes a finished agent burn the full idle timeout and then
read as a failure.

## Done looks like

all five, and a default wall clock an operator would
actually sit through.

## Record

**Status:** **done**. All five bounds are present. Idle and completion landed
in `293f558` (*feat(cell): the two bounds that make silence mean something*) as
`runtime.IDLE_TIMEOUT_S` (300s) and `runtime.COMPLETION_TIMEOUT_S` (10s), and
`Completed.bound` names which of the three ended a read loop rather than
collapsing them into one flag. The wall clock is no longer the unoverridden
3600s this item was written about: `session.py:1115` passes `TURN_TIMEOUT_S`
(900s), and idle catches a stall five minutes in either way.

**Done, 2026-08-20.** All five. `exec_stream` reads through a queue fed by a
reader thread, so every wait carries a deadline: `idle_s` (300s) before the
payload signals done, `completion_s` (10s) after it, and `timeout_s` for a turn
that keeps producing and never stops. `session.TURN_TIMEOUT_S` is 900s and is
bound onto the agent callable once, so plan, implement, repair, review and
rebuttal all carry it rather than inheriting the library's hour.

The split is load-bearing and is what the returned value now records.
`Completed.bound` names which bound fired; an idle or wall-clock expiry kills
and reports 124, a **completion window close reports 0 and is a success** — the
runner emitted its result and only a child was holding stdout open. `run_agent`
propagates it as `AttemptResult.bound` and its failure message names the bound
instead of saying "timed out" for all three. The done signal comes from
`run_agent` returning true out of `on_line`, not from the runtime parsing
events: the container seam does not know Saffron's schema.

Threads over `selectors`, measured against the alternative rather than
preferred: readiness on the fd is not a line, so a half-written one still
blocks `readline` and the fix is reimplementing line splitting over `os.read`.

**Amended 2026-08-21: one of the five was not bounding, and a bound firing
kills less than it looks like.** Two defects in the above, both measured.

The completion window was recomputed as `now + completion_s` at the top of
every loop iteration, and the `signalled` branch short-circuits the wall clock
— so every line a child wrote pushed the deadline out again and nothing else
applied. A child writing steadily after the result event held `exec_stream`
open forever: an unbounded wait, inside the function whose five bounds exist so
that no wait is unbounded. The window is now fixed once, when the result event
lands, and a chatty child cannot move it.

And the kill does not reach the cell. Measured against a real `container` — a
detached container, a long `container exec`, `proc.kill()` on the host side,
then a look at `/proc` from inside — the process is still there. Killing the
exec client kills the client. So an idle or wall kill left the agent running in
the cell while the driver went on to measure `commits_ahead`, run the whole
gate suite and resume the session, all in that same container, with an
abandoned agent still able to edit `/work` and commit underneath every one of
them. `runtime.reap_cell` now kills everything but PID 1 on those two bounds —
never on the completion window, which is a turn that finished. Measured again
after: the abandoned process is gone, `sleep infinity` survives, and the cell
still takes the next exec.
