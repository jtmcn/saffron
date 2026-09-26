---
id: R
title: "rev 22: a house style for the prose a cell reads"
revisions: [22]
question: "How a style rule holds prose that already breaks it: it limits growth, and it skips no file"
---

Saffron's own prose had no enforced style. On 2026-09-16, 1,712 of the 8,940
sentences in `CONTEXT.md`, `CLAUDE.md`, `DESIGN.md` and the specs ran over 25
words. A cell reads that prose on every task. The `prose` gate now holds it
(`.saffron/gates/prose.py`), and one choice in that gate is a principle.

59. **A style rule limits growth, and never exempts a whole file.**
    A rule that fails every file fails every task. Nobody rewrites all the
    prose first, so that rule gets switched off. A list of skipped files would
    stop checking the documents a cell reads most. So no file can gain hits of
    any rule. What a file already holds stays tolerated, and no baseline file is
    written.

**What changed.**

- A blocking `prose` gate counts hits per file and rule. Baseline subtraction
  (§5.4) does the limiting, with no change under `saffron/`. Its failure
  message is fixed per rule, so the identity is the file and the rule. A new
  hit then cancelled an old one. On 2026-09-26 the message took the hit's
  sentence, or its block's name and length (item b-044ae7).
- An advisory `terms` gate names the Saffron term for an avoided phrase. Each
  entry is quoted on an `_Avoid_` line in `CONTEXT.md`.
- A prek hook applies the same limit to a commit. A Claude Code hook reports
  new hits to the model after each edit.

**What it does not change.** Existing prose stays as written. Rewriting a
document is a backlog record of its own. Rendered text is exempt, because its
source is an appendix or `factory.ttl`.

