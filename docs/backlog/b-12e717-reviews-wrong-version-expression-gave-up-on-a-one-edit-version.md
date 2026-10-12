---
id: b-12e717
title: REVIEW's wrong-version expression gave up on a version one edit expresses
status: open
tier: 3
filed: 2026-09-29
specs: [SA-0193]
prs: [596]
commits: []
cites: []
related: [b-7e69d0]
---

## Problem

Found in the spec loop's run 22, 2026-09-29, on `SA-0193`.

`~/.saffron/batches/v0/SA-0193/wrong-versions.json` records criterion 1's
"A refusal is recorded only when HEAD did not move" with `"edit": null`. Its
outcome is `unproven`. The host expressed 15 of the 16 wrong versions.

The Spec seat expressed that version as one edit, and the witness killed it.
So a single edit exists. The record does not say why the session gave none.

## Done looks like

The host retries a version it could not express, or reports why. A reviewer
can tell "no single edit exists" from "the session stopped".

## Record

- 2026-09-29: filed from the spec loop's run 22.
- 2026-10-11: recurred on `SA-0258` in the spec loop's run 34. The batch
  log said "5 declared, 4 expressed" and named no version. The fifth,
  `os._exit(143)`, was `unproven` in `wrong-versions.json`. The Spec seat
  expressed it as one edit, and only an `IndexError` killed it. #812's
  review made the witness fail by assertion.
