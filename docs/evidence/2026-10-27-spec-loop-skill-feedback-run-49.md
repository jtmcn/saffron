# Feedback on run-saffron-spec-loop (run 49, 2026-10-26 to 2026-10-27)

Run 49's order was `SA-0320`, `SA-0321`, `SA-0322`, `SA-0317`, `SA-0318`
and `SA-0319`, the last two a chain on `SA-0317`. Their budgets came to $210.
One stack batch ran all six, and its deferred finish ran one follow-up,
`SA-0323`. The run spent about $159.09 of a $400 cap. Seven specs reached a
reviewed pull request, stacked as #976 to #982.

| Spec | PR | Spend of budget | Peak turns of ceiling |
|---|---|---|---|
| `SA-0320` | #976 | $18.54 of $26 | 94 of 140 |
| `SA-0321` | #977 | $49.12 of $85 | 190 of 240 |
| `SA-0322` | #978 | $30.36 of $25 | 92 of 130 |
| `SA-0317` | #979 | $7.63 of $24 | 17 of 140 |
| `SA-0318` | #980 | $12.94 of $28 | 61 of 120 |
| `SA-0319` | #981 | $8.88 of $22 | 52 of 150 |
| `SA-0323` | #982 | $4.42 of $8 | 14 of 40 |

Batch 58's cells spent $127.47. `saffron finish 58` spent about $31.62 on
its agent calls, `SA-0323`'s cell among them. Peak turns are the largest
turn count in each task's `events.jsonl`.

## What the run found

1. **The finishing layer cannot push after a draft (b-e0044f).** Finish 58
   drafted `SA-0323` and `SA-0324`, then committed both into
   `.saffron/specs/`. Its suite counted 40 new failures and escalated. The
   delegate counted 39 `prose` hits in the two drafts and one queue test.
   That test fails `SA-0323`, since its cell already ran.
2. **A review commit shipped a bug no lens read (b-549012).** The
   delegate's fix on #978 dropped a kill whenever an uncounted failure came
   with it. Both seats passed the diff below it, and `make check` was
   green. The finish's end review raised it as a blocker, and `SA-0323`
   fixed it for $4.42.
3. **The seats found five witness gaps the critic missed.** #976, #980,
   #981 and #982 each had a witness that a seat's probe survived. #978 had
   a survivor written as having stayed green. Each one is a rejection line.
4. **Two follow-up drafts had no frontmatter (b-781ea4).** The finish
   pooled both, so two findings filed nothing.
5. **The driver could not take in the finish's follow-up (b-719346).**
   `snapshot --force --add SA-0323` refused it, so the delegate edited
   `order.json` by hand.
6. **A held blocker reached `READY_FOR_REVIEW` (b-92c92a).** `SA-0322`'s
   critic held one blocker after REBUT. Both seats showed its mutant
   equivalent on the path it named, so the delegate withdrew it.
7. **The batch's holds were not in the skill.** A $300 batch holds 25% for
   the end review and 25% for the writer. That left about $150 for $210 of
   specs. The delegate stopped it during the image build, and the operator
   chose $400.
8. **A preflight failure printed a deferral line (b-2a03c2).** Batch 57
   failed on colima's port forward and ran nothing. It still told the
   operator to run `saffron finish 57`.
9. **The watch's hand-overs came hours late (b-2d2014).** Four wake-ups
   arrived in one burst after the review turns ended.

## What the reviews found

Fourteen seats reviewed seven pull requests and raised 37 findings. Review
commits fixed 32. Four needed no action, two of them unchecked, and one was
not a defect. Six were blockers, and all six were real.
`.saffron/rejections.md` holds 17 lines for this run, dated 2026-10-27.
Four of them are adequacy gaps.

This PR carries one hand fix. A docstring in
`test_vocabulary_agrees_with_context.py` lost a perfect tense that finish 58
found.

Nine new items carry what the stack left: b-e0044f, b-549012, b-719346,
b-1b8b1e, b-92c92a, b-2a03c2, b-d2afe3, b-1ff5a3 and b-3a0789.

## Run 48's items, checked

- [x] **The finish reads findings at the layer's pushed head (b-1b05be):**
  done in #976. Finish 58 still ran `main`'s code, so it re-raised four
  in-cell concerns that review commits fixed.
- [x] **`cite` rewrites a construct it finds at one new place (b-009d51):**
  done in #977. No layer of batch 58 was refused for a citation.
- [x] **A host-filed probe runs the tests that reach its file (b-b9365d):**
  done in #978.
- [ ] **A comment-only finding becomes a finishing-layer edit (b-01c53d):**
  open. The writer declined one docstring finding this run.
- [ ] **A gate checks every cited spec id (b-9c5b11):** open. It did not
  recur.
- [ ] **`record` refuses while its batch still runs (b-92fdbe):** open. It
  did not recur, since the delegate recorded on each hand-over.
- [ ] **The witness gate fails a find that matches other than once
  (b-a68b24):** open. It did not recur.
- [ ] **A follow-up draft that does not parse goes back once (b-781ea4):**
  open. It recurred twice.
- [ ] **The adequacy lens probes the way the Spec seat does:** open. Five
  witness gaps this run came from a seat's probe.

## Summary: what Saffron should absorb next

1. **The finishing layer retires a follow-up whose cell ran (b-e0044f).**
   A phase change. Every finish that drafts a spec escalates today.
2. **A lens reads each review commit (b-549012).** A phase change. One
   review commit this run dropped a kill.
3. **The adequacy lens probes the way the Spec seat does.** A lens change.
   It missed five witness gaps this run.
4. **A follow-up draft that does not parse goes back once (b-781ea4).** A
   phase change. Two findings were pooled for it.
5. **`snapshot` takes in a finish's follow-up (b-719346).** A driver
   change. It cost a hand edit of the order.
6. **A held blocker marks its pull request (b-92c92a).** A gate change.
   One pull request carried one this run.
7. **The skill states the batch's holds.** A skill text change, ranked
   last. It cost one stopped batch.

This PR changes no skill text.

## Next run

The order is empty. Stack #976 to #982 and this PR wait on the operator.
`SA-0324` is a draft in b-1b8b1e, never queued.
