# Feedback on run-saffron-spec-loop (nineteenth run after the rework, 2026-09-26 to 27)

Twelve specs ran as one chain, each cut from the one below it. All twelve
reached `READY_FOR_REVIEW` and stack as #539 to #553. Run 18's feedback is
checked below.

**Outcome:** twelve pull requests, linked and marked ready. The cells cost
**$128.12**, which includes two cells refused at PLAN. The operator stopped
the loop after `SA-0156`, which brings spec review into the stack batch. Sixteen
specs stay queued.

| Spec | PR | Spent | Attempts | In-cell findings | Seat blockers | Size |
|---|---|---|---|---|---|---|
| `SA-0178` | #539 | $5.08 of $18 | 1 | 0 | 0 | 741 of 3000 |
| `SA-0179` | #540 | $4.94 of $18 | 1 | 0 | 0 | 831 of 3000 |
| `SA-0180` | #541 | $15.28 of $24 | 1 | 1 blocker | 3 | 2140 of 3000 |
| `SA-0147` | #542 | $10.69 of $18, plus $2.84 refused | 2 | 2 concerns | 1 | 1432 of 3000 |
| `SA-0148` | #543 | $12.80 of $27 | 1 | 0 | 0 | 1688 of 3000 |
| `SA-0149` | #544 | $16.62 of $26 | 2 | 1 blocker, fixed in REBUT | 5 | 2625 of 3000 |
| `SA-0155` | #545 | $17.00 of $27 | 2 | 0 | 4 | 2806 of 3000 |
| `SA-0168` | #546 | $10.82 of $25 | 2 | 2 concerns | 0 | 1515 of 3000 |
| `SA-0181` | #549 | $5.85 of $22 | 1 | 1 concern | 3 | 1330 of 3000 |
| `SA-0169` | #550 | $2.09 of $22, plus $1.44 refused | 1 | 0 | 1 | 1098 of 3000 |
| `SA-0175` | #551 | $9.75 of $26 | 3 | 1 concern | 1 | 3947 of 3000 |
| `SA-0156` | #553 | $12.92 of $27 | 2 | 1 blocker, fixed in REBUT | 1 | 1937 of 3000 |

Sizes are after review. `SA-0175` runs at `standard`, where `size` only
advises, and the operator accepted it.

## What happened, in order

1. **The operator skipped step 1b.** The specs had been reviewed before the
   loop. No fact records that review, so the driver cannot tell (b-22ff3f,
   again).
2. **`SA-0147` was refused at PLAN.** Its plan priced 5800 changed tokens
   against 3000 at `elevated`. No spec in the chain declared
   `estimated_lines`, so `check` had nothing to price. The operator had it
   split into four specs through the spec chain, two review rounds and #538.
   The detour took about two hours.
3. **`SA-0178` ran on a merged parent's old branch.** `saffron cell` stacked
   it on `saffron/SA-0159` at `fd6513a6`, because run 18's merge was never
   reconciled in the ledger. The cell ran the gates from before #535.
   `saffron queue` reconciles, and `saffron cell` does not.
4. **`SA-0169` was refused at PLAN on a unit mistake.** Its plan read the
   spec's "about 2080 tokens" as 2100 lines, and the checkpoint multiplies
   lines by four. The change measures 2094 tokens. The operator had it split,
   and had the remaining sixteen specs priced before their cells. Seven priced
   over the ceiling and five within 20% of it. Only the three that could be
   refused at PLAN were changed, in #547. The detour took about 3.5 hours.
5. **The IMPLEMENT wall bound cut six of twelve first sessions and one repair.**
   `TURN_TIMEOUT_S` is 900 seconds. The cuts land mid-thought, after a tool
   call, and these specs need 60 to 110 turns. Salvage and a repair recovered
   every one, at the cost of an attempt each.
6. **A cut session left `SA-0169`'s cell test unwritten.** No criterion
   declares it, so no gate or lens saw it missing. The delegate caught it from
   size alone, 304 tokens against a measured 935. A subagent wrote it, and it
   passed in a real spec-session cell.
7. **The seats found blockers the in-cell critic passed on eight of twelve.**
   Two were build defects: `SA-0180`'s helper did not take the range the spec
   named for `SA-0147`, and `SA-0149`'s raising review left its dependents
   runnable. The rest were witnesses that let a mutant through, mostly one
   unpinned element of an asserted tuple.
8. **The in-cell critic caught its own gaps twice.** `SA-0149`'s and
   `SA-0156`'s criterion probes survived, and each implementer fixed the
   witness in REBUT.

## Run 18's items, checked

1. **`prose` compares hits by text (b-044ae7):** landed before this run. It
   now flags a docstring that shrinks as well as one that grows, and editing
   near an old hit makes the old hit new. Filed as a follow-up.
2. **The `tests` gate keys on pytest's usage error (b-76f08d):** landed. No
   `revert` skip was seen.
3. **`prose` reads comments in string literals (b-43061c):** landed. A code
   span wrapped across a line break still hides a hit.
4. **The stack batch absorbs step 2c:** not yet. `SA-0156` brings spec review
   into the stack batch; the end review's seats landed in run 18.
5. **A gate result's summary reaches `events.jsonl` (b-66e82d):** recurred.
   `SA-0147`'s attempt 1 had two new failures the log does not name.
6. **`snapshot` counts a merged parent as met (b-fab381):** fixed. The order
   held all 22, then 28, specs.
7. **A spec in a chain declares `estimated_lines`:** recurred, and it cost
   two detours. Filed as its own item.
8. **Preflight names processes (b-e0cd57):** not exercised. The four
   tolerated listeners were set up front.
9. **`status` names `snapshot --new` (b-bff670):** not exercised. The first
   command was `snapshot --new`.

## Summary: what to change first

1. **Raise or rethink the IMPLEMENT wall bound.** It cut half the sessions
   of this chain's larger specs. Every cut cost an attempt, and one cost a
   test nobody noticed was missing.
2. **Make PLAN's estimate carry its unit.** One refused cell and a 3.5-hour
   detour came from a token count read as lines.
3. **Price every spec before its cell.** The writer declares
   `estimated_lines`, and `check` applies the measured overrun of about 1.4.
   Both refusals this run would have been caught before a cell.
4. **`saffron cell` reconciles before it stacks.** A merged parent's old
   branch gave one cell stale gates, silently.
5. **One proxy per cell.** It is the only hard blocker to running two cells
   at once, which the chain's real dependency graph could use.
6. **A landed size far under `estimated_lines` is a signal.** It would have
   named `SA-0169`'s missing test without a delegate.
7. **The stack batch absorbs the seats' criterion walk.** The seats found
   blockers the critic passed on eight of twelve pull requests.
