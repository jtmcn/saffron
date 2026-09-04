# Batch orchestration — design

**Backlog item 58. `DESIGN.md` §4.4 and §4.2.1 are the specification; this
document does not restate them.** §4.2.1 already settles K, the stop
conditions, the breaker's membership, the schema, the command and the exit
codes, in more detail than a design doc written now would reach. What follows
is the three things it cannot contain: what of it is *built*, what two backlog
items fold into it, and where the seams are in the code that exists.

Cite §4.2.1 for any question this document does not answer. Where the two
disagree, §4.2.1 wins and this file is wrong.

---

## 1. The gap, measured

`saffron/cli.py` exposes four subcommands — `replay`, `cell`, `queue`,
`reconcile`. There is no `run_batch` anywhere under `saffron/`. `queue` runs
the whole scan and *prints* it; nothing executes the result.

So §9's v1 criterion — *a full night runs while you sleep, and you merge at
least half of what it produces before the coffee's cold* — is not merely unmet.
It is unreachable by any sequence of existing commands.

What runs specs today is `run-saffron-spec-loop`, a Claude Code skill driving
`saffron cell` once per spec with an agent supervising. That is the attended
loop working exactly as designed, and it is not the thing v1 names: the skill
is host tooling rather than the product, and it needs someone at the keyboard.

### What §4.2.1 specifies and the tree already has

Checked against the code, not assumed:

| §4.2.1 requires | State |
|---|---|
| Scan `.saffron/specs/*.md` from the export at `base_sha` | **built** — `_queue`, `cli.py:492` |
| Scan resolves to a task, not a spec | **built** — `scheduler.build_queue` |
| `DONE_STATES` / `REQUEUE_STATES` filter, keyed on `spec_sha` | **built** — `scheduler.py:63`, `:103` |
| The refusal gate's eight refusals | **built** — `scheduler._refuse` |
| `depends_on` admitted by merged, retired, or stacked parent | **built** — `SA-0020`, `SA-0022`, `SA-0025`, `SA-0026` |
| Per-task preflight: mirror, origin refusal, base pin | **built** — `_run_cell`, `cli.py:344`, but per *task* |
| The scan stamps in-flight tasks `ORPHANED` before filtering | **built** — `reconcile(…, stamp_orphaned=True)`, `reconcile.py:153`; `IN_FLIGHT_STATES` at `:54`. No caller passes it, which is the loop's job |
| `load_policy` validation as a preflight step | **missing** |
| Auth check before the night starts | **half** — presence at `cli.py:348`; validity, which is Appendix J's actual landmine, is unchecked |
| Disk-headroom check | **missing** |
| `batches` table, `runs.batch_id` | **missing** |
| The K=1 loop, four stop conditions, the breaker | **missing** |
| `saffron batch` and its exit codes | **missing** |

The scan is done. **The night is not.**

**Corrected 2026-09-04.** Two rows above first read `missing` and were wrong.
The `ORPHANED` stamp is fully built in `reconcile.py` — eight states
enumerated once, both branches tested, and a `stamp_orphaned` parameter whose
docstring already says *"no command in this version of Saffron is a batch
scan."* The error was grepping `scheduler.py` alone rather than the tree, and
it would have bought a spec for work already done. What is missing is only a
caller, which the loop is. The auth check is likewise half-present.

---

## 2. Two backlog items fold in, and neither stands alone

### Item 16 — a task's policy lineage

`repos.policy_sha` is per repo and written once, at cell start, from the export
at `base_sha`. When the default branch has moved, PACKAGE re-verifies under
`fetch_head`'s policy — a *different* declaration, correctly so — and nothing
records that.

§4.1's invalidation rule (*change a repo's gate declarations mid-batch and its
in-flight tasks are invalidated*) is the same question from the other end, and
item 16 says it should be answered with it. **It has no reader until batches
exist**: attended, one cell at a time, a policy cannot move under an in-flight
task because there is no flight. A batch is precisely that window.

**Decided:** a `policy_sha` column on `tasks`, written at cell start and
rewritten at PACKAGE when it differs. Invalidation then becomes a comparison
rather than a claim in a document. Built here, because building the loop
against a ledger that cannot say what a task ran under is building it twice.

### Item 44 — the enforceable half of the budget ceiling

`_over_budget` gates a turn on what has been spent *so far*, and a turn's cost
is not knowable until it ends. Measured on `SA-0031`: admitted under $18.00
with ~$6 spent, one IMPLEMENT turn cost $13.18 and the run ended at $19.17.

**Decided (backlog item 44):** `budget_usd` is a best-effort bound and says so
where it is declared. The enforceable ceiling is **per batch, checked between
tasks** — and it belongs here because between tasks is the only moment nothing
is mid-flight, which is exactly why a bound is enforceable there and cannot be
inside a turn.

This is §4.2.1's budget gate at K=1: *"one comparison before each task."* The
reserved-budget machinery §4.2 gate 3 describes is **not** built — it exists
only to stop K tasks passing on the same last $12, and at K=1 that race cannot
occur. §4.2.1 says so explicitly; this design does not reopen it.

---

## 3. Seams — what is reused rather than written

**The scan is `_queue`'s, lifted whole.** `cli._queue` already resolves the
mirror, exports `.saffron/` at the pinned `base_sha`, calls `build_queue` with
a repo slug and a `gh` callable, and collects refusals plus `gh` failures plus
`policy_unread`. A batch needs that same value and then iterates it. **Extract,
do not reimplement** — a second copy of the scan is a second answer to "what
would run tonight," and the two would drift the first time a refusal is added.

**The per-task preflight is `_run_cell`'s, hoisted.** `cli._run_cell` does the
token check, `ensure_mirror`, the origin refusal (`github_slug` read for its
refusal, not its value), the default-branch pin, `resolve_repo_id`, and the
protected-paths read at `base_sha`. §4.2.1's phrase is exact: *"Preflight is
what a task already does, hoisted, plus two."* The plus-two are `load_policy`
validation and the auth check; the disk-headroom check is a third that §4.2.1
refuses to defer alongside `gc`.

**The cell call is `run_one_cell`, unchanged.** It already takes a `CellSpec`,
a repo, a mirror, a ledger, an `out_dir` and an `emit`, and returns a
`CellOutcome` carrying the terminal state. The loop needs no new capability
from it — which is the evidence that the seam was put in the right place in
v0.5.

**`saffron gc` (§4.5) is deferred and its detection half is not.** §4.2.1 is
explicit: K=1 means `--until` kills at most one cell, so the leak is one volume
a night rather than three — but the accumulation is still unbounded, and
dropping the disk check as well *"turns a warned failure into a silent one."*

---

## 4. What this design deliberately does not build

Each is §4.2.1's own cut, repeated here so a reader does not take an absence
for an oversight:

- **No `--concurrency` flag.** K has one position. A flag for a one-position
  knob is item 18's defect wearing a CLI.
- **No `--repos` / `--all`.** Multi-repo is v2 (§9).
- **No conflict sets, no round-robin, no dependency-depth ordering.** All three
  arbitrate contention a two-deep queue does not have.
- **No reserved-budget arithmetic.** See §2 above.
- **No `tasks.priority` column.** It is read once, at scan, to sort a list
  already in memory. A column written at scan and read by nobody is item 18's
  pattern wearing a schema.
- **Exit code `1` is reserved, never emitted.** `0` for `DRAINED`, `BUDGET`,
  `UNTIL`; `2` for `INFRASTRUCTURE` and for a preflight failure that takes the
  batch. *A batch that drains with three failed tasks did its job.*

---

## 5. Risks

**The breaker's membership is easy to get wrong and §4.2.1 says why.** It
counts `GATE_ERROR`, `PREFLIGHT_FAILED` and `RATE_LIMITED`, and **resets on any
state a task earned — including `EXHAUSTED`.** Writing "resets on any terminal
state" would be a bug rather than a shorthand, because §3.3 lists `GATE_ERROR`
and `PREFLIGHT_FAILED` among the terminal states that reach the operator, so
the counter would reset on the very aborts it counts and never reach two.

**`RATE_LIMITED` is not `EXHAUSTED`.** A provider ceiling and a task that could
not pass its gates are different outcomes. `CLAUDE.md` names this as an
invariant; the breaker is the first place it is load-bearing at the batch
level.

**The auth check guards a measured landmine, not hygiene.** Appendix J found
that a cell whose agent cannot authenticate returns `subtype: "success"`,
`is_error: true`, `total_cost_usd: 0.0`. Unattended, an expired token at 22:00
produces a night of clean-looking nothing against a budget that never counts
down — the single worst failure mode this design has, because every other
failure at least reports itself.

**Nothing here is testable by watching it.** Every property above is a
property of an eight-hour unattended window. The tests are therefore fake
clocks, fake `run_one_cell` callables and injected ledger states — which is
why each spec below carries its own fixture strategy rather than deferring to
a live run.
