---
id: 76
title: A gitignore entry removes a tracked file from `lint` and `format`
status: open
tier: 3
specs: []
prs: [145]
commits: []
cites: []
related: []
---

## Problem

Found reviewing the `structure` gate (PR #145), where the same hole was closed.
ast-grep and ruff both walk with a gitignore filter that has no notion of what
git *tracks*: one line in `.gitignore` naming a file that is committed removes it
from the gate's view while it stays in the diff, in the index, and in the merged
result. Measured on `structure` before the fix — `fail` on the planted violation,
one line added, `pass` — and ruff documents the same walk (`--no-respect-gitignore`
exists precisely because of it).

`.gitignore` is in `integrity.gate_config`, which routes an edit to a person on
every gate at once — but that is the *tracked* half only, and a later review round
found the rest. A `.gitignore` naming both a violating tracked file and itself is
never added by `git add -A`: it reaches no diff, no commit, and nothing
`git status --porcelain -uall` reports, so no policy list can ever see it.
Measured on `structure` before its second fix: violation committed, scan `pass`.
Routing is not a substitute for refusing. What is left is per-gate:

- **`lint` and `format`** should stop respecting any ignore source and name their
  own exclusions, as `structure` now does with `--no-ignore vcs` and `--globs`.
  The reason to measure rather than guess: `.venv/` and `.claude/worktrees/` are
  gitignored, and a scan that walks into either is slow and reports third-party
  code. For `structure` that cost was 0.04s against 0.27s and zero new matches;
  ruff's own walk is a separate measurement.
- **`tests`** is a different question — pytest collects through its own config —
  and should be checked rather than assumed to share the defect.

## Done looks like

a test per gate in the shape of
`test_an_ignore_file_outside_the_diff_cannot_hide_a_violation`: a tracked file
that violates, an ignore file naming it, and the gate still reporting `fail`. The
`.git` directory in that fixture is load-bearing — the walker honours a
`.gitignore` only in a tree that looks like a repository, so without one the test
passes against the unfixed gate.
