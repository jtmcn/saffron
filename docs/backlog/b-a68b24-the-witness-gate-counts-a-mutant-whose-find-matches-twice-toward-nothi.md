---
id: b-a68b24
title: The witness gate counts a mutant whose find matches twice toward nothing, so a diff that repeats the line escapes it
status: open
tier: 2
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-9efbe2]
---

## Problem

Found in the spec loop's run 47, on `SA-0312` (#957).

`SA-0312`'s cell copied the single-entry fetch tail into a new helper. Criterion 5's
declared find, `    return head, branch`, then matched three times in `saffron/task.py`.
The witness gate skips such a find and counts it toward nothing
(`saffron/gates/core/witness.py:31-34`). So the gate passed criterion 5 with no mutant run.

The Standards seat counted the matches. The operator chose to fold the copy in review.
The gate hole stays open.

## Done looks like

A declared mutant whose find matches other than once fails the witness gate, and the
failure names the criterion and the count. A cell sees it as a gate failure it can repair.

## Record

- 2026-10-24: filed from the spec loop's run 47.
