---
id: b-5a69db
title: "A night stopped by SIGTERM or Ctrl-C closes `INFRASTRUCTURE`, which `CONTEXT.md` defines as the breaker firing"
status: open
tier: 3
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [65, b-5df2a7]
---

## Problem

Found by the Standards seat on #812 (`SA-0258`), in the spec loop's run 34.

`CONTEXT.md`'s **Batch stop reason** says `INFRASTRUCTURE` is the breaker
firing. It is the only reason that says the machine was wrong. A night an
operator stops also closes `INFRASTRUCTURE`. The `finally` in `run_batch`
writes it whenever nothing else closed the row (`saffron/batch.py:173-181`).
Ctrl-C reached that line before `SA-0258`, and SIGTERM reaches it now.
`DESIGN.md` §4.2.1 and `docs/HOST-HARDENING.md` say the same.

So a morning reading `INFRASTRUCTURE` cannot tell a broken machine from an
operator who stopped the night.

## Done looks like

Either `CONTEXT.md` widens `INFRASTRUCTURE` to cover a stopped night, or a
new stop reason names it. The vocabulary in `ontology/factory.ttl`, the
`StopReason` literal and the batch table's `CHECK` agree.

## Record

- 2026-10-11: filed from the spec loop's run 34 (#812).
