---
id: b-461729
title: Two different test-path rules decide where a vacuity probe may be applied
status: open
tier: 2
filed: 2026-09-19
specs: [SA-0119]
prs: []
commits: []
cites: [§5.5, §5.4]
related: [117, b-98dc4d]
---

## Problem

Found by the spec loop's Spec seat reviewing #375, 2026-09-19.

The host refuses a probe on a declared test path before calling `check_probe`,
and passes `test_paths=()` so the module's own guard is disabled
(`saffron/cell/session.py`). The two rules are not the same rule.
`check_probe`'s `_under` is a segment prefix, so `tests` covers
`tests/test_x.py`. `scope.matches` is a glob, so `matches("tests/test_x.py",
"tests")` is `False`.

Saffron declares `test_paths: ["tests/**"]`, so both agree here. A target repo
whose policy says `test_paths: ["tests"]` gets probes applied to its test
files. So does one that says nothing, since the default is `[]`. There,
deleting an assertion survives trivially and promotes the finding to a blocker.
`revert` refuses to run at all on an empty list. The probe path has no such
refusal.

The spec chose `scope.matches` deliberately, as the rule `revert` uses, and
`saffron/probe.py` was forbidden to it, so this is not that diff's to fix.

## Done looks like

One rule decides where a probe applies, and an empty `test_paths` is refused
rather than read as "nothing is a test".

## Record

- 2026-09-19: filed from the spec loop's run 9 (#375).
