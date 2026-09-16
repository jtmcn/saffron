---
id: 129
title: An empty `## Problem` section passes the loader
status: open
filed: 2026-09-15
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found reviewing PR #263. `_check_sections` in `records/load.py` refuses a
record with no `## Problem` section, but not a record whose Problem section is
empty. It tests that the section exists, where it tests `## Done looks like`
for content. Measured 2026-09-15: the good fixture's item 1, with its Problem
body removed, loads cleanly. A record that says nothing about what is wrong
then reads as a complete item.

## Done looks like

the loader refuses an empty `## Problem` for every status, with a test watched
failing against the check that only tests existence.

## Record

**Filed 2026-09-15.**
