---
id: 57
title: The vocabulary hook matches within a line, and this file is hard-wrapped
status: done
tier: 1
closed: 2026-09-12
specs: [SA-0073]
prs: [220]
commits: []
cites: []
related: [25, 40]
---

## Problem

**Status:** **done** — `SA-0073`, PR #220, merged 2026-09-12. Measured when it
was queued: one hit in the tree only a cross-line reading sees, in item 40 of
this file. It was the verb, not the retired noun, which the pattern cannot tell
apart, and it was reworded in the same commit so the spec starts from a clean
tree.

`.pre-commit-config.yaml`'s `retired-vocabulary` hook is `language: pygrep` with
`entry: '(?i)gate[ -]runs?\b'`. pygrep searches **line by line**, and every
prose file in this repo is hard-wrapped at ~78 columns, so a retired two-word
term that happens to straddle a line break is not seen.

**Measured, not reasoned.** Two files, same words:

```
_probe_flat.md     the retired two words, space between, one line  -> Failed  (caught)
_probe_wrapped.md  the same two words, split by a line break       -> Passed  (missed)
```

(Described rather than quoted, for the reason `.saffron/policy.yaml` gives about
its own suppression list: the tokens a check scans for are themselves scanned.)

And it has already happened here. Item 25 has carried *"`size` failed every
gate / run after"* since it was written; the hook ran over that line on every
commit since and passed it, because the wrap put `gate` and `run` on separate
lines. It was found only because a later edit put the same phrase on one line
and the hook rejected *that* — so the control's one catch to date was of a
sentence a person had just written, not of the one that had been sitting in the
file for a week.

**The rate is not marginal.** Across the 52 markdown files the hook covers
(its `exclude` drops `CONTEXT.md`, `CLAUDE.md`, `docs/superpowers/` and
`docs/evidence/`) the mean is **12.6 words per line**, so roughly **one
occurrence in thirteen** of any two-word term falls across a break. 28 lines in
those files already end in the bare word `gate`.

**This is Appendix I's shape in the vocabulary layer** — a control that reads
as present, reports green, and is not applying — which is the argument for
fixing it rather than noting it. It is also why the count matters: one in
thirteen is low enough that the hook looks like it works.

**Done looks like** the check reading the file rather than the line. `pygrep`
cannot: the cheapest honest fix is a small `language: script` hook that
normalises whitespace across line breaks before matching, which also makes the
pattern list somewhere a second retired term can be added. **Not** a
`multiline` pygrep flag alone — `\b` and `[ -]` would still have to grow a
newline case, and the next term added would need the same care, which is the
part that rots.

**One thing to decide with it, and it is not obviously a defect:** `CONTEXT.md`
carries dozens of `_Avoid_` terms and the hook enforces exactly one. That looks
deliberate — most of the others are common English (`run`, `session`, `the
tool`) and a mechanical match would drown in false positives, whereas
`gate[ -]run` is safely distinctive. Worth stating in the config so the next
reader does not take the gap for an oversight and "finish" it.
