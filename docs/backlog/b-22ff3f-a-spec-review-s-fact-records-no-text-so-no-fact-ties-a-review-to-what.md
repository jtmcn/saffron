---
id: b-22ff3f
title: A spec review's fact records no text, so no fact ties a review to what it read
status: open
tier: 3
filed: 2026-09-25
closed:
specs: []
prs: []
commits: []
cites: [§4.1]
related: [b-792ab2]
---

## Problem

A stack batch's spec review reads a revised text after a revision round
(`SA-0164`). The
`spec_review` fact carries the route, block and error (`SA-0155`) but no
`spec_texts` row number or `spec_sha`. Within a batch the cell runs straight
after the review, so it runs the approved text by construction. The record
cannot show which text a `run` route approved.

## Done looks like

The `spec_review` fact records the text's `n` and `spec_sha` it read.

## Record

- 2026-09-25: filed from the spec reviews of `b-792ab2`'s last build specs.
