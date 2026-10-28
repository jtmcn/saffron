---
id: b-d0baf7
title: "A green finish test once found the finish's branch in the mirror, on a commit that passed in the run beside it"
status: open
tier: 3
filed: 2026-10-27
specs: []
prs: []
commits: []
cites: [§5.7]
related: []
---

## Problem

Found on #985's pull request run, `40605098841`, at `cdd35b77`.

`tests/test_finish.py::test_a_green_finish_pushes_its_own_branch_and_opens_its_draft_pull_request`
failed at its mirror check (`tests/test_finish.py:1624`). The mirror held
`refs/heads/saffron/batch-1-finish` after `publish_finish`. The push writes
that ref only at the remote. The push run on the same commit passed, and
a rerun of the failed job passed. No earlier failure of this test shows in the
last 40 failed runs.

`publish_finish` pushes from a worktree of the mirror to a URL. One reading is
that git updated a ref it treats as tracking that remote. Nothing here measured
that.

## Done looks like

The cause is named from a measurement. Either the test holds on every run, or
the finish leaves no ref in the mirror whatever git does.

## Record

- 2026-10-27: filed from #985's CI run.
