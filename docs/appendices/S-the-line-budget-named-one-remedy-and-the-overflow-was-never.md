---
id: S
title: "rev 23: the line budget named one remedy, and the overflow was never that defect"
revisions: [23]
question: "A budget that names one remedy: over ~200 lines the cut is ordered, and the file a cell reads whole is the one it binds"
---

§8's second heuristic bounds `CLAUDE.md`. It was written 2026-08-21, when the
file was 123 lines. It reads: over ~200 lines, prose is standing where a gate
belongs. On 2026-09-17 an audit took the file to 206 and hit the bound twice.
Neither firing was that defect. One was a bullet missing for
`skip-is-spelled-in-full`, a gate since PR #241. The other was reference the
tree already states, the eight core gates and `package.py`. Measured at 206
lines: Commands 62, Architecture and Layout 44, Invariants 41, the opening 25,
Conventions 20, Agent skills 14.

60. **A threshold that names one cause is read as naming the only cause.**
    The number was right twice and the cause wrong twice. The audit then argued
    with the limit instead of cutting. A threshold says what to measure. The
    remedy is a separate list, ordered cheapest first, and an over-budget file
    is evidence for every item on it.

**What changed.**

- §8 orders the cut: what the tree states, then what a gate could hold, then
  what one phase alone needs. What is left is the pitfalls and the rationale.
- The order is external evidence rather than reasoning. Claude Code's memory
  docs, read 2026-09-17, target under 200 lines per file. Its `/doctor` check
  cuts "directory layouts, dependency lists, and architecture overviews" and
  keeps "pitfalls, rationale, and conventions that differ from tool defaults".
- Two arguments reach ~200 independently. §8 derived it from bucket drift, the
  docs from context cost and adherence. The figure is unchanged.
- The budget binds harder here than those docs assume. A cell reads one file,
  `CLAUDE.md` at the base sha (`session.py`), pasted as prompt text, so neither
  docs remedy reaches it. Path-scoped `.claude/rules/` never loads, and an
  `@path` import arrives as literal text. It enters five prompt templates a task
  before repair turns.

**What it does not change.** The ~200 figure. `CONTEXT.md`'s exemption, which
§5.3 earns by filtering the vocabulary per phase. Nothing under `saffron/`.

