---
id: b-76f08d
title: The `tests` gate reads a flag error anywhere in pytest's output, so `revert` skips every witness for a new CLI flag
status: done
tier: 1
filed: 2026-09-26
closed: 2026-09-26
by_hand: true
specs: []
prs: []
commits: [dfa1b5a8]
cites: [§5.4]
related: [b-66e82d, b-4a63b7]
---

## Problem

Found in the spec loop's run 18, 2026-09-26, reviewing #524 (`SA-0144`).

`.saffron/gates/tests.py:71` reports `error` when pytest's output holds the text
`error: unrecognized arguments`. Captured test output counts too. A witness that
calls `main([..., "--stack"])` prints that text when `revert` puts the source
back to base, because the flag does not exist there.

So `tests` returns `error` for the reverted run, and `revert` reads that as
`skip` ("the reverted run returned error and no readable verdict"). Both of
`SA-0144`'s witnesses fail at base, so the true verdict is `pass`. The cell's
gates printed `revert=skip` on the head, and nothing said why.

Every spec that adds a CLI flag gets a blind `revert`.

## Done looks like

- The check keys on pytest's own usage error, not on the substring in any
  captured output.
- A test drives a witness whose captured output holds the substring and whose
  reverted run fails, and `revert` reports `pass`.

## Record

- 2026-09-26: filed from the spec loop's run 18 (stack #531). The Spec seat
  reproduced the skip path by hand.
- 2026-09-26: fixed by hand in dfa1b5a8, since `.saffron/**` is protected. The
  gate keys on pytest's exit codes 3 and 4, and a witness fails on the old
  gate.
