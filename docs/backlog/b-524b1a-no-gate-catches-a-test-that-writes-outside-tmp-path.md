---
id: b-524b1a
title: No gate catches a test that writes outside its `tmp_path`, so a run leaves repositories on the host
status: open
tier: 3
filed: 2026-10-19
specs: []
prs: []
commits: []
cites: [§5.4]
related: []
---

## Problem

Found by both seats on #907, in the spec loop's run 44.

`SA-0278`'s cell repaired tests by creating bare mirrors at the fixed path
`/tmp/pinned-mirror.git` and in `tempfile.mkdtemp()` directories outside
`tmp_path`. The spec asked for each under `tmp_path`. The Standards seat
measured `/tmp/pinned-mirror.git` and 57 `mirror.git` directories left on
the host, and the mirror kept gaining refs across runs. Every gate passed,
and the critic raised nothing. Review moved them under `tmp_path`.

## Done looks like

A test that writes a file outside its `tmp_path` fails the suite. Or a
`structure` rule refuses a fixed `/tmp` path in `tests/`, and a `mkdtemp()`
with no `dir`. That rule ships with the `SA-0278` shape as its failing snippet.

## Record

- 2026-10-19: filed from the spec loop's run 44.
