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

## The spec chain as a task, `SA-0226` to `SA-0229`

Item b-98a3be asked which step of the spec chain can be cut on evidence.
The operator chose to move the chain into core. `DESIGN.md` §3.4 and the
vocabulary landed by hand first. Four writers then ran in parallel worktrees.
The `saffron draft` writer stopped at step 1 on size and split into `SA-0227`
and `SA-0229`. Each time below is the agent's own reported duration.

### Cost

| Spec | Draft | Review 1 | Revise 1 | Review 2 | Revise 2 |
|---|---|---|---|---|---|
| `SA-0226` | 22.0 min | 4.1 min | 18.7 min | 3.9 min | 12.0 min |
| `SA-0227` | 18.8 min to the split, then 19.9 min | 6.3 min | 13.1 min | 4.9 min | 12.1 min |
| `SA-0228` | 14.7 min | 3.3 min | 7.2 min | 3.2 min | 7.4 min |
| `SA-0229` | 22.9 min, then 9.9 min to reconcile | 5.2 min | 9.8 min | 4.3 min | 5.6 min |

Writing and revising took 194 minutes of agent time. The eight reviews took 35.
No spec had a third review. Each last revision ran every new wrong version on
its prototype instead, and every one was killed.

### Rounds

| Spec | Round 1 | Round 2 |
|---|---|---|
| `SA-0226` | 1 blocker, 3 concerns, 3 notes | 1 blocker, 2 concerns, 3 notes |
| `SA-0227` | 0 blockers, 6 concerns, 4 notes | 0 blockers, 3 concerns, 3 notes |
| `SA-0228` | 0 blockers, 2 concerns, 4 notes | 1 blocker, 1 concern, 4 notes |
| `SA-0229` | 0 blockers, 5 concerns, 5 notes | 0 blockers, 2 concerns, 3 notes |

### Each finding by class

- **Pinned values that make two builds agree.** The largest class, with two of
  the three blockers. Half-even and half-up rounding agreed on every pinned
  cost. So did rounding each phase before the sum. No fixture drove a float
  or a bool. Stripping an item and dropping its carriage returns both passed.
  The writers listed and killed their wrong versions, but each list missed
  the one the arrangement could not see. Pre-flight 1 asks which member of a
  set the witness drives. It does not ask which input separates two plausible
  implementations of one transform.
- **A caller in an unmerged parent's tree.** `SA-0226`'s round 1 blocker.
  `SA-0224`'s migration test calls `record_spec_review`, and that file does
  not exist at the spec's base. Pre-flight 6 reads the base only. It must also
  read each parent's pushed branch.
- **A build detail the spec left open.** Four `SA-0229` concerns. The spec did
  not say when the item is decoded or what its path is relative to. It also
  did not name the writer's policy loader or the written file's encoding.
  Each had a plausible wrong answer that passed the witness.
- **An operator decision the documents did not yet say.** Withholding a
  draft that declares another id gave `SPEC_WITHHELD` a second meaning. The
  hand edit landed in the spec's pull request.
- **Line drift across unmerged parents.** Two notes and one concern. A
  citation correct at the base moves once the parent merges.

### What the brief got wrong

My first brief put the ontology and `CONTEXT.md` in a cell's `touches`. Both
are `protected`. A writer measured it and the brief was corrected mid-draft.
The `SA-0229` writer drafted against a parent API it had to assume. The
reconcile pass cost 9.9 minutes and one review concern.

### What the next run changes

- Pre-flight 1 should name, for each value a criterion transforms, the input
  that separates each plausible implementation. Rounding mode, encoding,
  type and order were this run's four.
- Pre-flight 6 should read callers on every parent's pushed branch, not only
  at the base.
- A brief should check `protected` before it assigns `touches`.
- A parent and child from one split should be drafted in sequence. The child
  then reads the parent's spec rather than a description of it.

## Twenty-four specs in one evening, `SA-0230` to `SA-0255`

The operator asked for items 119 and 120 first, then every item that needed
no decision of theirs, while they were away. The delegate triaged the open
tier 1 and tier 2 items, then drafted, reviewed and stacked 24 specs.
`SA-0241` was drafted and reviewed, then parked. `SA-0236` and two more of
item 80's specs were designed and not drafted. Both wait on a decision.

### Triage

Seven read-only agents read 48 items against `958db033`.

| Verdict | Items |
|---|---|
| Ready, drafted | 28 items into 25 specs |
| Needs a decision | 80 (the mutants ref), 40/97, 42, 46, 49, b-3c7ce9, b-a8270f, b-4a63b7, b-e471bd, b-a7e5f3, b-490c9c, b-5b1f8a, the second half of b-a6bfb0 and of b-f582ee |
| By hand | 67, b-970f53, b-60d804, b-c94a2f |
| A measurement | 79, 93, b-abeb74 |
| Stale | b-8170eb (b-031ac2 closed it), b-593d50 (its premise is false), most of b-a4df62 (ADR 7 built it) |

### Decisions the delegate took

Each is the operator's to overturn. The pull requests name them.

- 119: hold back the smaller of $1.00 and half the remainder for the salvage
  turn. The reserve came from 7 measured salvage turns, the most $0.40.
- 120: REBUT always runs under its own cap, never the remainder. The cap
  is $10.00, by `SA-0203`'s own rule on 67 REBUTs, the most $9.29.
- b-f582ee, b-a6bfb0, b-34d743, b-04a5d9: the half or arm that needed no
  design call.
- b-60a399: infrastructure means `CellRuntimeError` alone.

### Rounds

| | Specs | Blockers | Concerns |
|---|---|---|---|
| First review | 25 | 7 | 67 |
| Second review | 11 | 4 | 19 |

Two first reviews found nothing to fix, `SA-0253` and `SA-0247`. Each
review took 3 to 10 minutes. Each draft took 19 to 49 minutes. A third
review never ran. The delegate fixed second-round findings by hand where
they were text, and sent them to the writer once where they needed a
prototype.

### Each finding by class

Counted over first reviews, blockers and concerns only.

| Class | Count | Caught by |
|---|---|---|
| A fixture that cannot tell the change from a narrower build | 14 | pre-flight 1 |
| The delegate's own hand edit to a protected file | 7 | pre-flight 12 |
| A spec drafted against a base without its parent's code | 6 | none yet |
| A witness green in the cell and red on the host, or the reverse | 5 | none yet |
| Two criteria, or a criterion and an instruction, disagreeing | 4 | pre-flight 2 |
| An operator decision the item left open | 4 | triage |
| Dictated text the `prose` gate refuses | 1 | pre-flight 12 |

The largest class is still the one pre-flight 1 names. The pre-flight asks
which members of a set the witness drives. These findings were inputs that
separate two builds of one transform. Examples are a remainder between $1
and $2, a base off `main`, and a message holding a newline.

### What the brief got wrong

- Briefs named parallel siblings as parents with a line range. Six specs
  drafted against `958db033` were wrong at their real base. The writers had
  no tree with the parent's code to read.
- One brief named `SA-0236`, which was then parked. Two specs carried it in
  `depends_on` until the delegate caught it.
- Item 120's first brief kept the $7.00 cap. The writer measured $9.29 and
  the brief changed.

### Tools this run needed

- `fixpin2.py` re-pins the queue smoke test from the tree it runs in. It
  replaces the per-layer hand merge that every earlier stacked run did.
- `stack.py` rebases each branch's own commits onto its parent and re-pins.
  It stopped once, on a `DESIGN.md` conflict between two specs' hand edits.
- The shared scratchpad cost three writers a prototype. One applied another
  writer's diff by mistake and reverted it.

### What the next run changes

- Draft a stacked child only after its parent's prototype exists, and hand
  the writer that diff. That removes the largest new class.
- Pre-flight 12 needs a command. Seven of the delegate's own sentences
  overclaimed. A check that reads each hand edit against its spec's claims
  would catch most of them.
- Give each writer its own scratch directory in the brief, not a shared
  scratchpad.
- The reviewer's prompt still says the cell's git is 2.39.5. It is 2.47.3,
  measured twice today.
