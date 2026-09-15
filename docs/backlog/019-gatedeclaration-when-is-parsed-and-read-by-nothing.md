---
id: 19
title: '`GateDeclaration.when` is parsed and read by nothing'
status: open
tier: 3
specs: []
prs: [46]
commits: []
cites: [§5.4, §10]
related: [17]
---

## Problem

**Status:** open. Found while declaring Saffron's own `shacl` gate (PR #46).

`repos/policy.py` accepts `when: "**/*.ttl"` on a gate declaration and stores it;
`run_suite` runs every declared gate in declaration order and consults it nowhere.
The only reader in the tree is an assertion in `tests/test_policy.py` that the
field parses. `DESIGN.md` §5.4 illustrates the contract with a conditional gate
and §10 calls repo-defined gates "conditional on touched paths", so a reader
following the design writes a clause the loader accepts and nothing honours —
backlog item 17's shape (`size` built and nothing calling it), one layer out.

Saffron's own `shacl` gate is declared **without** `when` for exactly this reason:
a control that reads as present and is not is Appendix I's founding defect, and
validation is milliseconds so conditionality buys nothing here. That dodges the
trap and leaves it armed for the second repo, which is why this is written down.

**Done looks like** one of: `run_suite` filters on `when` against the diff's
changed paths and a test proves a non-matching gate does not run; or `load_policy`
rejects `when` outright until something reads it, and §5.4's illustration drops
it. §5.4 now says the field is unread — that note comes out with the fix.
