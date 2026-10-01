---
id: b-a09d30
title: The loop's REVIEW lines read only declared `touches`, and `record` and `jev` disagree on a stale `findings.json`
status: open
tier: 3
filed: 2026-09-30
specs: [SA-0196]
prs: []
commits: []
cites: []
related: [b-66d1c3]
---

## Problem

Found in the spec loop's run 23, 2026-09-30, by #608's seats.

- `driver.py check`'s `review:` walk reads each ancestor's frontmatter
  `touches`. A bug-type spec declares none (`CONTEXT.md`'s **Touches**), and
  IMPLEMENT can widen a declared set. Such an ancestor changing REVIEW
  prints no line. All 57 bug specs in the tree declare `touches` today.
- `record`'s lens line counts a `findings.json` as the latest run's when it
  is no older than `gates/`. `_jev_cell` still anchors on `baseline.json`,
  which `SA-0196`'s spec calls the weaker anchor. The two can disagree about
  one file.
- A findings entry of `{"lens": null}` prints `lenses: None`.

## Done looks like

`check` says when an ancestor's REVIEW reach cannot be read from its
frontmatter. `record` and `jev --kind cell` share one staleness rule. A lens
name that is not a string reads as none recorded.

## Record

- 2026-09-30: filed from the spec loop's run 23.
