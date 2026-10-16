# Spec chain feedback, 2026-10-16

One item went through the chain at base `c2f817d3`: b-d31930, filed from the
spec loop's run 40. The driver arm went in by hand on `joel/check-runs-cite`.
This chain wrote the batch arm.

The first writer stopped at the overlap gate after 2 minutes. The check has
to read the commit a review reads, and only `saffron/cli.py` knows it. Three
queued specs touch that file. The operator chose a split. `SA-0294` holds the
core module and an injected `cite` on `run_stack_batch`, and runs next.
`SA-0295` wires it in `cli.py`, behind `SA-0279`.

| Spec | Round 1 | Round 2 | Size |
|---|---|---|---|
| `SA-0294` | 0B 2C 5N | 0B 3C 3N | 711 tokens, measured |
| `SA-0295` | 0B 4C 3N | 0B 2C 2N | 544 tokens, priced |

The two drafts took 16 and 14 minutes, run in parallel. The revisions took
12 and 8. Round 1 took 6 and 5 minutes, and round 2 took 5 and 3. Round 2's
findings were a sentence each, so the delegate applied them by hand.

The two drafts disagreed on one input. `SA-0294` read the queued text at the
head, and `SA-0295` read it at `base_sha`. The review exports `base_sha` and
reads the spec there (`saffron/cli.py:1029-1037`), so the delegate kept
`SA-0295`'s reading.

## Each finding by class

- **A witness that drives one member of a set.** 7 of 11 concerns. Round 1
  on `SA-0294` found that no row reached a `wrapped` call without a review.
  Two wrong placements of `cite` passed. Round 1 on `SA-0295` found that no
  single call order kills both a wrong key and a missing pop. Round 2 found
  three more: a refusal recording a spec review, a no-layer seed, and
  `heads=None` passing an identity check. Pre-flight 1 ran, and each writer
  ran a prototype. The reviewers still found members no row drove.
- **A name the spec leans on that means something else.** `file_at` raises
  for a directory, where the driver reports a missing file. Pre-flight 3
  checked that the name exists, not what it does on each input.
- **A change breaking a live check.** Two findings. `run_stack_batch`'s
  docstring sits at the `prose` gate's ten-line limit, and the spec asked to
  extend it. A witness told to replace the rig's fetch double would break two
  `preserves` witnesses. Pre-flight 6 reads enumerators, not limits.
- **A data flow the base cannot carry.** `SA-0295`'s cell is cut from
  `SA-0279`'s branch, and `SA-0279` does not depend on `SA-0294`. A linear
  stack carries it, which the spec now says. Pre-flight 4 reads `touches`,
  not which branch carries a second parent.
- **A citation one range off.** Two in round 2. `cite` passed both, because
  its moved-text check fires only when the quoted text sits elsewhere.

## What the delegate did by hand

- Reconciled the two drafts' text source.
- Ran the bookkeeping that neither writer could, since both shared a tree.
- Applied round 2's fixes to both specs.

## The next checks

1. **A writer's prototype probes ship with the spec.** Each reviewer called
   the writer's kills "unverified" and asked for a run. A table of each
   wrong version and the probe line that killed it would make that evidence.
2. **A docstring headroom check.** For each docstring a spec says to edit,
   print its line count against `DOCSTRING_LIMIT`. One grep removes a repair
   turn.
3. **A second parent's carrier.** For a `depends_on` with more than one
   entry, say whether the first parent's chain reaches each other entry.
