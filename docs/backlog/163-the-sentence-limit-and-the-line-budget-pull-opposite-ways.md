---
id: 163
title: The sentence limit and the CLAUDE.md line budget move the same text in opposite directions
status: open
filed: 2026-09-17
by_hand: true
specs: []
prs: [317]
commits: []
cites: [§5.4, §8]
related: [161, 162]
---

## Problem

`CLAUDE.md` is held by two bounds that do not know about each other. The `prose`
gate caps a sentence at 25 words (Appendix R, principle 59). §8 bounds the file
at about 200 lines and orders the cut (Appendix S, principle 60). The file sits
in the gate's `ROOT_FILES` and above §8's figure, at 206 lines.

The two move the same text in opposite directions. Splitting a sentence to clear
a `sentence-length` hit adds a line. Joining sentences to drop a line adds words
to one sentence. Neither bound names the other.

PR #317 hit this on a one-line correction. A Layout bullet gained four words
naming a second job, which carried it past 25, and the split took the file to
207. The version that satisfied both bounds dropped a word from an unrelated
clause in the same bullet.

Baseline subtraction narrows the exit further. The first attempt had already
taken the file to 19 semicolons from 20. Restoring the original punctuation then
read as growth, and the edit hook refused it. That is principle 59 working. It
also means a file's punctuation is a ratchet, and a later edit answering §8
cannot spend it.

## Done looks like

A reader of either bound learns about the other. The cheap arm is a sentence in
§8's heuristic naming the sentence limit as a constraint on how a cut is made.
Appendix R gains a sentence naming the budget. The wider arm is a measurement:
count how often a `CLAUDE.md` edit satisfying one bound breaks the other, and
record that the conflict is rare enough to leave.

## Record

**Filed 2026-09-17** from the review of PR #317, which hit the conflict and
resolved it by hand. By hand because both bounds live in `DESIGN.md`, which
`.saffron/policy.yaml` protects, so no cell can edit it.
