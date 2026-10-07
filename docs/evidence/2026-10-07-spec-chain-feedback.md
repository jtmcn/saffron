# Spec chain feedback, 2026-10-07

## The task page's spec, diff size and model, `SA-0225`

Item b-5aa016 came from the operator reading the view in use. The protected
half landed by hand first, as the view specs before it did. That was three
vocabulary terms, their shapes, three query columns and one §6.2 sentence.
The spec then covers `graph.py`, `server.py` and one rename in `pr_body.py`.

### Cost

| Step | Time |
|---|---|
| Draft | 22.0 min |
| Review 1 | 6.7 min |
| Revise 1 | 13.8 min |
| Review 2 | 4.1 min |
| Revise 2 | by hand, three sentences |

The draft did not split. A prototype measured 1467 tokens, then 1739 after
round 1, against a split line of 2400. Round 2's fixes were a missing case
and two fixture sentences, so they landed by hand with no third review.

### Rounds

| Round | Blockers | Concerns | Notes |
|---|---|---|---|
| 1 | 0 | 4 | 4 |
| 2 | 1 | 2 | 3 |

### Each finding by class

- **A claim over a set whose witness drives one member.** Round 2's blocker
  and one concern. The criterion named four reasons, and no case drove
  `hash mismatch`. It also claimed git "cannot run", and no case removed
  git. Pre-flight 1 would catch both if run per reason. The writer's
  prototype killed every listed wrong version, so a kill count does not
  prove the cases cover the claim.
- **A fixture that makes a wrong build right by coincidence.** One concern
  in each round. The unbatched decoy sat first only by creation order, and
  the witness mirror would have shared the first repo's path. This is
  yesterday's class again.
- **A name the spec leans on that means something else.** Two round 1
  concerns. `file_at` reads in text mode, so a CRLF spec would hash wrong.
  A disclosed mutant's error still carries the parsed spec. Pre-flight 3
  covers both, but only by reading the callee's body, not its signature.
- **A reader the spec did not name.** `projection.py` already read specs
  by hash, over every ref rather than `base_sha`. No check asks whether
  the tree already does the job another way.

### What the next run changes

- Pre-flight 1 should list each member of a named reason set beside the
  fixture case that drives it. A table in the brief would have caught
  round 2's blocker.
- Pre-flight 3 should read the body of every function the spec tells the
  cell to call, and not stop at its name and return type.
