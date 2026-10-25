---
id: b-f4eb52
title: The `terms` gate flags an avoided word used to rule it out, so it fails at base on `Never a ticket`
status: open
tier: 3
filed: 2026-09-23
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-440f17, b-8220e6]
---

## Problem

Found in the spec loop's run 15, 2026-09-22.

Every cell of run 15 had `terms=fail` in its baseline, and earlier runs had
`terms=pass`. The one hit is `saffron/intake.py:133`: `The unit of work. Never
a ticket, an issue, or a prompt.` That line names the avoided words to exclude
them, which is what `CONTEXT.md`'s own _Avoid_ lines do. The gate is advisory,
so nothing blocked. But a base failure that every cell inherits hides a new
hit in the same file behind baseline subtraction.

## Done looks like

`main` reports `terms=pass`, either by exempting a line that names avoided
words to rule them out or by rewording `intake.py:133`.

## Record

- 2026-09-23: filed from the spec loop's run 15.
- 2026-09-26: `terms` failed at base on all nine of the spec loop's run 18
  cells.
- 2026-09-27: `terms` failed at base on every cell of the spec loop's run 19.
- 2026-09-28: run 20's baseline reported `terms=fail` at base from
  `saffron/intake.py:134` ("Never a ticket").
- 2026-10-24: ADR 11 (#963) gives a banned phrase no correct use in the
  gate's scope. That rules out the exemption arm of Done, and the rewording
  arm stands (b-8220e6).
