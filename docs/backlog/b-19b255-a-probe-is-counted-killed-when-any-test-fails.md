---
id: b-19b255
title: A probe is counted killed when any test fails, so a probe that only lengthened a line reads as caught
status: open
tier: 1
filed: 2026-09-23
specs: []
prs: []
commits: []
cites: [§5.5.1]
related: [117, b-2750d5]
---

## Problem

Found in the spec loop's run 15, 2026-09-23, on `SA-0127` (#476).

The adequacy lens proposed a probe: `if reverted_result.status not in ("pass",
"fail"):` became the same test plus `and reverted_result.uncollected is None`.
REVIEW reported it killed. `probes.json` names the one failure that killed it:
`tests/test_saffron_gates.py::test_the_fast_gates_name_their_tool_and_pass_on_a_clean_tree[format]`.
The edit pushed the line past the formatter's width, so the format test failed.
No test of `SA-0127` failed. The Spec seat ran the same probe against the
criterion's witness, and it survived (`24 passed`). The delegate reproduced
that with `driver.py probe`.

So a probe the witnesses miss can read as caught whenever its text happens to
break a formatting, lint or unrelated test. The finding then leaves REVIEW as
"covered".

## Done looks like

A probe counts as killed only when a test the diff adds or a witness of the
probe's criterion fails by assertion. Any other new failure is reported
beside the verdict, not counted as the kill. A test pins the `SA-0127`
shape: a probe whose only failure is the format test reads as survived.

## Record

- 2026-09-23: filed from the spec loop's run 15 (#476).
