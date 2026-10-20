# Feedback on run-saffron-spec-loop (run 45, 2026-10-19 to 2026-10-20)

Run 45's order was the three specs that waited on stack #916: `SA-0290`,
`SA-0291` and `SA-0295`, $117 in all. #918 refreshed 15 citations first. One
`--stack` batch spent $77.70 of $400 and drained. All three ended
`READY_FOR_REVIEW`, as #919, #920 and #921, linked bottom to top.

## What the run found

1. **REBUT ran on every in-cell blocker.** `SA-0290` drew six criterion-probe
   survivors, and all six sat inside the diff. REBUT fixed each one, and each
   probe was killed on its re-run. `SA-0291` and `SA-0295` each drew one
   blocker, which REBUT fixed. The anchored path of b-e40d09 works. The
   unanchored path did not come up.
2. **The finish committed nothing.** Batch 39's end review left the tree
   unchanged, so run 44's red finish did not recur. It drafted one
   follow-up, `SA-0297`, from #919's packaged head. Two of its three items
   were review commits the delegate held. The batch refused the draft before
   any cell, since its mutant named text its own body carried (b-8a0c9a,
   b-589cf6).
3. **The end review found what both seats missed.** `_whole_word` restated
   `mirror._word_pattern`. A review commit on #919 now imports it.
4. **A cell split each comment with a blank line to pass the two-line
   limit.** The `comment-block` rule reads each half alone. Both seats saw it
   on #920, and the critic did not (b-998bb7).
5. **`make check` passed a docstring the commit hook refused.** The edit was
   unstaged, and the hook reads the index (b-08a36a).
6. **A test left out a field its spec gave it.** The six-criteria leg in
   `SA-0291` gave its fifth criterion no `subject`. So the one case that
   tests the collected run could not fail. The Spec seat's two-edit probe
   found it. REVIEW's adequacy lens and REBUT did not.
7. **`driver.py stack` ordered the stack right.** The order was one chain,
   so `depends_on` and branch order agreed (b-3a79a0 stays open).

## What the reviews found

Six seats reviewed three pull requests. The Spec seats ran about 100
probes, and one survived. Review commits landed on all three. The in-cell
critic raised three of the fixed findings as notes, and passed them.
`.saffron/rejections.md` holds 11 lines dated 2026-10-20. Two new items
carry what the stack left.

## Run 44's items, checked

1. **A host-filed survivor holds its task wherever its edit lands
   (b-e40d09):** not tested. Every survivor this run was anchored.
2. **A spec that adds a refusal is checked against the specs below it
   (b-e7898b):** did not recur. No spec this run added a refusal that
   refused its neighbours.
3. **A stack records each layer's base (b-3a79a0):** did not recur. The
   order was a single chain.
4. **A finish leaves no red commit and writes every follow-up to the tree
   (b-fe82d9, b-703e64):** half. No red commit this time. The follow-up
   `SA-0297` again lives only in the ledger.
5. **The cell's seed fetches the fixture heads (b-055fa3):** not tested. The
   four local fixture branches stayed in place.
6. **`adopt` takes a fixed task back to a waiting state (b-619b7d):** not
   tested. No task this run was adopted.
7. **The `prose` gate reads `.yaml` and `docs/agents/`, and a gate catches a
   test writing outside `tmp_path` (b-e9cd43, b-524b1a):** not tested.

## Summary: what Saffron should absorb next

1. **The end review drafts from the head the delegate will push
   (b-8a0c9a).** A phase change. In two runs running, a follow-up redid fixes
   a review commit held. The cheap form is a batch that hands the end review
   the review commits before it drafts.
2. **The `comment-block` rule joins a comment broken only by blank lines
   (b-998bb7).** A gate change. A cell has learned the split, and the gate
   is the only thing it reads.
3. **A host-filed survivor holds its task wherever its edit lands
   (b-e40d09).** A phase change. Carried from run 44, where it cost a
   reviewable task.
4. **`make check` reads the working tree for `prose` (b-08a36a).** A gate
   change. Today only the commit hook sees an unstaged edit.
5. **A refused follow-up is written to the tree (b-589cf6, b-703e64).** A
   phase change. `SA-0297` holds a number nothing in the tree shows.

No skill-text change shipped here. This PR adds one `check` rule to the
driver. It names a criterion whose mutant edits a file outside `touches`
and declares no `subject:`, the last hand step of b-000d04.

## Next run

Nothing is queued. `SA-0297` was refused and needs no re-run, since review
commits on #919 cover its three items.
