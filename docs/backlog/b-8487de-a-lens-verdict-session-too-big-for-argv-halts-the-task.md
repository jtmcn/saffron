---
id: b-8487de
title: A lens's verdict session gets its prompt through argv, so a large diff halts the task at `REBUTTING` instead of reporting `error`
status: done
tier: 1
filed: 2026-09-23
closed: 2026-09-23
specs: [SA-0140]
prs: [498, 501]
commits: []
cites: [§5.5, §5.6]
related: [b-19b255]
---

## Problem

Found in the spec loop's run 15, 2026-09-23, on `SA-0128` (#483).

The adequacy lens raised a blocker. REBUT fixed it and moved HEAD. The lens's
re-judge session then failed to start:
`CLIConnectionError: Failed to start Claude Code: [Errno 7] Argument list too
long` (`rebuttal.json`, `verdicts[0].error`). The patch was 40 KB. The task was
left `REBUTTING` with `$19.75` of `$24` spent, and PACKAGE pushed the branch
with no pull request. The driver recorded a halt, the operator's call.

Two defects meet here. The prompt reaches the agent SDK through the process's
argument list, which the OS caps. A verdict session that never ran is an
infrastructure failure, charged to nobody. It still left the task in an
in-flight state rather than `error`. The Spec seat later judged the rebuttal
by hand and found it held.

## Done looks like

The verdict session's prompt reaches the runner by stdin or a file, and a
patch of at least 200 KB re-judges without error. A verdict session that fails
to start ends the attempt as `error` and names the lens. It never leaves an
in-flight state the driver must call a halt.

## Record

- 2026-09-23: filed from the spec loop's run 15 (#483).
- 2026-09-23: `SA-0140` reached `READY_FOR_REVIEW` as #501 at $12.08 of $20,
  in the spec loop's run 16, and merged ahead of the loop's other cells. A
  system prompt now reaches the agent CLI as a file. `SA-0140` retires to
  `done/`.
