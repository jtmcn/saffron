# §6's morning queue, rendered from real rows

Taken 2026-08-25 for [#28](https://github.com/jtmcn/saffron/issues/28), which asks
what the morning queue actually renders against this repo's ledger and whether
§6's page is the right one. Reading §6 cannot answer it; the page had to be built
and looked at.

**The page was already built, which the ticket did not know.** `saffron/report/index.py`
ships `QueueLine`, `render_index`, `sort_key` and `append_queue_line` — §6's
*"~50 lines of Jinja"* is ~50 lines of f-strings, with a `ponytail:` comment
saying so. So the question is not whether §6's mock is the right page. It is
whether §6's *ranking* is the right ranking, which is a different question, and
the answer is no.

## Method

`docs/evidence/scripts/2026-08-25-queue-from-ledger.py`, runnable from the repo
root with `uv run python`. It points the **shipped** `render_index` and
`sort_key` at `~/.saffron/ledger.db`, so the page under test is the production
one and only the data source differs. It also diffs each row against
`~/.saffron/batches/v0/queue.json`, the store PACKAGE actually appends to.

Ten tasks, nine findings, thirty-one attempt rows, from the live runs `SA-0002`
through `SA-0007`. No row was constructed for this record.

## What the sort produced

| rank | repo | spec | state | att | cost | concerns | link |
|---|---|---|---|---|---|---|---|
| 2 | `saffron` | SA-0005 | `NOT_IMPLEMENTED` | 1 | $7.50 | 0 | — |
| 3 | `saffron` | SA-0006 | `READY_FOR_REVIEW` | 2 | $2.86 | 2 | PR #24 |
| 4 | `saffron` | SA-0002 | `READY_FOR_REVIEW` | 1 | $2.38 | 1 | PR #15 |
| 4 | `saffron` | SA-0007 | `READY_FOR_REVIEW` | 1 | $2.01 | 1 | PR #23 |
| 4 | `joel+v0.5-one-cell` | SA-0002 | `READY_FOR_REVIEW` | 1 | — | 0 | — |
| 4 | `joel+v0.5-one-cell` | SA-0002 | `READY_FOR_REVIEW` | 1 | — | 0 | — |
| 4 | `joel+v0.5-one-cell` | SA-0003 | `READY_FOR_REVIEW` | 1 | — | 0 | — |
| 4 | `joel+v0.5-one-cell` | SA-0004 | `READY_FOR_REVIEW` | 1 | — | 0 | — |
| 4 | `saffron` | SA-0004 | `READY_FOR_REVIEW` | 1 | — | 0 | — |
| **4** | `saffron` | **SA-0005** | `READY_FOR_REVIEW` | 1 | **$10.07** | **0** | **PR #21** |

Rank is `sort_key`'s first element, invisible on the real page. Two of §6's six
levels did any work.

## The headline: the worst outcome in the ledger sorts last, captioned clean

`SA-0005` (PR #21) is the most expensive task Saffron has produced — $10.07 over
8 phase-sessions and 173 turns. It went to REBUT with three blockers and **the
critic won**: two were adjudicated `confirmed`. It renders as `0 concerns` and
sorts tenth of ten.

Two mechanisms produce that, and both are §6's rather than the code's:

- `anchored_concerns` (`phases/review.py:241`) sums `severity == "concern"`. A
  blocker is not a concern at any verdict, so a sustained blocker contributes
  nothing to the number the page ranks on.
- §6's level 4 is *"everything else by concern count descending"*, and there is
  no level above it for a blocker the rebuttal failed to remove.

§6's stated guarantee is *"`blocker` never reaches this page unrebutted."* That
is true, and it is not the property that was needed. These were rebutted. The
guarantee protects against an unadjudicated blocker and says nothing about an
adjudicated one — and `CONTEXT.md`'s own distinction between a finding and a
concern is what makes the omission invisible in the prose.

**This is the page's whole job failing.** §6 exists so you can dismiss in ten
seconds and accept in two minutes; on this data it puts the row you must not
accept at the bottom, wearing the same caption as four scaffolding rows.

## Four more, in descending order of what they cost

**`tasks.risk` is corrupt for every task that ran before `SA-0007` landed.** Six
of these specs declare `risk: elevated` in frontmatter; the ledger records it for
one. `SA-0005` and `SA-0007` both declare `elevated` and both persist `standard`
— the scar left by `docs/BACKLOG.md` item 18's fifth instance, where `cli.py`
never passed `risk=spec.risk` into `CellSpec`. Sort level 3 therefore sorts one
task where it should sort six, and **the history cannot be corrected**: the
declared value is only right for tasks run after the fix.

> #28 predicted this level would sort nothing *because every run declared
> `elevated`*. It sorts nothing for the opposite reason. Both the ticket and
> [#34](https://github.com/jtmcn/saffron/issues/34) assert the uniform-`elevated`
> premise; the ledger contradicts it, and the specs contradict the ledger.

**One repo renders as three.** `repos.origin` is `UNIQUE` and takes a new row per
path Saffron was invoked from: the worktree
`…/.claude/worktrees/joel+v0.5-one-cell`, the checkout `/Users/joel/Code/saffron`,
and the remote `git@github.com:jtmcn/saffron.git`. §6 says *"repo is a column you
scan, not a heading you navigate"* — scan this one and you conclude two repos ran.

**The shipped ranking has already outgrown §6, with reasons written down.**
`_STATE_RANK` adds `PREFLIGHT_FAILED`, `GATE_ERROR`, `NOT_IMPLEMENTED`,
`EXHAUSTED`, `ORPHANED` and `RATE_LIMITED` to level 2, each with a comment
explaining that without it a dead cell or a provider wall sorts below a green PR.
§6 lists three states at that level. **The code is the better record and the prose
is the authority**, which is the wrong way round for a document specs cite by number.

**`N att` means something the `attempts` table does not store.** Rows there are
one per phase-session (§4.1: *"`phase` is the state the task was in when the turn
started"*), so `COUNT(*)` is turns — `SA-0005` has 8, `SA-0002` has 7. The column
wants repair-loop attempts. `1 + COUNT(phase = 'REPAIRING')` reproduces PACKAGE's
number **exactly on all four packaged tasks**, so it is recoverable; but the same
word means two things one join apart.

## The batch header cannot be rendered at all

| §6 field | Source | Status |
|---|---|---|
| counts by terminal state | `tasks.state` | renders |
| total spend | `tasks.spent_usd_est` | partial — 5 of 10 rows are `0.0` |
| wall clock | `batches.started_at/ended_at` | no table (§4.2.1 decides it) |
| per-repo preflight | `runs.preflight` | column exists, never written |
| base-suite status | `gate_results.run_id` | no baseline rows recorded |
| trailing accept rate | — | nothing records whether a task merged |

## And a question #28 did not ask

**There are two stores, and the ledger is not the authoritative one.**
`queue.json` is what PACKAGE appends to and what renders today. The ledger cannot
reproduce it: `risk` disagrees on two of four packaged tasks, and the diff stat
(`+180/−22`, in §6's mock and in `QueueLine`) is stored in no column at all.
Either the ledger gains what it is missing and becomes the source, or the page
keeps reading the store and §6 should stop implying otherwise. Left as a decision
rather than settled here.

## What survived

The index-not-viewer decision, f-strings over Jinja, and sorting by state rather
than grouping by repo. All three hold, and the last one holds *harder* on this
data than §6 argued: grouping by repo would have buried `SA-0005` under four
worktree rows carrying the same repo name.
