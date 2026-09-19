---
id: 117
title: The host never runs the probe the adequacy lens names, so a confirmed vacuity ships as a concern
status: open
tier: 1
filed: 2026-09-14
specs: []
prs: []
commits: []
cites: [§5.4.1]
related: [69, 109]
---

## Problem

**Tier 1.** Found running the spec loop over stack #251, 2026-09-14. The adequacy
lens must attach a `probe` — `{file, find, replace}` — to every finding
(`saffron/phases/review.py`, `_ReportedWithProbe`), and `CONTEXT.md` defines a
vacuity probe that survives the suite as the finding confirmed. Nothing in
production runs one. Its only reader is the lens corpus driver
(`docs/evidence/scripts/2026-09-08-lens-corpus.py`), scoring the lens offline; in a
cell the finding is anchored, counted, and reaches the morning queue as a `concern`
or `note` whatever running it would have said.

Five of the stack's eight adequacy runs named a probe that survived at the packaged
head, and each was a defect the review round then fixed:

| spec | PR | lens said | the probe | survival shown by |
|---|---|---|---|---|
| `SA-0082` | #244 | concern | `--inter-hunk-context=0` → `=1` | the loop's delegate |
| `SA-0081` | #248 | concern | cut every poll, not only the first | Spec seat |
| `SA-0085` | #250 | concern | `_green_at_base` reads `collected` only | Spec seat |
| `SA-0084` | #249 | note | `_clean` keeps the tail, `[-limit:]` | Spec seat |
| `SA-0080` | #247 | note | decode with no `except UnicodeDecodeError` | Spec seat |

This is item 69's question answered the way that item says it must be, by running,
and without a spec author declaring anything. That matters because §5.4.1 lets a
spec creating new code declare no mutant at all, and four of the five probes above
edit lines the diff itself added. The machinery exists: the cell's mutator,
`worktree.source_mutated` (`SA-0062`), applies a `Mutant` and restores it. The
witness-gate tests' host mutator is `tests/mutation.py`. The repo's `tests` gate
accepts a subset. What a probe lacks that a spec mutant has
is its witness — it names the edit, not the test that should die — so it runs under
the spec's declared witnesses and the diff's own added tests.

## Done looks like

each adequacy probe applied after REVIEW, the spec's witnesses
and the diff's added tests run under it, and the result deciding the finding: a
probe that survives becomes a blocker routed to REBUT with the probe named; one that
is killed drops its finding and is counted, so the lens's drop rate measures what
the corpus measures; one that does not apply is named, as `witness` names a mutant
that does not. Two limits for the design. REBUT then shows the implementer the
probe, and `SA-0079`'s REBUT shows what follows: it tightened a bound until the
named edit died and left a near neighbour surviving. And a probe handed back to the
implementer is the exposure item 109 closes for spec mutants — tolerable here only
because the lens authored it and a fresh one can be asked for each round.
