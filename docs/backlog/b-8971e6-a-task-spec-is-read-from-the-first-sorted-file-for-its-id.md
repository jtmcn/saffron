---
id: b-8971e6
title: regate and review read a task's spec from the first sorted file for its id, not the one whose sha matches
status: wontfix
tier: 3
filed: 2026-10-29
closed: 2026-11-07
specs: []
prs: []
commits: ["7cca25d6"]
cites: [§4.1]
related: []
---

## Problem

Raised by the Spec seat on #990, outside `SA-0326`'s `touches`.

`saffron/regate.py`'s `_spec_at_base` takes the first sorted
`SA-NNNN-*.md` file for a spec id, then compares its sha with the task's
`spec_sha`. `saffron/commit_review.py`'s `_spec_for_task` copies it. When
two files share an id, both commands decline a task whose file sorts
second. Nobody has seen two files share an id, so this is unmeasured.

## Done looks like

Both commands read the file whose sha is the task's `spec_sha`, or decline
naming every file that shares the id.

## Record

- 2026-10-29: filed from the spec loop's run 50.
- 2026-11-07: closed in grooming as wontfix, on the operator's ruling of 2026-11-07. This repo's records check refuses two spec files that share an id (`check_spec_ids_unique`, 7cca25d6), and `saffron next-id` hands out free ids. Reopen if any repo is seen with two spec files for one id.
