---
id: 112
title: A name bound to a suppression passes `integrity`'s scan
status: done
tier: 1
closed: 2026-09-13
specs: [SA-0077]
prs: [232]
commits: []
cites: []
related: []
---

## Problem

**Status:** **done**, by hand, 2026-09-13, on
`joel/suppression-aliases-and-inline-ignores`. `structure` carries
`skip-is-spelled-in-full`, with no `files:` scope so a helper outside `tests/`
is read too, and ast-grep's inline ignore comment is a `suppressions` token (the
second half below). #241's review, and its fix, ran five more skips pytest
honours that no token named, each under pytest 9.1.1: unittest's skip
decorators, its skip exception and method, pytest's import-or-skip, and the skip
marker added by string. The first four are tokens now; the fifth cannot be one —
the word is a gate status — so the rule reads it. Left open: a name reached
dynamically — `__import__`, `sys.modules`, a module's `__dict__` — the rule's
`ponytail:`.

**Tier 1.** Found reviewing `SA-0077` (PR #232), 2026-09-12 — in the wild, not
by probe. The agent needed a legitimate skip in `tests/conftest.py`, found that
`integrity` refuses the call form of pytest's skip, and bound pytest's skip
function to a private name ahead of its one call, with a comment saying that was
why. `integrity` passed the diff (`3 changed files clean of suppression and
gate-config edits`); the same diff with the literal call fails
`added-suppression`. The scan (`saffron/gates/core/integrity.py:272`) matches
each `policy.yaml` token as a substring of each added line, so it reads a
spelling, not a call: the alias covers every later call of that name in the
file, and the same move works for the expected-failure marker and for pytest's
skip marker applied without the decorator's `@`.

The review commit spelled the call literally, by operator decision, so #232
carries a suppression a person approved. Re-run in a cell, it fails
`integrity`, which is the point.

**Tier 1, not 2,** because it is the question the tier's soundness half exists
for: a blocking gate reported `pass` on a diff whose own comment described
getting past it, and none of the three lenses raised it.

**Done looks like** the suppression tokens matched as what they resolve to
rather than as text — an ast-grep rule over `tests/**` flagging any reference to
pytest's skip or expected-failure objects, called or not, is the likely shape —
with a witness built from `SA-0077`'s own alias, run against the substring scan
to prove it passes there. `.saffron/**` is `protected`, so it lands by hand.

**Folded in, 2026-09-13: that rule would not have held either.** ast-grep
honours its own inline ignore comment in `scan` — on the matched line, on the
line above, and scoped to one rule id, all three measured at 0.45.3 — and `scan`
has no flag that turns it off; `--no-ignore` reaches ignore *files* only. The
comment was no `suppressions` token, so one comment disarmed any `structure`
rule, the four gated invariants included, and `integrity` passed the diff.
`structure` cannot refuse it itself, so the fix is the token, and there a
substring scan is the right reader: a comment has no name to bind.
