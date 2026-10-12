---
id: b-c86c4b
title: "`probe.py` and `session.py` call a probe's reason a refusal, a word `CONTEXT.md` keeps for a task rejected before any cell starts"
status: open
tier: 3
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§5.5]
related: []
---

## Problem

Found by the Standards seat on #809 (`SA-0259`), in the spec loop's run 34.

`CONTEXT.md` defines **Refusal** as a task rejected before any cell starts.
`saffron/probe.py:153` uses the word for a probe that is not applied.
`probe_refusal` returns the reason, and `session.py:1574` calls it.
`session.py:1749-1752` binds it to `refusal` and writes it under a
`"refusal"` key in the wrong-version record.

`SA-0259` made the same clash in a prompt heading, and its review commit
renamed it. The older use in `probe.py` and `session.py` predates that spec.

## Done looks like

The probe's reason takes a word `CONTEXT.md` does not reserve, in the
function name, the local and the record key. The `terms` gate refuses
"refusal" for anything but a Refusal, or the operator decides the overlap
is acceptable.

## Record

- 2026-10-11: filed from the spec loop's run 34 (#809).
