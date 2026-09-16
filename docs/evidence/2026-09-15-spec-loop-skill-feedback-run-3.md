# Feedback on run-saffron-spec-loop (third run after the rework, 2026-09-15)

Six specs queued — `SA-0087` → `SA-0088` → `SA-0089` → `SA-0091` (a chain), plus
`SA-0090` and `SA-0092`. Run from the main checkout, driver as of `0ea4547`.
Run 2's feedback is `2026-09-14-spec-loop-skill-feedback-run-2.md`; its items are
cited here as "run 2, item N".

**Outcome:** one reviewable pull request (#274, `SA-0087`) and $9.77 spent, on one
cell. The operator chose to stop after `SA-0087` before any cell ran, so the
other five specs are reviewed but unrun. Backlog items filed: 131–135.

## Summary: what to change first

1. **The N1 host probe is checked once, and a listener can appear mid-loop**
   (observation 1). It cost one cell start. Nothing spent — preflight runs before
   any agent turn — but the failure names an address and a port, not a process,
   and the operator has to translate. Fix: a GOTCHAS line saying to re-run the
   probe immediately before each cell rather than once per loop, with the
   one-liner that names the process.
2. **`stack`'s dry run still errors on a single reviewable PR** (run 2, item 3;
   still open). The skill's step 2c ends by telling you to run it, and with one
   PR it exits 1 with `a stack needs two or more reviewable pull requests`. That
   reads as a failure at the end of a clean review.
3. **A mutation probe that reverts with `git checkout --` discards the
   reviewer's own fixes** (observation 4). Cost: one silent loss of six edits,
   caught only because two later probes reported `NOT APPLIED: 0`. Fix: a step 2c
   line saying to back the file up to a temp path and restore from that.

**What worked and should stay:** the up-front push question, `snapshot`'s table,
`record`'s spend line, `size` run after the push, and the two seats — which again
found what the lenses did not.

## Run 2's items, checked against this run

- **Item 1, the halt path.** Not exercised: no cell halted. The *recovery* half
  was, and worked exactly as GOTCHAS describes — `SA-0087`'s ceilings were raised
  in a spec PR merged to main, then `snapshot --force` re-queued it at its new
  `spec_sha` and kept every other recorded outcome. Closed as far as this run
  can close it.
- **Item 2, the Monitor.** `budget:` and `PLAN` are in `pattern` now. The 30-minute
  expiry is unchanged and was hit once; re-arming with `tail -n 0 -F` worked and
  did not replay. Still open, still cheap to live with.
- **Item 3, small refusals.** The allowlist is in the command block now. The dry
  `stack` refusal on one PR is unchanged — see above.

## Observations

1. **Preflight refused a cell on a listener that appeared after the loop
   started.** At session start the only non-loopback listener was `rapportd`. By
   the first cell a media player was bound to `10.0.0.105:53991`, and preflight
   ended the run with `host services answered from inside a cell at
   10.0.0.105:53991 — bind them to 127.0.0.1`. Exit 2, $0 spent. The message
   names the address; finding the owner took
   `lsof -nP -iTCP:53991 -sTCP:LISTEN`. Quitting the app's window was not
   enough — the process kept the port, and the same PID was still bound
   27 minutes later.

2. **Step 1b's blockers were decisive, and the backtest caveat did not reach
   them.** Two of the four verified blockers would each have cost a cell:
   - `SA-0087`, check 5 (size vs ceiling): its only measured build came to 293 of
     a `bug` ceiling of 300 that `size` **blocks** on at `elevated`, and the spec
     had grown a whole criterion since. The retype to `feature` was made before
     the cell; the cell's diff came to **515**. At `type: bug` it would have
     failed a blocking gate.
   - `SA-0089`, check 1: the Notes prescribed `runtime.create_network`, which
     defaults to the subnet the implementer's still-live network holds, so it
     raises at REVIEW after IMPLEMENT is paid — and `_stub_the_runtime` stubs
     `create_network` to a no-op, so both witnesses would have gone green.

   Both are worth recording because the standing guidance is to discount step
   1b. That guidance is scoped to two classes the backtest named — check 4
   ceilings, and "witness already green at base". Neither of these is in those
   classes. The discount should stay scoped to the two classes rather than
   widening to the whole agent.

3. **`size` went over the ceiling on review commits for the third time** (item
   40; #247 before, #274 now). The cell left the branch at 515 of 600; review
   commits took it to 644. The skill's ordering — push, then `size`, then ask —
   worked, and the operator accepted the overrun on item 40's own reasoning.
   Three occurrences is the evidence item 40 is waiting for.

4. **A probe helper reverted with `git checkout -- <file>` and silently
   discarded the reviewer's own fixes.** `git checkout --` restores `HEAD`, not
   the working state, so after the first probe every subsequent probe ran against
   the cell's unfixed source. Two later probes reported `NOT APPLIED: 0`, which is
   what surfaced it. Restoring from a `cp` backup is the fix, and the re-run
   changed one result: the commit-failure classification **survived** its probe
   and needed a witness of its own.

5. **The two seats found six blockers past three lenses that found none between
   them** on correctness and contract. The Standards seat found the one that
   mattered most — `git add -A` letting an agent end its task as infrastructure —
   which is a product defect rather than a standards one, so the seat's remit
   caught something outside its own description. The Spec seat independently
   confirmed both adequacy concerns as survived, and found three more dead
   witnesses. No overlap between the seats except those two.

6. **`record`, `status` and `size` all read correctly.** `record` exited 0 with
   `SA-0087  READY_FOR_REVIEW  #274  $9.77 of $20.00`; `status` showed the
   `reviewed <sha>` column after the review commit.

7. **Step 5's records check caught a bad section name immediately** — the body
   sections are a closed set, and `RecordError` named the file, the offending
   section and the allowed three. Nothing to change.
