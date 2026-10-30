---
id: b-78a590
title: A criterion probe names one edit against a claim of up to twelve sentences, so the seats still find the sentences it left
status: open
tier: 1
filed: 2026-10-30
specs: []
prs: []
commits: []
cites: [§5.4.1, §5.5.1]
related: [b-2750d5, b-7e69d0, 117, b-27bacc, b-98dc4d]
---

## Problem

Ranked third in the spec loop's runs 49 and 50, under the words "the adequacy
lens probes the way the Spec seat does". The spec chain of 2026-10-27 skipped
it because it had no record. This is that record.

Every loop feedback since 2026-09-14 says the review seats found a defect the
in-cell critic missed. Run 49 counted five witness gaps the seats found and
the critic did not. Run 50 counted nine, all real, five of them after REBUT.
`.saffron/rejections.md` holds 43 lines in its adequacy bucket. Each is a
witness a seat's probe got past and a review commit then strengthened.

The host already probes each claim. `run_criterion_probes` buys one fresh
session per criterion (`saffron/phases/review.py:483`), and `criterion-probe.md`
asks it for "the smallest edit to the source" that makes the claim false. One
edit comes back, and `_apply_criterion_probes` runs the criterion's witness
under it (`saffron/cell/session.py:1942`). The spec's own `wrong_versions`
add more edits, but `DESIGN.md` §5.4.1 says what those are worth: an edit
steered by the author's list is no evidence about what the list missed.

Measured over the 22 `SA-03xx` tasks whose records sit in
`~/.saffron/batches/v0/`: 122 criterion probes, 6 survived. 518 wrong
versions, 25 survived.

`SA-0327` (#996) shows what one edit per claim misses. Its six claims run 6,
2, 10, 10, 12 and 8 sentences, and each sentence states something a witness
could fail to read. Each got one edit. Two survived. The Spec seat then ran
43 probes over the same six claims, and five survived. Review commit
`d9c418ee` strengthened the five witnesses:

- claim 1's emitted line names the written path
- claim 3's commit diff adds the draft's path alone
- claim 3's judged path is the draft's
- claim 6's `verify` passes `reverify` both shas
- claim 5's parse send-back followed by a red judgement pools once

Each is a sentence of a claim the cell had probed, at a different sentence.
The seat's advantage is not a better edit. It is one edit per sentence.

## Done looks like

The criterion probe session is shown one claim and the diff, as today. It
names one edit per sentence of that claim, up to a ceiling the prompt states,
and each edit names the sentence it makes false. The host applies every edit in the
gate-only cell and runs the criterion's witness under each. A survivor is an
`adequacy` blocker for REBUT, as one is today. `criterion-probes.json` lists
each edit under its criterion the way `wrong-versions.json` lists each
version, and the REVIEW line counts edits over criteria. The session still
never sees the witness.

The number to watch is the adequacy bucket of `.saffron/rejections.md` per
loop run. Three runs in a row where no Spec seat probe survives a witness the
cell probed means the seats can go. If the number does not move, the next arm
is the seat's other habit: a session shown the witness, asked for the edits
it would not notice.

## Record

- 2026-10-30: filed by hand, from runs 49 and 50 and the `SA-0327` probe
  records.
