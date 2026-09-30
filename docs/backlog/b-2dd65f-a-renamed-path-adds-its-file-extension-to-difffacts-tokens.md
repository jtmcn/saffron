---
id: b-2dd65f
title: A renamed path adds its file extension to `DiffFacts.tokens`
status: open
tier: 3
filed: 2026-09-29
specs: [SA-0194]
prs: [598]
commits: []
cites: []
related: [b-38d45f]
---

## Problem

Found in the spec loop's run 22, 2026-09-29, by `SA-0194`'s Spec seat.

Measured at #598's head. A diff renames `legacy.py` to `modern.py`. A finding
on `x.md:1` reads `run setup.py first`. It anchors, through the token `py`.

`parse_diff`'s rename branch tokenizes the whole path
(`saffron/agents/findings.py:89`). So every renamed file adds its extension to
the tokens.

## Done looks like

The rename branch tokenizes the stem and not the extension. A test drives the
rename above and reads the finding unanchored.

## Record

- 2026-09-29: filed from the spec loop's run 22.
