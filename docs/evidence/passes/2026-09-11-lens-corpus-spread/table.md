**3/12 declared defects graded** (5/12 seen) across 8 fixture(s).

Per run, each scored alone: 1/12 · 2/12 · 3/12 graded. The headline counts a defect graded in any run, so it rises with `--runs`; these are the spread.

| Fixture | Defect | Seen | Graded | Anchored blockers |
|---|---|---|---|---|
| SA-0045 | `reflow-defeats-guard` | 0/3 | 0/3 | 0, 0, 0 |
| SA-0046 | `reflow-defeats-guard` | 0/3 | 0/3 | 2, 1, 0 |
| SA-0048 | `refusal-codes-unpinned` | 3/3 | 3/3 | 1, 2, 2 |
| SA-0050 | `breaker-reset-unguarded` | 3/3 | 2/3 | 0, 1, 1 |
| SA-0054 | `parent-branch-unpinned` | 0/3 | 0/3 | 0, 0, 1 |
| SA-0054 | `stop-line-unwitnessed` | 0/3 | 0/3 | 0, 0, 1 |
| SA-0055 | `pinned-base-unwitnessed` | 0/3 | 0/3 | 0, 0, 0 |
| SA-0055 | `readiness-guard-unwitnessed` | 0/3 | 0/3 | 0, 0, 0 |
| SA-0062 | `dirty-restore` | 1/3 | 0/3 | 1, 1, 0 |
| SA-0062 | `truncating-write` | 1/3 | 0/3 | 1, 1, 0 |
| SA-0063 | `notes-neutralization-unwitnessed` | 1/3 | 1/3 | 2, 1, 2 |
| SA-0063 | `empty-notes-heading-unwitnessed` | 0/3 | 0/3 | 2, 1, 2 |

**16 verified vacuities** — adequacy-lens findings whose named edit left the fixture's suite green. 16 of 22 probe(s) that answered survived; 0 unproven and in no denominator, over 8 fixture(s) probed this invocation at 3 run(s) each — which need not be every fixture in the table, since recall is re-derived from every run JSON on disk and a resumed pass probes only what it ran. A total over those runs, not a rate over them, so it does not compare with a pass at a different `--runs`. Not comparable with the recall line above either: one lens, and a lower bound — a killed probe may have broken the program rather than been noticed, which is adjudicated per probe and not computed.
