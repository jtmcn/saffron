---
id: 54
title: The drift test rides the `tests` gate, so the ledger cannot say which check failed
status: open
tier: 3
specs: []
prs: []
commits: []
cites: [§5.4]
related: []
---

## Problem

`tests/ontology/test_generated_surfaces_are_current.py` is what catches a
vocabulary that moved ahead of its derived surfaces. It is a pytest test, not a
`.saffron/gates/` executable, and that was chosen deliberately: it inherits its
`tool` field by execution (`pytest --version`), which a hand-written gate would
have to obtain itself (§5.4, Appendix H) — the exact hole Appendix H is about.

The cost is paid in the morning queue. An operator sees "some test failed" rather
than a named gate, and the distinction between "the code is wrong" and "the
generated documents are stale" is one the ledger cannot make.

## Done looks like

either a `.saffron/gates/` executable that runs the render and
obtains its own `tool` by executing something real, or a written decision that the
test is enough — with the reason, so the next reader does not re-litigate it. It
becomes worth doing the first night an operator misreads a stale-surface failure
as a code failure.
