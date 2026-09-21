---
id: b-606ea3
title: '"Projection", "materialization", "emitter" and "checked walk" name SA-0107''s and SA-0108''s work and have no glossary entry'
status: done
closed: 2026-09-21
tier: 2
by_hand: true
filed: 2026-09-18
specs: [SA-0107, SA-0108]
prs: []
commits: [21488e89]
cites: [§4.6, §9]
related: [65, 72, b-946f03]
---

## Problem

Found 2026-09-18, writing `SA-0107`.

`SA-0107` creates `saffron/projection.py`, and `SA-0108` a command that
materializes it.
`DESIGN.md` §9 v2.5 and Appendix T call the whole the emitter. `SA-0108` adds
the checked walk and a `saffron chains` command. None of these terms is in
`CONTEXT.md`. `ontology/` is forbidden to the spec for the reason
`docs/agents/issue-tracker.md` gives, so the cell cannot add them.

## Done looks like

Each term the merged code uses has a `CONTEXT.md` entry rendered from
`ontology/factory.ttl`, or an `_Avoid_` line that points at the one it uses.
This is done by hand, because `CONTEXT.md` is `protected` and generated.

## Record

**Filed 2026-09-18** with `SA-0107`, as its vocabulary follow-up.
- 2026-09-21: Done by hand. `CONTEXT.md` §8 gains **Projection**, **Emitter** and **Checked walk**, and the **Emitter** entry defines materialize. The entries are hand-written, because `tests/ontology/test_no_dead_terms.py` rejects a vocabulary class no shape reads.
