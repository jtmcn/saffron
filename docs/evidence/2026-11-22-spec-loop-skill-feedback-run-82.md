# Feedback on run-saffron-spec-loop (run 82, 2026-11-22)

Run 82 kept the goal of runs 55 to 81: implement every backlog item. It ran
`SA-0419` in two batches.

| Batch | Spec | PR | Outcome | Spend of budget |
|---|---|---|---|---|
| 101 | `SA-0419` | none | spec review routed `revise`, no cell | $3.22 of $32 |
| 102 | `SA-0419` | #1290 | `REBUTTAL_UNJUDGED` | $13.87 of $32 |

Both batches ran with `--stack --defer-end-review`. Batch 101 first refused
`--budget 50`, since it holds a reserve and a writer share. It then ran at
$80. Its spec review routed `SA-0419` to revision over mutants its clone
could not see. The revision needed $63 against $56.78 left, so no cell
ran. Batch 102 ran at $100, its spec review routed `run`, and its cell
reached REVIEW. REBUT's agent then exited on an API error with no output.
By the operator's call, the delegate took the branch by hand.

Beside the loop, the spec chain merged `SA-0421` (#1289) and `SA-0422`
(#1291). The witness pattern hand edit from `SA-0416` merged as #1287,
and a stale citation in `SA-0419` was fixed in #1288.

## What the run found

1. **A spec review revised a spec over a mutant it cannot see.** The ref
   is kept out of cells on purpose, and the host can read it. Filed as
   b-216235.
2. **REBUT died on an API error, and nothing retried it.** The task halted
   at `REBUTTAL_UNJUDGED` after $13.87. Three host probes were left for a
   person.
3. **`saffron adopt` refused the halted task.** So #1290 merged with no
   adopted task, and `driver.py size` could not measure it. Recorded on
   b-619b7d.
4. **A record push stalled for over two hours.** The batch waited with no
   output until a person killed the push. Filed as b-65eb8f.
5. **An exception kill is not always weak.** Three of the Spec seat's
   probes died "only by errors", because each wrong version raised where
   the claim says the call succeeds. b-c2f264 should count an exception as
   a survivor only when the claim expects no exception.
6. **Each host probe died on a neighbour, not on its own witness.** The
   critic's three probes all died somewhere in their files. Each
   criterion's own witness let its probe through.

## What the reviews found

- `SA-0419`: the delegate's first review commit answered the three host
  probes. The Spec seat then ran 34 probes and found three blockers. Each
  was a positive case the claim names and no witness drove. The Standards
  seat found four notes. Two were fixed, and two were kept as they stand.

## Run 81's items, checked

- [ ] **The `witness` gate reads an exception-only kill as a survivor:**
  open, on b-c2f264. Item 5 refines it.
- [ ] **The adequacy lens moves a claim's deciding case off each edge:**
  open.
- [ ] **The follow-up writer's draft meets `prose` before the suite:** open,
  on b-703e64. No finish ran this run.
- [ ] **A rate-limited task resumes its cell instead of starting over:**
  open.
- [ ] **The driver fills the seat prompts:** open.
- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2.

## Summary: what Saffron should absorb next

1. **REBUT retries an agent that exited on an API error.** A phase change,
   with no item yet. Item 2 is the evidence.
2. **The host checks a spec's mutants before its spec review.** A phase
   change, on b-216235. Item 1 is the evidence.
3. **A record push runs under a time limit.** A tool change, on b-65eb8f.
4. **The `witness` gate reads an exception-only kill as a survivor where
   the claim expects success.** A gate change, on b-c2f264.
5. **`saffron adopt` takes a halted task.** A tool change, on b-619b7d.

This PR changes no skill text.

## Next run

Run 83 runs `SA-0421`, then `SA-0422`, which depends on it.
