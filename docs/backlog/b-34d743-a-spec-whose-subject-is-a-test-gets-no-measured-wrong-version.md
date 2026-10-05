---
id: b-34d743
title: A spec whose subject is a test gets no measured wrong version, and REVIEW's line still counts them expressed
status: open
tier: 1
filed: 2026-10-05
specs: [SA-0200]
prs: [674]
commits: []
cites: [§5.5]
related: [b-3c17ab, b-7251b5]
---

## Problem

Found in the spec loop's run 28.

`SA-0200`'s fix is to two test files. Its REVIEW printed `wrong versions: 14
declared, 13 expressed`. Every one of the 14 ended `unproven`
(`~/.saffron/batches/v0/SA-0200/wrong-versions.json`). The 13 expressed edits
each targeted `tests/test_scheduler.py` or `tests/test_queued_specs.py`.
`probe_refusal` (`saffron/probe.py:166`) refused each one with "is a test, a
probe must target source".

So a spec whose subject is a test gets no measured check at all. The REVIEW
line reads as 13 of 14 checked, and none was. The delegate found the gap only
by reading the file.

b-3c17ab is the neighbour. It covers a version REVIEW cannot express as a
source edit. Here REVIEW expressed each one, and the probe refused it.

## Done looks like

A wrong version against a test file is run, or REVIEW's line counts the
refused ones apart from the expressed ones. A test drives a spec whose only
`touches` are tests and asserts the line does not read them as expressed.

## Record

- 2026-10-05: filed from the spec loop's run 28.
