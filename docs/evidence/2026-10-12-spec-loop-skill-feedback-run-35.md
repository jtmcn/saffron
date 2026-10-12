# Feedback on run-saffron-spec-loop (run 35, 2026-10-12)

Run 35 took all 11 queued specs, `SA-0260` to `SA-0271`. The operator chose
one `--stack` batch at $962. The spec budgets total $393.

Eight specs became a stack, #827 to #847. `SA-0269` ended `EXHAUSTED` at
$41.03 of $36, and its two children were refused for depending on it.

## What happened, in order

1. **A halted task's row stayed in flight after its PR merged.** Batch 22 left
   `SA-0259` at `REVIEWING` with no `pr_url`. #809 merged, and `reconcile`
   never saw it, because it asks GitHub only about rows with a PR. The
   delegate stamped the row `MERGED` by hand, on the operator's word.
2. **Batch 23 failed on an empty image store.** The cell runtime held no
   images, not even the proxy. `container run` then asked Docker Hub for
   `saffron/proxy` and got a 401. The batch exited 2 at $0 and wrote a
   `GATE_ERROR` row for `SA-0260`. The delegate built both images by hand and
   started batch 24.
3. **`make check` passed a comment the commit hook refused.** A review edit
   on #829 grew a comment to three lines. `make check` exited 0, and the
   `prose` hook then refused the commit. The ratchet reads only the staged
   index, so an unstaged edit passes `make check`.
4. **A witness asserted a default value, so the fallback it named was
   unwitnessed.** On #845 the REBUT fix asserted `effective_risk ==
   "standard"` on a spec with no `risk:`. The adequacy lens confirmed the
   blocker still stood, and the task packaged anyway. Both seats found it
   again.
5. **Cells cite `CONTEXT.md` for notes it does not hold.** #844 cited "ADR 7,
   criterion N", and #845 cited four `CONTEXT.md` notes that do not exist or
   that say the opposite. No gate reads citations.
6. **The `witness` gate caught a surviving mutant and blocked nothing.** On
   #846 the witness looped over the set the declared mutant shrinks. The
   gate reported "1 of 2 witness(es) survived their own mutant" twice.
   `witness` blocks only at `elevated` risk, and `SA-0267` was `standard`.
   The Spec seat found it again by hand.
7. **`SA-0269` ran out of budget on its third gate attempt.** Attempt 1 had
   26 new failures, attempt 2 had 4, and attempt 3 had 4. Its branch is
   pushed with no PR.
8. **The end review found three real blockers the seats missed.** It read
   the packaged heads, before the review commits. Its `SA-0262` docstring
   concern was already fixed. Its crossed-pair witness on `SA-0262` and two
   swapped versions on `SA-0267` were new. The delegate fixed all three
   before the push. None of its fifteen findings became a follow-up.
9. **The driver measured and linked the wrong stack.** Batch 24 put
   `SA-0261` below `SA-0264`, against the snapshot. `size` and `stack`
   rebuild the order from `depends_on`, so three layers measured 0 and three
   counted a parent. The dry `stack` linked the PRs out of order. The
   operator marked them ready with `gh pr ready` on the batch's own bases.
10. **One layer is over its ceiling.** `SA-0265` measures 3076 tokens
    against 3000 after review. The operator accepted it.

## Run 34's items, checked

1. **A lens that fails ends its task in a decided state (b-032c3e,
   b-f7a591)**: pending. The operator moved b-032c3e to tier 1, and
   `SA-0259`'s row needed a hand stamp.
2. **A check that each witness drives every part of its claim (b-20043f)**:
   pending. It recurred on #828 as one bound driving both cuts.
3. **A spec review that checks prescribed text against `CONTEXT.md`**:
   filed as b-aff9ea. `SA-0268` prescribed a false README line.
4. **An end review over the reviewed heads (b-8a0c9a, b-27bacc)**: pending.
   It recurred as item 8 above.
5. **A driver that stacks and restacks the chain (b-f10412)**: pending. It
   recurred as item 9 above.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-12 are the
evidence.

1. **`witness` blocks at every risk tier (b-02d328).** A gate policy
   change, and the cheapest here. The host already ran the mutant and saw it
   survive. One `blockingAt` line in `ontology/factory.ttl` decides it. It is
   the operator's gate-policy call.
2. **Preflight names a missing image (b-1c20da).** A gate change. A batch
   whose proxy or base image is absent refuses before any row is minted.
3. **A lens that fails ends its task in a decided state (b-032c3e,
   b-f7a591).** A phase change, carried over from run 34.
4. **A `terms` rule that resolves citations (b-54ad4f).** A gate change.
   Eight comments across two layers cited entries that do not exist.
5. **The adequacy lens names a default-valued witness (b-714ccd,
   b-20043f).** A lens change. A confirmed blocker after REBUT should keep
   the task from packaging.
6. **The spec reviewer checks prescribed text (b-aff9ea).** A lens change on
   the spec chain.
7. **An end review over the reviewed heads (b-8a0c9a, b-27bacc).** A phase
   change, carried over from run 33. This run it found real blockers, so
   reading the current heads makes it worth more.
8. **A driver that reads the batch's own stack (b-f10412).** A skill change,
   ranked last.

## The loop's own gaps

- **Seats stay.** The seats found a blocker the critic missed on four of
  eight layers.
- **The end review earns its place.** It found three blockers both seats
  missed. Read its findings before the push, not after.
- **Stage before `make check`.** The skill says so, and run 35 still lost a
  commit to it. A `make check` that runs the staged ratchet removes the step.
- **The GitHub API limit bites in step 5.** One `gh pr list` search hit the
  hourly limit after the stack's reads. Read merged PRs from `git log`.
