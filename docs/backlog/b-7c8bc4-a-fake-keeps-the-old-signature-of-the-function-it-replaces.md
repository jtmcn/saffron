---
id: b-7c8bc4
title: A fake keeps the old parameter order of the function it replaces, so a revert to the old call passes
status: open
tier: 2
filed: 2026-10-13
specs: [SA-0271]
prs: [868]
commits: []
cites: [§5.5]
related: [b-20043f]
---

## Problem

Found by the Standards seat on #868 in the spec loop's run 37.

`SA-0271` moved `gateway` ahead of `ports` in
`preflight.assert_host_is_unreachable`. The spec told each fake to follow.
Three fakes in `tests/test_session.py` and `tests/test_cli.py` kept the old
order. A revert of `session.py`'s call to the old positional form passed every
test, though the real function then swaps the two. The delegate
reordered the fakes, and the same revert then failed two tests.

The same pull request held a second shape. Two `cell` fixtures discarded the
subnet `allocate_network` returned and re-derived the pool's first /24, with
a comment that reasoned nothing else would hold it. In-cell REVIEW raised
neither.

## Done looks like

The adequacy lens names a fake whose parameters differ from its target's. It
also names a fixture that drops a value its own call returned.
A host check that compares each `monkeypatch.setattr` fake's signature with
its target's would decide the first without a model.

## Record

- 2026-10-13: filed from the spec loop's run 37. Both were fixed in review on
  #868.
