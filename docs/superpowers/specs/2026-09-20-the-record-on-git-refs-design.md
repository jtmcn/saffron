# The record moves to git refs, and the ledger stops being authoritative

Backlog item 170, designed. It closes `DESIGN.md` §6's open fork — *"there are
two records of a night and the authoritative one is the file, not the
database"* — by naming one authoritative record and deriving the rest from it.

The spike that makes it admissible is
`docs/evidence/2026-09-17-state-on-git-refs.md`. The approach it probed was
chosen before this document: per-target refs pushed to the real remote, with the
ledger folded out of them. What was open, and is decided here, is the record's
shape, what happens to the 99 tasks already stored, and where a night's own
identity lives when every ref belongs to one target.

Line numbers cited in item 170 have drifted. The budget check is
`saffron/batch.py:194`, the spec-declared tier comment is
`saffron/cell/session.py:1522`, and the `queue.json` store is
`saffron/report/index.py:214`.

## The problem

A night is recorded in three places. `~/.saffron/ledger.db`, which `CONTEXT.md`
§8 calls authoritative for state. `~/.saffron/batches/v0/`, which holds the
artifacts and `queue.json`, and which the morning index renders from. And the
repository with GitHub, which holds branches, pushed shas, pull requests and
spec retirement. No rule says which wins.

They already disagree. Reconstructing all 68 stored rows from the ledger on
2026-09-17 found `risk` differing on 1 row and a naive reconstruction of
`attempts` differing on 4.

The cause is not a missing column. `tasks.risk` holds the tier the spec
*declared*, written at task creation, and `session.py:1522` says so: *"The
spec-declared tier only: no diff exists yet for an `elevate_on`"*. `_finish`
writes `risk=outcome.effective_risk`, the tier the diff *earned*. Two
quantities under one name. `SA-0085` is the row that shows it — it declares no
`risk:` at all, so the ledger carries the default `standard` while the store
carries the earned `elevated`.

## Decisions taken in design

- **Scope.** The record as an interface, the refs backend, and the fold to the
  ledger, on one host. Cloud, the artifact content-addressed store and a
  Saffron-owned state repository are named as things the interface must not
  preclude, and are not built.
- **Encoding.** A pure append-only log of facts per task. State is a replay.
- **The record mints its own task key**, because the ledger's `task_id` is an
  autoincrement the fold produces.
- **A record entry is a fact, not an event.** `saffron/events.py` owns "event"
  for the stream §8 keeps separate.
- **The batch is a fold, not a store.** Nothing anywhere holds a batch or a
  run. Both are derived from the task records.
- **Migration.** All 99 tasks, unambiguous fields only. A field the ledger
  cannot vouch for is absent rather than defaulted.
- **`queue.json` becomes a render before it goes**, and the two are checked
  against each other over real nights first.
- **Three of the spike's four unproven items are accepted in writing**, each
  with a cost and a clause that reopens it. The fourth was probed today and
  the result is below.

## 1. What this reverses, and why the old refusal does not reach it

Three places say SQLite is the system of record. `DESIGN.md` §4.6 rule 1: *"SQLite
remains the system of record. The graph is a projection with no write path
back."* And `docs/superpowers/specs/2026-09-02-ontology-authoritative-design.md`
twice — its section 2, *"The ledger is authoritative for facts"*, and its section
3, *"The ledger stays the system of record"*.

The argument under all three is §4.1's: a dependency-free state store is what
lets Saffron recover from Saffron. §4.6 rule 1 adds the second half — *"a
dual-write arrangement would trade it away for nothing at all: divergence in an
audit trail is worse than either store alone."*

Both halves survive the reversal, which is why it is admissible.

A git repository is dependency-free in the same sense the SQLite file is. It
needs no server, no migration and no schema. It is also already a hard
dependency of every path Saffron has: a task that cannot reach git produced
nothing to record.

And this is not dual-write. One writer appends to the record; one fold derives
the ledger. The ledger is deletable at any time, so it has no claim to defend and
nothing to diverge from. §4.6 rule 1's own words are what the new arrangement
satisfies, with the two stores exchanged: the *ledger* is now the projection
with no write path back.

Appendix U's principle 62 is the governing one. *A refusal reaches only as far
as its reason.* The reason here was argued against divergence between two
authoritative stores. An arrangement where the second store is derived is
outside it.

**What this does not reverse.** §4.1's `failures` argument stands unchanged —
the identity `(gate, file, code)` has to be queryable for baseline subtraction,
no-progress detection and the flywheel's question. That is a requirement on the
*ledger*, which is still SQL, and the fold is what satisfies it.

## 2. The record is an interface

Four operations, with no git in their signatures:

- `append(task_key, fact) -> None`. Appends one fact. Never rewrites, never
  deletes, never reorders.
- `read(task_key) -> list[Fact]`. The task's whole log, in append order.
- `task_keys() -> list[str]`. Every task key the record holds, so the fold has
  something to iterate over without git in its own signature.
- `compare_and_swap(key, expected, new) -> bool`. Unused on one host, and the
  seam a cross-host budget needs. It is specified now so a later backend does
  not have to reshape the fold to add it.

A fifth rule is a constraint rather than an operation: **the record holds facts
and content hashes, never artifacts.** `baseline.json`, `lens-gates.json` and
transcripts stay in the batch tree, and a fact names them by hash. The
measurement behind this was item 170's 2026-09-17 figure: `~/.saffron/ledger.db`
at 6.7 MB for 102 tasks, about 65 KB of facts each, against
`~/.saffron/batches/v0/` at 132 MB, about 1.3 MB each. That per-task number is
wrong. `docs/evidence/2026-09-20-fold-rebuild-time.md` found 287 KB of fact
JSON per task uncompressed, four times the estimate, and one `prose` gate
result alone weighing 1.27 MB. The conclusion still holds: packed, the same 118
tasks compress to 2.32 MiB, about 20 KB a task, still three orders of magnitude
below the artifacts. Facts are cheaper than what produced them, the tail is
heavier than assumed, and only facts go in the record.

Refs are the first implementation of this interface. A later store replaces the
backend and leaves the fold alone.

**The ledger keeps its name.** An earlier draft called it the index, which
`CONTEXT.md` §8 already gives to the morning page, and "projection" is worse —
`DESIGN.md` §4.6, §1.4 and §9 give it to the RDF graph, `saffron/projection.py`
is the module that emits one, and backlog item b-606ea3 is open on that word
having no glossary entry. Nothing here needs a new noun: what changes is that
the ledger is derived, not what it is called.

## 3. The refs backend

One ref per task, in the target repository the task ran against:

```
refs/saffron/tasks/<task_key>
```

Each `append` is a commit. Its tree carries the whole log to date, one blob per
fact:

```
facts/0001.json
facts/0002.json
...
```

Git's content addressing means every earlier blob is already stored, so the tree
grows by one object per append. The commit message names the fact kind and the
task, so `git log --oneline refs/saffron/tasks/<task_key>` is a readable
history with no tool.

Reading a task means reading the latest tree once and replaying its blobs; the
parent chain is never walked for state. What the chain carries is the append
history, and it is what makes the fast-forward check below mean something — a
push that is not a fast-forward is a writer that did not see every append.

The push carries no `--force`:

```
git push origin refs/saffron/tasks/<task_key>:refs/saffron/tasks/<task_key>
```

A non-fast-forward refusal therefore means a stale writer. Re-reading and
retrying is the caller's, and no caller does it yet: `append` lets the refusal
propagate, and no production path sets a remote. The retry lands with the
wiring. The spike measured that refusal directly, and it is the primitive the
cross-host budget needs later — the thing `batch.py:194` cannot provide across
hosts, because a SQLite file is local to one.

**What the spike settled about this layout.** A cell reaches neither the ref nor
its objects, by two independent mechanisms: `worktree.py`'s seed sequence fetches
only what it names, and the remote is removed before the agent runs. GitHub
accepts the namespace, keeps it out of branch listings and out of a default
clone, and serves it back on an explicit fetch. `gh pr list` is unaffected.

**Two costs the spike confirmed rather than supposed.** The trail is visible to
anyone with read access, so on a public repository the costs, findings and
critic claims are public. And a local clone of a mirror carries the objects by
hardlink even though the refs do not come with it, so *"clone the mirror"* is
not a way to hand somebody a scrubbed copy.

### Replay, and what it costs

State is a replay of the log. This was chosen over a snapshot tree because it is
what "append-only log" means without qualification: no commit restates a fact
an earlier one established, so no two commits can disagree about one.

The cost is that every read of a task's state is O(its history), and the fold
replays every task on every rebuild. At today's scale that is nothing — about
100 tasks at roughly 15 facts each is some 1,500 blob reads for a full rebuild,
against a local object store. It is written down because it is the first thing
that will stop being nothing: a rebuild is O(tasks x facts), and the mitigation,
when it is needed, is the one item 170 already names — finished tasks fold into
one history per period, which also bounds ref advertisement.

### Fact shape

A record entry is a **fact**, never an event. `saffron/events.py` owns "event"
for the `events.jsonl` stream, and §8 below is about keeping the two apart; one
word for both is where that separation would start to fail.

A fact is a JSON object with a kind, a timestamp, the batch key, and a payload
typed per kind. The kinds are a closed set covering what the ledger's tables hold today: task
creation and each state transition, attempt open and close with its cost and
terminal reason, gate results with their failures, findings with their three
judgements, and decisions.

Two fields are on every fact and are what makes the batch a fold rather than a
store: `batch_key` and `repo`.

**A task's identity in the record is not the ledger's.** `tasks.task_id` is a
SQLite autoincrement, and the fold mints it. An id the fold produces cannot name
the ref the fold reads, so a task carries a `task_key` generated at creation,
and the ledger holds it in a `record_key` column.

## 4. The fold

`saffron fold` rebuilds `~/.saffron/ledger.db` from the record. In the end
state nothing writes the ledger directly: every write goes to the record and the
fold follows. That end state is not this design's — here both are written, so
the fold's output can be compared against a ledger the old path produced, and
no production caller constructs a `Ledger` with a record at all. Cutting the
direct writes is the second plan's, with the `queue.json` cutover of §6.

The test is the one item 170 names, and it is the whole acceptance criterion for
this part: **delete the ledger, rebuild it, and get the same rows.**

Two artifacts carry it, because a unit test cannot depend on a private
`~/.saffron/ledger.db`. The test pins the mechanism on a fixture. A committed
benchmark script carries the corpus claim, folding a record synthesised from
real stored rows and comparing every table as a multiset. Neither alone is the
criterion: the fixture proves the fold agrees with itself, and the script proves
it agrees with itself over real shapes and real counts. What no artifact here
proves is a fold over a record a night actually wrote, because no night has
written one.

The ledger keeps its schema. §4.1's tables are a good analytical surface and
this changes nothing about them — it changes only what writes them.

## 5. The batch is a fold, and the run with it

§4.4 gives a batch one budget, one concurrency pool and one `--until`, spanning
every selected repo. Per-target refs give a task a home and give a batch none.

Nothing stores a batch. Every fact carries its `batch_key`, so a night's roster,
spend, wall clock and terminal-state counts are derived by scanning every
enabled target's `refs/saffron/tasks/*` for facts bearing that key.

The budget follows. `batch.py:194` reads
`budget_usd - ledger.batch_spend(batch_id)` today; it reads the same quantity
folded from the record instead. **No counter exists anywhere**, which is
stronger than a counter that agrees: there is nothing for a crash to leave
half-written and nothing for a stale writer to overwrite. The compare-and-swap
of §2 is what makes this efficient across hosts later, never what makes it
correct.

**What that costs has no number, and it is the one that can invalidate this
section.** `batch.py:194` runs before every task, and a fold over every enabled
target's refs is O(every task the record holds) rather than O(the night). The
whole-record fold measures 9.94 s over 118 tasks
(`docs/evidence/2026-09-20-fold-rebuild-time.md`). A night of ten tasks pays
that ten times, and the multiple grows with the record. There are two ways out
and this design picks neither. Read the spend from the derived ledger, which
makes a lagging store decide a ceiling. Or give the record an index per batch,
which is the second store §1 refuses. Plan 2 opens on this rather than reaching
it.

**This closes item 177.** A run stops being minted per task and becomes a fold
over the tasks sharing a `batch_id` and a `repo` — which is what §4.1 and
`CONTEXT.md` already define a run as, and what `SA-0100` could not make true
while every task minted its own.

## 6. `queue.json` becomes a render, then goes

Three steps, in order, because the fold's fidelity is worth measuring against
nights that already happened rather than against a fixture:

1. PACKAGE keeps writing `queue.json` at `report/index.py:214`. The fold also
   produces one, from the record, into a sibling path.
2. A check asserts the two are identical. It runs over the stored batch trees
   and over each new night. A disagreement is a fold defect, found while the
   store that would have caught it is still there.
3. Once the check has held across several batches, PACKAGE stops writing and
   the file is deleted. The index renders from the fold.

Between steps 1 and 3 `queue.json` is a render, not a store, and is named that
way in the code so it is not mistaken for one.

**This closes item 171.** The diff stat computed at `package.py:792` becomes a
fact field, so `added` and `removed` land in the record. Today they reach
`queue.json` and no store at all — §6's own mock renders `+180/−22` from a
number the ledger has no column for.

## 7. Migration

All 99 tasks move into the record. Only fields the ledger can vouch for are
written; a field it cannot is absent, not defaulted.

`risk` is the case that matters. It is written where the spec declared a tier,
and left absent otherwise. `SA-0085` therefore carries no declared tier rather
than a `standard` it never claimed. The earned tier needs a field of its own
and does not have one yet: `attempt_closed`'s payload is exactly
`close_attempt`'s arguments, and `effective_risk` reaches none of them. It lands
with the migration. The two quantities §4.1 conflated
under one name become two names, and the ambiguity dies at the migration
boundary instead of crossing it.

This also closes §4.1's second instance of its own failure — *"a column named
for a measurement it cannot make"*. `tasks.risk` is `NOT NULL DEFAULT
'standard'`, so all 99 rows read as measured rather than absent. That is
invisible rather than merely open, and it is why a faithful migration was
refused.

The trailing accept rate survives the migration: it reads `MERGED`, which is
unambiguous on all 65 rows that carry it.

## 8. Two streams, and the rule that keeps them from drifting

The record is not `events.jsonl`. That file stays local and is never the record,
because `saffron watch` tails it live and git cannot stream.

So there are two streams, and two streams is how divergence starts — which is
the exact defect this design exists to close. One rule prevents it:

> **Every record append also emits an event. No event implies an append.**

The rule binds from the point a production caller constructs a `Ledger` with a
record. Nothing does yet, and `_append` emits nothing, so the rule is stated
here and implemented with that wiring.

One direction only. The two can differ in prose, and can never differ on whether
something happened. An append that failed to emit is a missing line in a log; an
emit with no append would be a fact outside the record, and the rule forbids it.

**This is why item 43's open half does not block.** Item 170 lists 43, 166 and
167 as landing first. 166 and 167 are done (PRs #360 and #342). What is left of
43 is one free string, `re-verify: {label} suite at {sha}` in
`phases/package.py`, on the stream that is not the record. It should still be
typed; it is not a prerequisite.

## 9. Accepted rather than measured

Item 170 requires each of the spike's four unproven items to be closed by
measurement or accepted in writing with what it costs if wrong. One was probed
today. Three are accepted.

**Rulesets — accepted, with one new measurement.**
`docs/evidence/scripts/2026-09-20-refs-under-a-ruleset.sh` created a throwaway
private repository and tried to install six rulesets. Every call returned 403:
*"Upgrade to GitHub Pro or make this repository public to enable this
feature."* Reads of `repos/{slug}/rulesets` returned the same. So on GitHub Free
a private repository cannot carry a ruleset at all, and for that class of target
the question is moot — nothing can refuse the namespace. The baseline case in the
same probe pushed `refs/saffron/tasks/SA-0099` and it was accepted.
*Unmeasured:* whether a repository that *can* carry rulesets refuses ref
creation outside `refs/heads/*`. *Cost if wrong:* that target cannot hold its own
record and its facts must move to a Saffron-owned repository, which is the
arrangement §10 already keeps the interface open for. *Reopens on:* the first
target repository on a paid plan or a public one.

**Survival — accepted.** The spike measured minutes, not weeks. Whether
server-side gc prunes objects reachable only from a ref outside `refs/heads/*`
is unproven. *Cost if wrong:* a night's facts vanish from the remote while the
local ledger still holds them, so the loss is recoverable by re-push and is
detectable by the fold disagreeing with the remote. *Reopens on:* the first fold
that finds a ref's objects missing.

**Push rights from a fork — accepted.** A contributor working from a fork has no
push access for non-branch refs upstream. *Cost if wrong:* it bounds which
repositories this can serve to those where the operator has push rights, which
is every repository Saffron targets today. *Reopens on:* onboarding a target
Saffron cannot push to directly.

**Contention — accepted.** That a stale push is refused is measured. That a
retry loop over it is correct under real contention is not: one repository and
sequential cells today, so there has been nothing to contend. *Cost if wrong:* a
concurrent night loses or double-counts an append. *Reopens on:* the tier-0 gate
itself — a night of more than one task is the first thing that could contend,
and no such night has run.

## 10. What this does not build

Three things are named so the interface does not preclude them, and are not work
here.

- **A cloud runtime.** The second driver behind the whole change. What it needs
  from this design is the compare-and-swap of §2 and the absence of a local
  counter in §5, both of which are present.
- **The artifact content-addressed store.** §2 fixes the rule that the record
  holds hashes; where the bytes live is unchanged, and the batch tree stays as
  §4.1 describes it.
- **A Saffron-owned state repository.** It is what a target that refuses
  `refs/saffron/*` would need, and what a cross-target budget counter would live
  in if §5's fold ever becomes too slow. Neither is true yet.

## 11. Documents amended

Each of these asserts something this design reverses, and each is amended in
place rather than contradicted from a distance.

- `DESIGN.md` §4.6 rule 1 — restated. SQLite is the projection; the record is
  the system of record. The rule's argument is kept, with the two stores
  exchanged.
- `DESIGN.md` §6 — the fork is closed. The paragraph beginning *"The queue reads
  `queue.json`, not the ledger"* names the record and the render.
- `DESIGN.md` §4.1 — the ledger is described as derived rather than
  authoritative, and the two quantities under `risk` are separated.
- `DESIGN.md` §4.4 — the budget is a fold, not a counter.
- `DESIGN.md` §10 and `CLAUDE.md`'s "Layout" — both enumerate the packages
  under `saffron/`, and neither lists `saffron/record/`. `CLAUDE.md` is not
  `protected` and is done here; §10 lands with the rest.
- `CONTEXT.md` §8 — the **Ledger** entry stops saying "Authoritative for state"
  and says what it is instead: derived from the record, deletable, rebuilt by
  the fold.
  A new **Record** entry names this one, and its _Avoid_ line separates it from
  `records/`, the dev-only package holding Saffron's own project documents,
  whose `records.load.Record` is a second class of that name. The two never meet
  — `records/` imports nothing from `saffron/` and nothing under `saffron/`
  imports it, which its own docstring states — so the collision is in the
  vocabulary rather than in the code, and the vocabulary is where it is settled.
  Both entries are generated from `ontology/factory.ttl`, so the vocabulary is
  edited and `uv run python -m ontology.render` regenerates them.
- `docs/superpowers/specs/2026-09-02-ontology-authoritative-design.md` sections
  2 and 3 — amended in place, since they assert the opposite twice.

`DESIGN.md` and `CONTEXT.md` are `protected`, and this document amends a design
document under `docs/superpowers/specs/`. A cell can land none of it, which is
why item 170 is filed `by_hand: true`.

A new appendix records the reversal, as Appendix U records the appendices one. It
is a second instance of principle 62, and the principle is cited rather than
restated.

## Order of work

The implementation decomposes into six pieces, in dependency order:

1. The record interface and the refs backend, with the push-refusal path
   exercised.
2. The fold, and the delete-and-rebuild test against real stored nights.
3. The migration of the 99 tasks.
4. The batch and run folds, and `batch.py:194` reading the budget from them.
5. `queue.json` as a render, its equality check, and then its removal.
6. The document amendments and the appendix.

Steps 1 to 5 are code and can go through cells. Step 6 cannot.

## Open, and deliberately

**Whether the fold runs continuously or on demand.** The design says the ledger
is rebuilt from the record and does not say when. Continuous keeps `saffron
queue` fast and reintroduces a writer that can lag; on demand is simpler and
makes the morning index pay for the rebuild. The rebuild time now exists: 9.94 s
over 118 tasks, measured 2026-09-20. It does not settle the question on its own.
The number grows with the record, and the budget check of §5 reads the same
quantity once a task rather than once a morning.

**What the budget check costs.** §5 removes the counter and prices nothing in
its place. It is the first question plan 2 takes, and §5 says why.
