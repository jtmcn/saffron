---
id: b-e0e720
title: "The `prose` gate reads no attribute docstring, so a field's own text escapes the word rules"
status: open
tier: 3
filed: 2026-11-23
specs: []
prs: []
commits: []
cites: []
related: [b-440f17]
---

## Problem

Found by the Standards seat on `SA-0426` (#1308), in the spec loop's run 84.

`.saffron/gates/prose.py` reads a docstring only from the nodes in
`_DOCUMENTED`: a module, a function and a class. A bare string under a field
assignment is none of them. So the new docstring on `Failure.detail` carried
an em-dash, and no gate saw it. The seat found it by hand.

b-440f17 closed the same gap for Python comments and for the other docstrings.

## Done looks like

The `prose` gate judges a string literal that follows an assignment in a class
body as a docstring. A test seeds one with an em-dash and sees it reported.

## Record

- 2026-11-23: filed from the spec loop's run 84.
