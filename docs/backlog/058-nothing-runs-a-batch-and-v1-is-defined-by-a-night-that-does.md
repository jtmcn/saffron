---
id: 58
title: Nothing runs a batch, and v1 is defined by a night that does
status: done
tier: null
specs: [SA-0009, SA-0045, SA-0054]
prs: []
commits: [57b676c]
cites: [§4.1, §4.4, §9]
related: [16, 44, 56, 66]
---

## Problem

**Status: done** — seven specs, `SA-0045` through `SA-0054`, PRs #115/#116/#117
/#120/#121/#122/#123, merged together as `57b676c`. `saffron batch --repo .
--budget 50 --until 06:30` exists, `saffron/batch.py` owns the loop, the
`batches` table records the night, and `docs/host/dev.saffron.batch.plist` is
the launchd job. Absorbed items **16** and half of **44**, both now closed
above.

**A night has been run, against an empty queue** — `DRAINED`, exit `0`, $0.00,
2026-09-05 (`docs/evidence/2026-09-05-first-batch-drained.md`). That proves
readiness, the mirror fetch, the scan, `reconcile`, the ledger row, the
deadline resolving to tomorrow, and the exit code.

**No cell has started under a batch.** So the budget gate, the breaker,
`--until` firing, packaging, the orphan sweep and what a night costs are all
tested and none is measured. A night with one cheap spec in it is the next
thing worth running, and until it has, this item is done in the sense that the
code exists rather than in the sense that the night works.

What the review round found is worth recording, because it is the argument for
the round: seven tests across the stack named behaviour they did not guard, and
every one read fine. Two migration guards asserted the string `replace` had
just removed; the breaker reset was deletable with the suite green;
`parent_branch=None` would have targeted `main` from every stacked child; both
operator-facing print lines were replaceable with `pass`. And the token probe
was inert — `400` read as valid, so it accepted any string at all (item **66**,
and `docs/evidence/2026-09-05-token-probe-request-shape.md`). None of that was
caught by reading. It was caught by running the mutation, and by one live
measurement.

**Tier 0.** Not found by a run — found by asking what the other 29 items were
being ordered *toward*, 2026-09-04.

`saffron/cli.py` exposes four subcommands: `replay`, `cell`, `queue`,
`reconcile`. There is no `run_batch` anywhere under `saffron/`. `queue` prints
what a batch *would* run and reconciles pull request state; nothing executes
it. §4.4 "Batch orchestration" is design with no implementation, and §9's v1
criterion — *a full night runs while you sleep, and you merge at least half of
what it produces before the coffee's cold* — is therefore not merely unmet but
structurally unreachable.

What runs specs today is `run-saffron-spec-loop`, a Claude Code skill driving
`saffron cell` once per spec with an agent supervising. That is the attended
loop working as intended, and it is **not** the thing v1 names: the skill is
host tooling, not the product, and it needs someone at the keyboard.

**This is why it sits above the whole backlog.** Every open item is a
refinement of a pipeline that cannot yet run unattended, and "what would hurt
most on the first unattended night" cannot be honestly ranked while nothing can
produce one. Two items fold into it rather than standing alone:

- **Item 16** — a task's policy lineage. §4.1's invalidation rule (*change a
  repo's gate declarations mid-batch and its in-flight tasks are invalidated*)
  is a doc claim with no reader until batches exist, and a batch is exactly the
  window where a policy moves under an in-flight task. Building the runner
  against a ledger that cannot say what a task ran under is building it twice.
- **Item 44**'s enforceable half — a per-batch ceiling, checked *between* tasks.
  That is the only place a spend bound is enforceable at all, because nothing is
  mid-flight at that moment; `budget_usd` cannot be, for the reason item 44 now
  records.

**Done looks like** a plan, split into specs by that plan — the shape
`docs/superpowers/plans/2026-08-31-operator-visibility.md` uses. **Not one
spec.** §4.4 spans `cli.py`, a new orchestration module, `scheduler.py` and
`ledger.py`, and item 56 is the measurement of what happens when a spec that
wide reaches a cell: `SA-0009`, $31.60, `EXHAUSTED`, zero lines merged. The
plan itself is written by hand — §4.4 is design, and `DESIGN.md` is
`protected`.
