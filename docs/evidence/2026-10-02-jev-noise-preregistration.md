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

Every finding a reviewer marks `note` in a counted spec review or PR review
round. A cell review round is out, since nothing labels it. A note is
flagged when Q2's probability of severity 0 in `jev.ttl` is at least 0.5.

## 2. The two classes

- **Noise.** A note labelled `not-a-defect`.
- **Acted on.** A note labelled `real` whose disposition is anything but
  `no-action`.

A `real` note left alone and an `unverified` note count in neither class.

## 3. The bar

Both counts are required.

- **Catch.** At least half of the noise is flagged.
- **Cost.** At most one acted-on note in twenty is flagged.

## 4. The cutoff

A review round counts when the commit in its `round.json` descends from the
merge commit of this file. `git merge-base --is-ancestor` decides it. Its
`labels.json` carries `"schema": 2` and is written before anyone reads its
`jev.ttl`.

## 5. The stopping rule

Scoring ends at 40 noise notes. A hard stop falls on 2026-12-31 in case they
never arrive. The scorer copies the 2026-10-02 script, adds the cutoff filter
and changes nothing else.

## What the result decides

A pass files an item to let step 1b and step 2c leave a flagged note
unanswered, still saved and labelled. A fail keeps Q2 as an observation and
closes b-ef334d.
