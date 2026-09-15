---
id: 40
title: A host-side fix round can undo a gate the cell passed
status: open
tier: 1
specs: [SA-0029, SA-0080, SA-0086]
prs: [91, 247, 255]
commits: [4ba8bdf]
cites: [§5.4]
related: []
---

## Problem

`SA-0029` (PR #91) left its cell at 548 changed lines, inside the 600 a
`feature` gets. Two host-side review rounds took it to **863**. The `size` gate
executes inside the cell, against the cell's own diff; nothing re-runs it after the
operator commits review fixes to the branch, so the branch merges failing a
blocking gate it passed on the way out.

Most of the growth is tests, and that is the second half of the finding:
`_changed_lines` counts the whole diff, so a spec whose acceptance criteria
demand thorough tests is charged for satisfying them. `SA-0029` has fourteen
criteria, and both reviews of it added tests precisely because criteria were
being held up by comments. Cutting those to reach 600 would trade a real
control for a number.

## Done looks like

Done looks like: the loop running `size` (at minimum) against the branch before
it is marked ready, and a decision on whether the ceiling should count test
lines at all — §5.4 sets one number for a diff whose test half is mandated
elsewhere. Recorded rather than fixed here: PR #91 is over the ceiling and is
being merged over it deliberately, with this item as the record.

## Record

It happened again on 2026-09-14: `SA-0080` (PR #247, stack #251) left its cell at
294 changed lines against a `bug`'s 300, and the review round took it to 367 — two
witnesses, one of which is the only test that fails on the defect the spec exists
for, and a shared decode helper. The operator chose to merge it over the ceiling,
with this item as the record.

And the same day with `scope` instead of `size`: `SA-0086` (PR #255) forbade
`saffron/report/pr_body.py`, and its review round edited that file (`4ba8bdf`),
by operator decision. The diff had made the file's `"packaged"` sentence false
on every unmoved-base pull request. `scope` runs in the cell against the cell's
diff, so nothing on the branch records that it now carries a forbidden path. It
is the same fix: re-run the gates the cell passed against the branch before it
is marked ready, and have an operator's exemption leave a record.
