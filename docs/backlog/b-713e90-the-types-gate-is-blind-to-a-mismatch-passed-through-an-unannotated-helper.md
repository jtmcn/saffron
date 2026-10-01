---
id: b-713e90
title: The `types` gate passes a type mismatch routed through an unannotated helper, and no token marks it
status: done
tier: 3
filed: 2026-09-28
closed: 2026-09-30
by_hand: true
specs: []
prs: []
commits: [9ef9e7b2, f7111df9]
cites: [§5.4]
related: [39, 112]
---

## Problem

Found in the spec loop's run 20, 2026-09-28, by #565's seats (`SA-0160`).

`SA-0160`'s spec asked for a rate-limit reset of `"soon"`, a `str` where the
field is `int | None`. The cell wrapped it in an unannotated identity. With the
literal in place, `ty check tests/test_cli.py` reported `invalid-argument-type`.
Wrapped, it passed.

Review routed it through one unannotated `_turn` helper
(`tests/test_cli.py:5052-5056` at `6fc23834`, used at `:5088`). That matches
`_attempt` (`tests/test_spec_review.py:26`). The operator accepted that one
pattern and asked for the hole to be filed. `integrity` reads suppression
tokens, and an unannotated helper carries none.

## Done looks like

A deliberate ill-typed test value carries a token `integrity` can read, or a
structure rule names the unannotated-helper pattern. A test holds the wrapped
`"soon"` failing `types` without the token.

## Record

- 2026-09-28: filed from the spec loop's run 20.
- 2026-09-30: structure rule `no-unannotated-identity` names the cell's
  wrapper: a def, an applied lambda or a named lambda that hands its one
  argument back, a docstring beside it or not. It has
  zero hits on the tree. An unannotated helper that forwards into a typed call
  stays unnamed, since 241 test helpers do that on purpose.
  The rule makes `structure` fail on the wrapped value, not `types`.
