# Feedback on run-saffron-spec-loop (eighteenth run after the rework, 2026-09-26)

Nine specs ran as one chain, each cut from the one below it. All nine reached
`READY_FOR_REVIEW` and stack as #531. Run 17's feedback is checked below.

**Outcome:** nine pull requests, #522 to #530, linked and marked ready. The
cells cost **$111.81** of **$209** budgeted. No cell ran twice.

| Spec | PR | Spent | Attempts | In-cell blockers | Seat blockers | Size |
|---|---|---|---|---|---|---|
| `SA-0142` | #522 | $10.15 of $18 | 1 | 1 | 1 | 1065 of 3000 |
| `SA-0143` | #523 | $15.18 of $27 | 2 | 1 | 1 | 1595 of 3000 |
| `SA-0144` | #524 | $13.57 of $20 | 1 | 2 | 0 | 1085 of 3000 |
| `SA-0145` | #525 | $14.18 of $24 | 2 | 0 | 0 | 1737 of 3000 |
| `SA-0146` | #526 | $15.57 of $27 | 1 | 2 | 6 | 2938 of 3000 |
| `SA-0153` | #527 | $12.44 of $28 | 2 | 0 | 1 | 2944 of 3000 |
| `SA-0154` | #528 | $16.17 of $28 | 2 | 1 | 2 | 2836 of 3000 |
| `SA-0157` | #529 | $8.92 of $22 | 1 | 0 | 2 | 1746 of 3000 |
| `SA-0159` | #530 | $5.62 of $15 | 1 | 1 | 1 | 241 of 1300 |

Every in-cell blocker was withdrawn after REBUT. Sizes are after review.

## What happened, in order

1. **`status` named the wrong command.** Run 17 had merged, and `status`
   said to run `snapshot --force`. That exited 1 with no candidates.
   `snapshot --new` was right, and neither output said so (b-bff670).
2. **`snapshot` kept nine of thirty-one specs.** `SA-0147` depends on
   `SA-0159` and on `SA-0138`, which had merged. `_order` admits a refused
   child only when every parent is in the order, so it stranded twenty-two
   specs. The refusal line named `SA-0159`, which was in the order
   (b-fab381).
3. **The operator skipped step 1b.** The spec chain in #508 had reviewed all
   nine. No fact records that review, so the driver cannot tell (b-22ff3f).
4. **Preflight refused the first start on the same two listeners as run 17.**
   The message named ports. The delegate found RAATServer and limactl with
   `lsof`, and the operator tolerated both (b-e0cd57).
5. **`terms` failed at base on all nine cells.** It is b-f4eb52's false
   positive, and the policy marks the gate advisory. The skill still sends
   every base failure to the operator.
6. **The `prose` gate misled a repair turn.** `SA-0143`'s first attempt added
   an em dash and a 34-word sentence to `run_task`'s docstring. The repair
   turn was pointed at an older comment near line 421. It rewrote that
   comment, the file's count went flat, and the cell's own hits shipped
   (b-044ae7).
7. **`revert` skipped `SA-0144`'s witnesses, and nothing said why.** The Spec
   seat traced it to the `tests` gate reading `error: unrecognized
   arguments` in captured output as its own error (b-76f08d).
8. **The wall bound cut two IMPLEMENT sessions.** `SA-0153` had four commits
   and `SA-0157` had none. Salvage recovered both, and each passed its gates
   on the next attempt.
9. **Three specs landed at the size ceiling.** `SA-0146` packaged at 2987 of
   3000, `SA-0153` at exactly 3000, and `SA-0154` planned 3800. No spec in
   the chain declares `estimated_lines`, so `check` had nothing to price.
   Review shrank each.
10. **The seats found defects the in-cell critic passed on seven of nine.**
    `SA-0146`'s Standards prompt judged a repo's words against Saffron's own
    glossary. Both seats found it, and no lens did. Witness gaps survived on
    `SA-0142`, `SA-0143`, `SA-0144`, `SA-0146`, `SA-0153` and `SA-0154`.
11. **Docstrings grew unseen five times, and text in string literals escaped
    `prose` three times.** Review fixed each by hand (b-044ae7, b-43061c).

## Run 17's items, checked

1. **`census` accepts a declared removal (b-f30189):** not exercised.
   `census` passed on every cell.
2. **Spec review reads `census`:** not exercised, since step 1b was skipped.
3. **Gate failure identities reach `events.jsonl` (b-66e82d):** recurred.
   `revert`'s skip reason reached no record. Two repair turns read gate source
   to learn what failed.
4. **The base-failure rule reads the policy:** recurred on all nine cells, and
   the delegate treated `terms` as a note without asking. The skill text is
   unchanged.
5. **`driver.py status` reconciles merges (b-bff670):** recurred, point 1.
6. **Preflight names what it refuses (b-e0cd57):** recurred, point 4. This is
   its third run in a row.

## Summary: what to change first

1. **`prose` compares hits by text, not counts per file (item b-044ae7).** It
   cost a review commit on six of nine pull requests and misdirected one
   repair turn. A gate change ends all of it.
2. **The `tests` gate keys on pytest's own usage error (item b-76f08d).** A
   one-line gate fix. Every spec that adds a CLI flag has a blind `revert`
   until it lands.
3. **`prose` reads comments in SQL and prompt strings (item b-43061c).** Three
   pull requests shipped text no rule reads.
4. **The stack batch absorbs step 2c.** The Spec and Standards seats found
   what the lenses passed on seven of nine. `SA-0146` and `SA-0153` built those
   seats as end-review lenses, and `SA-0157` wires them into `saffron batch
   --stack`. Once it merges, the next run can let the batch read each layer
   and compare its findings with the hand seats.
5. **A gate result's summary reaches `events.jsonl` (item b-66e82d).** A
   repair turn and the delegate both guessed what failed.
6. **`snapshot` counts a merged parent as met (item b-fab381).** A skill
   driver fix that unblocks the other twenty-two specs.
7. **A spec in a chain declares `estimated_lines`.** Three specs landed at the
   ceiling with no warning before the cell. The spec writer's text should ask
   for it. An intake refusal for a `feature` spec with none is the gate form.
8. **Preflight names processes (item b-e0cd57).**
9. **`status` names `snapshot --new` once a loop's pull requests merge (item
   b-bff670).**
