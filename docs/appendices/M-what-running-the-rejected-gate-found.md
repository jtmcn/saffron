---
id: M
title: "rev 15: what running the rejected gate found"
revisions: [15]
question: "What *running* the rejected gate found, beyond what reading it found — three corrections in twenty minutes"
---

Backlog item 1 said to read `SA-0004`'s rejected patch and its review before writing anything. Executing it as well took twenty minutes and returned three corrections, one of which nothing had recorded. Full record in `docs/evidence/2026-08-22-integrity-rejected-gate-measured.md`.

**The batch tree holds a later patch than the one Appendix K reviewed.** `rebuttal.json` records `head_moved: true`: the implementer changed the removal check during REBUT and the lens withdrew its blocker. Appendix K describes the code as applied and reviewed; the export is one fix past it. Both are honest about different artifacts, which is the shelf-life problem of Appendix K's own "patches perish" note arriving in a second form.

- **The `\ No newline at end of file` defect is already fixed.** All four positions git emits the marker parse cleanly. The backlog line claiming a branch sits in the wrong place is struck.
- **The removal check is run adjacency, not net line count.** So the `parametrize` false positive is gone — and the evasion is *cheaper* than Appendix K says, not harder. Not a comment longer than the test: one adjacent added line of any content, because the gate never asks what the added line says.
- **The suppression scan fails this repository's own merges.** Substring matching over every added line in every file means prose containing a token fails. `d1141d0`, the merge of PR #5, returns `fail` on two docstrings that quote `@pytest.mark.skip` while explaining that a critic's claim routinely quotes it. This is also what the "sixteen violations on its own pull request" were.

52. **When a check keeps needing a better heuristic, the question is in the wrong coordinate system.** Three rewrites of "was a test removed?" against diff text produced three different wrong answers, because the diff does not contain the answer — it contains a shadow of it. The set of collected tests contains it exactly, and comparing two sets needs no heuristic at all. The tell is not that a heuristic is imperfect; it is that each repair moves the failure somewhere else rather than shrinking it.

The corollary is the cheaper half: **the data a core gate needs may already be in a result it is holding.** Item 1 assumed test-set comparison required `revert`'s §2.1 exception — core invoking the repo's `tests` gate twice more. It did not. The baseline and head suites already run `tests`; the names needed reporting, not fetching, and the whole exception dissolved into one optional field.

---

