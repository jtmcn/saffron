---
id: b-00534f
title: "`qualify` reads an unreadable mirror path as an absent one"
status: done
tier: 2
filed: 2026-09-30
closed: 2026-10-09
specs: [SA-0238]
prs: [785]
commits: []
cites: []
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 23, 2026-09-30, by #610's Standards seat.

`saffron/qualify.py:63-67` defines `_read_head`, which wraps
`mirror.file_at` and returns `None` on any `GitError`. `file_at` returns
`None` only for an absent path. Its docstring says "absent is an answer,
unreadable is not" (`saffron/repos/mirror.py:246-247`). `UnreadablePath` is a
`GitError`, and so is a failed git call. Each becomes an absent file, which
then feeds `anchor(read_head=...)`.

`SA-0161` (#610) carried a byte-for-byte copy into `saffron/follow_up.py`.
#610's review removed that copy, so a read error there now propagates.
`qualify.py` was forbidden to that spec.

`error` is not `fail`. A broken read must not be filed as a decision about
the finding.

## Done looks like

`qualify` lets a mirror read's `GitError` propagate. A test drives an
`UnreadablePath` through it and sees the raise.

## Record

- 2026-09-30: filed from the spec loop's run 23.
- 2026-10-07: specced as `SA-0238`. `qualify` lets a mirror read error
  propagate, and the follow-up adapter reports it as one stopped line.
- 2026-10-09: done by `SA-0238` (#785) in the spec loop's run 32. `qualify`
  raises on a read the mirror cannot answer and records nothing for it.
