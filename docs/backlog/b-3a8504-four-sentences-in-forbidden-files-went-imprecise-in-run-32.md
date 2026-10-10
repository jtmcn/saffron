---
id: b-3a8504
title: "Four sentences in files run 32's specs forbade say less than the code now does"
status: open
tier: 3
filed: 2026-10-09
specs: []
prs: [784, 785, 788]
commits: []
cites: []
related: []
---

## Problem

Found by the seats of #784, #785 and #788 in the spec loop's run 32. Each
spec forbade the file, so the seat left the line.

- `file_at`'s docstring says the unreadable shapes raise `GitError`
  (`saffron/repos/mirror.py:246`). They raise `UnreadablePath`, a subclass,
  which `SA-0238` now catches apart.
- `saffron/task.py:227` and `tests/test_package.py:197` say the seed fetches
  the default refspec. `SA-0237` names `refs/heads/*` in the seed, so both
  now read as if config chose the refspec.
- `tasks_by_repo`'s docstring says `spec_id` rides along "for a caller that
  wants to name the task" (`saffron/ledger.py:1061`). `reconcile` reads it to
  narrow rows.

## Done looks like

Each sentence names what the code does. No behaviour changes.

## Record

- 2026-10-09: filed from the spec loop's run 32.
