---
id: b-52e670
title: "A SIGTERM during a silent agent turn waits for the turn to end"
status: open
tier: 2
filed: 2026-10-10
specs: []
prs: []
commits: []
cites: [§4.3]
related: [b-5df2a7]
---

## Problem

Measured on macOS while `SA-0245` and `SA-0258` were written, 2026-10-10.
Those specs make SIGTERM raise `KeyboardInterrupt`, so a stopped cell tears
down. A stop that lands during a silent agent turn still waits for the turn.

The turn runs in `exec_stream` (`saffron/cell/runtime.py:492`). A daemon
thread, `_pump`, reads the exec process's stdout line by line
(`runtime.py:540-546`). The main thread waits on a queue inside
`with proc:` (`runtime.py:550`).

- The handler ran 0.51 seconds after the signal, in the main thread.
- The unwind then reached `Popen.__exit__`, which closes stdout first.
- That close blocked on the buffer lock the `_pump` thread held in
  `readline`. It waited until the child exited.

`SA-0258`'s second reviewer reproduced it apart from the prototype. The parent
read a piped child on a thread, and the child printed nothing for six seconds.
The parent unwound only when the child exited, at 6.0 seconds, under CPython
3.12.12.

An agent turn is silent while the model thinks or a tool runs, which is most
of its wall time. So a stop can wait minutes. Under launchd, a stop that
outlasts the exit timeout becomes a SIGKILL, and a SIGKILL skips the teardown
both specs add. Linux is unmeasured, but the host process runs on macOS.

## Done looks like

A SIGTERM during a silent turn unwinds within a stated bound, and the
teardown still runs. One way is to end the exec process before the pipe is
closed. Another is to never close a pipe another thread is reading. A witness
drives a piped child that prints nothing and outlives the bound.

## Record

- 2026-10-10: filed from writing `SA-0245` and `SA-0258`, which name it out of
  scope.
