# Operator visibility Implementation Plan

> **For agentic workers:** this plan is **not** implemented by a subagent or
> by hand. Each task's deliverable is a Saffron spec file; the implementation
> is done by an agent in a cell driven by `saffron cell`. The steps here are
> the operator's. Do **not** invoke `superpowers:subagent-driven-development`
> or `superpowers:executing-plans` on it — that would hand-write the code
> these specs exist to have the factory write, in a repo whose point is that
> it writes its own.
>
> Subagents *are* used, twice per spec, and only to review: L3 reviews the
> spec before a cell spends money against it, and L7 reviews the diff per
> `superpowers:requesting-code-review` after the pull request is marked ready.
> Reviewing is the one thing a fresh context is better at than this session.

**Goal:** Make what the factory is doing and what it did visible — a typed
host event stream, a ledger that records what the page needs, and a page
sourced from the ledger rather than from a store only successful tasks write.

**Architecture:** `watch: Callable[[str], None]` becomes
`emit: Callable[[Event], None]`, fanned out to a terminal renderer printing
exactly what it prints today and an append-only JSONL log in the batch tree.
The ledger gains the three things the page cannot render without. The page is
then re-sourced from SQL, which makes the 13 task rows that never reach
PACKAGE visible and lets roughly half of `report/index.py` be deleted rather
than extended.

**Tech Stack:** Python (uv), pytest, stdlib `sqlite3`, f-string HTML (no Jinja
— see the `ponytail:` in `report/index.py`), `apple/container` for
cell-marked tests.

**Spec:** `docs/superpowers/specs/2026-08-31-operator-visibility-design.md`

## Global Constraints

- **Specs are numbered from the highest existing `SA-` id + 1.** Confirmed
  against `origin/main` at `aaafda5` (2026-09-01): `SA-0028` is highest and has
  **shipped** (PR #87), so this plan's ten are `SA-0029`–`SA-0038`.
  **Re-confirm before writing each file** — this set has been renumbered twice.
- **Every figure in a spec body is a dated measurement, and they go stale
  fast.** The ledger moved from 23 task rows to 29, and lifetime spend from
  $127.00 to $186.52, in the twenty-four hours between the design and this
  revision. Each `## Context` carries the date it was measured; **re-take the
  numbers at L1** and correct the body before committing the spec. A cell reads
  a stale figure as fact.
- **Every frontmatter field is required**: `id`, `title`, `type`, `priority`,
  `depends_on`, `touches` (or `envelope` for a bug), `forbidden`,
  `budget_usd`, `max_attempts`, `max_turns`, `risk`.
- **A spec cannot introduce the frontmatter it is written in** — `Spec` sets
  `extra="forbid"` (§3.2). None of these adds a field.
- **`DESIGN.md`, `CONTEXT.md` and `.saffron/**` are `protected`.** `SA-0023`
  refuses at gate 0 any spec whose `touches` names them, so every §6 edit is a
  by-hand follow-up (Task 11) with a `docs/BACKLOG.md` entry — the shape
  `SA-0018`, `SA-0021` and `SA-0024` established.
- **Vocabulary is enforced**, `CONTEXT.md`'s `_Avoid_` lists included: "cell"
  not "sandbox", "cell runtime" not "Docker", "batch" ≠ "run", "gate result"
  not "gate run".
- **Commit subjects** are lowercase `type(scope): what changed`, about the
  defect rather than the file.
- **`error` ≠ `fail`** wherever an event or a page carries a gate status.
- **Every cell runs sequentially.** v0.5 runs one attended cell; §4.2's
  concurrency pool is not built. The `depends_on` chains below are therefore
  honest about ordering rather than aspirational.

---

## Why ten specs

The design describes three parts. Three specs would make three diffs too wide
for their own repair loops — `docs/BACKLOG.md` item 25 records that failure
already, and `SA-0022` and `SA-0025` were both split mid-flight for it.

| design part | specs | why it splits |
|---|---|---|
| 1 — event seam | `SA-0029`–`SA-0031` | a new module, then ~70 `watch` sites in a 1495-line file, then 33 across four phase files and three in `cli.py` |
| 2 — ledger gaps | `SA-0032`–`SA-0034` | three independent changes sharing only `ledger.py`; the third has unknown blast radius |
| 3 — renderer | `SA-0035`–`SA-0038` | query, then render-and-delete, then the task page, then the timeline |

`SA-0034` is a **bug**, not a feature, and takes an `envelope` rather than
`touches`. Why `findings.verdict` is NULL is not known — measured, the write
path fires and the verdict half arrives empty, on n=2. Declaring `touches`
would mean diagnosing it by hand first, which §3.2 says inverts the economics:
the operator does the expensive part and the agent types. DIAGNOSE proposes
the scope and the operator ratifies it (§5.2).

## File structure

**Created by cells:** `saffron/events.py` (vocabulary, `EventLog`,
`read_log`, `describe` — top level, not under `report/`, because the
scheduler and PACKAGE emit these too and it keeps part 1 clear of
`saffron/report/**`); `saffron/report/render.py`; `tests/test_events.py`.

**Modified by cells:** `saffron/cell/session.py`, `saffron/phases/*.py`,
`saffron/ledger.py`, `saffron/report/index.py`, `saffron/replay.py`, and the
matching tests.

**`saffron/cli.py` is touched once, by `SA-0031` — and the design said it
never would be.** That claim was true at `7ab27cf` and false one commit later:
`256e529`, a review fix on `SA-0026` landed 2026-08-31, gave
`_resolve_stacked_on` a `watch=print` parameter and two `watch(...)` call sites
(`cli.py:226`, `:292`, `:297`). Two things follow. The *reason* for keeping
`cli.py` out — not colliding with in-flight stacking work — has expired, since
`SA-0026` (#84) and `SA-0027` (#88) have both merged. The *constraint*
underneath it survives and is restated as an acceptance criterion in
`SA-0031`: **the `emit` default stays in `session.py`.** `cli.py:393` calls
`run_one_cell` with no `emit` argument and must keep doing so. `SA-0031`
migrates three lines in `_resolve_stacked_on` and nothing else in that file.

**Also modified by cells, and missed by the first cut of this plan:**
`tests/test_implement.py`, `tests/test_package.py`, `tests/test_package_cell.py`,
`tests/test_rebut.py`, `tests/test_review.py`, `tests/test_agent_runner.py`,
`tests/test_cli.py`. Each calls a migrated function with `watch=`, `tests` is a
blocking gate, and a migration with no scope to repair them exhausts. They are
in `SA-0031`'s `touches` for that reason.

---

## Task 0: `SA-0028` has shipped — re-confirm numbering and collisions

**Renumbered twice here already, which is why this task exists.** `SA-0026`
merged, and PR #85 added two more specs in the same window — `SA-0027` (an
inertness guard whose retiring spec cannot reach the file) and `SA-0028` (an
implement turn that dies on its ceiling with nothing committed). This plan's
ten moved from `SA-0027`–`SA-0036` to `SA-0029`–`SA-0038`. Assume it happens
again.

**Both have since shipped** — `SA-0027` as PR #88, `SA-0028` as PR #87 — so
part 1's floor is in place and Task 1 is unblocked. What remains of this task
is the re-check, and the re-check is the half that has never once come back
clean: the first pass of this plan cleared `cli.py` and `cli.py` had acquired
a `watch` parameter the day before.

### `SA-0028` was part 1's floor, and it has landed

Its `touches` are `saffron/cell/session.py`, `saffron/phases/implement.py`,
`tests/test_session.py`, `tests/test_implement.py` — part 1's exact territory.
That alone would make it a dependency. The deeper problem is what it *does*:

> - the watch line says which ceiling stopped it — `SA-0005`'s lesson, that a
>   run stopped by one of three ceilings must say which
> - a salvage that produces nothing still ends `NOT_IMPLEMENTED`, and the
>   watch line distinguishes "was cut off and could not be salvaged" from
>   "finished and produced nothing"

**It adds `watch` lines**, and they are on `main` now — four `SALVAGE:` lines
and `IMPLEMENT: finished and produced nothing`, at `session.py:1143`–`1201`. So
`SA-0029`'s golden fixture — the whole basis on which part 1's migrations are
verified — could not have been captured before this landed: it would record
output that was about to change, and the migrations would then fail against a
stale fixture for a reason that is not a migration bug. That is why even
`SA-0029`, which touches only `saffron/events.py` and its own tests, declares
`depends_on: SA-0028`: the dependency is the fixture, not the module. The
declaration stays in the frontmatter as the record of why; the gate now passes
it.

**And its two new facts want event fields, not strings.** "Which of three
ceilings stopped this" and "cut off versus finished empty" are exactly the
kind of structured fact part 1 exists to stop losing — `SA-0029`'s `Budget`
and `Terminal` dataclasses should carry them as typed fields when it models
the vocabulary. Landing `SA-0028` first means modelling them once; landing it
after means retrofitting two strings into a seam that has just been typed.

`SA-0027` does not collide: it touches `saffron/cli.py`,
`saffron/scheduler.py` and `saffron/repos/mirror.py`, none of which any spec
in this plan modifies.

### Steps

- [ ] **Step 1: Re-confirm `SA-0028` has shipped.** It had, at `aaafda5`.

```bash
git fetch origin && git log --oneline -5 origin/main
gh pr list --state merged --limit 8 --json number,title -q '.[] | "\(.number) \(.title)"'
grep -c 'SALVAGE:' saffron/cell/session.py
```

Expected: PR #87 merged, and the `SALVAGE:` watch lines present in
`session.py`. **A spec file in `.saffron/specs/` proves nothing either way** —
retirement (L8) lags merging in this repo, and `.saffron/specs/` currently
holds nine specs whose code is already on `main`. Check the pull request and
the code, never the spec file's location.

- [ ] **Step 2: Rebase**

```bash
git rebase origin/main
```

This runs on the default branch, before any stack exists. **Once a stack is
open, do not rebase by hand** — `gh stack sync` fetches, reconciles with
GitHub, rebases the chain and refreshes pull request state in one operation,
and a bare `git rebase` inside a stack rewrites branches Saffron has already
pushed. If `sync` prints both chains and says `Sync aborted`, local and remote
have diverged; stop and read, do not force.

- [ ] **Step 3: Re-confirm the next free id**

```bash
ls .saffron/specs/ .saffron/specs/done/ | grep -o 'SA-[0-9]\{4\}' | sort -u | tail -3
```

Expected: highest is `SA-0028`. If higher, renumber every spec below **and**
the design doc's numbering note together, so the two do not drift. This has
already happened twice.

- [ ] **Step 4: Re-check part 1's territory — in the code, not only in the specs**

```bash
# specs still queued against part 1's files
grep -l 'saffron/cell/session.py\|saffron/phases/\|saffron/cli.py' .saffron/specs/SA-*.md
# and the check that would have caught cli.py: where `watch` actually is
grep -rn 'watch' --include='*.py' saffron/ \
  | grep -v '^saffron/cell/session.py' | grep -v '^saffron/phases/'
grep -rln 'watch=' --include='*.py' tests/
```

**The spec grep alone is not enough, and this is the check that failed.** It
returns merged-but-unretired specs as false positives, and it cannot see a
`watch` parameter that arrived as a *review fix* on a spec whose own `touches`
never mentioned one — which is exactly how `cli.py` acquired three of them.

Read the second and third commands' output against `SA-0030`'s and `SA-0031`'s
`touches`. **Every file they list must appear in one of the two**, or the
migration ends `EXHAUSTED` against a blocking `tests` gate it has no scope to
repair. As of 2026-09-01 that set is `saffron/cli.py` plus seven test files,
and all eight are in `SA-0031`.

Any spec still queued against `session.py`, `phases/` or `cli.py` is a fresh
collision with part 1, and the same reasoning as `SA-0028` applies: if it adds
or changes a `watch` line, it lands before `SA-0029`'s golden fixture is
captured, not after.

---

## Stacking: two mechanisms, and the plan runs on the wrong one by default

**This plan was written before `.claude/skills/run-saffron-spec-loop` existed
and assumed each pull request merges before the next cell starts.** That is one
valid way to run it. The other — the skill's, verified against this repo on
2026-09-01 — leaves every pull request open and links them into a GitHub stack
for one review pass. The two are not interchangeable, and four things break if
you switch without reading this section.

**There are two stacking mechanisms and only one of them stacks the code.**
Saffron's own (`SA-0026`): `cli._resolve_stacked_on` reads `depends_on[0]`'s
newest task in `DEPENDENCY_WAITING_STATES` — `READY_FOR_REVIEW`, `APPROVED`,
`MERGE_TRAIN` — fetches that branch, and cuts the worktree from it, so PACKAGE
opens the child's pull request *against the parent's branch*. `gh stack link`
is the operator's, and it only retargets a base on GitHub; it moves no commits.
Saffron's is the real one. `gh stack` is presentation over it.

### K=1: only `depends_on[0]` is ever consulted

`_resolve_stacked_on`'s docstring is explicit — *"A spec naming a second,
unmerged parent does not stack on it too … out of reach by design."* Two specs
here name two parents, and both are wrong as written for an unmerged stack:

- **`SA-0035` declares `depends_on: [SA-0033, SA-0034]`**, so it would stack on
  `SA-0033` and its worktree would **not contain `SA-0034`'s verdict write** —
  the input its own `sustained`/`unkept` criterion needs. `SA-0034` depends on
  `SA-0033`, so `SA-0034`'s branch already carries both. **Fixed below by
  putting `SA-0034` first**; the newest parent goes in slot 0, always.
- **`SA-0038` declares `depends_on: [SA-0037, SA-0031]`**, and those are on two
  different chains. No ordering of that list fixes it: K=1 can reach one.

### Therefore: two stacks, run and merged in sequence

`gh stack` stacks are strictly linear — one parent, at most one child — and
this plan's dependency graph forks. It cannot be one stack. Nor should the two
chains be open at once:

```
stack 1   (main) <- saffron/SA-0029 <- saffron/SA-0030 <- saffron/SA-0031
                    ── merge, then ──
stack 2   (main) <- saffron/SA-0032 <- SA-0033 <- SA-0034 <- SA-0035
                                    <- SA-0036 <- SA-0037 <- SA-0038
```

Merging part 1 before `SA-0032`'s cell starts pays for itself four times:
`SA-0038`'s second parent becomes `MERGED` and satisfies the gate without
needing a slot; `SA-0032` cuts from a `main` that already carries part 1's
`docs/BACKLOG.md` entries; the two chain heads stop being siblings; and each
stack stays inside a size a single review pass can hold.

**Do not run the two chains concurrently.** They would be sibling branches from
the same `base_sha`, and **eight of the ten specs name `docs/BACKLOG.md` in
`touches`** — all but `SA-0032` and `SA-0034`, whose `envelope`s do not reach it
and whose DIAGNOSE therefore cannot propose it. That is the exact collision the
skill measured on `SA-0027`/`SA-0028`, where both appended `## 34.` and
`git merge-tree` reported a conflict while the stacked pull request page
rendered clean. Eight specs is a seven-way version of it.

### `saffron queue` stops answering once the first pull request is open

The skill's own measurement: `build_queue` is computed against **open** pull
requests, so the moment one is open, every later spec is refused twice over —
`an open pull request from another task already targets this spec`, and
`touches overlaps open pull request's changed files`, which for this plan is
`docs/BACKLOG.md` every time.

`saffron cell` is unaffected: the attended path checks `protected` collisions
(`protected_touch_refusal`) and retirement markers (`retirement_refusal`) and
**nothing else** — no `depends_on` check, no overlap check, no open-pull-request
check. It will happily run a spec `queue` refuses. That is what makes the stack
workflow possible and what makes L2 below conditional.

### Nothing merges until the stack does

`gh pr merge` cannot merge a stack. The final merge is one command per stack,
bottom-up and all-or-nothing:

```bash
gh stack merge <top-pr> --yes --squash    # that PR and every unmerged PR below it
```

If any pull request in that set cannot merge, none do.

## The per-spec loop

Every task below runs the same steps. They are written once here and
referenced by number, rather than repeated ten times.

**If you are running the stack workflow, `.claude/skills/run-saffron-spec-loop`
is authoritative for the mechanics** — the plan snapshot, `PYTHONUNBUFFERED=1`,
recording from the ledger rather than the transcript, and `gh stack link`. What
follows is this plan's spec-specific content laid over the same loop, with the
steps that differ marked.

**Two of them are independent-agent reviews, and "independent" is the whole
point.** Both reviewers are dispatched as subagents with *no access to this
session's history* — they get the spec, the design document and the diff, and
nothing about how any of it came to be written. A reviewer that has read the
reasoning is checking the reasoning against itself, which is the same defect
as regenerating a golden fixture after a migration.

- **L1 — Write the spec** to `.saffron/specs/<id>-<slug>.md`, body verbatim
  from the task.
- **L2 — Verify intake and gate 0:** `uv run saffron queue --repo .`.
  Expected: the spec appears **queued**. If **refused**, read the reason and
  fix the spec before spending a cell — a `touches`/`protected` collision, an
  acceptance criterion naming a path no `touches` pattern matches, or an
  unsatisfied `depends_on`. This check costs nothing; `SA-0021` cost $0.82 to
  learn the same thing after a mirror fetch, an image build and a model turn.

  **Under the stack workflow this check only means something for the first
  spec of each stack.** Once one pull request is open, `queue` refuses every
  later spec on `an open pull request from another task already targets this
  spec` and on `touches overlaps … docs/BACKLOG.md`, and neither is a defect
  in the spec. Two refusals still are, because `saffron cell` checks them too
  and they are the cheap ones this step exists for:

  - `refused  … protected …` — a `touches` entry hitting `policy.yaml`'s
    `protected` list. Real; fix the spec.
  - `refused  … retired-by …` — a retirement marker this spec's `touches`
    cannot reach (`SA-0027`). Real; fix the spec.

  Everything else, once a pull request is open, is the queue telling you the
  batch is in flight. Read the refusal; do not "fix" a spec against it.
- **L3 — Independent spec review.** Dispatch a subagent with a clean context.
  A spec is the input to a cell that will spend $8–18 against it and to a
  critic that will use its acceptance criteria as a rubric, so a defect here
  is the most expensive kind to find late. Give the reviewer the spec file,
  `docs/superpowers/specs/2026-08-31-operator-visibility-design.md`, and
  `DESIGN.md` §3.2, and ask specifically:

  - Is every acceptance criterion **checkable** — could a critic hold the diff
    against it and reach a verdict — or is any of them an aspiration?
  - Does any criterion name a path no `touches` pattern matches? (Gate 0
    refuses that, and L2 has already checked mechanically; this is the reading
    that catches a criterion whose path is *implied* rather than named.)
  - Is `## Out of scope` doing real work, or restating the title?
  - Does the spec ask for anything the design does not support, or omit
    anything the design requires of this part?
  - Is anything in it a guess presented as a measurement?

  Act on the findings; if any change touches frontmatter, re-run **L2**.
- **L4 — Commit the spec on the default branch:**
  `git commit -m "spec(<id>): <title>"`. Spec files never travel on a cell's
  branch — `.saffron/**` is `protected`, no cell can write one, and
  `saffron cell` reads the file from the working copy while the cell's worktree
  comes from the mirror. Commit and push to `main` even while a stack is open.
- **L5 — Run the cell:**

```bash
env CLAUDE_CODE_OAUTH_TOKEN=(bash -c 'source ~/.secrets; printf %s $CLAUDE_CODE_OAUTH_TOKEN') \
  uv run saffron cell .saffron/specs/<id>-<slug>.md --repo .
```

  Exit `0` reviewable · `1` the task did not make it · `2` infrastructure,
  which is owed a re-run and charged to nobody.
- **L5a — Ratify a scope proposal.** *Bug specs only (Tasks 4 and 6).* See
  "The ratification detour" below. Skip entirely for a feature or refactor
  spec, which declares its own `touches`.
- **L6 — Read the PR, then mark it ready.** Read the disagreements first; the
  PR body puts them above the gate table because that is where judgment is
  worth most (§6). `gh pr ready <n>` — **do not merge yet.**

  PACKAGE opens drafts deliberately (§5.7) and `gh pr ready` is the operator
  ratifying one. Never reach for `gh stack submit --open`, which flips every
  pull request in the stack at once.
- **L7 — Independent code review**, per the `superpowers:requesting-code-review`
  skill, on the now-ready PR:

```bash
gh pr view <n> --json baseRefOid,headRefOid -q '.baseRefOid, .headRefOid'
```

  Dispatch the reviewer subagent with the skill's `code-reviewer.md` template:

  - `{DESCRIPTION}` — what the cell built, one or two sentences
  - `{PLAN_OR_REQUIREMENTS}` — **the spec's own acceptance criteria**, which
    are already the requirements document and already the critic's rubric
  - `{BASE_SHA}` / `{HEAD_SHA}` — from the command above

  `gh pr view <n> --json baseRefOid` returns the **parent branch's** head for a
  stacked pull request, not `main`'s, so the range is that layer's own diff.
  That is what makes a ten-spec chain reviewable at all; do not substitute
  `main` for it.

  Fix Critical before merging, fix Important before proceeding to the next
  task, note Minor. Commit fixes **on the cell's branch** (`saffron/<id>`) and
  push — never on `main`, and never on the branch above. **Push back if the
  reviewer is wrong, with reasoning** — the skill says so, and this repo's own
  REBUT phase exists because a reviewer's confirmed finding and a correct
  finding are not the same thing.

  **Then stop. Do not merge.** Merging mid-loop is the sequential workflow, and
  it is a different plan: it rebuilds the queue against a moved `main`, and it
  denies every later spec the parent branch `_resolve_stacked_on` needs, since
  a `MERGED` parent yields `(None, None)` and the child cuts from `main`
  instead. Under the stack workflow the merge is Task 12, once per stack.
- **L8 — Retire, after the stack merges, not here.**
  `git mv .saffron/specs/<id>-*.md .saffron/specs/done/`, committed as
  `chore(specs): retire <id> as shipped`. Retiring a spec whose pull request is
  still open removes the file `saffron queue`, `record` and
  `_retirement_markers_at` all read. Task 12 does this for a whole stack.

### Why two reviews and not one

They catch different failures and neither substitutes for the other. L3 reads
a spec nobody has implemented, where the failure mode is an unfalsifiable
acceptance criterion — cheap to fix, and ruinous once a cell has spent $16
satisfying it in a way you did not mean. L7 reads a diff, where the failure
mode is code that satisfies every criterion and is still wrong.

Saffron's own adversarial critic already ran inside the cell at L5, and L7 is
deliberately not a second copy of it: the critic judged the diff against the
spec from *inside* the run that produced it, under lenses the repo configured.
L7 is outside that loop and reviews the same diff with the repo's own
standards in hand. Where they disagree, that disagreement is the most useful
thing on the page.

### The ratification detour (L5a)

`SA-0032` and `SA-0034` are `bug` specs with an `envelope` and no `touches`,
so DIAGNOSE proposes the scope and the cell **stops** at `SCOPE_REVIEW`,
exiting `1`. That is the door §5.2 designed, not a failure — but the plan must
be honest that the door is half-built.

`docs/BACKLOG.md` item 31: *"Nothing in `saffron/` performs the writeback yet:
`SCOPE_REVIEW` writes `scope_proposal.json` and stops for a human."* And it
cannot simply be built, because `SA-0024` made the deny lists independent of
`touches` while this repo lists `.saffron/**` under `protected` — so a
host-authored writeback commit to `.saffron/specs/…` would fail `scope` as a
protected path, a blocking failure the agent cannot repair without destroying
the ratification you just granted.

So ratification is by hand:

1. Read `~/.saffron/batches/v0/<id>/scope_proposal.json`.
2. If the proposed `touches` is right, write it into the spec's frontmatter
   yourself. If it is wrong, the spec's `envelope` or its problem statement is
   wrong — fix that and go back to **L2**, rather than editing the proposal
   into something the diagnosis did not support.
3. Commit **on the default branch**, not on any cell branch:
   `git commit -m "ratify(<id>): <what the diagnosis found>"`.
4. Re-run **L5**. The second cell implements against the ratified `touches`.

**Editing the spec moves its `spec_sha`, and that is load-bearing.** The
ratified file is a different spec as far as the ledger is concerned, so the
first cell's `SCOPE_REVIEW` row belongs to the old sha and the second cell
mints a new task. That is correct — but it also means the loop driver's
`record` will say `no task for <id> at <sha> — did the cell run?` if you record
before re-running. Ratify, re-run L5, then record.

**This costs two cells for each of those two specs**, and the DIAGNOSE turns
are paid twice. Budget for it: `SA-0032` and `SA-0034` are the only two tasks
in this plan where the stated `budget_usd` is a per-cell figure rather than a
per-spec one.

---

## Task 1: `SA-0029` — the event vocabulary and its log

Additive and deliberately inert: nothing emits these yet. `SA-0022` and
`SA-0025` both shipped machinery with no producer for the same reason — a
seam is easier to review before thirty call sites move onto it.

**Interfaces produced:** `saffron.events.Event` (union), the nine dataclasses,
`EventLog(task_dir)`, `read_log(path) -> list[Event]`,
`describe(event) -> str`. Consumed by every later task in parts 1, 3 and 4.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0029
title: the host has no event vocabulary, so a night's sequence exists only as prose
type: feature
priority: 1
depends_on:
  - SA-0028
touches:
  - saffron/events.py
  - tests/test_events.py
  - tests/fixtures/watch-golden.txt
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/scheduler.py
  - images/**
budget_usd: 10
max_attempts: 3
max_turns: 90
risk: standard
---

## Context
`run_one_cell` takes `watch: Callable[[str], None] = print`, and roughly thirty
call sites author prose into it — `gates: attempt 2, 3 new failures -> repair`,
`budget: $4.20 of $9.00 — stopping`. The structure behind each line lives in an
f-string and is gone when the terminal scrolls.

The repo already does this correctly one level down: `images/agent_runner.py`
emits Saffron's own typed events as JSON lines and `phases/implement.py`'s
`_consume` renders them with `watch(_describe(event))` — structure first, prose
at the edge. Host-side the arrangement is inverted.

This spec builds the vocabulary and changes no caller. Nothing emits an `Event`
when it lands.

## Problem
- **There is no type that can carry a host-side fact.** `SA-0030` and `SA-0031`
  migrate call sites and cannot begin without one.
- **A night's sequence is unrecoverable.** The ledger records outcomes and not
  order. Three task rows in this repo's ledger are `ORPHANED` at `$0.00` with
  one attempt or none — a cell that died with nothing written. SQL can say a
  task ended that way; it cannot say how far it got first.
- **The current output has no recorded shape**, so a migration that changes it
  by accident cannot be caught. The golden fixture here is what later specs
  assert against.

## Acceptance criteria
- [ ] `saffron/events.py` defines a frozen dataclass per kind — `Preflight`,
      `Baseline`, `PhaseStart`, `Attempt`, `GateResult`, `Budget`, `Agent`,
      `Terminal`, `Teardown` — each carrying a timestamp and the `spec_id`
      plus its own typed fields
- [ ] `GateResult` carries all four statuses (`pass`, `fail`, `skip`, `error`)
      and a test asserts `error` and `fail` are distinguishable after a
      round-trip: `error` means the gate broke and is charged to nobody
- [ ] `EventLog(task_dir)` appends exactly one JSON object per line to
      `events.jsonl` and flushes per event, so a cell killed mid-run keeps
      everything written before the kill
- [ ] `read_log` drops a truncated **final** line and returns every whole line
      before it — a test writes a file ending mid-object and asserts the
      earlier events survive. Per-line tolerance, never a whole-file discard,
      the rule `_existing_queue_rows` already applies
- [ ] `read_log` tolerates an unknown event kind rather than raising, so a log
      written by a newer Saffron stays readable
- [ ] `Agent` carries a cell event dict **verbatim** under one key, and no
      Agent SDK type is imported: `images/agent_runner.py` stays the only file
      that has ever seen one
- [ ] `describe(event)` returns the exact line today's `watch` call site would
      have printed, for every kind
- [ ] `tests/fixtures/watch-golden.txt` records the current terminal output of
      a driven session, captured from **unmodified** code and committed here as
      the fixture `SA-0030` and `SA-0031` assert against
- [ ] An `EventLog` write failure raises nothing to its caller — a test points
      it at an unwritable path and asserts the call returns
- [ ] A `ponytail:` names the ceiling: one file per task, no rotation, tens of
      MB a night by §4.1's estimate
- [ ] Every new test runs with no network and no cell

## Out of scope
**Every call site.** `saffron/cell/**` and `saffron/phases/**` are `forbidden`
here. `SA-0030` and `SA-0031` migrate them.

**Any renderer.** `saffron/report/**` is `forbidden`. The page is `SA-0036`.

**Emitting from the scheduler.** It has no `watch` today and gains events when
§4.2's orchestration exists; adding them now is events with no producer.

**Reading the log for a decision.** Nothing consumes `events.jsonl` for
control, here or ever: every control that matters lives outside the cell.

**Rotation, compression or a size cap.** Named as a ceiling, not built.

## Notes for the agent
**The golden fixture must be captured from unmodified code.** A fixture
generated after a change proves the change agrees with itself. This spec
changes no call site, which is what makes the capture trustworthy — and it is
the reason this spec exists separately at all.

**A "driven session" needs no container, and the fixture test must not be
marked `cell`.** `tests/test_session.py` carries **no** `pytest.mark.cell`: it
drives `run_one_cell` end to end against a stubbed runtime, a stubbed export
and a monkeypatched `run_agent`, and that is where the capture comes from.
`pyproject`'s `addopts` excludes `cell`-marked tests from the default run, so a
golden assertion carrying that marker would be **skipped by `make check`** and
`SA-0030` and `SA-0031` would then verify their migrations against a test that
never executes. Capture and assert host-side, unmarked.

**Unmodified means "after `SA-0028` has landed", not "now".** `SA-0028` adds
`watch` lines — one naming which of three ceilings stopped a run, one
distinguishing "cut off and could not be salvaged" from "finished and produced
nothing". A fixture captured before it records output that is about to change,
and `SA-0030` and `SA-0031` then fail against a stale fixture for a reason that
is not a migration bug. That is what `depends_on: SA-0028` is buying here, in a
spec that shares no file with it.

**Model `SA-0028`'s two new facts as typed fields, not as strings inside a
message.** "Which of the three ceilings stopped this" belongs on `Budget` or
`Terminal` as a field, and "cut off versus finished empty" belongs on
`Terminal` — both are exactly the kind of structured fact this vocabulary
exists to stop losing, and `SA-0005`'s lesson (a run stopped by one of three
ceilings must say which) is the reason `SA-0028` wrote them in the first place.
They arrive as prose; do not enshrine them that way.

**`_describe` already exists in `phases/implement.py`** for the cell's own
events. `SA-0031` moves it. Write `describe` here so that the moved one can
collapse into it, not beside it.

**A dataclass per kind, not one class with a `type` string.** The cell uses a
dict discriminator because it crosses a process boundary and must never raise
on an unknown shape. The host does not cross one, and a typed field is what
lets a renderer know what it holds.

Commit after each coherent step. Uncommitted work dies with the cell.
```

- [ ] **L2–L8** as described in "The per-spec loop".

---

## Task 2: `SA-0030` — `session.py`'s call sites become events

**Interfaces:** consumes everything from Task 1. Produces
`run_one_cell(..., emit=...)` with `watch` gone from `session.py`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0030
title: the supervisor's twenty progress lines are prose, and the record needs events
type: refactor
priority: 1
depends_on:
  - SA-0028
  - SA-0029
touches:
  - saffron/cell/session.py
  - tests/test_session.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/events.py
  - images/**
budget_usd: 14
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
`SA-0029` shipped `saffron/events.py` — the vocabulary, `EventLog`,
`read_log`, `describe` — and a golden fixture recording the terminal output of
a driven session, captured from code nothing had yet changed. Nothing emits an
event.

`saffron/cell/session.py` is 1322 lines and holds about twenty `watch(...)`
call sites: preflight's proxy and image lines, the baseline summary, the
plan checkpoint, per-attempt gate decisions, the budget stop, teardown's patch
export, and the terminal line.

## Problem
- **The supervisor is where the sequence is decided and where it is lost.**
  Every phase transition, every attempt decision and the budget stop pass
  through here as a string.
- **`emit` has no producer.** `SA-0029` built a vocabulary with no caller; the
  seam is unproven until a real driver uses it.
- **The default lives in the wrong place to be changed later.** `run_one_cell`
  is where `watch` is defaulted, and `cli.py` never names it. That is what
  keeps this whole change out of `SA-0026`'s file, and it is only true while
  the default stays here.

## Acceptance criteria
- [ ] Every `watch(...)` in `saffron/cell/session.py` is an `emit(<Event>)`,
      and no signature in the file still carries a `watch` parameter
- [ ] **The terminal output does not change.** A test drives a session and
      asserts its printed lines equal `tests/fixtures/watch-golden.txt`, line
      for line
- [ ] `saffron/cli.py` is not modified and is not in `touches`: the default
      `emit` is constructed inside `session.py`, and a test calls
      `run_one_cell` with no `emit` argument and asserts it still prints
- [ ] The default `emit` fans out to both consumers — the terminal renderer and
      an `EventLog` at `task_dir` — and a test asserts a driven session leaves
      an `events.jsonl` whose `read_log` returns the same sequence the terminal
      printed
- [ ] A gate result event carries `error` distinctly from `fail`, and a test
      drives an attempt where a gate errors and asserts the recorded status
- [ ] An `EventLog` failure does not abort a run: a test makes `task_dir`
      unwritable and asserts the session still reaches its terminal state
- [ ] `phases/` is untouched — it still receives a `watch`-shaped callable, and
      a test asserts the seam between them is intact until `SA-0031`
- [ ] Every new test runs with no network and no cell. **The golden-output
      test in particular must not carry the `cell` marker**: `pyproject`'s
      `addopts` excludes those from the default run, and a skipped assertion is
      how this spec's one real acceptance criterion passes without executing.
      `tests/test_session.py` drives `run_one_cell` against a stubbed runtime
      today and has no `cell` marker anywhere — follow it

## Out of scope
**The phases.** `saffron/phases/**` is `forbidden`. `SA-0031` migrates them,
and doing both here is one diff too wide for one repair loop (item 25).

**Changing any message.** If a line reads badly, it still reads exactly that
way after this spec. The golden fixture is the point; improving copy in the
same diff makes it impossible to tell a migration bug from an edit.

**Any renderer, and any new event kind.** `SA-0029` fixed the vocabulary. A
call site that does not fit an existing kind is a finding for the pull request
body, not a tenth dataclass added here.

## Notes for the agent
**The golden fixture is the acceptance criterion, not a convenience.** If it
does not match, the migration is wrong — do not regenerate it. It was captured
in `SA-0029` from code nothing had changed, which is the only capture that
proves anything.

**Keep the `emit` default in `session.py`.** Moving it to `cli.py` would put
this diff in `SA-0026`'s file for no gain, and `cli.py` is `forbidden` here.

**`phases/` still takes a `watch`.** Adapt at the boundary — the phase call
sites keep receiving a string-taking callable until `SA-0031`. A half-migrated
seam that leaves both files broken is the failure this split exists to avoid.

**Six test files outside this spec's `touches` call a phase function with
`watch=`** — `test_implement.py` (27 sites), `test_package.py` (7),
`test_package_cell.py`, `test_rebut.py`, `test_review.py`,
`test_agent_runner.py` — and the adapter is the only thing keeping them green.
That is what makes this spec's scope sufficient and `SA-0031`'s wider: `tests`
is a blocking gate, and a migration that cannot edit its callers' tests cannot
pass. Do not remove the adapter here to be tidy.

**`error` ≠ `fail`, and the events must not blur them.** `fail` means the
repo's code is wrong; `error` means the gate broke, aborts the attempt, and is
charged to nobody.

Commit after each coherent step. Uncommitted work dies with the cell.
```

- [ ] **L2–L8.**

---

## Task 3: `SA-0031` — the phases' call sites become events

**Interfaces:** consumes Tasks 1–2. Produces a repo with no `watch` parameter
anywhere.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0031
title: four phase modules still speak prose to a supervisor that speaks events
type: refactor
priority: 1
depends_on:
  - SA-0030
touches:
  - saffron/phases/implement.py
  - saffron/phases/package.py
  - saffron/phases/rebut.py
  - saffron/phases/review.py
  - saffron/cli.py
  - tests/test_session.py
  - tests/test_implement.py
  - tests/test_package.py
  - tests/test_package_cell.py
  - tests/test_rebut.py
  - tests/test_review.py
  - tests/test_agent_runner.py
  - tests/test_cli.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/ledger.py
  - saffron/cell/session.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/events.py
  - images/**
budget_usd: 16
max_attempts: 4
max_turns: 130
risk: elevated
---

## Context
`SA-0030` migrated the supervisor and left an adapter at the phase boundary:
`phases/` still receives a string-taking callable. Thirty-three call sites
remain, measured 2026-09-01 — `implement.py` 8 (the agent stream and its
raw-line quarantine), `package.py` 11 (re-verify, conflict, refusal-to-push,
the pull request URL), `rebut.py` 9, `review.py` 5.

**And three more in `saffron/cli.py`, which this plan said would never be
touched.** `_resolve_stacked_on` takes `watch=print` and calls it twice
(`cli.py:226`, `:292`, `:297`), added by `256e529` — a review fix on `SA-0026`,
landed the day this plan was written, on a spec whose own `touches` named no
`watch`. It is the last `watch` outside `phases/`, so it is this spec's or
nobody's.

`implement.py` is the interesting one. It already holds `_describe`, written
for the **cell's** events, and calls `watch(_describe(event))`. `SA-0029`
shipped a host-side `describe`. Two functions now render events, and only one
of them should survive.

## Problem
- **The adapter is a seam with no owner.** It exists so `SA-0030` could land
  without touching four more files, and it is dead weight the moment those
  files move.
- **Two `describe` implementations will drift.** The host and the cell
  rendering the same event two ways is exactly the divergence structure-first
  exists to prevent.
- **PACKAGE's lines are the ones an unattended morning needs most** — a refused
  push, a conflict with the default branch, new failures against `main` — and
  they are strings.
- **Seven test files call a migrated function with `watch=`** —
  `test_implement.py` (27 sites), `test_package.py` (7), `test_cli.py` (3 on
  `_resolve_stacked_on`), `test_package_cell.py`, `test_rebut.py`,
  `test_review.py`, `test_agent_runner.py` — and `tests` is blocking. They are
  in `touches` because a migration that cannot repair its callers' tests cannot
  pass its own gates.

## Acceptance criteria
- [ ] Every `watch(...)` in the four phase modules **and in
      `cli._resolve_stacked_on`** is an `emit(<Event>)`, and no signature in
      `saffron/` still carries a `watch` parameter — a test greps the package
      and asserts none remains. `saffron/cli.py` is in `touches` precisely so
      this criterion can be discharged rather than worked around
- [ ] **`cli.py:393` still calls `run_one_cell` with no `emit` argument**, and
      a test asserts it. Migrating three lines in `_resolve_stacked_on` is not
      licence to move the seam up: the default `emit` stays constructed in
      `session.py`
- [ ] The seven test files in `touches` are migrated with their callees and the
      suite is green — no `watch=` remains anywhere under `tests/`
- [ ] The adapter `SA-0030` left at the phase boundary is **deleted**
- [ ] **The terminal output does not change**, asserted against
      `tests/fixtures/watch-golden.txt` as in `SA-0030`
- [ ] `implement.py`'s `_describe` is gone and its behaviour is served by
      `events.describe`; a test asserts a cell event renders identically to
      the line `_describe` produced
- [ ] An `Agent` event wraps the cell's event dict verbatim, and the
      `agent: (raw)` path — a line that is not an event, from a process sharing
      the runner's stdout — is still shown to the operator and still never
      parsed as one
- [ ] A test asserts an unknown cell event kind reaches the log and the
      terminal without raising
- [ ] Every new test runs with no network and no cell, and the golden-output
      test is **not** `cell`-marked, for the reason `SA-0030` gives: `addopts`
      would exclude it and the migration would verify against a skipped
      assertion. `tests/test_package_cell.py` is the one file here that is
      genuinely cell-marked; nothing new joins it

## Out of scope
**`saffron/cell/session.py`.** `forbidden` — `SA-0030` finished it.

**Everything in `saffron/cli.py` except `_resolve_stacked_on`'s three lines.**
The file is in `touches` to finish the seam, not to be refactored. `SA-0026`
and `SA-0027` have both merged, so nothing is racing for it — which is exactly
why a wider edit here would be unforced.

**Changing any message**, for the reason `SA-0030` gives.

**The scheduler and `reconcile`.** Neither has a `watch` today.

**Any renderer.** Part 3.

## Notes for the agent
**Delete `_describe`; do not leave it wrapping the new one.** A one-line
delegation is how two renderers survive a refactor meant to end them.

**`cli.py` is in `touches`, and the design document says it never would be.**
That claim was true when the design was written and false one commit later.
Where the two disagree, the code is the authority: `grep -rn watch
saffron/cli.py` settles it, and this spec was cut after that grep was run.

**`implement.py`'s raw-line branch is a security boundary, not a formatting
case.** A line that is not JSON came from a process sharing the runner's
stdout inside an untrusted cell. It is shown, truncated, and never read as an
event. Preserve that exactly.

**`package.py` runs after the money is spent.** Its events are what an
unattended morning reads about a task that got all the way to PACKAGE and
still produced nothing mergeable. Do not economise on them.

Commit after each coherent step. Uncommitted work dies with the cell.
```

- [ ] **L2–L8.**

---

## Task 4: `SA-0032` — `runs.preflight` is a column nothing writes

**Interfaces:** produces a written `runs.preflight`. Consumed by `SA-0036`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0032
title: runs.preflight is written on none of twenty-three runs
type: bug
priority: 1
depends_on:
  - SA-0026
envelope:
  - saffron/ledger.py
  - saffron/cell/session.py
  - tests/**
touches:
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/events.py
budget_usd: 8
max_attempts: 3
max_turns: 70
risk: standard
---

## Context
§4.1's schema gives `runs` a `preflight` column and §6's batch header lists
per-repo preflight status as one of its six fields. Measured **2026-09-01**
against `~/.saffron/ledger.db`: **0 of 29 runs** have it set — it was 0 of 23 a
day earlier, so the gap widens with every cell and closes with none.

Preflight runs on every cell — it starts the proxy, asserts the route out
(§5.1.1), builds the image if the Dockerfile moved, and brings the cell up —
and its outcome is discarded.

§6's own rule is the argument: *a header field with no source is not a smaller
header — it is a field that renders a confident em-dash.*

## Problem
- **The column exists and nothing assigns it.** This is not a missing schema;
  it is a write that was never wired.
- **A failed preflight is the most expensive kind of nothing.** `PREFLIGHT_FAILED`
  exits `2` and is charged to nobody, and the record of *why* survives only in
  the terminal.
- **A batch header cannot report per-repo preflight** while its source is NULL
  on every row.

## Acceptance criteria
- [ ] `runs.preflight` is non-NULL for every run a driven cell creates
- [ ] A session that **fails** preflight records a value saying so, and a test
      drives that path — the failing case is the one the header exists for
- [ ] The recorded value distinguishes at least "passed" from "failed"; if it
      carries a reason, the reason is bounded in length and a test asserts a
      long one does not corrupt the row
- [ ] The write happens where the outcome is known, not re-derived later from
      a task state
- [ ] Existing rows stay NULL and are not backfilled — a value invented for a
      run nobody observed is the "column named for a measurement it cannot
      make" failure §4.1 warns about
- [ ] A test opens a ledger created before this change and asserts it reads
- [ ] Every new test runs with no network and no cell, except any that must
      drive a real session, which carries the `cell` marker

## Out of scope
**The other five header fields.** `SA-0033` does the diff stat, `SA-0034` the
verdict, and batch wall clock has no source until §4.2.1's `batches` table.

**Rendering it.** `saffron/report/**` is `forbidden`. `SA-0036`.

**Changing what preflight checks.** `preflight.py` is outside the envelope.
This records an outcome; it does not alter one.

## Notes for the agent
**This is a bug spec with an `envelope` and no `touches` for a reason.** The
write belongs where preflight's outcome is known, and whether that is one call
site in `session.py` or also a `Ledger` method is what DIAGNOSE answers. The
scope proposal is ratified before any of it is written (§5.2).

**Do not fold this into the run's `status`.** `runs.status` says how the run
ended; `preflight` says whether the machine was fit to start. A run can pass
preflight and still abort.

**A sibling defect lives in the same function, and it is not yours.**
`ontology/RATIONALE.md`'s Q3 — gates that never fired — is blocked on exactly
one thing: *"the declared set, which preflight parses and drops."* That is the
same shape as this spec's defect, in the same place: preflight computes
something and discards it. It is a **different value** (the declared gate set,
not the preflight outcome) and it is outside this spec's problem statement.
Note it in the pull request body if DIAGNOSE lands next to it, and do not
widen the envelope to take it — an unasked-for fix riding inside a bug fix is
what `## Out of scope` exists to stop.

**`runs.preflight` is per-run, and a run is one repo's slice of a batch.** A
batch is not a run (§4.1) — resist recording this at batch level, which has no
table yet.

Commit after each coherent step. Uncommitted work dies with the cell.
```

- [ ] **L2–L8, including L5a.** This is a bug spec: the first cell exits `1`
      at `SCOPE_REVIEW` having written `scope_proposal.json`, which is the
      door §5.2 designed and not a failure. Ratify by hand and re-run L5 — see
      "The ratification detour". **Two cells, and `budget_usd: 8` is per
      cell.**

---

## Task 5: `SA-0033` — the diff stat is computed and discarded

**Interfaces:** produces `tasks.added`, `tasks.removed` (nullable INTEGER).
Consumed by `SA-0035`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0033
title: a task's diff stat survives only in a store that only PACKAGE writes
type: feature
priority: 1
depends_on:
  - SA-0032
touches:
  - saffron/ledger.py
  - saffron/cell/session.py
  - saffron/phases/package.py
  - tests/test_ledger.py
  - tests/test_session.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/events.py
budget_usd: 12
max_attempts: 4
max_turns: 100
risk: elevated
---

## Context
The morning queue renders a diff stat — `+579/−13` on `SA-0019`'s real row —
and it is in no ledger column. It exists only in
`~/.saffron/batches/v0/queue.json`, which `_finish` in `phases/package.py`
writes and only a task that reaches PACKAGE ever gets to.

A task that ends `EXHAUSTED` still produces a patch: teardown exports
`patch.diff` for **16 of 17** task directories (measured 2026-09-01; 12 of 13 a
day earlier), including `SA-0009`, the $31.60 most expensive task in the
ledger. Its `patch.json` records `base_sha`, `tree_base` and the changed file
list — and no line counts.

## Problem
- **The size of what a failed task built is unrecorded.** "It burned $31.60 and
  wrote how much?" has no answer in SQL.
- **PACKAGE is the only writer**, so the record is conditional on success.
- **`SA-0022` split the two bases and this is where the split bites.**
  `base_sha` pins the run's gates and policy; `tree_base` is what the worktree
  is built on and what `worktree.export_patch` is called with. They are equal
  for every unstacked task, which is every task today.

## Acceptance criteria
- [ ] `tasks` gains `added` and `removed` as nullable INTEGER columns, via the
      additive-migration shape `_add_gate_result_reference` establishes
- [ ] A test opens a database created before the migration and asserts it opens
      and reads
- [ ] Teardown writes the stat, so a task that never reaches PACKAGE records
      it: a test drives a session to `EXHAUSTED` and asserts both columns are
      populated
- [ ] **The stat is computed against `tree_base`, never `base_sha`.** A test
      builds a `CellSpec` with `stacked_on` set so the two differ and asserts
      the recorded stat matches the diff against `tree_base`. A test that does
      not set `stacked_on` cannot distinguish them and does not discharge this
      criterion
- [ ] PACKAGE does not write a second, conflicting stat
- [ ] A task with an empty diff records `0`/`0`, not NULL — the two mean
      different things and a page will show them differently
- [ ] Existing rows stay NULL and are not backfilled
- [ ] Every new test runs with no network and no cell, except those that must
      drive a real session, which carry the `cell` marker

## Out of scope
**Rendering it.** `saffron/report/**` is `forbidden`. `SA-0035`.

**Removing `queue.json`'s copy.** `_finish` keeps writing its store until
`SA-0036` deletes the whole path. Two writers briefly is deliberate; a
half-removed store is worse than a duplicated number.

**A per-file stat.** `patch.json` already lists changed files. Two integers is
what the page renders.

## Notes for the agent
**The `tree_base` trap is the whole risk in this spec.** A stat computed from
`base_sha` passes the entire suite today, because the two are equal on every
path an operator can reach, and then gives a stacked child its parent's diff
the first time stacking runs — reintroducing the defect `SA-0022` exists to
have fixed, one layer along. A test that does not set `stacked_on` proves
nothing here.

**An additive migration, not a rebuild.** `docs/BACKLOG.md` records why
`_add_gate_result_reference` needed SQLite's 12-step rebuild and why a
`PRAGMA foreign_key_check` after it is theatre. Two nullable columns need
`ALTER TABLE ... ADD COLUMN` and nothing more.

**A real ledger with 29 task rows exists at `~/.saffron/ledger.db`.** There is
no route to it from a cell and you must not try. Write the migration so that
it would open.

Commit after each coherent step. Uncommitted work dies with the cell.
```

- [ ] **L2–L8.**

---

## Task 6: `SA-0034` — the critic's verdict is never recorded

A **bug**, with an `envelope`. Why the column is NULL is not known.

**Interfaces:** produces a written `findings.verdict`. Consumed by `SA-0035`
for §6's level 3.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0034
title: findings.verdict is NULL on every finding, so a sustained blocker cannot be counted
type: bug
priority: 1
depends_on:
  - SA-0033
envelope:
  - saffron/phases/rebut.py
  - saffron/cell/session.py
  - saffron/ledger.py
  - saffron/agents/**
  - tests/**
touches:
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/events.py
budget_usd: 14
max_attempts: 4
max_turns: 110
risk: elevated
---

## Context
§6's sort level 3 ranks **sustained blockers** — a blocker the critic verdicted
`confirmed` and the implementer answered with an argument rather than a fix.
Both halves are load-bearing, and the first is `findings.verdict`.

Measured **2026-09-01** against `~/.saffron/ledger.db`, and the picture is
sharper than it was a day earlier, when `verdict` was NULL on 19 of 19.

`verdict` is now non-NULL on **1 of 29** findings — and the denominator that
matters is neither number. Only **five findings belong to a task that ran REBUT
at all** (5 `REBUTTING` attempt rows in 91), and REBUT judges blockers, so the
population where a verdict is even expected is **two rows**:

| finding | spec | task state | `verdict` | `rebuttal` |
|---|---|---|---|---|
| 14 | `SA-0020` | `EXHAUSTED` | NULL | present |
| 29 | `SA-0027` | `READY_FOR_REVIEW` | `withdrawn` | present |

**The write path works.** Finding 29 is a `contract`-lens blocker the critic
withdrew, and both fields landed from the same `record_rebuttal` call. So the
question is not "does anything write `verdict`" — it is "why did finding 14's
arrive empty when finding 29's did not", and there is now a **contrast case**
to diff against. A working run beside a broken one, one call apart, is a far
better instrument than the single lead this spec was cut from.

The other 24 findings carry NULL verdicts because REBUT never ran on their
tasks. That is correct, not the defect, and must not be counted as it.

## Problem
- **The critic's judgement is persisted once in two chances.** `record_rebuttal`
  takes `verdict` and writes it. On finding 29 the value arrived; on finding 14
  it was `None`.
- **Level 3 has effectively never rendered.** One stored verdict, on a
  `withdrawn` blocker — which is by definition not a sustained one — and §6
  measured that the most expensive task in the ledger, `SA-0005` at $10.07,
  renders `0 concerns` on the bottom line of ten for exactly this reason.
- **The rebuttal half works in both cases**, which is what narrows the fault:
  the same call, the same row shape, one field set and one not, on one of the
  two.

## Acceptance criteria
- [ ] The cause is established **before** any fix, by reading
      `rebut.first_answers` against `result.verdicts` on **both** recorded
      REBUTs — finding 14 (`SA-0020`, empty) against finding 29 (`SA-0027`,
      written) — and stated in the pull request body. **The contrast is the
      instrument:** what differs between the two runs is the answer. Name which
      of the three it was — never produced, produced under keys that do not
      match, or produced and dropped
- [ ] **If the difference is that the critic produced no verdict for finding
      14, then nothing in `saffron/` is broken and the correct outcome is to
      say so and stop.** That is a finding for the pull request body and a
      candidate spec of its own, not a fix to write. A spec with no route to
      "this is working" will invent something to repair
- [ ] The 24 findings on tasks that never ran REBUT are **not** treated as
      instances of this defect. A NULL verdict on a finding no critic judged is
      correct, and a change that writes one is worse than the bug
- [ ] Otherwise, a regression test exists that fails on the current `main`
- [ ] After a REBUT producing verdicts, `findings.verdict` is non-NULL for
      every judged blocker
- [ ] A test drives the recording path with both a `confirmed` and a
      `withdrawn` verdict and asserts both round-trip
- [ ] A blocker the critic judged and the implementer did not answer, and one
      the implementer answered and the critic did not judge, are both
      representable — the two fields are independent and a fix that couples
      them is wrong
- [ ] `findings.adjudication` is untouched and stays NULL: it is the operator's
      judgement, and nothing in this spec is the operator
- [ ] `findings.anchored` keeps its meaning — a dropped finding is kept, not
      deleted, because the drop rate is the signal that a lens is badly
      prompted
- [ ] Every new test runs with no network and no cell

## Out of scope
**Counting sustained blockers, or rendering them.** `saffron/report/**` is
`forbidden`; `sustained_blockers` and `unkept_fixes` already exist and are
called by PACKAGE. This spec supplies their missing input.

**Changing what the critic judges, or the REBUT prompt.** If the verdicts are
never produced, that is a finding for the pull request body and its own spec —
a prompt change is not a bug fix and must not ride along inside one.

**Backfilling the 19 existing findings.** A verdict invented for a REBUT
nobody observed is a fabricated judgement.

## Notes for the agent
**Measure before fixing; the acceptance criteria are ordered that way on
purpose.** The population is two rows and one of them is *correct* — which is
better evidence than two failures would have been. A fix written against a
guess is the mistake this repo's measured-fact convention exists to prevent.

**These figures moved in a single day** — 0 of 19 verdicts became 1 of 29, and
the second data point is what turned a lead into a contrast. Re-run the queries
before the DIAGNOSE turn. If a third REBUT has happened since, it is either a
second working case or a second broken one, and either changes the
diagnosis.

**Both blocker-bearing tasks are `EXHAUSTED`,** so they never reached PACKAGE
and `sustained_blockers` was never called on them either. That is a second,
independent reason level 3 has never rendered, and it is `SA-0035`'s to fix —
do not chase it here.

**`findings` carries three judgements and they must not collapse.** `verdict`
is the critic's confirm-or-withdraw at REBUT; `adjudication` is the operator's;
`rebuttal` is the implementer's argument. Three words, three actors (§6).

**This is a bug spec: DIAGNOSE proposes `touches` inside the envelope and the
operator ratifies it.** Do not widen the envelope; if the cause lies outside
it, say so and stop — that is a `SCOPE_REVIEW`, not a failure.

Commit after each coherent step. Uncommitted work dies with the cell.
```

- [ ] **L2–L8, including L5a.** As Task 4: `SCOPE_REVIEW` is the ratification
      door, ratification is by hand, and this is **two cells with
      `budget_usd: 14` per cell.** The proposal is worth reading closely here
      — this spec's first acceptance criterion is a measurement, so the
      diagnosis it proposes a scope from is itself the deliverable.

---

## Task 7: `SA-0035` — the queue's rows, from the ledger

Query and aggregation only. Nothing renders differently when it lands.

**Interfaces:** produces `saffron.report.render.queue_rows(ledger) -> list[QueueLine]`.
Consumed by `SA-0036`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0035
title: nothing can build a queue row from the ledger, so the page reads a store only success writes
type: feature
priority: 1
depends_on:
  - SA-0034
  - SA-0033
touches:
  - saffron/report/render.py
  - tests/test_report.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/report/index.py
  - saffron/events.py
budget_usd: 14
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
`append_queue_line` has exactly two callers — `_finish` in `phases/package.py`
and `replay` in `replay.py` — so a task that never reaches PACKAGE never
reaches the page. Measured **2026-09-01**: the ledger holds **29 task rows
across 17 specs in 7 states**; `queue.json` holds **14 rows, all of them
`READY_FOR_REVIEW`**. Lifetime spend is **$186.52**, of which `EXHAUSTED`
alone is $58.15 and appears on no page.

A day earlier the same queries said 23 rows, 13 specs, 6 states and $127.00.
**Re-take them at L1; the ratio is the finding, not the figures.**

`SA-0032`, `SA-0033` and `SA-0034` closed the three gaps that made the ledger
unable to answer for a row. This spec builds the query. It renders nothing.

## Problem
- **No function turns ledger rows into `QueueLine`s.** `Ledger.queue_lines`
  exists, has no production caller, and returns the printer's columns rather
  than the page's.
- **Row granularity is undecided and both obvious answers are wrong.** One row
  per task puts `SA-0013`'s nine `$0.00` `ORPHANED`/`NOT_IMPLEMENTED` dev-era
  rows — ten task rows totalling $1.62 — at rank 2, atop a page read in ten
  seconds. One row per spec at the newest state loses `SA-0019`'s `EXHAUSTED`
  run at $12.12 — the defect this whole design exists to fix.
- **`attempts` means two things.** The page's `attempts` is gate attempts; the
  table counts phase sessions. `SA-0013` carries 13 attempt rows across
  `IMPLEMENTING` and `REVIEWING` for a page that means 1; `SA-0019` carries 9
  across three phases. A naive count renders a number an order of magnitude
  too large.

## Acceptance criteria
- [ ] `queue_rows(ledger)` returns `QueueLine`s built from SQL, reading no
      `queue.json`
- [ ] **One row per `(repo, spec_id)`**, carrying the newest task's state, the
      **sum** of `spent_usd_est` across every task for that spec, and a task
      count when it exceeds one. A test builds a fixture ledger with two tasks
      for one spec at different states and asserts one row, the later state,
      and the summed cost
- [ ] `attempts` counts `REPAIRING` sessions, not rows in `attempts`. A test
      builds a task with four attempt rows across `IMPLEMENTING`, `REVIEWING`
      and `REPAIRING` and asserts the rendered count is not 4
- [ ] The count is **labelled with its phase**, not rendered as a bare `att`.
      `ontology/saffron.ttl`'s `withinPhase` states the rule — *"'Attempt 3'
      without a phase is ambiguous — name both (`CONTEXT.md` §2)"* — and this
      page is where the ambiguity is visible, since the number it shows and
      the number in the `attempts` table differ by design
- [ ] A row carries whether its state is a `TerminalState` or only an
      `EndState`, the distinction `ontology/saffron.ttl` draws and
      `tasks.state` conflates into one TEXT column. `MERGED` is history;
      `ORPHANED` is an unanswered question, and a page that renders them as
      the same kind of string reproduces the conflation the ontology named
      first. The design's `ORPHANED` section carries the argument
- [ ] `concerns` counts findings of severity `concern` only — `note` is
      excluded by construction (`CONTEXT.md` §5)
- [ ] `sustained` and `unkept` are computed from `findings.verdict` and the
      implementer's action, and a test builds a fixture with a `confirmed`
      blocker answered by an argument and asserts it counts as `sustained`
- [ ] A task that never reached PACKAGE produces a row whose caption is derived
      from its state and gate results, with no `note` read from any store
- [ ] `added`/`removed` come from the columns `SA-0033` added, and a NULL
      renders as missing rather than as zero
- [ ] `sort_key` is imported unchanged from `report/index.py` and not
      reimplemented; a test asserts a fixture with an `EXHAUSTED` task and a
      `READY_FOR_REVIEW` task orders the first above the second
- [ ] Every test starts from a fixture **ledger**, never from a hand-built
      `QueueLine` — a test that constructs the value it asserts on proves
      nothing about the query
- [ ] Every new test runs with no network and no cell

## Out of scope
**Rendering, and deleting anything.** `report/index.py` is `forbidden` here.
`SA-0036` swaps the writer and deletes the store's machinery.

**Changing `sort_key`.** It has been correct and starved. Changing it in the
diff that first feeds it makes it impossible to say which change moved a row.

**The batch header.** `SA-0036`.

## Notes for the agent
**Per spec, newest state, summed cost is the shape that keeps both the money
and the brevity.** It is stated as an acceptance criterion because it is the
decision this spec turns on, and both alternatives are defensible until you
look at the real rows.

**`census` compares sets and the baseline subtraction counts.** Nothing here
does either; do not borrow a helper from one expecting the other's rule.

**`Ledger` is `forbidden`.** Query through its existing methods, or read with
SQL through the connection it exposes — do not add a method to it. If the
query genuinely needs one, that is a finding for the pull request body.

**`depends_on` lists `SA-0034` before `SA-0033`, and the order is not
cosmetic.** `cli._resolve_stacked_on` consults `depends_on[0]` and nothing
else, so slot 0 decides which branch this worktree is cut from. `SA-0034`
depends on `SA-0033`, so its branch carries both; `SA-0033`'s carries only
itself, and a cell cut from it would have no `findings.verdict` write to build
`sustained` and `unkept` against. Newest parent in slot 0, always.

Commit after each coherent step. Uncommitted work dies with the cell.
```

- [ ] **L2–L8.**

---

## Task 8: `SA-0036` — the page renders from the ledger

The one spec in this plan whose output the operator sees.

**Interfaces:** consumes `queue_rows`. Produces `write_index(ledger, out_dir) -> Path`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0036
title: the morning queue cannot show a task that failed, and reads green after a bad night
type: feature
priority: 1
depends_on:
  - SA-0035
touches:
  - saffron/report/render.py
  - saffron/report/index.py
  - saffron/phases/package.py
  - saffron/replay.py
  - tests/test_report.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/events.py
budget_usd: 16
max_attempts: 4
max_turns: 130
risk: elevated
---

## Context
`SA-0035` built `queue_rows`, which answers for every task row. Nothing calls
it. The page still renders from `queue.json`, whose 14 rows are **all**
`READY_FOR_REVIEW` while the ledger records most of those specs as `MERGED` —
`reconcile` updates the ledger and nothing updates the store.

Three specs appear on no page at all: `SA-0009` (`EXHAUSTED`, **$31.60**),
`SA-0020` (`EXHAUSTED`, $14.43), `SA-0021` (`PLAN_REJECTED`, $0.82) — exactly
what §6's sort levels 1 and 2 exist for. Measured 2026-09-01: 29 task rows
across 17 specs in 7 states, against `queue.json`'s 14 in one. Re-take both at
L1.

## Problem
- **The page reads green when the night was not.** Failures absent, successes
  stale: it reports a good night after a bad one. That is a control reporting
  green while disconnected from what it measures — Appendix I's finding,
  relocated into the reporting layer.
- **§6's sort has never been reached.** Every real row ranks 5. `sort_key` is
  not wrong; it has never been given a row it could rank.
- **The header under-reports lifetime spend by roughly half**, and the missing
  half is almost entirely `EXHAUSTED` — the state meaning a task could not pass
  its own gates. It was 47% of $127.00 when this was cut; the percentage moves
  with every run and the direction does not.

## Acceptance criteria
- [ ] `write_index` renders from `queue_rows` and `queue.json` is read by
      nothing
- [ ] `append_queue_line`, its `flock`, `_existing_queue_rows`, the per-row
      validator and `_migrate_v0_store` are **deleted**: a full re-render has
      no read-modify-write to serialise
- [ ] `_atomic_write` survives and is what writes `index.html`
- [ ] `_finish` in `phases/package.py` and `replay` call the new path, so
      neither keeps a second writer alive
- [ ] The header renders five fields — terminal-state counts, total spend,
      per-repo preflight, base-suite status, trailing accept rate — and
      **omits** batch wall clock rather than dashing it, with a comment naming
      the `batches` table as its missing source
- [ ] Total spend equals `select sum(spent_usd_est) from tasks`, asserted
      against a fixture ledger
- [ ] Trailing accept rate is computed over prior completed tasks, never the
      current batch: a rate claiming to score the night it printed would report
      on work that has not happened
- [ ] Every value interpolated into HTML is escaped, including text that
      originated in a cell — a test asserts a state or caption containing
      `<script>` renders inert
- [ ] `docs/BACKLOG.md` records that §6's "the queue reads `queue.json`"
      paragraph is now wrong and the correction is by hand
- [ ] Every new test runs with no network and no cell

## Out of scope
**Per-task pages and the live tail.** `SA-0037` and `SA-0038`.

**A diff viewer.** §6's argument stands: the pull request is the diff viewer
and it is better than anything built here.

**A server.** No HTTP surface, no long-lived process.

**Deleting `queue.json` from disk.** The file stops being read and stops being
written. Removing an operator's existing batch tree is not this spec's call.

**The evidence record.** `docs/evidence/` is not in `touches`, and the record
the design's Verification section asks for is **Task 11's, by hand**. It
requires pointing the shipped renderer at `~/.saffron/ledger.db`, and there is
no route from a cell to the host's ledger — `SA-0033`'s own notes say so in as
many words. An agent asked for it could only write numbers it guessed, which is
the one thing `## Notes for the agent` exists to forbid.

## Notes for the agent
**This is the first spec in the sequence whose output a human looks at**, and
it is the first whose correctness a test cannot fully establish. The operator
renders the page against the real ledger at L6 and writes the evidence record
at Task 11; your job is to make that render possible and correct, not to
describe what it would have shown.

**Deleting the lock is correct and will feel wrong.** `flock` guards a
read-modify-write of `queue.json`. A full re-render from SQL has no read half.
Keeping it "to be safe" preserves a mechanism whose reason has been removed.

**`sort_key` stays exactly as it is.** See `SA-0035`.

**The trailing accept rate is trailing.** This batch's rate is unknowable when
the batch ends, because merging is what happens next.

Commit after each coherent step. Uncommitted work dies with the cell.
```

- [ ] **L2: Verify intake.** No acceptance criterion here names a path outside
      `touches` — the evidence record that used to be one has moved to Task 11,
      because a cell cannot reach `~/.saffron/ledger.db` to produce it. Gate 0
      matches acceptance criteria against `touches` patterns, and a criterion
      naming a path no pattern matches is a refusal; a criterion naming a path
      the *cell* cannot reach is worse, because gate 0 admits it.
- [ ] **L3–L5.**
- [ ] **L6: Render the page and look at it before marking it ready.** From the
      branch, against the real ledger — the operator can do this and the cell
      could not:

```bash
sqlite3 ~/.saffron/ledger.db \
  "select count(*), count(distinct spec_id), round(sum(spent_usd_est),2) from tasks"
```

Expected: one row per spec (17 at the last count, not 29), `SA-0009` near the
top at `EXHAUSTED` and $31.60, and a header total matching the query. This is
the one review in the plan that is not only a diff read, and the one place a
rendered page can be wrong in a way no test and no reviewer will catch from a
diff. **Keep the rendered page — Task 11's evidence record is written from
it.**

- [ ] **L7: Independent code review.** Give this reviewer the rendered
      `index.html` as well as the diff — it is the artifact, and a reviewer
      reading only `render.py` is reading the recipe rather than the dish.
- [ ] **L8.**

---

## Task 9: `SA-0037` — a task page from the ledger

**Interfaces:** produces `write_task_page(ledger, task_id, out_dir) -> Path`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0037
title: what a failed task did exists only in sqlite and a directory walk
type: feature
priority: 2
depends_on:
  - SA-0036
touches:
  - saffron/report/render.py
  - tests/test_report.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/events.py
budget_usd: 14
max_attempts: 4
max_turns: 120
risk: standard
---

## Context
`SA-0036` made a failed task visible as a row. A row says `EXHAUSTED · 4 att ·
$31.60` and stops. Answering "what did $31.60 buy" still means opening
`sqlite3`, joining `attempts`, `gate_results` and `failures`, and walking
`~/.saffron/batches/v0/SA-0009/`.

§6's *index, not a viewer* holds and is not reopened: the diff stays on the
pull request. What has no home is what GitHub cannot show — the gate table
across attempts, the findings with their verdicts, and per-attempt cost.

## Problem
- **The most expensive task in the ledger is the least legible.** `SA-0009` at
  $31.60 has a full gate history reachable only through SQL.
- **A task with no pull request has nowhere to point.** The index links to a
  pull request, and the rows this design made visible are precisely the ones
  without one.
- **A row cannot carry a gate history.** Four attempts against sixteen gates is
  a table, not a cell.

## Acceptance criteria
- [ ] `write_task_page` writes `out_dir/<spec_id>/index.html` — the existing
      `task_dir` — so the page lands beside `patch.diff`, `plan.json` and
      `baseline.json`
- [ ] Every index row links to its task page, including rows with no pull
      request; a row with one links to both, distinctly labelled
- [ ] The gate table shows every gate result across attempts with its status,
      and `error` is displayed distinctly from `fail`
- [ ] Failures render with `(gate, file, code)`, the identity three mechanisms
      key on, and `line` is displayed but not presented as part of it
- [ ] Findings render with `severity`, `anchored`, `verdict` and `rebuttal`
      side by side, and a `blocker` confirmed against an argument is visually
      distinct from one confirmed against a fix — §6's two level-3 counts are
      different failures and wording them the same hides the one that matters
- [ ] Per-attempt cost renders, and a `$0.00` from a session whose `subtype` is
      `error_during_execution` is not presented as a measured zero
- [ ] Cost is labelled as the estimate it is: §4.1 is explicit that every
      figure the runtime reports is a client-side estimate
- [ ] Every value interpolated into HTML is escaped — a test asserts a finding
      claim containing `<script>` renders inert
- [ ] A render that raises never propagates: a test asserts a session completes
      with an unwritable output directory
- [ ] Every new test runs with no network and no cell

## Out of scope
**The timeline and liveness.** `SA-0038` reads `events.jsonl` and adds the
refresh. This page is SQL-only and must be good without a log, because every
task that ran before `SA-0029` has none.

**A diff viewer**, a server, and any transcript rendering.

**Changing the index.** `SA-0036` settled it; this adds links.

## Notes for the agent
**A task with no events is the common case here, not the edge case.** This
spec must not read `events.jsonl` at all — that is what makes `SA-0038`'s
addition safe.

**`terminal_reason` exists because a crashed session may report every cost
field as zero.** A `$0.00` attempt with `subtype = error_during_execution` is
not a free attempt and must not read as one.

**`cost_usd_est`'s suffix is not decoration.** A heading that says "spent"
over an estimate is how an estimate becomes a fact (§4.1).

Commit after each coherent step. Uncommitted work dies with the cell.
```

- [ ] **L2–L8.**

---

## Task 10: `SA-0038` — the timeline, and the live tail

The event log's first reader.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0038
title: the event log has no reader, and a running task looks identical to a finished one
type: feature
priority: 2
depends_on:
  - SA-0037
  - SA-0031
touches:
  - saffron/report/render.py
  - tests/test_report.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/events.py
budget_usd: 12
max_attempts: 4
max_turns: 100
risk: standard
---

## Context
`SA-0029` through `SA-0031` made every host-side progress line an event and
appended it to `task_dir/events.jsonl`. Nothing has ever read one — that was
deliberate, so the seam could be proven by its unchanged terminal output rather
than by a consumer.

`SA-0037`'s task page renders from SQL alone. It shows what a task ended with
and not the order it got there, and a task still running looks exactly like one
that finished.

## Problem
- **The sequence is recorded and invisible.** `ORPHANED` is the state that
  argues hardest for it: three task rows at `$0.00` with one attempt or none,
  where SQL can say the cell died and only the log can say how far it got.
- **A running task is indistinguishable from a finished one.** The page is
  static and says nothing about which it is looking at.
- **This is the last consumer the design named**, and until it exists
  `SA-0029`'s record is a cost with no return.

## Acceptance criteria
- [ ] The task page renders a phase timeline from `events.jsonl` via
      `read_log` when one exists
- [ ] A task whose log is **absent** still produces a page — a test asserts it,
      because every task that ran before `SA-0029` has none
- [ ] A truncated final line is tolerated by `read_log` and not re-handled
      here; a test asserts a log ending mid-object still renders its whole
      prefix
- [ ] An unknown event kind renders as an unknown entry rather than raising
- [ ] A `<meta http-equiv="refresh">` is emitted **only** while the task is in
      a non-terminal state, with a `ponytail:` naming the ceiling — this is
      polling, chosen over a server deliberately
- [ ] The index marks a task that is currently running, distinctly from every
      terminal state
- [ ] Agent-authored text from the log is escaped — a test asserts an event
      carrying `<script>` renders inert. A cell is untrusted and the renderer
      is host-side
- [ ] The `agent: (raw)` quarantine survives into the page: a line that was
      never an event is displayed as such and never rendered as one
- [ ] A render that raises never propagates
- [ ] Every new test runs with no network and no cell

## Out of scope
**A server, a socket, or any push mechanism.** Meta-refresh is the chosen
ceiling and its cost is named where it is paid.

**Rendering the agent's transcript.** The log holds tool-use and text events;
this is a timeline, not a conversation. A transcript viewer is a different
thing and may not be worth building at all.

**Reading the log for anything but display.** No control decision consumes it,
here or ever.

**Changing the index beyond the running marker.**

## Notes for the agent
**`read_log` already tolerates a truncated final line — do not add a second
tolerance layer.** A cell killed mid-write is the normal case for exactly the
tasks this page exists for.

**This spec names two parents on two different chains, and `depends_on[0]` is
all Saffron can stack on.** `SA-0037` is slot 0 and is what this worktree is
cut from; `SA-0031` — which is what writes the `events.jsonl` this page reads —
**must already be `MERGED`** before this cell runs, so the gate is satisfied by
the default branch rather than by a branch nothing can reach. That is why part
1 merges before part 2 starts. Running it any other way gives this cell a tree
with no event emission in it and a spec asking it to render one.

**Liveness here is honest polling and the comment must say so.** The design
chose regenerated static HTML over a server; a page that implies it is live
oversells what a meta-refresh does.

**The event log is the only place in this design where untrusted text reaches
a host-side renderer.** Escape everything, and keep the raw-line quarantine
visible as a quarantine.

Commit after each coherent step. Uncommitted work dies with the cell.
```

- [ ] **L2–L8.**

---

## Task 11: The by-hand follow-ups

Three protected documents no cell can correct. Each spec above leaves a
`docs/BACKLOG.md` entry naming what drifted; this pays them off.

- [ ] **Step 1: Correct `DESIGN.md` §6.** Rewrite *"The queue reads
      `queue.json`, not the ledger, and that is currently undecided rather
      than chosen"* to state that the ledger is the source and the event log
      is the live tail. Correct its two stale gap claims — `tasks.risk` **is**
      written, a merge **is** recorded. Restate *index, not a viewer*
      explicitly, since `SA-0037` adds a per-task page and a reader could take
      that as a reversal.
- [ ] **Step 2: Add an event-schema subsection under §4.** Add a subsection;
      **never renumber** — section numbers are an API and specs cite them.
- [ ] **Step 3: Correct §5.3's supervisor paragraph**, which describes a
      `watch` callable that no longer exists.
- [ ] **Step 4: Add a backlog item for `ORPHANED`'s classification.**
      `ontology/saffron.ttl` files it as an `EndState` that does not reach the
      operator, on the rationale *"downstream of a judgement they already
      made"* — which fits the four post-decision states and not a crash.
      `_STATE_RANK` ranks it 2, among the states that need you. Record the
      disagreement, that the page took `index.py`'s side, and that moving the
      term is a by-hand edit: `ontology/shapes/**` is in `gate_config`, so
      `integrity` refuses an edit no spec's `touches` names, and a design
      document should not quietly move a term in a vocabulary.
- [ ] **Step 5: Write the evidence record.** `SA-0036`'s L6 rendered the
      shipped page against `~/.saffron/ledger.db`; this writes it up as
      `docs/evidence/2026-09-01-queue-from-the-ledger.md`, in the shape of
      `docs/evidence/2026-08-25-morning-queue-from-real-rows.md` — a script
      under `docs/evidence/scripts/` pointing the **shipped** `write_index` and
      `sort_key` at the real ledger, changing only the data source, plus row
      count, state spread and total spend.

      **This is by hand because it cannot be otherwise.** The precedent record
      was produced the same way — `docs/evidence/scripts/2026-08-25-queue-from-ledger.py`,
      runnable from the repo root, committed under `docs(design)` — and no cell
      can reach the host's ledger. It was an acceptance criterion of `SA-0036`
      in the first cut of this plan, which an agent could only have discharged
      by inventing the numbers.
- [ ] **Step 6: Close the backlog entries** the ten specs added, each with the
      commit that closed it — the shape items 1 and 29 use.
- [ ] **Step 7: Commit.**

```bash
git add DESIGN.md docs/BACKLOG.md docs/evidence/
git commit -m "docs(design): the queue reads the ledger, and §6 said otherwise"
```

---

## Task 12: Link, check and merge each stack

Runs **twice** — once for part 1 (`SA-0029`–`SA-0031`), once for part 2 and 3
(`SA-0032`–`SA-0038`). Part 1's run completes before `SA-0032`'s cell starts.

- [ ] **Step 1: Link the pull requests, bottom to top.**

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py stack            # dry run
uv run .claude/skills/run-saffron-spec-loop/driver.py stack --execute
```

`link` is the command, not `submit`: PACKAGE has already opened every pull
request, `link` takes existing numbers and keeps no local tracking state, and
`submit` force-pushes from a local stack that does not exist here. If a chain
is already stacked by Saffron — every spec in it declaring a parent in slot 0 —
`link` finds each base already correct and changes nothing, which is the
outcome to want.

- [ ] **Step 2: Check the merge, not the pull request page.** A stacked page
      renders a clean diff because GitHub computes it from the merge base. That
      is not the check.

```bash
git merge-tree --write-tree origin/saffron/SA-0030 origin/saffron/SA-0031
```

Run it for each adjacent pair. `docs/BACKLOG.md` is in eight of the ten specs'
`touches` and is append-only, so it is where a conflict will be — including the
item *number*, not only the text: `SA-0027` and `SA-0028` both wrote `## 34.`
A chain cut parent-from-parent should be clean; **any conflict here means a
spec ran unstacked**, and the fix is to find which cell printed no
`stacked on …` line, not to resolve the conflict and move on. If you do have to
renumber, grep the *code* for comments citing the old number — four cited
`item 34` last time.

- [ ] **Step 3: Merge the stack.** One command, all-or-nothing, bottom-up:

```bash
gh stack merge <top-pr> --yes --squash
```

**Never `gh pr merge`** — it cannot merge a stack, and used per pull request it
would land them out of order against bases that no longer exist. If the set
cannot merge, none of it does; read the failure and fix the layer it names.

- [ ] **Step 4: Sync and prune.**

```bash
gh stack sync --prune
git checkout main && git pull
```

- [ ] **Step 5: Retire the stack's specs** — the L8 deferred from each task.

```bash
git mv .saffron/specs/SA-00NN-*.md .saffron/specs/done/
git commit -m "chore(specs): retire SA-00NN…SA-00NN as shipped"
```

- [ ] **Step 6 (part 1's run only): confirm the default branch carries the
      event seam** before `SA-0032`'s cell starts, since `SA-0038` depends on
      it being `MERGED` rather than merely open:

```bash
git log --oneline origin/main | head -5
grep -rn 'watch' --include='*.py' saffron/ | grep -v 'watches it'
```

Expected: no `watch` parameter anywhere in `saffron/`.

---

## Self-review

**Spec coverage.** Design part 1 → Tasks 1–3. Part 2's three gaps → Tasks 4–6,
one spec each, carrying the `tree_base` trap (Task 5) and the measure-first
discipline (Task 6). Part 3 → Tasks 7–10, split query / render / page /
timeline. The design's "What `DESIGN.md` must change" → Task 11, which also
carries the evidence record its Verification section asks for, because that
record cannot be produced from inside a cell. Its sequencing section → Task 0
and the `depends_on` chain.

**Ontology alignment**, checked against `ontology/saffron.ttl` and
`RATIONALE.md`: the `EndState` / `TerminalState` split reaches the page as a
`SA-0035` criterion; `withinPhase`'s "name both" rule reaches it as another;
`costUsdEst`'s "an estimate, and the suffix is not decoration" is a `SA-0037`
criterion; Q3's dropped declared-gate set is noted as adjacent to `SA-0032`
and explicitly not its job. Nothing here edits the ontology, and nothing
should: `ontology/shapes/**` is in `gate_config`, so `integrity` refuses an
edit no spec's `touches` names, and the `shacl` gate is blocking.

**Dependency chain**, and every link is either a real consumption or a
same-file serialisation, since nothing can run concurrently anyway:

```
SA-0026 ─→ SA-0032 ─→ SA-0033 ─→ SA-0034 ─→ SA-0035 ─→ SA-0036 ─→ SA-0037 ─┐
 (shipped)                                                                 ├─→ SA-0038
SA-0028 ─→ SA-0029 ─→ SA-0030 ─→ SA-0031 ──────────────────────────────────┘
 (shipped)
```

**The two branches join at `SA-0038`, not at `SA-0035`.** An earlier drawing of
this diagram merged them one box early; the frontmatter is the authority, and
it says `SA-0035` depends on `SA-0033` and `SA-0034` while `SA-0038` depends on
`SA-0037` and `SA-0031`. Part 1 and part 2 never meet until the timeline needs
both a task page and an event log.

`SA-0026` (#84), `SA-0027` (#88) and `SA-0028` (#87) have all merged, so every
link in this chain is now satisfiable and Task 1 can start.

**Type consistency.** `Event`, `EventLog`, `read_log`, `describe` (Task 1) are
consumed under those names in Tasks 2, 3 and 10. `queue_rows` (Task 7) →
`write_index` (Task 8) → `write_task_page` (Task 9). `tasks.added` /
`tasks.removed` named identically in Tasks 5 and 7. `sort_key` is imported,
never reimplemented.

**Two risks this plan does not remove.**

*Cost, corrected upward twice.* **Twelve cells, not ten**: `SA-0032` and
`SA-0034` are bug specs whose first cell stops at `SCOPE_REVIEW`, so each is
run twice and its DIAGNOSE turns are paid twice. Summing the declared budgets
with those two counted twice gives **$152**, and `SA-0031` is $4 of that
increase — it took `saffron/cli.py` and seven test files after the first cut of
this plan left them unreachable. Call it a **$150–165** ceiling before any
repair loop, against a lifetime spend that has itself reached $186.52.
Splitting raised the total and lowered the per-spec risk; the ratification
detour raises it again and is not optional. If a spec exhausts, re-cut it
rather than raising its budget — a wide mechanical diff that cannot pass its
own gates is usually a spec that should have been two.

*The ratification detour is by hand and cannot be automated here.* Item 31:
the writeback is designed, documented and half-built, and `SA-0024` plus this
repo's `protected` list mean a host-authored commit to `.saffron/specs/…`
would fail `scope` as a protected path. So L5a is manual, and a plan that
treated `SCOPE_REVIEW` as a failure would re-run those specs for no reason
while a plan that treated it as automatic would wait forever.

*This plan was written for a workflow that merges each pull request, and the
stack workflow breaks four of its steps.* `.claude/skills/run-saffron-spec-loop`
post-dates it. The corrections are in "Stacking: two mechanisms" and Task 12,
and the load-bearing ones are that `_resolve_stacked_on` reads `depends_on[0]`
and nothing else — which had `SA-0035` cutting from the wrong parent and leaves
`SA-0038`'s second parent unreachable unless part 1 merges first — and that
`saffron queue` stops answering once any pull request is open, so L2's refusal
is no longer evidence about the spec. Neither is visible from reading the plan;
both come from reading `cli.py`.

*Every measurement in this plan decays, and faster than it reads.* Between the
design (2026-08-31) and this revision (2026-09-01) the ledger went from 23 task
rows to 29, spend from $127.00 to $186.52, a seventh `tasks.state` appeared
(`RATE_LIMITED`), `findings.verdict` went from 0 written to 1, and
`session.py` grew 173 lines. Nothing in the argument moved; every figure did.
Worse, the one fact this plan built a design constraint on — that `cli.py` does
not name `watch` — was falsified by a *review fix on another spec* landed the
same day, which no grep of queued specs would ever have caught. Task 0 Step 4
now greps the code rather than the specs for that reason. Treat every number in
a `## Context` as a claim with a date on it.

*Neither review is Saffron's own critic.* The adversarial critic runs inside
the cell at L5 under the repo's lenses; L3 and L7 are outside that loop. L7 in
particular reads the same diff the critic already judged — that overlap is
deliberate, and a disagreement between them is signal rather than waste.
