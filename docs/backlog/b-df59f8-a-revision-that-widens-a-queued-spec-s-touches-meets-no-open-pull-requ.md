---
id: b-df59f8
title: A revision that widens a queued spec's touches meets no open pull request overlap refusal
status: open
tier: 3
filed: 2026-09-25
closed:
specs: []
prs: []
commits: []
cites: [§4.2, §4.2.1]
related: [b-792ab2]
---

## Problem

A stack batch's spec review can revise a queued spec (`SA-0164`), and a
revision can widen `touches`. `SA-0150` runs gate 0 and `parse_spec` again
on the recorded text. It cannot run the two open pull request refusals,
because `run_task` has no `gh`. `SA-0162` runs the overlap refusal for
follow-ups only. So a revision whose new `touches` overlaps an open pull
request runs anyway. Principle 54 is half held for revisions.

## Done looks like

A revised text meets the open pull request refusals before its cell, as a follow-up does.

## Record

- 2026-09-25: filed from the spec reviews of `b-792ab2`'s last build specs.
