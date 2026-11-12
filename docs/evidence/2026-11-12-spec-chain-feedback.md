# Spec chain feedback, 2026-11-12

Continues `docs/evidence/2026-11-11-spec-chain-feedback.md`. Check numbers
carry on from its 41.

## SA-0381 (b-4a9207), after spec loop run 65

A follow-up draft that declares `depends_on` has those lines cut before
`_validate`. Finish 83 pooled all three of its groups for that refusal. The
writer measured $10.27 and 12 suites spent on them, and 55 findings in 16 of
67 finishes pooled the same way. It also found that the drafts declared the
top layer, not their origin's parent, which corrected a Record line.

**Review 1: 1 blocker, 3 concerns, 2 notes.** The writer revised.

- The claim listed every reader of the cut text but the returned candidate's
  `spec`. The batch's gate 0 compares that spec's `depends_on` with the
  recorded text, so a version returning the uncut spec passed the witness.
  Pre-flight 1 missed it, since the set was readers after the function
  returns.
- The claim and Out of scope answered a quoted key differently.
- A column-0 comment inside a list could move its entries into `forbidden`
  after the cut. A guard now keeps the cut only when the parsed spec matches.
- `send_back` quoted the uncut text while `judge` reported cut-text lines.

**Review 2: 0 blockers, 1 concern, 3 notes.** The concern asked for a mutant
on the ref for an edited function. The spec keeps the honest `skip`.

## Checks to build (SA-0381)

42. A claim that lists the readers of a changed value names each reader
    after the function returns, and the gate that later compares it.
