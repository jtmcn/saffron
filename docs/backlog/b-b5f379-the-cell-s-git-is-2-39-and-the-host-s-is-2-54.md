---
id: b-b5f379
title: The cell's git is 2.39 and the host's is 2.54, so a git behaviour measured on one side fails on the other
status: open
tier: 2
filed: 2026-09-18
by_hand: true
specs: []
prs: []
commits: []
cites: [§5.1.2, §5.4]
related: [173, 176]
---

## Problem

Found in the spec loop's run 7, 2026-09-17, by the spec review of `SA-0105`.

`images/cell-base.python.Dockerfile` builds from `python:3.12-slim-bookworm` and
installs Debian's `git`. Bookworm ships git 2.39.5, and nothing pins it. The
host runs git 2.54. The cell runs the `tests` gate, so a witness has to hold
on 2.39.5. `mirror.diff_stat` runs on the host, so production reads its
counts with the host's git.

`SA-0105` as first written told the cell to add `--no-patch` between
`DIFF_FLAGS` and `--shortstat`, measured on git 2.54. On 2.39.5 that prints
nothing in either position, which reads every diff as `(0, 0)`. Measured in
`saffron/cell:saffron`: `git diff <DIFF_FLAGS> --no-patch --shortstat` printed
nothing. The spec was fixed before its cell (#333). The Spec seat on #340 then
found the other side of the same gap: `--no-patch` in that position passes every
witness on the host, so `make check` misses an edit the cell's gate catches.

`python:3.12-slim-trixie` (Debian 13) offers git 2.47.3 and Python 3.12.14,
measured 2026-09-18 with `apt-cache policy git` in that image. That narrows the
gap and does not close it.

Two comments already record 2.39 behaviour: `tests/test_integrity.py:271` ("on
the 2.39 the cell image carries it was ignored") and
`docs/evidence/scripts/2026-09-13-history-and-diff-pins.sh:4`.

This goes by hand: a cell runs inside the image it would change, and
`pytest -m cell` is the operator's.

## Done looks like

- `images/cell-base.python.Dockerfile` builds from `python:3.12-slim-trixie`,
  and `DESIGN.md`'s line naming the base image says so.
- `saffron/cell-base:python` and `saffron/proxy` are rebuilt, and
  `uv run pytest -m cell` passes.
- Every comment and workaround citing git 2.39 is re-measured on 2.47 and kept,
  corrected, or removed. `saffron/repos/mirror.py`'s `diff_stat` comment still
  holds on 2.47.
- Optional: a test reads `git --version` in the cell and on the host. It names
  a minor-version difference, so a spec measured on one side hears about the
  other.

## Record

- 2026-09-18: filed from run 7, with the trixie git version measured. No other
  work is done.
