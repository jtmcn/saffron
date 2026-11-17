---
id: SA-0407
title: "A lens with an error keeps the host's survivors out of REBUT, and the log names none of them"
type: feature
priority: 3
risk: elevated
estimated_lines: 340
estimate_measured: true
depends_on: [SA-0406]
consumes:
  - saffron/phases/review.py:host_survivors
  - saffron/phases/review.py:rebuts_despite_errors
  - saffron/phases/review.py:incomplete_after_rebut
touches:
  - saffron/cell/session.py
  - saffron/phases/review.py
  - tests/test_session.py
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
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - saffron/phases/implement.py
  - tests/test_review.py
  - tests/test_rebut.py
  - tests/test_task.py
  - tests/test_events.py
  - tests/test_agent_runner.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 54
max_attempts: 3
max_turns: 240
acceptance:
  - claim: >-
      When a lens has an `error`, REVIEW's pool cut nothing, and
      `review.rebuts_despite_errors(reviews, cut)` holds, the task goes to
      REBUT. REVIEW's line is the line `review.review_state` returned, then
      `, and N host-filed survivor(s) go to REBUT`. N is the count
      `review.host_survivors` returns over every lens. REBUT takes every
      blocker `review.anchored_blockers` returns, as it does today.
      `run_rebut` gets each lens with an `error` in `unreviewed`, so such a
      lens gets no verdict session. Each other lens holding a blocker gets
      its own. When REBUT ends `READY_FOR_REVIEW` or `REBUTTAL_UNJUDGED`,
      the task ends `REVIEW_INCOMPLETE`, and so does its ledger row. Its
      REBUT line and `rebuttal.json`'s `state` and `why` carry that state
      and `review.incomplete_after_rebut(reviews, entries)`. `entries` is
      the list `_rebut_gates` wrote to `rebut-probes.json`, or empty when
      it wrote none. The witness drives three cells. In one, adequacy's
      output is not the schema twice. In one, adequacy's session fails. In
      both, adequacy holds both survivors. In the third, correctness's
      session fails, contract files a blocker of its own, and adequacy
      holds both survivors with no `error`. REBUT ends `READY_FOR_REVIEW`
      with no verdict, `REBUTTAL_UNJUDGED` on a fix claimed and not
      committed, and `READY_FOR_REVIEW` on two lenses' verdicts. The two
      survivors are of a criterion's own edit and of the spec's own wrong
      version. Their fates are killed, survived, and not asked again
      because HEAD did not move.
    witness: tests/test_session.py::test_a_lens_with_an_error_still_sends_the_hosts_survivors_to_rebut_and_ends_incomplete
    wrong_versions:
      - The session never routes a REVIEW with a lens with an `error` to REBUT.
      - The session passes no `unreviewed` to `run_rebut`, so adequacy with an `error` still gets a verdict session.
      - The session passes every lens in `review.LENSES` as `unreviewed`, so no lens gets a verdict session.
      - The task keeps the state REBUT decided.
      - The task ends `REVIEW_INCOMPLETE` only when REBUT decided `READY_FOR_REVIEW`.
      - The task ends `REVIEW_INCOMPLETE` only when HEAD moved during REBUT.
      - "`rebuttal.json` is written before the override, so it keeps the state and `why` REBUT decided."
      - "`incomplete_after_rebut` is given an empty list, so every survivor reads not asked again."
      - The session keeps only the killed entries, so a survivor the probe left alive reads not asked again.
      - REVIEW's line stays the line `review_state` returned.
      - N counts only the survivors a lens with an `error` holds.
      - N counts every blocker `anchored_blockers` returns.
  - claim: >-
      Beside a lens with an `error`, REBUT's own `EXHAUSTED` and
      `GATE_ERROR` stand. The outcome, the ledger row, the REBUT line and
      `rebuttal.json`'s `state` and `why` carry REBUT's own state and line.
      The witness drives `EXHAUSTED` from a red gate re-run and from a probe
      cell that refuses the post-rebuttal patch. It drives `GATE_ERROR`
      from a gate re-run whose `tests` gate reports `error`. A rebuttal
      turn that REBUT's cap cuts ends the task `REVIEW_INCOMPLETE`, never
      `EXHAUSTED`. Its REBUT line and `rebuttal.json` carry criterion 1's
      line, and the outcome keeps its `rebut_result`, whose `state` reads
      `REVIEW_INCOMPLETE`.
    witness: tests/test_session.py::test_beside_a_lens_with_an_error_rebuts_own_stops_stand_and_a_cut_ends_incomplete
    wrong_versions:
      - A red gate re-run ends `REVIEW_INCOMPLETE` too.
      - A probe cell that refuses the post-rebuttal patch ends `REVIEW_INCOMPLETE` too.
      - A gate re-run whose gate errors ends `REVIEW_INCOMPLETE` too.
      - A REBUT cap cut still turns the outcome to `EXHAUSTED`.
      - A REBUT cap cut ends `REVIEW_INCOMPLETE` but still clears `rebut_result`.
  - claim: >-
      A REVIEW whose pool could not cover the wrong-version session sends
      nothing to REBUT, even beside a lens with an `error` and a host-filed
      survivor. It ends `REVIEW_INCOMPLETE` on
      `review_state`'s cut line, prints no REBUT line and writes no
      `rebuttal.json`. With money left, the same lenses and probe costs send
      the survivors to REBUT on criterion 1's lines and write
      `rebuttal.json`. When every witness kills its edit, no host-filed
      survivor exists. REVIEW's line is then `review_state`'s line for a
      lens with an `error`, character for character, with no REBUT line and
      no `rebuttal.json`.
    witness: tests/test_session.py::test_a_review_cut_at_its_pool_or_left_no_survivor_sends_nothing_to_rebut
    wrong_versions:
      - The session passes no cut to `review.rebuts_despite_errors`.
      - The session routes on any lens with an `error` and no REVIEW cut, survivor or not.
  - claim: >-
      A lens with an `error` and no host-filed survivor still ends its task
      `REVIEW_INCOMPLETE`, and its ledger row reads the same.
    witness: tests/test_session.py::test_a_lens_that_errored_ends_its_task_in_a_state_no_batch_scan_takes_back
    preserves: true
---

## Context

Backlog item **b-f7a591**, which cites `DESIGN.md` §5.5. A lens returned no
findings on `SA-0259`, and the host's two survived criterion probes under it
never reached REBUT. `SA-0406`, this spec's parent, adds the helpers. This
spec wires them into `_drive_cell`. Every `saffron/cell/session.py` and
`saffron/task.py` line number below was read at `cb15ea09`. `SA-0406`
changes `saffron/phases/review.py` and `saffron/phases/rebut.py`, so those
are cited by name.

**What `SA-0406` gives this spec.** None of the three helpers exists at
`cb15ea09`. They are `consumes` entries, and `run_task` resolves each one
at this spec's tree base. `review.host_survivors(reviews)` returns each
host-filed survivor `anchored_blockers` keeps, in its order.
`review.rebuts_despite_errors(reviews, cut)` holds when `cut` is `None`,
some lens has an `error` and `host_survivors` returns one.
`review.incomplete_after_rebut(reviews, entries)` returns
`review_state`'s line for a lens with an `error`. A clause follows for
each host-filed survivor such a lens holds, with what `entries` says of it.
`run_rebut` takes a keyword `unreviewed`, and a lens it names gets no
verdict session. `review_state` keeps its return.

**How REVIEW ends today.** `_drive_cell` calls `review.review_state` once
and prints its line (`saffron/cell/session.py:3671-3672`). REBUT runs only
on `REBUTTING` (`saffron/cell/session.py:3689`), over
`review.anchored_blockers(reviews)` (`saffron/cell/session.py:3693`).
`review_state` returns `REVIEW_INCOMPLETE` for any lens with an `error`
before it counts a blocker. The host appends every survivor to the
`adequacy` `LensReview`, with an `error` or not
(`saffron/cell/session.py:2176`, `2268`, `2278`).

**What `_rebut_gates` records.** It asks each blocker whose probe survived
again, but only when HEAD moved (`saffron/cell/session.py:3760-3767`,
`3779`). It writes the entries to `rebut-probes.json`
(`saffron/cell/session.py:3814-3816`). Nothing after it reads them.

**How REBUT's outcome is written.** `run_rebut` is called at
`saffron/cell/session.py:3929-3960`. A REBUT cap cut is
`cap.cut is not None and result.state == "REBUTTAL_UNJUDGED"`
(`saffron/cell/session.py:3963`). The overrides of `result.why` follow
(`saffron/cell/session.py:3964-3979`). `rebut_result` is bound at `3980`,
and `rebuttal.json` is written at `3986-3988`. The outcome is read from
`result` at `4029`. A cut then sets `EXHAUSTED` and clears `rebut_result`
(`saffron/cell/session.py:4044-4046`). The REBUT line follows at `4048`,
and the ledger row is set at `4061-4062`.

**Why a cut beside a lens with an `error` keeps `rebut_result`.**
`run_task` packages an `EXHAUSTED` task with no `rebut_result` and an
anchored blocker (`saffron/task.py:1009-1013`). A cut that ended
`EXHAUSTED` and cleared it here would open a draft pull request over a
lens that never reviewed.
`saffron package`'s orphaned path reads `review_state` and refuses a
`REVIEW_INCOMPLETE` task (`saffron/task.py:1448-1450`). It still refuses
this one.

## Problem

A lens with an `error` keeps the host's own survivors out of REBUT, and the
log names none of them. Send them to REBUT and name each one after it.

1. **The route.** Call
   `review.rebuts_despite_errors(reviews, review_pool.cut)` right after
   `review_state`. If it holds, set the outcome to `REBUTTING`. Keep the
   names of the lenses with an `error`. Print REVIEW's line as criterion 1
   gives it.
2. **No verdict for a lens with an `error`.** Pass those names to
   `run_rebut` as `unreviewed`. Every other caller keeps the default.
3. **The entries.** Keep the list `_rebut_gates` wrote to
   `rebut-probes.json`. It stays empty when HEAD did not move.
4. **The end state.** On this path REBUT's own `EXHAUSTED` and
   `GATE_ERROR` stand. Any other end sets `result.state` to
   `REVIEW_INCOMPLETE` and `result.why` to
   `incomplete_after_rebut(reviews, entries)`. Do it
   after every other override of `result.why` and before `rebuttal.json`
   is written. A REBUT cap cut on this path ends here too, and keeps its
   `rebut_result`.
5. **The docstring.** `review_state`'s docstring ends its paragraph on a
   lens with an `error` with "and there is no finding set to rebut
   against". That clause goes false here. Drop it, and keep the sentence
   before it, "An unrun lens must not read as a clean review". Change
   nothing else in `saffron/phases/review.py`.

## Out of scope

- **The helpers themselves.** `SA-0406` owns them, and
  `saffron/phases/rebut.py` is forbidden here.
- **`rebut_state`'s line beside a named lens.** Every blocker can sit
  under a lens in `unreviewed`. `rebut_state` then reads no verdict and returns
  `READY_FOR_REVIEW` with "every blocker withdrawn by its own lens". On
  this path that line never stands, since item 4 replaces it.
- **Which name `unreviewed` matches.** The verdict loop in `run_rebut`
  matches a blocker's own `Finding.lens`, and the session passes each
  `LensReview.lens` with an `error`. The two agree here. `review.run_lens`
  and `review.run_review` build a lens with an `error` with no findings. The host
  appends every survivor to the `adequacy` `LensReview`
  (`saffron/cell/session.py:2176`), and `review.survivor_finding` sets
  each survivor's `Finding.lens` to `adequacy`. So no witness drives a
  blocker whose `Finding.lens` differs from its holder.
- **The unproven fate.** `SA-0406`'s witness reads its text. The session
  passes the entries through unread, and the witness here drives killed,
  survived and not asked again.
- **The other ways in.** The witness drives one or two of each set. Left
  undriven are three more `EXHAUSTED` ends: a repair turn that left the
  gates red, a critic cell that refuses the patch, and an empty patch.
  So are five `GATE_ERROR` ends: a drifted re-run, a probe-infrastructure
  block, either binary patch, and a verdict lens that never started. The
  `REBUTTAL_UNJUDGED` of a verdict session with an `error` is undriven, as
  are REBUT cuts at the extraction or verdict stage. So are the
  `READY_FOR_REVIEW` ends on a confirmed or a contradicted verdict. Item 4
  reads only `result.state`, so each follows from the members driven. A
  survivor of a parent's wrong version is undriven, and so is a REVIEW cut
  at a lens or at a criterion probe. `rebuts_despite_errors` decides both
  in `SA-0406`, and its witness drives them.
- **The lens's own JSON failure.** b-4e0868 owns it.
- **The lens's own line.** `run_review` prints it before any survivor
  exists. The final line names the survivors.
- **What gets pushed.** `run_task` pushes the branch of every outcome
  PACKAGE did not take (`saffron/task.py:1088-1093`). A `REVIEW_INCOMPLETE`
  branch can now carry the rebuttal's commits, as a `REBUTTAL_UNJUDGED`
  branch already does.
- **A `retired_first`.** This adds no refusal of a spec.
- **A new term.** "Host-filed survivor" is `CONTEXT.md`'s own phrase.
- **Hand edits, already amended in this spec's pull request.** Two
  replace one sentence, and five end a paragraph or an entry. Each new
  sentence is quoted on a line of its own.

  `DESIGN.md` §5.5, the paragraph opening **A lens that produced no
  findings ends the task `REVIEW_INCOMPLETE`**. Its sentence ending
  `no finding set exists to rebut.` now reads as follows.

  > An unrun lens must not read as a clean review.
  > Without a REVIEW pool cut, the host's own survivors still go to REBUT.
  > A lens with an error gets no verdict session there.
  > REBUT's own `EXHAUSTED` or `GATE_ERROR` stands.
  > Any other end, a REBUT pool cut included, leaves the task `REVIEW_INCOMPLETE`.
  > Its line names each host-filed survivor a lens with an error holds.
  > It also names what the post-rebuttal probe left of each (`SA-0407`).

  `CONTEXT.md`, the **`REVIEW_INCOMPLETE`** entry. Its sentence ending
  `no finding set exists to rebut.` now reads as follows.

  > An unrun lens never reads as a clean review.
  > Without a REVIEW pool cut, the host-filed survivors still go to REBUT first (`SA-0407`).
  > The task then ends here unless REBUT ends `EXHAUSTED` or `GATE_ERROR`.

  Five more sentences say a REBUT pool cut ends `EXHAUSTED`, or that each
  lens holding a blocker answers it. Each paragraph or entry now ends on
  its exception, so no sentence after it reads it as its subject.

  `DESIGN.md` §5.6, the paragraph opening **REBUT runs under a fixed cap of
  its own**, now ends as follows.

  > Beside a lens with an error in REVIEW, a REBUT a pool cut short ends `REVIEW_INCOMPLETE` instead, on the line §5.5 names.

  `DESIGN.md` §5.6, the paragraph opening **The order, settled**, now ends
  as follows.

  > Beside a lens with an error in REVIEW, that lens answers no blocker (§5.5).
  > The task then ends `REVIEW_INCOMPLETE` wherever this paragraph names `READY_FOR_REVIEW` or `REBUTTAL_UNJUDGED`.

  `DESIGN.md` §5.7, the paragraph opening **A task REBUT could not pay for
  is packaged too**, now ends as follows.

  > None of this paragraph reaches a REBUT beside a lens with an error in REVIEW.
  > A pool that cuts such a REBUT short ends it `REVIEW_INCOMPLETE`, and PACKAGE never runs (§5.5).

  `CONTEXT.md`, the **`EXHAUSTED`** entry, now ends as follows.

  > Beside a lens with an error in REVIEW, a REBUT pool cut ends `REVIEW_INCOMPLETE` instead.

  `CONTEXT.md`, the **`REBUTTAL_UNJUDGED`** entry, now ends as follows.

  > Beside a lens with an error in REVIEW, a REBUT that would end here ends `REVIEW_INCOMPLETE` instead, cut or not (`SA-0407`).

## Notes for the agent

**New or edit.** Criteria 1 to 3 build new behaviour, so they declare
witnesses and no mutant, and `witness` reports `skip` for them. Criterion 4
is `preserves`, and its witness exists and passes at `cb15ea09`. Each
wrong version under a criterion is one its witness must fail. REVIEW turns
each into an edit and asks the witness. Do not ask them yourself.

**Keep every existing test as it is.** Rename no test. The `census` gate
reads a renamed test as a removed one.

**The session witnesses.** One shared helper in `tests/test_session.py`
can drive all three. Build it from `_stub_the_runtime`, `_rebuttable`,
`_drive`, `_tests_result`, `_probe_answer`, `_wrong_version_answer`,
`_rebuttal_turn_has_run`, `_ANCHORING_DIFF`, `_GROWN_PATCH`,
`_CRITIC_CONTAINER`, `_PROBE_POLICY` and `_TASK_BASE`. Give the spec two
criteria. The first has a criterion probe on `src/x.py`, and the second
declares one wrong version on `src/y.py`. Answer `read_at_head` from your
own file contents, with `None` for `_CRITIC_CONTAINER`.

- These were measured on the prototype. The gate-only cell's `run_gate`
  answers one leading ask first. Then for each named edit it answers a
  witness ask, and for a survivor a whole-suite ask after it. REBUT's
  probe then answers a baseline, then one ask per survivor.
- A lens whose output is not the schema twice takes two scripted turns.
  One whose session fails takes one `implement.AgentFailed`.
- A REBUT cap cut is a rebuttal turn raising `implement.AgentFailed` with
  `_cut_off_turn(cost=10.25)`, HEAD unmoved.
- For a probe cell that refuses the patch, stand in for
  `session.probe_findings`. Raise `CriticPatchRejected` for a `patch` of
  `_GROWN_PATCH`, and call the real one for any other. Import the class
  from `saffron.cell.worktree`, since
  `tests/test_rebut.py::test_the_critic_patch_exceptions_are_imported_from_worktree_alone`
  fails on `session.CriticPatchRejected`.
- `tests/test_session.py` already defines `_task_state`. A second `def` of
  a name there replaces the first for every test, so search before naming
  a helper. The prototype's first whole suite failed six tests this way.
- A REVIEW pool cut needs the spec's `budget_usd` low enough that the pool
  opens at its floor of $8.00. Lens and probe costs then leave under $2.00
  before the wrong-version session.
- Count verdict sessions as the prompts in `cell.turns` equal to
  `rebut.VERDICT_TURN_PROMPT`. Read the ledger row's state from
  `ledger._db`, as criterion 4's witness does.
- A claim of no REBUT line or no file needs a positive case. A cell in
  the same test shows that line or file, read the same way.

**Measured.** On 2026-11-17 a prototype on `SA-0406`'s own prototype at
`cb15ea09` passed all three new witnesses and the whole suite (5348
tests). With
`saffron/cell/session.py` reverted to `cb15ea09`, each new witness failed
in its body. Each wrong version above was applied to the prototype, and
its own criterion's witness failed on every one.

**The `prose` gate** reads every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. The errored-lens line's em dash is today's text
and stays.

**Size.** `size_gate` counted this spec's own changes over `SA-0406`'s at
1360 tokens: 109 in `saffron/cell/session.py`, 11 in
`saffron/phases/review.py` and 1240 in `tests/test_session.py`. That is
against the `feature` ceiling of 3000. `estimated_lines` is that over
four. `saffron/cell/session.py` is in `elevate_on`, so this spec runs
`elevated`.
