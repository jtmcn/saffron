---
id: b-ea1d13
title: The spec writer sizes the change after drafting it, and its step 3 names a check that cannot pass
status: open
filed: 2026-09-20
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [b-b69bb6, 157, 159]
---

## Problem

Filed 2026-09-20 from `SA-0113`, drafted by the `spec-writer` agent outside a
loop run. Two of the agent's six steps cost time in a way the agent file can
fix.

**Step 1 sizes the change, and the caller learns the answer last.** The step
reads "Scope the change, then size it". An estimate past the ceiling splits
into a parent and children. `SA-0113` came back as the parent of a split, and
that decision reached the caller in the final report, 35.7 minutes in. A caller
told at minute two can dispatch one writer per child instead.

**Step 3 names a check that cannot pass.** It reads "Done when
`uv run saffron queue --repo .` lists it as a candidate or refuses it only on
its parent". `saffron/cli.py:535-539` exports `.saffron/specs` from the mirror
at `base_sha`. An uncommitted spec is invisible to that command, so the step is
unreachable in the order the steps are written. The agent worked around it by
driving `build_queue` against the working tree, which is the call the step
wants.

## Done looks like

Step 1 reports the size estimate and the split decision to the caller before
drafting. It arrives as its own output, not as a line in the final report.
Step 3 names the working-tree `build_queue` call, or says the queue check waits
until the caller commits. Both are edits to `.claude/agents/spec-writer.md`.

## Record

- 2026-09-20: filed from `SA-0113`. `by_hand` because the file is the writer
  agent's own instruction surface. This repository's precedent is that a prompt
  or procedure edit is hand work, while a computed check gets a spec.
  Items 157, 158, b-4589be and b-865399 are all `by_hand` for the same reason,
  and `SA-0092` and `SA-0112` are the other side of it.
