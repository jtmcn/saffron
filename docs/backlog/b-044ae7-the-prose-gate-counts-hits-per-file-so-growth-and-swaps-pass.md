---
id: b-044ae7
title: The `prose` gate counts hits per file, so a docstring that grows or a comment block swapped for another passes
status: done
tier: 2
filed: 2026-09-19
closed: 2026-09-26
by_hand: true
specs: []
prs: []
commits: [39ab1e4b]
cites: [§8]
related: [b-122686, 70]
---

## Problem

Found in the spec loop's run 8, 2026-09-19, reviewing #353 (`SA-0106`).

`prose` compares each file's hit count per rule with the base
(`.saffron/policy.yaml:23-24`, `.saffron/gates/prose.py:104`). A hit is one
docstring or one comment block, whatever its length. So a docstring already
over the limit can grow with no new hit. A new comment block also passes if
the same diff trims an older block under the limit.

The `SA-0106` cell commit `22855a4` did both, with the `comment-block` and
`docstring-length` rules from #347 in force:

- `run_batch`'s docstring grew from 33 lines to 53
  (`saffron/batch.py:68` at `22855a4`), and four more over-limit docstrings grew.
- Three new multi-line comment blocks were added in `saffron/batch.py` and
  `saffron/cli.py`.
- Three older comments were cut to two lines, and the lines cut held their
  reasons, including the item-70 reason at `saffron/batch.py:263`.

The per-file count stayed level and `prose` passed. The review commit
`9a8e7c4` restored the base lengths and the three older comments. The
`CLAUDE.md` rule from b-122686 was in the cell's context the whole time.

## Done looks like

`prose` judges each docstring and comment block the diff touches, not a count
per file. A block over the limit that grows fails. A new block over the limit
fails whatever the diff removes elsewhere in the file. A test holds both, with
`22855a4`'s shape as the fixture.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353).
- 2026-09-26: recurred six times in the spec loop's run 18 (stack #531).
  Docstrings grew past ten lines unseen on #522, #525, #527 and #529. On #523
  the repair turn was pointed at an older comment near `task.py:421`. It
  rewrote that, the count went flat, and the cell's own em dash and 34-word
  sentence shipped. Review fixed each by hand.
- 2026-09-26: fixed by hand in 39ab1e4b, since `.saffron/**` is protected. Each
  failure's identity is its sentence, or its block's name and length. The
  commit hook reads the same identity.
