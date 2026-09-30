---
id: b-38d45f
title: A finding outside every hunk is anchored by any shared word, stopwords included
status: done
tier: 2
filed: 2026-09-29
closed: 2026-09-29
specs: [SA-0194]
prs: [598]
commits: []
cites: [§5.5]
related: [b-cd5fd2, b-e40d09, b-1e9a7a]
---

## Problem

Found in the spec loop's run 21, 2026-09-29, on #581 (`SA-0192`).

`_is_anchored` anchors a finding on a line outside every hunk when that line
shares any `\w+` token with a changed line (`saffron/agents/findings.py:166`,
`_WORD` at `:26`). Stopwords count. `CONTEXT.md` defines **Anchored** as a
line "naming an identifier the diff changed".

`SA-0192`'s host probe filed a blocker on `review-correctness.md:30`. That line
sits outside every hunk. It anchored through `changed`, `code`, `is`, `lenses`,
`other`, `the` and `what`. Both seats checked it. The finding was real, so the
anchor did no harm here. The same rule anchors a false one as easily.

## Done looks like

Anchoring outside a hunk counts identifier-shaped tokens only, or drops
stopwords. A test anchors a finding whose line shares only common words with
the diff and reads it unanchored.

## Record

- 2026-09-29: filed from the spec loop's run 21.
- 2026-09-29: closed by `SA-0194` (#598). Anchoring outside a hunk ignores 54 common words.
