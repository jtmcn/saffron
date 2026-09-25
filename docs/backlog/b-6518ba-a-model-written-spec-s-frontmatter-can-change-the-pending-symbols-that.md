---
id: b-6518ba
title: A model-written spec's frontmatter can change the pending_symbols that silence the dead gate
status: open
tier: 3
filed: 2026-09-25
closed:
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-792ab2]
---

## Problem

`SA-0167`'s finishing suite lets the host's commit touch
`.saffron/specs/*.md` with no protected list. A revised or follow-up spec
text is written by a model. Its frontmatter can add `pending_symbols`, which
`.saffron/gates/dead.py:113-126` reads to defer `dead` failures in later
cells. `gate_config` routes a `.saffron/**` edit to a person
(`.saffron/policy.yaml:127`), but the finish exempts the spec directory. The
operator's read of the finishing diff before merge is the only check.

## Done looks like

Gate 0 refuses a recorded spec text whose `pending_symbols` differ from its queued file's, or the finish flags the change.

## Record

- 2026-09-25: filed from the spec reviews of `b-792ab2`'s last build specs.
