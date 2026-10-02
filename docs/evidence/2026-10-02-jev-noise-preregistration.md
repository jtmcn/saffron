# Jev's noise score on review notes: the pre-registration

**PROPOSED.** Every value below is a proposal. It takes effect when the
operator approves the pull request that adds this file. Backlog item b-ef334d.

## The pilot, which counts for nothing

`2026-10-02-jev-scores-graded.md` graded Jev's saved answers by hand labels
nobody pre-registered. Over the reviewer's notes alone, at three cutoffs on
Q2's probability of severity 0:

| Cutoff | not-a-defect flagged | acted on and flagged |
|---|---|---|
| 0.4 | 43 of 63 | 20 of 356 |
| 0.5 | 38 of 63 | 10 of 356 |
| 0.6 | 26 of 63 | 8 of 356 |

## 1. What is scored

Every finding a reviewer marks `note` in a counted review round. A note is
flagged when Q2's probability of severity 0 in `jev.ttl` is at least 0.5. A
note with no Q2 answer counts unflagged. A counted review round Jev never
scored still counts, and each of its notes counts unflagged.

## 2. The two classes

- **Noise.** A note labelled `not-a-defect`.
- **Acted on.** A note labelled `real` whose disposition is anything but
  `no-action`.

A `real` note left alone and an `unverified` note count in neither class.

## 3. The bar

Both counts are required.

- **Catch.** At least half of the noise is flagged.
- **Cost.** At most one acted-on note in twenty is flagged.

## 4. Which review rounds count

A spec review or PR review round counts when its `labels.json` carries
`"schema": 2`. Schema 2 exists only from the merge of this file, so every
counted label postdates it. A cell review round never counts. A spec
reviewed on both sides of the merge counts its schema-2 review rounds only.
The labeller writes `labels.json` without reading `jev.ttl`. Nothing in the
loop prints a score, so this rests on that rule alone.

## 5. The scorer and the stopping rule

`harness/jev_grade.py` is the scorer, and `driver.py noise` runs it over every
review round on disk. Its tests pin each rule above. It runs once, on the
first day it reports 40 noise notes or more, over every counted review round
on disk that day. On 2026-12-31 it runs regardless. Under 40 noise notes it
reports `inconclusive`, and that decides nothing.

## What the result decides

A pass files an item to let step 1b and step 2c leave a flagged note
unanswered, still saved and labelled. A fail or an `inconclusive` keeps Q2 as
an observation and closes b-ef334d.
