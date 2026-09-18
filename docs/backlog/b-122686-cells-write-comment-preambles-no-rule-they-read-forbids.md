---
id: b-122686
title: Cells write multi-paragraph comments because no rule they read says not to
status: done
closed: 2026-09-18
tier: 2
filed: 2026-09-18
specs: []
prs: [346]
commits: []
cites: [§8]
related: []
---

## Problem

Found in the spec loop's run 7, 2026-09-18, across all five pull requests.

Every run-7 cell wrote a comment preamble, and a review commit trimmed each one.

| Spec | Cell commit | What it wrote |
|---|---|---|
| `SA-0104` | `6212711` | a 4-line inline comment |
| `SA-0099` | `77d02e0` | a 15-line SQL comment and a 13-line docstring |
| `SA-0100` | `3f6a4bc` | an 11-line comment |
| `SA-0103` | `3887987` | a 7-line comment |
| `SA-0105` | `75bdc2b` | an 18-line docstring, where its spec asked for "a short comment on the read" |

The operator's rule for terse comments lives in their private instructions,
which a cell never sees. The repo's `CLAUDE.md` is the cell's standing
instruction surface (§8). It has no rule on comment length.

## Done looks like

Either `CLAUDE.md` gains a line on comment length, or a `prose` or `structure`
rule refuses an added comment block over a stated length. The rule is the
stronger fix, since `CLAUDE.md` asks that rules be promoted to gates.

## Record

- 2026-09-18: filed from the spec loop's run 7 (stack #335 ← #338 ← #339 ←
  #342 ← #340). Surfaced by the review commits on #335, #338, #339, #342 and
  #340.
- 2026-09-18: done by #346, as a `CLAUDE.md` line (bucket 2). The `prose` or
  `structure` rule this item calls stronger is not built.
