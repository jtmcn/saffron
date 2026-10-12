---
id: b-f7a591
title: "A lens that errors drops the host's criterion-probe blockers filed under it, and the log says it produced nothing"
status: open
tier: 2
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§5.5]
related: [b-032c3e, b-4e0868, 60]
---

## Problem

Measured on `SA-0259` in the spec loop's run 34.

The adequacy lens returned malformed JSON twice, and the re-prompt did not
recover it. REVIEW then printed "['adequacy'] produced no findings, the
review is incomplete". The task halted at `REVIEWING` with its gates green
on the first attempt. PACKAGE pushed the branch and opened no PR.

`findings.json` held more than the error. The host had filed two
criterion-probe blockers under that lens, both `survived`, against criterion
3's witness. Neither reached REBUT. The log line named neither. The PR seat
later confirmed both and found two more. A reader of the batch log would
take the lens for empty.

The lens's own JSON failure is b-4e0868's remaining half. The halt reading
as in flight is b-032c3e.

## Done looks like

A host verdict reaches REBUT and the outcome whatever its lens returns. The
log names each blocker an errored lens carries. A test drives a lens error
beside a survived criterion probe and reads both in the outcome.

## Record

- 2026-10-11: filed from the spec loop's run 34 (#809).
