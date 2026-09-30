---
id: b-abeb74
title: No REVIEW lens reads CLAUDE.md's conventions against the hunks, and the Standards seat finds them on every PR
status: partial
tier: 1
filed: 2026-09-28
closed:
specs: [SA-0189, SA-0191, SA-0192]
prs: [579, 580, 581]
commits: []
cites: [§5.5]
related: [79, b-17d0d5, b-7e69d0]
---

## Problem

Found in the spec loop's run 20, 2026-09-28. The operator ranked it third.

REVIEW runs three lenses: correctness, contract and adequacy
(`saffron/phases/review.py:39-42`). None judges a hunk against `CLAUDE.md`'s
conventions. The Standards seat found such defects on every pull request of the
run.

- A comment that contradicts its code: #565's timeout comment, #566's "lone
  witness concern" docstring three times.
- A restated constant: #559's `record_key`, #560's `3600`.
- A citation to a section that does not say it: #562's `§4.2.1` references.

## Done looks like

A fourth lens reads each hunk against `CLAUDE.md` and the `Conventions` it
states. It is measured on run 20's Standards findings before and after.

## Record

- 2026-09-28: filed from the spec loop's run 20.
- 2026-09-29: partial after `SA-0189` (#579), `SA-0191` (#580) and `SA-0192`
  (#581) in the spec loop's run 21. The conventions lens exists. ADR 8's
  measured pass is still hand work: a fixture of run 20's five Standards
  defects in its own directory, scored with `harness/lens_scoring.py` before
  and after. The lens ran live in no cell, because lenses run from the
  host's `main` (item b-66d1c3). Item b-78ccc7 holds what the Standards seat
  found the prompt would miss.
- 2026-09-29: the measured pass ran for `SA-0195` on the run-20 fixture, one run per
  arm. Both arms saw two of five defects: `SA-0186` gained, `SA-0160` lost. At one run
  per arm the effect is unmeasured. The fixture and the driver's `--with-claude-md`
  landed in #602.
