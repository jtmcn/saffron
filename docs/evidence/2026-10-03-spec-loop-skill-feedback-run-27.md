# Feedback on run-saffron-spec-loop (run 27, 2026-10-03)

Run 27 ran the three specs the spec chain queued in #652 to #654: `SA-0197`,
`SA-0198` and `SA-0199`. Run 26's feedback is checked below.

**Outcome:** three specs reached `READY_FOR_REVIEW`.
- Two spec PRs merged before their cells: #657 and #663.
- The stack is #659, then #662, then #670, with step 5 on top.
- The cells cost **$58.67** against $87 of budget, as the ledger records it.
  `SA-0199` spent its whole $33.00.

| Spec | PR | Spent | Peak turns | In-cell blockers | Seat blockers the critic passed | Review commits |
|---|---|---|---|---|---|---|
| `SA-0197` | #659 | $11.36 of $23 | 42 of 180, one repair | 0 | 3 | 1 |
| `SA-0198` | #662 | $14.31 of $31 | 94 of 180 | 0 | 1 | 1 |
| `SA-0199` | #670 | $33.00 of $33 | 174 of 200 | 3, withdrawn after REBUT ($5.82) | 6 | 1 |

## What happened, in order

1. **Step 1b found a second parent that carries no code.** `SA-0199` declared
   `depends_on: [SA-0198, SA-0197]`. A cell is cut from `depends_on[0]`
   alone. The operator chained the three specs in #657 (b-c94a2f).
2. **No review had read any spec's final text.** The chain's last edits were
   hand edits or an unreviewed revision. Round 1 found no blocker and ten
   concerns.
3. **Two concerns were measured, not argued.** ext4 in the cell image lists
   directories in creation order. A `KeyboardInterrupt` that escapes a test
   aborts pytest, and the `tests` gate then reads `error` (b-970f53).
4. **The operator made three calls at step 1b.** The chain, the accept rate's
   window as written, and a failed page rewrite that goes on with the night.
5. **Auto mode refused both spec PR merges** under the standing grant. The
   operator said "merge 657" and "merge 663" in chat.
6. **`SA-0198`'s first start stopped at preflight.** Colima started between
   two cells and listened on port 53. The operator stopped it, and the re-run
   went green (b-835bfb).
7. **`SA-0199`'s step 1b took five rounds.** Rounds 2 to 4 each found a hole
   in the delegate's own fix of the round before.
8. **REVIEW worked on `SA-0199`.** Two of its three blockers were declared
   wrong versions its host-filed probes caught. REBUT fixed both.
9. **The seats still found ten blockers the critic passed.** Each was a part
   of a claim no assertion told apart from a wrong build. Four on #670 were
   parts the spec's notes asked for and the cell dropped (b-20043f).

## Run 26's items, checked

1. **Re-prompt a malformed wrong-version answer (b-7251b5)**: not seen. All
   three answers parsed. Each gap was a version REVIEW could not express.
2. **A refused API connection is infrastructure (b-031ac2)**: not seen. The
   one refused start was preflight's, and it exited 2 as it should.
3. **A lens that walks each part of a claim to its assertion**: not absorbed.
   Seen again: all ten seat blockers had that shape.
4. **Leave the suite to GATE (b-23a149)**: not seen. No session hit its wall.
5. **The parent-branch review belongs in `next`**: not absorbed. Both ran.
   `SA-0198`'s found notes only. `SA-0199`'s found the header witness hole.
6. **Spec review checks each printed line on every path**: not seen.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` are the evidence.

1. **A check that each witness drives what its claim and notes ask.** A lens
   change, and b-20043f's gate. All ten seat blockers were a part of a claim no
   assertion distinguished. Four were parts the notes spelled out.
2. **Read an interrupted pytest session as `fail` (b-970f53).** A gate change.
   It now charges wrong code to the gate, and skips the rest of the suite.
3. **Refuse a second `depends_on` entry at intake (b-c94a2f).** An intake
   change. Its parent's code never reaches the cell, and its open PR refuses
   the child on a plain night.
4. **Show the operator which criterion failed (b-3b8eb2).** A phase change.
   The delegate guessed the cause from the repair turn's edits.
5. **Probe the host before a cell starts (b-835bfb).** A driver change.
6. **Tell a test-side wrong version from an unproven one (b-3c17ab).** A
   REVIEW change.

## The loop's own gaps

- **The delegate's witness edits need a measurement.** Three rounds each
  found a hole in the last fix. A run of the arrangement would have settled
  it once, as the skill says for an `unmeasured` one.
- **Auto mode refuses `gh pr merge`** for a spec PR the grant covers. Each
  merge waited for the operator to say so in chat.
- **The session's guard refuses** `for` loops, `$(…)` in an argument and
  `printf` with backticks. `jev.sh` and `cell.sh` wrap the credentials.
- **`bookkeeping` could not step the smoke test's ordinal** after a merge of
  `main` rewrote the docstring's top paragraph. The delegate wrote it by hand.
