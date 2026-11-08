---
id: SA-0343
title: "REVIEW hands every session the whole remainder, so a cell spends past its own budget"
type: bug
priority: 1
estimated_lines: 131
estimate_measured: true
depends_on: [SA-0342]
touches:
  - saffron/phases/review.py
  - saffron/cell/session.py
  - tests/test_review.py
  - tests/test_session.py
  - tests/test_events.py
  - tests/test_lens_scoring.py
  - docs/evidence/scripts/2026-09-07-lens-scoring.py
  - docs/evidence/scripts/2026-09-08-lens-corpus.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/adr/**
  - docs/appendices/**
  - docs/backlog/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/gates/**
  - saffron/task.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/end_review.py
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - tests/test_rebut.py
budget_usd: 52
max_attempts: 3
max_turns: 240
risk: elevated
acceptance:
  - claim: >-
      A REVIEW session that REVIEW's pool cannot cover does not start, and no
      later session starts. The task ends `REVIEW_INCOMPLETE`, in the ledger and
      on its `REVIEW_INCOMPLETE: $N spent` line. The last `REVIEW:` line says
      the review was cut at its budget. It names the lens, or the criterion's
      witness, of the session that did not start. Every session that did not
      start is filed with an error, in `findings.json`,
      `criterion-probes.json` or `wrong-versions.json`. The
      task's spend is its spend before REVIEW plus the cost of each session
      that ran. A lens that failed with a cost takes that cost off REVIEW's
      pool, so the next lens's cap is lower by it. The witness drives a cut at
      each of the three kinds of session: the fourth lens after a failed
      second lens, the second criterion probe, and the second wrong-version
      session.
    witness: tests/test_session.py::test_a_review_that_crosses_its_pool_starts_no_later_session
    wrong_versions:
      - A lens that failed costs the pool nothing, so the third lens is capped at $5.00 rather than $3.75 and the fourth lens starts.
      - Each of the three REVIEW calls opens its own pool from the remainder, so the criterion probes start after a lens was cut.
      - A session starts while the pool holds more than zero, so the second criterion probe starts with $1.75 left.
      - Only a lens that did not start ends the task `REVIEW_INCOMPLETE`, so a criterion probe or wrong version cut reaches `READY_FOR_REVIEW`.
      - The cut reuses the errored-lens line, so the last `REVIEW:` line never says the review was cut at its budget.
      - A criterion probe that did not start files no entry, so `criterion-probes.json` holds one entry fewer than the spec declares.
      - The pool is never decremented, so every session is capped at the opening figure and none is cut.
      - The pool takes off each session's cap rather than its reported cost, so the second lens is cut at once.
      - The pool opens at the whole `budget_usd` rather than the remainder, so each cap is $0.20 too high.
  - claim: >-
      A REVIEW that fits REVIEW's pool runs every lens, criterion probe and
      wrong-version session, and reaches `READY_FOR_REVIEW` as it does today.
      Each session, and each re-prompt turn, is capped at what the pool has
      left. The pool opens at the task's remainder when REVIEW starts, floored
      at `REVIEW_FLOOR_USD` once per name in `review.LENSES`. Each session's
      reported cost comes off the pool when it ends. That cost includes the
      re-prompt turn of a lens, a criterion probe and a wrong-version session,
      and the cost of a criterion probe or wrong-version session that failed.
      The witness drives a remainder above that floor and two below it, with
      the four declared lenses and with three. The three-lens REVIEW's last
      session starts with exactly `REVIEW_FLOOR_USD` left.
    witness: tests/test_session.py::test_a_review_that_fits_its_pool_runs_every_session_capped_at_what_is_left
    wrong_versions:
      - The pool is never decremented, so every session is capped at the whole remainder as at base.
      - The pool is floored at `REVIEW_FLOOR_USD` once, so a $3.00 remainder cuts the fourth lens.
      - The floor is a fixed $8.00, so a three-lens REVIEW opens at $8.00 rather than $6.00.
      - A session starts only while the pool holds more than the floor, so the three-lens REVIEW cuts its last session at $2.00.
      - The pool opens at the whole `budget_usd` rather than the remainder.
      - A criterion probe that failed costs the pool nothing, so the next session's cap is $1.25 too high.
      - A wrong-version session that failed costs the pool nothing.
      - A re-prompted criterion probe or wrong-version session costs the pool only its first turn.
      - A re-prompted lens costs the pool only its first turn.
  - claim: >-
      A lens whose session failed still ends its task `REVIEW_INCOMPLETE`, a
      state no stamping batch scan takes back.
    witness: tests/test_session.py::test_a_lens_that_errored_ends_its_task_in_a_state_no_batch_scan_takes_back
    preserves: true
---

## Context

Backlog item **b-d39d9a**, under `DESIGN.md` §4.3 and §5.5. Related:
b-2f4746. Every line below was read at `964ad3a7`.

**What the design now says.** Commits `fa20707d` and `964ad3a7` amended the
design by hand, and `84a8df56` amended the glossary by hand, in this pull
request.
§4.3's paragraph now opens "REVIEW draws on one pool, and REBUT departs from
the spend row" (`DESIGN.md:534`). It says REVIEW's pool is the remainder when
REVIEW starts, floored at $2 per declared lens "so the lenses share at least
$2 each". The floor does not promise that every lens starts. Each later session gets what
the pool has left, and the host takes each cost off as it ends. A session the
pool cannot cover does not start, and the task ends `REVIEW_INCOMPLETE`.
§5.5's paragraph on that state now says the same, and that "Its line then says
the review was cut at its budget" (`DESIGN.md:1253`). §5.5.1's "Ungated"
paragraph now prices each lens at $2 of REVIEW's floor (`DESIGN.md:1270`).
`CONTEXT.md` gained a **Review pool** entry that says the same
(`CONTEXT.md:90-94`). Its `REVIEW_INCOMPLETE` entry gained "A REVIEW session
its pool could not cover ends the task here too" (`CONTEXT.md:766-767`). This
spec makes those five passages true of the code.

**What REVIEW spends today.** `critic_budget` returns the remainder, floored at
`REVIEW_FLOOR_USD` of $2 (`saffron/cell/session.py:184-186`, `:90`). REVIEW
calls it once, as `probe_budget` (`saffron/cell/session.py:3171`). It hands
that figure whole to `review.run_review` (`saffron/cell/session.py:3248`), to
`review.run_criterion_probes` (`:3263`) and to `review.run_wrong_versions`
(`:3278`). `run_review` passes it to every lens in `LENSES`
(`saffron/phases/review.py:378-394`). Each criterion probe gets it as its own
cap (`saffron/phases/review.py:519-524`), and so does each wrong-version
session (`saffron/phases/review.py:732-737`). The comment above the floor says
the cap is "never decremented between them" (`saffron/cell/session.py:80-89`).
REVIEW's cost is summed into `spent` once, after every session has run
(`saffron/cell/session.py:3387-3397`). `_over_budget` holds `spent` against
the budget (`saffron/cell/session.py:2595-2610`). Its last call comes before
the notes turn, ahead of REVIEW (`saffron/cell/session.py:3026`).

**What a re-prompt spends.** `_parse_or_reprompt` resumes a session whose
output was not the schema, capped at the session's cap less the failed turn's
cost. It returns both turns' summed cost
(`saffron/phases/review.py:235-290`). A session whose turn raised
`AgentFailed` reports its partial attempt's cost
(`saffron/phases/review.py:527-538`, `:743-746`, `:327-331`).

**How REVIEW ends today.** `review_state` returns `REVIEW_INCOMPLETE` only for
a lens with an `error` (`saffron/phases/review.py:976-989`). The cell calls it
once, after every record is written, and passes its line to `_phase_start`
(`saffron/cell/session.py:3413-3414`). An errored criterion probe or wrong
version does not stop the task. Its entry carries an `error` and the REVIEW
line names its witness (`saffron/phases/review.py:583-604`, `:766-787`). The
cell pairs `criterion-probes` entries with `spec.acceptance`, and wrong-version
entries with the criteria declaring wrong versions, each by
`zip(..., strict=True)` (`saffron/cell/session.py:3328-3345`). The task's own
last line is a `TaskOutcome` event (`saffron/cell/session.py:3765-3773`).
`describe` renders it as "`{outcome}: ${spent} spent, session …`"
(`saffron/events.py:982-985`).

**What it cost.** `SA-0335` declared `budget_usd: 69`. IMPLEMENT and GATE
spent $40.81. REVIEW then ran four lenses and 40 criterion probes over 15
criteria. The cell reached `READY_FOR_REVIEW` at $76.77.

## Problem

1. **REVIEW draws on one pool.** REVIEW opens REVIEW's pool once, where it
   computes `probe_budget` today. It opens at the remainder,
   `spec.budget_usd - spent`, or at `REVIEW_FLOOR_USD` times
   `len(review.LENSES)`, whichever is larger. `critic_budget` goes, and so
   does its test (`tests/test_session.py:7719-7726`). `REVIEW_FLOOR_USD` stays
   in `session.py` at $2. Rewrite its comment (`saffron/cell/session.py:80-89`)
   to say what the pool is.
2. **The three REVIEW calls share it.** `run_review`, `run_criterion_probes`
   and `run_wrong_versions` each take REVIEW's pool in place of `budget_usd`.
   A small type in `saffron/phases/review.py` holds what is left, the floor,
   and the first session it could not cover. The lenses run first, as
   today. Each session is capped at what is left when it starts. Its cost,
   as the session reports it, comes off when it ends. A re-prompt turn stays
   inside its session's cap through `_parse_or_reprompt`, as today. `run_lens`
   keeps its `budget_usd`, since `saffron/end_review.py:396` and `:643` call
   it.
3. **A session the pool cannot cover does not start.** A session starts only
   while the pool holds at least `REVIEW_FLOOR_USD`. Otherwise it buys no turn
   and is filed as an error. A lens is filed as a `LensReview` whose `error`
   names the cut. A criterion probe gets an entry with that `error`, a
   `cost_usd` of 0 and no probes. A wrong-version session gets
   `_unresolved_wrong_versions` with that `error`. So every list keeps one
   entry per session declared, and the `strict=True` pairing still holds.
4. **The cut ends the task `REVIEW_INCOMPLETE`.** The cell hands
   `review_state` the session REVIEW's pool could not cover. Where there is
   one, `review_state` returns `REVIEW_INCOMPLETE` with a line saying the
   review was cut at its budget, naming that session. A lens is named by its
   name in `LENSES`, and a criterion probe or wrong-version session by its
   criterion's witness. The cell emits that line as the `REVIEW:` line it
   emits today. `TaskOutcome` then reads `REVIEW_INCOMPLETE`, and the ledger
   writes the state, through the paths an errored lens takes.
5. **Spend is counted once.** The sum at `saffron/cell/session.py:3387-3397`
   stays the one place REVIEW's cost reaches `spent`. A session that did not
   start adds nothing to it. Rewrite the comment above it, since REVIEW is now
   bounded.

## Out of scope

- REBUT's fixed cap and reserves, and REVIEW's reserved share of a task's
  budget (backlog item 119). PACKAGE makes no model call.
- `run_lens`'s signature, and the end review's lenses that call it.
- The adequacy probes and the criterion-probe edits that run after the
  sessions (`saffron/cell/session.py:3301-3364`). They run in Gate-only cells
  and buy no turn.
- `DESIGN.md`, `CONTEXT.md` and ADR 8. ADR 8 still prices the fourth lens as
  "three remainders to four"
  (`docs/adr/0008-review-reads-each-hunk-against-the-standing-instructions.md:112-115`).
  That is a record of the decision as it stood, and it is `protected`.
- The gap between the cell's $76.77 and `record`'s $80.11 after PACKAGE on
  `SA-0335`. This spec did not find its cause.

## Notes for the agent

**Stack order.** `depends_on: [SA-0342]` orders the stack only. `SA-0342`
edits `revert.py` and the gate contract, and this spec consumes nothing it
adds. `SA-0340` also edits `session.py`, at REBUT's write site. Keep this
spec's edits in `session.py` inside REVIEW's block and the budget helpers.

**Mutants and new code.** The code each criterion is about is new: the pool,
its floor check and the cut line. The base does not fix its spelling, so no
criterion declares a mutant and `witness` reports `skip` for each. The wrong
versions under each criterion are what REVIEW runs. Do not run them yourself.
Criterion 3 names a test that exists, and it must stay green.

**Both witnesses.** Drive each through `_drive` in `tests/test_session.py`.
Script each turn's cost, and read each REVIEW turn's cap from
`cell.turn_options[i]["max_budget_usd"]`, past the plan and IMPLEMENT turns.
Use costs in multiples of $0.25, and vary them where a cell asserts what
comes off. A fixture whose sessions all cost the same cannot tell a pool
that takes off each cost from one that counts sessions. A plan and an IMPLEMENT turn of $0.10 each leave a
`budget_usd` of 10.2 a remainder of $10.00. A `budget_usd` of 3.2 leaves
$3.00, under the $8.00 floor.

- Criterion 1 drives three cells, each with two criteria declaring one wrong
  version. One cell's first lens costs $3.00 from an $8.00 pool. Its second
  lens raises `AgentFailed` carrying a $1.25 attempt, and its third costs
  $2.00, so the fourth lens is cut. The third lens's cap is $3.75. One cell's lenses leave $2.50 and its first
  criterion probe costs $0.75, so the second probe is cut. One cell's
  sessions leave $3.50 and its first wrong-version session costs $2.00, so
  the second is cut. Each asserts the cap sequence, the state, the spend and
  both lines. It also reads the three records, in order. The sessions that
  answered carry no `error`, and the failed lens and every session that did
  not start carry one.
- Criterion 2 drives three cells, each with three criteria declaring one
  wrong version. One opens at a $20.00 remainder. It re-prompts the second
  lens, the second probe and the second wrong-version session. It fails the
  first probe and the first wrong-version session, each with a cost. One
  opens under the floor, ten sessions at $0.50 each. The last runs nine such
  sessions with `review.LENSES` patched to drop `conventions`, so it opens at
  $6.00. Each asserts every cap, the state and the spend. So read
  `review.LENSES` when REVIEW starts, never at import.

Both arrangements were run against a prototype of the change. Every wrong
version listed under each criterion failed that criterion's witness. With
the source reverted, both witnesses failed.

**Each new test must fail with the source reverted.** Neither witness names a
name the change adds, so both collect at base. Any test you add that names
the pool type does so inside its function, through `review.`, never by a
module-scope import.

**Tests that assert the old cap.** The helper `_review` passes
`budget_usd=2.0` to `run_review` (`tests/test_review.py:71-85`). So do
thirteen direct calls of the other two, at `tests/test_review.py:1289`,
`:1371`, `:1515`, `:1592`, `:1645`, `:1707`, `:1861`, `:1952`, `:2039`,
`:2161`, `:2269`, `:2366` and `:2511`. So does one more call, at
`tests/test_events.py:2582-2592`. Each breaks until it hands REVIEW's pool
instead. A test that is not about the pool hands one
that covers every session it scripts. Five of them assert a per-session
figure the shared pool changes. They are
`test_a_criterion_probe_answer_that_is_not_the_schema_is_reprompted_once_in_its_own_session`
(`tests/test_review.py:1464`),
`test_each_criterion_with_wrong_versions_gets_one_session_that_turns_each_into_an_edit`
(`:1807`, whose `:1899` and `:1902` assert two sessions both capped at $2.00),
`test_a_wrong_version_answer_that_is_not_the_schema_is_reprompted_once_in_its_own_session`
(`:2116`), `test_a_wrong_version_reprompt_fires_once_and_only_where_a_lens_would`
(`:2222`) and `test_both_callers_refuse_a_reprompt_on_the_one_rule` (`:2381`).
Rewrite each figure to what the pool leaves. Keep what each test is about,
the re-prompt rule and the session per criterion. Two tests in
`tests/test_session.py` assert that a later session holds the same cap as an
earlier one. They are
`test_each_claim_is_asked_of_its_own_session_that_is_never_shown_a_witness`
(`tests/test_session.py:11865`, its assert at `:11959`) and
`test_criterion_probes_and_wrong_versions_share_one_gate_only_cell_and_the_spend`
(`tests/test_session.py:13577`, its assert at `:13670`). Assert the cap REVIEW's pool leaves instead.
A prototype of the change failed these seven tests and the `critic_budget`
test, and no others.

**The two evidence scripts.** Each passes `budget_usd=args.budget_usd` to
`run_review` (`docs/evidence/scripts/2026-09-07-lens-scoring.py:184`,
`docs/evidence/scripts/2026-09-08-lens-corpus.py:453`). Each help text calls
that figure "per lens" (`:83`, `:311`). Keep it per lens: hand `run_review` a
pool of that figure times `len(review.LENSES)`, and say so in the help text.
`tests/test_corpus.py:573` replaces `run_review` with a stub that takes any
keyword.

**One stale comment.** `tests/test_lens_scoring.py:795-801` says a past figure
of $3.30 is "the remainder `critic_budget()` left". The function goes, so name
REVIEW's cap there instead. Leave `LENS_CEILINGS` as it is.

**Docstrings.** `run_review`'s docstring opens "Every declared lens, in
order" (`saffron/phases/review.py:377`). A cut makes that untrue, so say a
lens REVIEW's pool cannot cover does not start.

**Words.** Write "REVIEW's pool" or "the review pool" in comments and
docstrings, never a bare "pool" (`CONTEXT.md:90-94`). New comments and docstrings take no em-dash,
semicolon, contraction or sentence over 25 words.
