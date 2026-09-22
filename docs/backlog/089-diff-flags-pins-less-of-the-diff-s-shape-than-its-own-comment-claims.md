---
id: 89
title: '`DIFF_FLAGS` pins less of the diff''s shape than its own comment claims'
status: partial
tier: 1
specs: [SA-0072, SA-0082, SA-0121]
prs: [219, 244]
commits: []
cites: [§2]
related: [115]
---

## Problem

**Found reviewing `SA-0072`, 2026-09-11, and outside it:**
- **`--no-renames` is guarded by no test.** Removing it left all 1745 tests
  green, because `_hostile_repo` never renames a file.
- **Three more repo-local settings still move the pinned diff:**
  - `diff.interHunkContext` merges two hunks into one. That has the same
    anchoring effect as `diff.context`.
  - `color.ui=always` puts escape codes on the `diff --git` line, so `scope`
    errors on every attempt.
  - `diff.ignoreSubmodules=all` hides a gitlink from the name-only listing, so
    `scope` never sees a path outside `touches`.

Each wants its own flag and its own witness. None is a value `pinned_diff`
measured, which is why `SA-0072` leaves them out.

Found building the lens-corpus harness's byte-identity check (2026-09-08),
which had to reproduce `export_patch`'s output on a host it does not control
and, in doing so, needed three flags `saffron/cell/worktree.py` does not set.

`worktree.py:127`'s comment over `DIFF_FLAGS` says it pins "the shape of every
diff the host reads" against config the agent can write inside its own
worktree (§2). The five flags at `worktree.py:131-144` back that for
`diff.srcPrefix`/`dstPrefix`/`noprefix`/`mnemonicPrefix`, `diff.external`,
`diff.textconv` and rename detection — but not for `core.abbrev`,
`diff.context` or `diff.algorithm`, none of which any flag or `-c` override
here touches. An agent that runs `git config diff.context 40` (or
`core.abbrev`, or `diff.algorithm patience`) before its own commits changes
`export_patch`'s bytes with nothing in this module noticing, which is a
narrower guarantee than the comment states.

**Severity is low, and worth saying plainly rather than implying.**
`core.abbrev` and `diff.algorithm` are cosmetic here: nothing host-side parses
an `index` line's hash or cares which algorithm chose a hunk boundary.
`diff.context` has the one real effect — `saffron/agents/findings.py`'s
`parse_diff` puts every line a hunk's declared range covers into
`hunk_lines` (`findings.py:79`), context lines included, and `_is_anchored`
(`findings.py:135`) tries `hunk_lines` first. A wider context widens what a
finding may anchor to. The blast radius is capped two ways: `facts.tokens`,
the second anchoring target, is collected only from `+`/`-` lines
(`_consume_hunk`, `findings.py:102-110`), which no context setting moves; and
the merged commit still comes from git objects, never from the archived
`patch.diff` — nothing about this lets unreviewed code into the tree it did
not already reach some other way. What it can do is nudge a finding onto a
line it would not otherwise have reached, and leave the archived patch a
record of what an agent chose to show rather than what the range actually
contains.

`harness/recovery.py`'s `pinned_diff` is the worked example: reproducing a
recorded patch on an arbitrary host needed `--abbrev=7 --unified=3
--diff-algorithm=myers` on top of `DIFF_FLAGS` and its two `-c` overrides, all
three measured against every one of this repo's own recorded patches rather
than assumed.

## Done looks like

Dropping the
duplicate flags from `pinned_diff` afterwards is a harness change, left for
later — and its docstring still says `_git` has "two `-c` overrides", which is
five now. `tests/test_package.py:361` keeps a third copy of `DIFF_FLAGS`, five
flags of eleven, under a fixture that calls itself "shaped exactly like
`worktree.export_patch`'s output"; it should import the tuple (found reviewing
`SA-0082`, PR #244, 2026-09-14).

## Record

`DIFF_FLAGS` (or `_git`'s `-c` overrides) gaining the same
three pins `pinned_diff` already carries — an explicit `--unified=<n>` matters
most, since it is the one with anchoring consequences; `--abbrev`/
`--diff-algorithm` close the comment's claim rather than a live hazard. Cite
`harness/recovery.py`'s `pinned_diff` for the exact flags and the measurement
behind each.

**Status: the three measured pins are done — `SA-0072`, PR #219, merged
2026-09-12.** It takes
`pinned_diff`'s measured values rather than choosing new ones.

**The four below: merged, 2026-09-14 — `SA-0082`, PR #244, in stack
#251.** The `.gitmodules` half the review found is item 115. Probed
that day on git 2.39.5 (the cell image) and 2.54, with identical results
(`docs/evidence/scripts/2026-09-13-history-and-diff-pins.sh`).
`--ignore-submodules=none`, `--no-color` and `--inter-hunk-context=0` each
restore the pinned shape. `-c color.ui=never` does not beat `color.diff=always`.
One correction to the bullet below: `color.ui=always` leaves the name-only
listing clean, so its escape codes land in the patch, not in the list `scope`
reads.
