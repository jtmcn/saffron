# Operator visibility — design

Three sub-projects, in dependency order, that give the operator a picture of
what the factory is doing and what it did: a typed host event stream, the
three ledger gaps the page cannot render without, and a renderer sourced from
the ledger rather than from the batch tree.

They are cut into ten specs, `SA-0029`–`SA-0038`, in
`docs/superpowers/plans/2026-08-31-operator-visibility.md`. This document
argues the design; the plan holds the spec bodies and the dependency chain.

> **Citations:** a bare `§` cites `DESIGN.md`, per repo convention. This
> document's own sections are cited as *part N*. Code is cited by **file and
> symbol, never `file.py:NNN`** — two rebases during this design moved every
> line number it originally carried, and a citation that decays faster than
> the argument is worse than no citation.

The starting position is not "there is no UI." §6's morning queue exists and
ships — `saffron/report/index.py`, `QueueLine`, `sort_key`, `render_index`,
`append_queue_line`. The finding that motivates all three sub-projects is that
**the page it renders cannot see the work that needs the operator**, and the
reason is structural rather than a defect in the sort.

## What was measured

Run, not reasoned. One snapshot of `~/.saffron/ledger.db` and
`~/.saffron/batches/v0/queue.json`, taken 2026-08-31. An earlier pass produced
different attempt counts because a cell was mid-run against the live database;
every number below comes from the single consistent snapshot.

> **Re-measured 2026-09-01, one day later**, and the figures below are kept as
> the dated snapshot they are rather than edited in place. What moved: **29**
> task rows across **17** specs in **7** states (`RATE_LIMITED` is new), total
> spend **$186.52**, `queue.json` at **14** rows still all in one state,
> `patch.diff` present for 16 of 17 task directories, and `findings.verdict`
> written on **1** of 29 — see part 2's gap 3, which that one row changes. What
> did not move: `runs.preflight` at 0, `SA-0009` invisible at $31.60,
> `EXHAUSTED` holding $58.15, three `ORPHANED` rows at $0.00. **Every argument
> below survives; no figure in it does.** The plan's Global Constraints require
> re-taking them at L1.

**The ledger holds 23 task rows across 13 specs in 6 states. `queue.json`
holds 10 rows across 10 specs in one state.**

| `tasks.state` | rows | spend |
|---|---|---|
| `MERGED` | 9 | $60.81 |
| `EXHAUSTED` | 3 | **$58.15** |
| `READY_FOR_REVIEW` | 1 | $6.24 |
| `NOT_IMPLEMENTED` | 6 | $0.99 |
| `PLAN_REJECTED` | 1 | $0.82 |
| `ORPHANED` | 3 | $0.00 |
| **total** | **23** | **$127.00** |

The page's header sums the rows it has: **$67.05 of $127.00**. It
under-reports what Saffron has spent by 47%, and the missing half is almost
entirely `EXHAUSTED` — the state that means a task could not pass its own
gates.

**Three specs appear on no page at all**, and they are exactly the ones §6's
sort levels 1 and 2 exist for:

| spec | state | spend | attempt rows |
|---|---|---|---|
| `SA-0009` | `EXHAUSTED` | **$31.60** | 4 |
| `SA-0020` | `EXHAUSTED` | $14.43 | 6 |
| `SA-0021` | `PLAN_REJECTED` | $0.82 | 1 |

`SA-0009` is the most expensive thing in the ledger and exists in no rendered
output.

**A spec that failed and was re-run shows only the success.** `SA-0019` has
two task rows — `EXHAUSTED` at $12.12, then `MERGED` at $16.20. The page
reports `$16.20`. The $12.12 attempt is not a row that sorts low; it is a row
that does not exist.

**And the ten rows it does show are stale.** Nine say `READY_FOR_REVIEW` for
specs the ledger records as `MERGED`: `reconcile` updates the ledger, and
nothing updates the store.

### Why — the store has exactly two writers

`append_queue_line` is called from `_finish` in `saffron/phases/package.py` and
`replay` in `saffron/replay.py`. Nowhere else. **A task that never reaches PACKAGE
never reaches the page.** So §6's ranks 0 through 2 — `SKIPPED`,
`SCOPE_REVIEW`, `MERGE_FAILED`, `PLAN_REJECTED`, `PREFLIGHT_FAILED`,
`GATE_ERROR`, `NOT_IMPLEMENTED`, `EXHAUSTED`, `ORPHANED`, `RATE_LIMITED` —
are unreachable from the production store, and every real row ranks 5.

`sort_key` is not wrong. It has never been given a row it could rank.

### What the ledger can and cannot answer today

Two of the gaps §6 names have closed since it was written, which changes the
recommendation rather than confirming it:

- `tasks.risk` is written on **23/23** rows. §6 says it "was never written for
  tasks that ran before `SA-0007`"; that is now stale.
- `MERGED` is recorded on **9** rows. §6 says "nothing anywhere records
  whether a task was merged, which is the trailing accept rate's whole input."
  That input now exists.

Three gaps remain, and part 2 is about them:

- `runs.preflight` written on **0/23** runs.
- The diff stat (`added`/`removed`) in no column. `patch.json` exists for 12
  of 13 task directories, `SA-0009` among them, and carries the file list but
  no line counts.
- `findings.verdict` NULL on **19/19** findings; `findings.adjudication` NULL
  on all of them, as §4.1 and §6 both expect for now.

### Two traps for an SQL-sourced page

**`attempts` does not mean `count(*) from attempts`.** The page's `attempts`
is *gate attempts*; the table counts *phase sessions*. Measured: `SA-0013`
renders `att 1` against 4 attempt rows; `SA-0019` renders `att 2` against 5.
A naive count renders a number four times too large.

**`note` is authored prose, not a fact.** PACKAGE writes strings like
`conflicts with #209`. There is no column that could hold it for a task that
never reached PACKAGE — which is the population this whole design exists to
render.

## The decision: the ledger is the source, the event log is the live tail

§6 leaves this open in as many words — *"Either the ledger gains what it is
missing, or this section stops implying the ledger is the source."* This
design takes the first branch.

The evidence decides it. The batch-tree store is written by the phase that
only runs on success, so it structurally cannot hold the 3 invisible specs,
the 13 non-terminal task rows, or 47% of the spend. The ledger already holds
all 23 rows, and after part 2 it holds everything the page renders. There is
no version of "one surface for live and finished work" that reads from a
store only a successful task writes to.

**The corollary is that the fix for the missing rows is the removal of a
writer, not the addition of one.** `queue.json` becomes derived output, then
goes away.

`ORPHANED` deserves more than one note, because it is the state that argues
hardest for the event log **and** the one place this design has to adjudicate
between two artifacts in the repo that disagree.

Three task rows are `ORPHANED` at `$0.00` with zero or one attempt: a cell
that died with nothing recorded. SQL can say a task ended that way; only an
event log can say how far it got first.

### The `ORPHANED` disagreement, and which side this takes

`ontology/saffron.ttl` splits `tasks.state` into two sets, and its reason for
the split is precisely this page's problem — `RATIONALE.md`: *"the state a
task ends in is a wider set than the states that reach the operator, and
`tasks.state` is one TEXT column for both."*

`saffron:TerminalState` holds the nine states that reach the operator.
`saffron:EndState` additionally holds `APPROVED`, `CHANGES_REQUESTED`,
`REJECTED`, `MERGED` — *"downstream of a judgement they already made"* — **and
`ORPHANED`**. So the ontology says `ORPHANED` does not reach the operator.

`_STATE_RANK` in `report/index.py` ranks it **2**, among the states that need
you. Neither artifact cites the other, and both ship.

**This design takes `index.py`'s side, and the ontology's own comment is the
argument.** The rationale *"downstream of a judgement they already made"* fits
the four post-decision states exactly and does not fit `ORPHANED`, which is
appended to that list as *"plus the state a crash produces."* A crash is not a
judgement, and a task that died having spent nothing is not something the
operator has already decided about — it is something nobody has looked at. On
the measured ledger it is three rows.

**But the ontology's distinction is the right one and the page should use its
words.** A page rendering all 23 rows shows `EndState`s, not `TerminalState`s
— `MERGED` is on it nine times — and the two want different treatment: a
`MERGED` row is history, an `ORPHANED` row is an unanswered question. Part 3
therefore renders the distinction rather than flattening `tasks.state` into
one column of strings, which is the conflation the ontology named first.

Reclassifying `ORPHANED` in the `.ttl` is **out of scope**: `ontology/shapes/**`
is in `gate_config`, so `integrity` refuses an edit no spec's `touches` names,
and this design should not be the thing that quietly moves a term in a
vocabulary. It goes to `docs/BACKLOG.md` as a by-hand item with this argument
attached.

---

## Part 1 — the event seam (`SA-0029`–`SA-0031`)

**The move already exists in the repo, one level down.** Inside a cell,
`images/agent_runner.py` emits Saffron's own typed events as JSON lines, and
`saffron/phases/implement.py`'s `_consume` renders them with `watch(_describe(event))`
— structure first, prose derived at the edge. Host-side the arrangement is
inverted: `run_one_cell` takes `watch: Callable[[str], None] = print` and
roughly thirty call sites author prose directly, so the structure exists only
inside an f-string and dies at the terminal.

`saffron/events.py` holds the vocabulary: a frozen dataclass per kind —
`Preflight`, `Baseline`, `PhaseStart`, `Attempt`, `GateResult`, `Budget`,
`Agent`, `Terminal`, `Teardown` — each carrying a timestamp, the `spec_id`,
and its own typed fields. Top level, not under `saffron/report/`: the
scheduler and PACKAGE emit these too, and `report/` is the consumer.

`watch` becomes `emit: Callable[[Event], None]`, fanned out to two consumers:

```
emit ──┬─→ TerminalRenderer   # _describe(event) -> the line printed today
       └─→ EventLog           # appends JSONL to task_dir/events.jsonl
```

`task_dir` is `out_dir / spec.spec_id` (`_drive_cell`), so the log lands
beside `patch.diff`, `plan.json` and `baseline.json`.

**The acceptance criterion is that the terminal output does not change.** A
golden capture of today's `watch` lines for a driven cell, taken before the
migration, must come back byte-identical after it. That is what makes a
thirty-site mechanical diff verifiable instead of trusted, and it is what
keeps this sub-project from growing a UI.

**"Before the migration" has a floor, and `SA-0028` set it.** That queued spec
adds `watch` lines — one naming which of three ceilings stopped a run, one
distinguishing "cut off and could not be salvaged" from "finished and produced
nothing" — so the capture is only trustworthy once it has shipped. Part 1
waits on it for that reason even in the spec that shares no file with it.

**And `SA-0028` is the best available evidence that this part is worth
building.** It exists because `SA-0005` was stopped by one of three ceilings
and nothing said which, and its remedy is to add two more strings to a seam
that can only hold strings. Two facts an operator needs, arriving as prose,
written by someone who had no other place to put them — while this design was
being written. Part 1 is what gives the next such fact somewhere to go.

Three details follow from invariants that already hold:

- **The cell's events nest; they are not re-flattened.** `Agent` wraps the
  cell's already-Saffron-shaped event dict. The host still never sees an SDK
  type, and the `agent: (raw)` path stays quarantined as untrusted text from
  a cell.
- **Append-only, flushed per event.** A cell that dies mid-write leaves a
  truncated final line. The reader drops a partial trailing line rather than
  discarding the file — the same per-row tolerance `_existing_queue_rows`
  already applies, for the same reason.
- **The log is a record, not a control.** Nothing reads it to make a
  decision; every control that matters stays where it is. `ponytail:` its
  ceiling — one file per task, no rotation, tens of MB a night by §4.1's own
  estimate.

## Part 2 — the ledger's three gaps (`SA-0032`–`SA-0034`)

Independent of part 1; the two can run in either order.

**Gap 1 — `runs.preflight`, written 0/23.** §6's own rule is that "a header
field with no source is not a smaller header — it is a field that renders a
confident em-dash." The column exists and nothing assigns it. `_drive_cell`
runs preflight and holds the outcome — proxy up, route asserted (§5.1.1),
image built, cell up — and writes it there. The smallest of the three by a
wide margin.

**Gap 2 — the diff stat.** `added` and `removed` are computed in PACKAGE and
land only in `queue.json`. Two columns on `tasks`, not a render-time re-parse
of `patch.diff`: re-parsing would make an SQL-sourced page depend on the batch
tree, which is the dependency this design removes. The stat is computable for
tasks that fail — teardown already exports `patch.diff` for 12 of 13 task
directories, `SA-0009` among them — so teardown computes and stores it, and
PACKAGE stops being the only writer.

**The stat is computed against `tree_base`, never `base_sha`.** `SA-0025`'s
predecessor `SA-0022` split the two: `base_sha` pins the run's gates and
policy, while `CellSpec.tree_base` is what the worktree is built on and what
`worktree.export_patch` is called with (`session.py`, and `patch.json` now
records both). They are equal for every unstacked task, so a column filled
from `base_sha` would pass every test in the tree today and silently give a
stacked child its parent's diff the first time stacking runs — the exact
defect `SA-0022` exists to have fixed, reintroduced one layer along. The
spec must name `tree_base` and test the stacked case.

**Gap 3 — `findings.verdict`, NULL on 19/19 when this was written.** The
evidence points at the verdict half specifically rather than at the write path.
Only **2** `REBUTTING` attempt rows existed in 65. Both anchored blockers
belonged to `EXHAUSTED` tasks. Finding 14 (`SA-0020`) carries a rebuttal —
`fixed: Confirmed the finding by reading package.py` — beside a NULL verdict,
written by the same `record_rebuttal` call (in `_drive_cell`'s REBUT branch), so
`argued.get(n)` returned a value and `judged.get(n)` did not.

**One day later this gap acquired its contrast case, and it is the most useful
thing that has happened to this sub-project.** Re-measured 2026-09-01: finding
29 (`SA-0027`, a `contract`-lens blocker) carries `verdict = withdrawn`
*and* a rebuttal, both from the same call. So the write path works, and the
population where a verdict is even expected is two rows — one written, one not.
The question is no longer "does anything write `verdict`" but "what differs
between those two REBUTs". The other 24 findings are NULL because REBUT never
ran on their tasks, which is correct and must not be counted as the defect.

It is still a bug spec, and more clearly so: with a working case beside a
broken one, the outcome "the critic produced no verdict for finding 14, and
nothing in `saffron/` is broken" is now live and the spec must be able to
reach it. **This sub-project's first task is one measurement** —
`result.verdicts` against `rebut.first_answers` on *both* recorded REBUTs — and
the fix follows what it finds. Guessing here would be the mistake
`CONTEXT.md`'s measured-fact convention exists to prevent.

**Level 3 has never rendered, for two independent reasons**, and both must be
fixed for it to work: no verdict is stored, *and* both blocker-bearing tasks
are `EXHAUSTED`, so `sustained_blockers` and `unkept_fixes` were never called
on them at all. Part 3 fixes the second by rendering those tasks.

**The two traps, handled.** `attempts` is derived from `REPAIRING` sessions
rather than a row count, or stored outright — the choice is the spec's, but
rendering 4 where the page means 1 is a defect the spec must name. And `note`
does not become a column: in part 3 the caption is derived at render time from
state plus gate results, so a task that never reached PACKAGE gets one too.

**What this part deliberately does not do:** it adds no write path for failed
tasks. The ledger already has all 23.

## Part 3 — the renderer (`SA-0035`–`SA-0038`)

Depends on both parts above.

`saffron/report/render.py` reads the ledger for settled state and the tail of
`events.jsonl` for whatever is in flight, and writes `out_dir/index.html`
plus a page per task at `out_dir/<spec_id>/index.html` — which is `task_dir`,
so each page lands beside the artifacts it links to.

**One row per spec, not per task, and the measurement forces the choice.**
The ledger's 23 task rows are not 23 things an operator acts on: `SA-0013`
alone holds 10, nine of them `$0.00` `ORPHANED` or `NOT_IMPLEMENTED` from
early development. Rendered per task those nine rank 2 and occupy the top of
a page read in ten seconds. Rendered per spec at the *newest* task's state,
`SA-0019`'s `EXHAUSTED` attempt disappears again — the defect this design
exists to fix. So the row is keyed `(repo, spec_id)` as it is today, carries
the newest task's state, **sums spend across every task for that spec**, and
shows a task count when it exceeds one:

| renders as | why it is the honest line |
|---|---|
| `SA-0009  EXHAUSTED  1 task  $31.60` | invisible today |
| `SA-0019  MERGED  2 tasks  $28.32` | today reads `$16.20`; the failed run's $12.12 is not lost |
| `SA-0013  NOT_IMPLEMENTED  10 tasks  $1.62` | ten runs, the last producing nothing — which is the fact |

Thirteen rows, not ten and not twenty-three. Per-task detail lives on the
per-task page, where it does not compete with triage.

**And §6's sort reaches its own top levels for the first time.** `SA-0009` at
`EXHAUSTED` and $31.60 arrives at rank 2, above every green pull request, and
the $59.95 that has never appeared on a page appears. `sort_key` is
unchanged. It was always right and was being fed ten rows that could only
rank 5.

**The per-task page shows what GitHub cannot, and nothing more.** §6's "an
index, not a viewer" holds: the diff stays on the pull request, which is the
best-engineered component in the stack and free. The page shows the phase
timeline from the event log, the gate table across attempts from
`gate_results` and `failures`, findings with verdict and rebuttal side by
side, and per-attempt cost. For `SA-0009` that answers "what did $31.60 buy",
which today takes `sqlite3` and a directory walk.

**Concurrency gets simpler.** `append_queue_line` needs `flock` because it is
a read-modify-write of `queue.json`. A full re-render from SQL has no read
half, so the lock, `_existing_queue_rows`, its per-row validator and
`_migrate_v0_store` all go away and `_atomic_write` alone carries it — about
half of `report/index.py` deleted rather than extended.

**Liveness is a `<meta http-equiv="refresh">`, present only while a task is in
flight, with its ceiling named in a `ponytail:`.** This is the honest cost of
choosing regenerated static HTML over a server, and the design says so rather
than implying the page is live.

**A render that raises must never abort a cell.** `emit` is fire-and-forget; a
render failure is recorded as an event and swallowed. This is the mirror of
`_finish`'s rule rather than a contradiction of it: PACKAGE refuses to write a
line for a pull request that was never opened, and the renderer refuses to
kill a run over a page.

**Everything from a cell is escaped.** The event log carries agent-authored
text, a cell is untrusted, and the renderer is host-side. `html.escape` on
every interpolation, as `_row` already does.

**The header ends at five of six.** After part 2: terminal-state counts, total
spend, per-repo preflight, base-suite status (231 baseline gate results across
the runs), and trailing accept rate, whose input now exists. Batch wall clock
does not: it needs the `batches` table §4.2.1 defers. Per §6's own rule it is
omitted rather than dashed.

## What `DESIGN.md` must change

Before part 3 lands, not after. §6 currently states that the queue reads
`queue.json`, and calls the source of truth "undecided rather than chosen."
This design chooses, so that paragraph is rewritten to say the ledger is the
source and the event log is the live tail. Its two stale gap claims —
`tasks.risk` unwritten, nothing recording a merge — are corrected against the
measurements above. §6's *index, not a viewer* position is unchanged and
worth restating, since part 3 adds a per-task page and a reader could
otherwise take that as a reversal.

Add subsections; never renumber. The event schema is new surface and wants
its own subsection under §4, cited by all three specs.

## Order, and what each is worth alone

| part | worth alone |
|---|---|
| 1 — event seam | structured record of a night; terminal output unchanged |
| 2 — ledger gaps | preflight, diff stat and verdicts stop being em-dashes |
| 3 — renderer | the 3 invisible specs and 47% of spend become visible |

**The three parts are ten specs**, `SA-0029`–`SA-0038`, cut in
`docs/superpowers/plans/2026-08-31-operator-visibility.md`, which holds the
dependency chain and each spec's body. Three specs would make three diffs too
wide for their own repair loops — item 25 records that failure, and `SA-0022`
and `SA-0025` were both split mid-flight for it. Part 1 splits into a
vocabulary and two migrations (`session.py` alone is 1322 lines); part 2 into
its three independent gaps; part 3 into query, render, task page, timeline.

**Part 2's verdict gap is a `bug` with an `envelope`, not a `feature` with
`touches`.** Why `findings.verdict` is NULL is not known — the write path
fires and the verdict half arrives empty, on n=2. Declaring `touches` would
mean diagnosing it by hand first, which §3.2 says inverts the economics: the
operator does the expensive part and the agent types. DIAGNOSE proposes the
scope and the operator ratifies it (§5.2). The same applies to
`runs.preflight`, where the write belongs wherever preflight's outcome is
known.

**All ten run sequentially, as cells, after `SA-0026` lands.** Not because the
dependencies require it — part 1's do not — but because v0.5 runs one attended
cell at a time and §4.2's concurrency pool is not built.

> **Correction, 2026-09-01: under the stack workflow the dependencies *do*
> require an ordering, and it is part 1 first, merged.** `.claude/skills/run-saffron-spec-loop`
> leaves every pull request open and links them, and `cli._resolve_stacked_on`
> consults **`depends_on[0]` and nothing else** (K=1, its own docstring). Two
> consequences this design did not anticipate, because it was written against a
> merge-each-time loop where a `MERGED` parent always reaches the default
> branch:
>
> - `SA-0035` names `SA-0033` before `SA-0034` and would be cut from
>   `SA-0033`'s branch, without the `findings.verdict` write its own criteria
>   consume. The plan reorders the list; the newest parent belongs in slot 0.
> - `SA-0038` names parents on two different chains — `SA-0037` and `SA-0031` —
>   and K=1 can reach one. So part 1 must be **merged**, not merely open, before
>   part 2 starts, which also stops the two chain heads being siblings appending
>   to the same `docs/BACKLOG.md`.
>
> Neither is a defect in this design's argument; both are facts about the
> stacking mechanism that only appear when nothing merges between cells. The
> plan's "Stacking: two mechanisms" section and Task 12 carry them.

**Part 1 declares no dependency on `SA-0026`, and that is a finding rather
than an omission.** The seam looks like it should collide over
`saffron/cli.py`, and at `7ab27cf` it did not: `cli.py` never named `watch` —
it called `run_one_cell` and took the default. So the `emit` fan-out is
constructed inside `session.py`. **Keeping the default there is a design
constraint, not an accident**: moving it up would put the seam in stacking's
file for no gain. Recorded here because it stops mattering as scheduling and
starts mattering as design the moment the conflict-set scheduler exists.

> **Correction, 2026-09-01 — the second half of that claim was falsified within
> a day, and the way it failed is worth more than the claim was.** `256e529`, a
> *review fix on `SA-0026`*, gave `cli._resolve_stacked_on` a `watch=print`
> parameter and two call sites (`cli.py:226`, `:292`, `:297`). So `cli.py` **is**
> in a spec's `touches` — `SA-0031`'s — and part 1's last three `watch` sites
> live there.
>
> The constraint survives its rationale. The *reason* given for keeping
> `cli.py` out was avoiding a collision with in-flight stacking work, and that
> has expired: `SA-0026` and `SA-0027` have both merged. The *rule* — the
> `emit` default stays constructed in `session.py`, and `cli.py:393` calls
> `run_one_cell` with no `emit` argument — is now an acceptance criterion of
> `SA-0031` rather than a property the plan could take for granted.
>
> **What this says about the method.** The falsifying change was authored by a
> review fix on a spec whose own `touches` named no `watch` at all. No amount
> of reading queued spec frontmatter would have caught it; only grepping the
> code would. A design that reasons about which files a change can reach must
> re-derive that from the tree, not from the specs, immediately before
> spending. The plan's Task 0 Step 4 now does.

**Part 3 goes last, and the reason is not politeness about ordering.** It is
the only part that changes what the operator sees, and it renders the record
the other two populate. Shipped before part 2, its preflight and verdict
columns are em-dashes on every row — §6's own warning about a header field
with no source, self-inflicted.

### What waits for v1, and what does not

An earlier draft of this design held part 3 back until late in v1. That was
too strong, and the correction is worth recording because the argument was
wrong in a specific way.

Only two things in part 3 need v1: **batch wall clock**, which needs the
`batches` table §4.2.1 defers, and the **multi-repo columns**, which are v2's
`--repos`. §6's own rule disposes of the first by omitting a field with no
source, and the second renders correctly with one repo.

The mistaken half of the argument was "the operator is watching, so the page
adds nothing." That covers the *live* half only. The triage half is worth
having now and has nothing to do with unattended nights: `SA-0009`'s $31.60
takes `sqlite3` and a directory walk to see today, and that is equally true
whether or not anyone watched the night it burned.

> **Spec numbering:** confirmed against `origin/main` at `7ab27cf`. `SA-0026`
> is shipped; `SA-0027` and `SA-0028` are queued spec files from PR #85, so
> these take `SA-0029`–`SA-0038`. **Renumbered twice already** — once when
> `SA-0026` appeared mid-design, once when `SA-0027`/`SA-0028` did. Re-confirm
> before writing each spec file; the plan's Task 0 is where that happens.

**`SA-0026` collides with part 2, and the collision is one file.** Stacking's
producer touches `saffron/ledger.py` and `tests/test_ledger.py`, which is
exactly where part 2's `runs.preflight` write and diff-stat columns go. It
`forbid`s `saffron/report/**`, `saffron/cell/**` and `saffron/phases/**`, so
parts 1 and 3 are clear of it and so is part 2's teardown half — the overlap
is the ledger module alone. Part 2 therefore declares `depends_on: SA-0026`
rather than racing it: §4.2's conflict-set scheduler does not exist yet, so
nothing else would keep two tasks out of the same file.

## What this deliberately does not build

- **A diff viewer.** §6's argument stands and this design does not reopen it.
- **A server.** No `saffron ui`, no HTTP surface, no long-lived process.
  Regenerated static HTML, opened from the batch tree.
- **A TUI.** The terminal renderer stays exactly what it prints today.
- **Adjudication capture.** `findings.adjudication` is NULL on every row and
  stays that way here. It is the input to the critic-ROI query (§4.6) and
  wants its own spec; a page that could write it is a different thing from a
  page that renders.
- **An RDF class for the event log.** `ontology/saffron.ttl` keeps an explicit
  *"left unmodelled because nothing reads them"* list —
  `prov:wasInvalidatedBy` for `spec_sha` invalidation, tool-call granularity,
  DCAT — and the event log joins it. The ontology's discipline is to model
  what something reads, `RATIONALE.md`'s bottom line is *"don't build the
  emitter"*, and nothing here reads RDF. Stated rather than left inferred,
  because this design adds a whole record type and silence would read as an
  oversight. Revisit at v2.5 (§9) with the emitter, or never.

## Verification

Golden HTML against a fixture ledger for the renderer, and a golden terminal
capture for the event seam.

Beyond that, the repo's evidence discipline applies: a record under
`docs/evidence/` that points the **shipped** renderer at the real
`~/.saffron/ledger.db` and changes only the data source, in the shape of
`docs/evidence/2026-08-25-morning-queue-from-real-rows.md`. That method is
what makes the 10-versus-23 claim checkable rather than asserted, and it is
how the next reader will find out that these numbers have moved on too.
