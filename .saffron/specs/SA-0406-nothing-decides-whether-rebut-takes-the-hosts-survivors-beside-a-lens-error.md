---
id: SA-0406
title: "Nothing decides whether REBUT takes the host's survivors beside a lens with an error, or names what it left of them"
type: feature
priority: 3
risk: standard
estimated_lines: 281
estimate_measured: true
pending_symbols:
  - saffron/phases/review.py::rebuts_despite_errors
  - saffron/phases/review.py::incomplete_after_rebut
touches:
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - tests/test_review.py
  - tests/test_rebut.py
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
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/agents/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/report/**
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/probe.py
  - saffron/intake.py
  - saffron/phases/package.py
  - saffron/phases/implement.py
  - tests/test_session.py
  - tests/test_task.py
  - tests/test_events.py
  - tests/test_agent_runner.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 48
max_attempts: 3
max_turns: 230
acceptance:
  - claim: >-
      `review.host_survivors(reviews)` returns each blocker
      `review.anchored_blockers(reviews)` returns whose claim opens with
      `review.HOST_FILED`, in that order. `review.rebuts_despite_errors(reviews,
      cut=None)` is true exactly when `cut` is `None`, some lens has an
      `error`, and `host_survivors` returns at least one. Both hold for a
      survivor of a criterion's own edit, of the spec's own wrong version
      and of a parent's wrong version. They hold for an unanchored
      survivor of the criterion's own edit and for anchored survivors of
      the two wrong versions. The lens with an `error` can sit before or
      after the lens holding the survivor, or hold it itself. A lens's own blocker whose probe survived counts for neither
      function. Beside those survivors `review.review_state` still returns
      `REVIEW_INCOMPLETE` and today's errored-lens line, character for
      character.
    witness: tests/test_review.py::test_a_lens_with_an_error_routes_to_rebut_only_beside_a_host_survivor_and_no_cut
    wrong_versions:
      - "`rebuts_despite_errors` ignores `cut`."
      - "`rebuts_despite_errors` reads only the first lens's `error`."
      - "`rebuts_despite_errors` reads only the last lens's `error`."
      - "`rebuts_despite_errors` is true only when a lens with no `error` holds a host-filed survivor."
      - "`host_survivors` keeps only anchored survivors."
      - "`host_survivors` keeps any blocker whose probe survived, a lens's own included."
      - "`host_survivors` drops a survivor of a wrong version."
      - "`host_survivors` drops a survivor of a parent's wrong version."
      - "`host_survivors` sorts its result by file."
      - "`review_state` returns `REBUTTING` when `rebuts_despite_errors` holds."
  - claim: >-
      `review.incomplete_after_rebut(reviews, entries)` returns today's
      errored-lens line, with no period added, when no lens with an
      `error` holds a host-filed survivor. Otherwise it returns that line,
      a period, then one clause per host-filed survivor a lens with an
      `error` holds, in `host_survivors` order. A survivor's fate comes
      from the entry in `entries` whose `probe` matches the survivor's
      edit in `file`, `find` and `replace` together. An entry that differs
      in any one of the three does not match. A killed entry names every
      failure, in order. An unproven entry names its reason. A survivor
      with no matching entry reads not asked again. Two survivors of one
      edit each get a clause, with the same fate. The line names every
      lens with an `error`. A survivor held by a lens with no `error` gets
      no clause.
    witness: tests/test_review.py::test_the_incomplete_line_names_what_the_rebuttal_left_of_each_survivor_under_a_lens_with_an_error
    wrong_versions:
      - A killed fate names only the first failure.
      - An unproven fate leaves out its reason.
      - A survived entry reads not asked again.
      - The line names only the first lens with an `error`.
      - The line ends with a period when it names no survivor.
      - A fate is matched on the edit's file alone.
      - A fate is matched on file and find, so an entry with another replace still matches.
      - A fate is matched on file and replace, so an entry with another find still matches.
      - A fate is matched on find and replace, so an entry on another file still matches.
      - The line also names the survivors a lens with no `error` holds.
      - The line gives one clause per distinct edit, so two survivors of one edit share one clause.
      - The clauses are sorted by file and line.
  - claim: >-
      `rebut.run_rebut` takes a keyword `unreviewed`, a collection of lens
      names that defaults to empty. A lens it names gets no verdict
      session. Every other lens holding a blocker still gets its own. The
      rebuttal turn's prompt still carries every blocker, and every blocker
      keeps the number its place in `blockers` gives it. So a guarded
      blocker a healthy lens withdraws is still refused under its own
      number. The witness names `adequacy` alone in a list, `correctness`
      alone in a tuple, `correctness` and `contract` in a set, and all three
      lenses in a list. The lens left to verdict is `correctness` or
      `adequacy`.
    witness: tests/test_rebut.py::test_a_lens_named_unreviewed_gets_no_verdict_session_and_keeps_its_numbers
    wrong_versions:
      - "`run_rebut` ignores `unreviewed`."
      - Any non-empty `unreviewed` drops every verdict session.
      - Only the first name in `unreviewed` is honoured.
      - A named lens's blockers are dropped from `blockers` before numbering.
      - A named lens's blockers are left out of the rebuttal turn.
      - The blockers left for the verdict sessions are numbered again from 1.
      - The guard is read over the numbering with the named lenses' blockers dropped.
  - claim: >-
      `review.review_state` still returns `REVIEW_INCOMPLETE` for a lens
      with an `error`, before or after a lens holding a blocker or a
      concern.
    witness: tests/test_review.py::test_a_lens_that_errored_ends_review_incomplete_whatever_the_others_found
    preserves: true
---

## Context

Backlog item **b-f7a591**, which cites `DESIGN.md` §5.5. A lens returned
no findings on `SA-0259`, and the host's two survived criterion probes under it never
reached REBUT. This spec is the first of two. It adds the predicates and
the line a REVIEW with a lens with an `error` needs. With them the host's own
survivors can go to REBUT, and a line can name what REBUT left of them.
`SA-0407` wires them into `_drive_cell`. Every line number below was read at
`a5c1f2e9`.

**How a lens with an `error` ends REVIEW today.** `review.review_state` checks
REVIEW's pool cut first. It then returns `REVIEW_INCOMPLETE` for any lens
with an `error`, before it counts a blocker
(`saffron/phases/review.py:1079-1106`). Its errored-lens line is
`f"{errored} produced no findings — the review is incomplete"`, with
`errored` the list of lens names (`saffron/phases/review.py:1100`). Its
docstring ends that paragraph with "there is no finding set to rebut
against" (`saffron/phases/review.py:1088`). That docstring is ten lines,
the `prose` gate's limit. `_drive_cell` calls it once
(`saffron/cell/session.py:3671`), and REBUT runs only on `REBUTTING`
(`saffron/cell/session.py:3689`). `saffron package`'s orphaned path calls it
too and refuses a task it reads as `REVIEW_INCOMPLETE`
(`saffron/task.py:1448-1450`). That is why its return stays as it is.

**Where the host's survivors sit.** `review.survivor_finding` files each
host-filed survivor under `lens="adequacy"` (`saffron/phases/review.py:894-935`).
Its claim opens with `review.HOST_FILED` (`saffron/phases/review.py:56`). Its
edit is its `probe`, and its `probe_verdict` is `survived`. The criterion probes append each one to the
adequacy `LensReview`, with an `error` or not
(`saffron/cell/session.py:2176`, `2268`, `2278`). Each comes from one
`survivor_finding` call, which passes a recorded `version` and `parent`
when the pair holds them (`saffron/cell/session.py:2238-2244`). That covers
a criterion's own edit, the spec's own wrong version and a parent's wrong
version.
`review.anchored_blockers` keeps every blocker that anchored or whose claim
opens with `review.HOST_FILED`. It reads `reviews` in order, and each
lens's findings in order (`saffron/phases/review.py:982-998`). `review.probe_key` is an edit's
`(file, find, replace)` (`saffron/phases/review.py:1027-1030`).

**What REBUT does with its blockers.** `run_rebut` numbers `blockers` from 1
(`saffron/phases/rebut.py:916`) and hands every one to the rebuttal turn.
It then gives each lens in `review.LENSES` that holds a blocker its own
verdict session (`saffron/phases/rebut.py:1013-1036`). `review.LENSES`
names `correctness`, `contract` and `adequacy`
(`saffron/phases/review.py:41-45`). The withdrawal guard is read over that
same numbering (`saffron/phases/rebut.py:1041`). `run_rebut`'s docstring is
ten lines (`saffron/phases/rebut.py:903-912`), the `prose` gate's limit. `run_rebut`
has four callers: `saffron/cell/session.py:3929`,
`tests/test_agent_runner.py:851`, `tests/test_events.py:2728` and the
`_run` helper at `tests/test_rebut.py:521`.

**What the post-rebuttal probe re-run records.** `_rebut_gates` asks each
blocker whose probe survived again over the post-rebuttal patch, but only
when HEAD moved (`saffron/cell/session.py:3779`). It writes the entries to
`rebut-probes.json` (`saffron/cell/session.py:3814-3816`). When HEAD did not
move it builds none, which is what the not-asked-again fate reads.
`probe_findings` builds one entry per distinct edit
(`saffron/cell/session.py:1920-1938`). Each entry holds `probe_verdict`
and `probe.record_fields`, whose `probe` is the edit's `model_dump()`,
with `reason` and `failures` (`saffron/probe.py:423-442`).

## Problem

A REVIEW with a lens with an `error` never sends the host's own survivors to
REBUT, and no line names them. Add what `SA-0407` needs to do both.
Nothing in `saffron/` calls `rebuts_despite_errors` or
`incomplete_after_rebut` yet, so both are in `pending_symbols`. On a
prototype of this spec alone, the `dead` gate failed on exactly those two.
`host_survivors` is reached through them.

1. **`review.host_survivors(reviews)`.** The blockers
   `anchored_blockers` returns whose claim opens with `HOST_FILED`, in its
   order.
2. **`review.rebuts_despite_errors(reviews, cut=None)`.** It needs three
   things to be true: no cut, some lens with an `error`, and a host
   survivor.
3. **`review.incomplete_after_rebut(reviews, entries)`.** `entries` is the
   list `_rebut_gates` writes to `rebut-probes.json`, or an empty list.
   Build today's errored-lens line, as `review_state`'s docstring names it,
   from one shared helper that
   `review_state` uses too, so the two cannot drift. When a lens with an
   `error` holds a host survivor, append a period and one clause per such
   survivor. Each clause is one space, then the lens,
   ` host-filed survivor `, its file, `:`, its line, `: `, its fate and a
   period. The four fates, each exactly as written:

   ```
   killed after the rebuttal by <every failure in the entry, joined by ", ">
   survived the probe after the rebuttal
   unproven after the rebuttal, <the entry's reason>
   not asked again after the rebuttal
   ```

4. **`run_rebut(..., unreviewed: Collection[str] = ())`.** Skip a named
   lens in the verdict loop alone. Leave `blockers`, their numbering, the
   rebuttal turn and the guard as they are. Document the keyword in a
   comment beside it, since the docstring is at its limit.
5. **`review_state`'s docstring.** Drop "and there is no finding set to
   rebut against". Nothing calls `rebuts_despite_errors` at this spec's
   head, so the new words say what it decides and never that a caller sends
   anything to REBUT. The docstring is at its ten-line limit, so the new
   words take no extra line. Leave `review_state`'s code and return alone.

## Out of scope

- **The wiring.** `SA-0407` calls these from `_drive_cell`, passes
  `unreviewed`, prints the new lines and sets the end state. This spec
  changes no line of `saffron/cell/` and no outcome of a cell.
- **The state `run_rebut` returns beside a named lens.** Its blockers get
  no verdict. When every lens holding a blocker is named and the rebuttal
  argued, `rebut_state` returns `READY_FOR_REVIEW` with "every blocker
  withdrawn by its own lens" (`saffron/phases/rebut.py:721`). That line is
  false on this path. `SA-0407` overrides the state and line there, and no
  criterion here pins `state` or `why` for it.
- **Two entries for one edit.** `probe_findings` writes one entry per
  distinct edit, so no witness drives a duplicate entry. The first match
  decides.
- **A lens with an `error` and its own findings.** Such a lens holds only
  what the host appended. So no witness drives one of its own.
- **Hand edits.** None. `DESIGN.md` §5.5 and `CONTEXT.md`'s
  `REVIEW_INCOMPLETE` entry say no finding set exists to rebut. That stays
  true until `SA-0407` changes the route, so its pull request carries both
  edits.
- **A `retired_first`.** This spec adds no refusal of a spec.
- **A new term.** "Host-filed survivor" is `CONTEXT.md`'s own phrase
  (`CONTEXT.md:787`).

## Notes for the agent

**New or edit.** Criteria 1 to 3 build new code, so they declare
witnesses and no mutant, and `witness` reports `skip` for them. Criterion 4
is `preserves`, and its witness exists and passes at `a5c1f2e9`. Each wrong
version under a criterion is one its witness must fail. REVIEW turns each
into an edit and asks the witness. Do not ask them yourself.

**At base each new witness fails in its body.** Reach every new name
through the module, as `review.host_survivors` or a `run_rebut` keyword.
The reverted source then fails at the call, never at collection.

**The `review.py` witnesses** build every host survivor with
`review.survivor_finding` over `Criterion` and `Mutant` from
`saffron.intake`, never as a hand-written claim. Build one of each kind:
the criterion's own edit, a wrong version, and a parent's wrong version.
Mark one unanchored. Build each entry as a dict with `probe` (the edit's
`model_dump()`), `probe_verdict`, and `failures` or `reason` where needed.
For the field match, give three entries that each differ from one
survivor's edit in one field alone. Write each expected line as a literal
in the test. To drive clause order, give one lens with an `error` its survivors in
an order that file and line do not sort to.

**The `run_rebut` witness** reuses `_run`, `_blocker`, `_rebuttals`,
`_argued`, `_verdicts`, `_verdict`, `_WITHDRAWAL_ARGUMENT` and
`_WITHDRAWAL_HOST_SENTENCE` in `tests/test_rebut.py`. Add `unreviewed` to
`_run` and pass it on only when a test names it, so every other test keeps
the default. Build the guarded blocker with `review.survivor_finding` over
a `preserves` criterion passed as `acceptance`. Put the named lens's
blocker first, so the healthy lens's own blocker is number 2. Count agent
calls with `_run`'s `record`: one rebuttal, one extraction, then one per
verdict session. Read the rebuttal turn's prompt from `record[0]`.

**What the witnesses leave undriven.** No case leaves `contract` as the
lens that verdicts, and no wrong-version survivor is unanchored. The claims
name only what the witnesses drive.

**Keep every existing test as it is.** Rename no test. The `census` gate
reads a renamed test as a removed one.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. The errored-lens line's em dash is today's text and stays.

**Measured.** On 2026-11-17 a prototype at `a5c1f2e9` passed the three new
witnesses, and the whole suite passed on it (5340 tests). With `saffron/phases/` reverted to `a5c1f2e9`, each
new witness failed in its body. Each wrong version above was applied to the
prototype, and its own criterion's witness failed on every one.

**Size.** `size_gate` counted the prototype at 305 changed tokens outside
`tests/` and 818 under it, against the `feature` ceiling of 3000.
`estimated_lines` is the sum over four.
