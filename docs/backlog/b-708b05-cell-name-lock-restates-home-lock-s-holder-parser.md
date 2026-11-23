---
id: b-708b05
title: "cell_name_lock restates home_lock's holder parser, and a contender in the write window names a stale holder"
status: open
tier: 3
filed: 2026-11-22
specs: []
prs: []
commits: []
cites: [§5.1]
related: [b-d9ed45]
---

## Problem

Found by finish 103's end review of `SA-0422` (#1299), in the spec loop's
run 83. The finish pooled both findings, so no follow-up ran.

- `_read_holder` in `saffron/cell_name_lock.py` restates the one in
  `saffron/home_lock.py` line for line. The two copies already drifted
  once, on `-1` against `unknown`, before a review commit matched them.
- The holder writes its pid and text after `flock` grants the lock.
  Release never clears the file. So a contender that refuses inside that
  window reads the last holder's line and names a pid that holds nothing.

## Done looks like

One holder parser serves both locks. A refusal inside the write window
names no stale holder, and a test drives that window.

## Record

- 2026-11-22: filed from finish 103's pooled end review findings.
