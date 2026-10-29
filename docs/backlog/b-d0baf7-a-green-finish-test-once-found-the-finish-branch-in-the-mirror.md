---
id: b-d0baf7
title: "A green finish test once found the finish's branch in the mirror, on a commit that passed in the run beside it"
status: done
tier: 3
filed: 2026-10-27
closed: 2026-10-29
specs: []
prs: [992]
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
- 2026-10-29: measured. CI failed this test on all 12 runs on runner image
  `20261025.179.1`, which ships git 2.56.0. It passed on all 8 runs on
  `20261012.163.1`, which ships git 2.55.0. Git 2.56's release notes say a
  push to a URL now updates the ref a matching remote's fetch refspec names.
  The test mirror is a `clone --mirror` of that URL, so the push writes the
  finish branch into the mirror at the pushed sha. The test now accepts that
  one ref and nothing else new.
