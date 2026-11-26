---
id: SA-0440
title: "The end review's writer drafts a follow-up for a finding whose claim names an unretired spec outside the stack that already touches its file"
type: bug
priority: 2
estimated_lines: 43
estimate_measured: true
touches:
  - saffron/follow_up.py
  - tests/test_follow_up.py
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
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/agents/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/qualify.py
  - saffron/finish.py
  - saffron/end_review.py
  - saffron/spec_review.py
  - saffron/mutants.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/events.py
  - saffron/regate.py
  - saffron/parent_versions.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/report/**
  - tests/test_cli.py
  - tests/test_finish.py
  - tests/test_qualify.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
budget_usd: 30
max_attempts: 3
max_turns: 200
risk: standard
acceptance:
  - claim: >-
      `follow_up.write_follow_ups` opens no spec writer session for a
      qualified finding whose claim names an unretired spec's id as a whole
      word, where that spec's `touches` holds the finding's file. An
      unretired spec here is one `intake.discover_specs` finds directly in
      `specs_dir`, with its default refusals, less every layer of the stack
      under review. The other findings of that group are still drafted, in
      their own order. The witness drives the id bare, in backticks, and
      with `'s` after it. It drives a `touches` entry that is the exact path
      and one that is a glob. It keeps in the draft a claim naming an
      unretired spec whose `touches` lack the file, and a claim naming no
      spec. It also keeps a claim naming a longer id that starts with an
      unretired id, one naming a spec in `done/`, and one naming a spec
      discovery refuses for an inline mutant. It keeps a claim naming the
      finding's own layer, one naming a lower layer and one naming a higher
      layer, each whose `touches` hold the file. A group holding owned and
      unowned findings is drafted once from the unowned ones. A group whose
      every finding is owned gets no session.
    witness: tests/test_follow_up.py::test_a_finding_an_unretired_spec_names_and_touches_gets_no_writer_session
    wrong_versions:
      - "Any unretired spec the claim names owns the finding, whatever its `touches` hold."
      - "Any unretired spec whose `touches` hold the file owns the finding, whether or not the claim names it."
      - "The claim names a spec when its id is a substring of the claim, so a longer id that starts with it counts."
      - "The stack's own layers count as unretired specs outside the stack."
      - "Only the finding's own layer is left out, so a claim naming another layer counts."
      - "The layers are left out only from the finding's own index in `stack.layers` down, so a claim naming a higher layer counts."
      - "The specs in `done/` count as unretired specs."
      - "Discovery runs with `retired=True`, as `_origin_file_text` calls it, so a spec refused for an inline mutant counts."
      - "A `touches` entry holds the file only when it equals the path, so a glob never does."
      - "One owned finding sends its whole group past the writer."
    covers:
      - set: the spellings of an unretired id in a claim
        members:
          - member: the id bare
            driven_by: tests/test_follow_up.py::test_a_finding_an_unretired_spec_names_and_touches_gets_no_writer_session
          - member: the id in backticks
            driven_by: tests/test_follow_up.py::test_a_finding_an_unretired_spec_names_and_touches_gets_no_writer_session
          - member: the id followed by `'s`
            driven_by: tests/test_follow_up.py::test_a_finding_an_unretired_spec_names_and_touches_gets_no_writer_session
      - set: the forms of a `touches` entry that holds the file
        members:
          - member: the exact path
            driven_by: tests/test_follow_up.py::test_a_finding_an_unretired_spec_names_and_touches_gets_no_writer_session
          - member: a glob
            driven_by: "A `touches` entry holds the file only when it equals the path, so a glob never does."
      - set: the claims that leave a finding in the draft
        members:
          - member: a claim naming an unretired spec whose `touches` lack the file
            driven_by: "Any unretired spec the claim names owns the finding, whatever its `touches` hold."
          - member: a claim naming no spec, in an unretired spec's `touches`
            driven_by: "Any unretired spec whose `touches` hold the file owns the finding, whether or not the claim names it."
          - member: a claim naming a longer id that starts with an unretired id
            driven_by: "The claim names a spec when its id is a substring of the claim, so a longer id that starts with it counts."
          - member: a claim naming the finding's own layer
            driven_by: "The stack's own layers count as unretired specs outside the stack."
          - member: a claim naming a lower layer whose `touches` hold the file
            driven_by: "Only the finding's own layer is left out, so a claim naming another layer counts."
          - member: a claim naming a higher layer whose `touches` hold the file
            driven_by: "The layers are left out only from the finding's own index in `stack.layers` down, so a claim naming a higher layer counts."
          - member: a claim naming a spec in `done/`
            driven_by: "The specs in `done/` count as unretired specs."
          - member: a claim naming a spec discovery refuses for an inline mutant
            driven_by: "Discovery runs with `retired=True`, as `_origin_file_text` calls it, so a spec refused for an inline mutant counts."
      - set: the shapes of a group holding an owned finding
        members:
          - member: a group holding owned and unowned findings
            driven_by: "One owned finding sends its whole group past the writer."
          - member: a group whose every finding is owned
            driven_by: tests/test_follow_up.py::test_a_finding_an_unretired_spec_names_and_touches_gets_no_writer_session
    positive_case: >-
      The same `write` spy that sees no session for the owned group sees
      one session for the mixed group before it, and one for the higher
      layer's group after it. The first prompt carries each of the seven
      unowned claims, so the spy that finds no owned claim in it reads a
      prompt the writer was given.
  - claim: >-
      Each finding the first criterion leaves out joins `pooled` alone, one
      `Pooled` per finding, with a reason naming its owning spec's id and
      the finding's file. `emit` prints that reason on the `pooled` line
      `_pool` already writes. `finish.write_findings` then lists the
      finding with outcome `pooled` and that same reason. This holds for a
      group met once the writer sub-cap cannot cover another session. The
      witness drives one group with three owned findings, two owned by one
      spec and one by another, and one unowned finding. It meets that group
      after an earlier group's session left less than one more session. It
      reads exactly one finding in each `Pooled` that holds an owned one.
    witness: tests/test_follow_up.py::test_a_finding_an_unretired_spec_owns_is_pooled_alone_naming_that_spec
    wrong_versions:
      - "An owned finding is dropped from its group and joins no `Pooled`."
      - "The reason says an unretired spec owns the finding but names no id."
      - "The reason names the owning spec but not the file."
      - "The owned findings of a group join one `Pooled`, whose reason names only the first owner."
      - "The owned findings of a group join one `Pooled` per owner, each holding every finding that owner owns."
      - "Ownership is checked after the sub-cap check, so a group met past the sub-cap pools whole under the sub-cap's reason."
    covers:
      - set: the places an owned finding is listed
        members:
          - member: the `pooled` list
            driven_by: "An owned finding is dropped from its group and joins no `Pooled`."
          - member: the emitted `pooled` line
            driven_by: tests/test_follow_up.py::test_a_finding_an_unretired_spec_owns_is_pooled_alone_naming_that_spec
          - member: "`findings.json`, through `finish.write_findings`"
            driven_by: tests/test_follow_up.py::test_a_finding_an_unretired_spec_owns_is_pooled_alone_naming_that_spec
      - set: the owners of one group's findings
        members:
          - member: the first owner
            driven_by: "The reason says an unretired spec owns the finding but names no id."
          - member: a second, different owner
            driven_by: "The owned findings of a group join one `Pooled`, whose reason names only the first owner."
      - set: the findings one owner owns in one group
        members:
          - member: its first finding
            driven_by: tests/test_follow_up.py::test_a_finding_an_unretired_spec_owns_is_pooled_alone_naming_that_spec
          - member: a second finding of the same owner
            driven_by: "The owned findings of a group join one `Pooled` per owner, each holding every finding that owner owns."
    positive_case: >-
      The unowned finding in the owned findings' group is pooled with the
      sub-cap's reason, so the sub-cap was spent when the group was met.
      The earlier group's finding reads `follow_up` in the same
      `findings.json`, so the file lists a drafted finding as well as
      pooled ones.
---

## Context

Backlog item **b-cc87b1**, which cites `DESIGN.md` §4.2.1. Line numbers
below were read at `42107252`.

**What happened.** Batch 47's end review qualified an in-cell concern at
`saffron/finish.py:259`. Its claim said the origin spec "defers the fix to
`SA-0306`". `SA-0306` was unretired, outside the stack, and its `touches` held
`saffron/finish.py`. The writer still drafted `SA-0310` for $1.11, which
restated `SA-0306`'s criterion. `SA-0306` merged the next day (#941).

**Every qualified group meets the writer.** `write_follow_ups` walks
`qualification.groups` (`saffron/follow_up.py:372`). A group is pooled
before its session only for an earlier halt, a spent sub-cap, a stale probe
or no changed test path (`saffron/follow_up.py:373-405`). Then it reaches
`write(group, prompt)` (`saffron/follow_up.py:444`). Nothing reads the
spec files. `qualify._decide` files a finding `qualified` from its anchor and
probe alone (`saffron/qualify.py:275-289`).

**The spec files are already in hand.** `write_follow_ups` takes `specs_dir`
(`saffron/follow_up.py:289`). The batch passes the `.saffron/specs`
directory it exported at the pinned base (`saffron/cli.py:1856-1858`,
`saffron/cli.py:1979`). That directory holds the stack's own layers too.
Each layer's spec id is `graded_fields(...).spec_id`, as `top` reads it
(`saffron/follow_up.py:313`).

**Why "unretired", not "queued".** §4.2.1 calls a spec queued only while
no task at its `spec_sha` is in a state done with it (`DESIGN.md:495`,
`saffron/scheduler.py:1446-1449`). That reading needs the ledger. This
check reads the spec files alone, so a spec whose task already merged
still counts until it moves to `done/`.

**A pooled finding already reaches the operator.** `_pool` appends a
`Pooled` and emits `pooled <task key> <file>: <reason>`
(`saffron/follow_up.py:321-323`). `finish._layer_findings`, which
`write_findings` calls, remaps a `qualified` row to outcome `pooled`, with
the reason, when `_match_pooled` finds it in `pooled`
(`saffron/finish.py:297-312`, `saffron/finish.py:338-366`). The match reads lens, line and claim. The
probe check already splits a group and pools only its dropped findings
(`saffron/follow_up.py:384-397`). If `write_follow_ups` raises, the batch
pools each finding not already in `pooled`, so a finding pooled here is not
listed twice (`saffron/cli.py:1990-2009`).

**Measured over the finishes on this host.** `~/.saffron/batches/v0/finish/`
holds 75 `findings.json` files, batches 13 to 105. 140 findings there read
`follow_up` or `pooled` at a head whose `.saffron/specs` the home mirror
holds, across 41 batches. Each was matched against the unretired specs at
its own head, less that batch's layers. Specs the current intake refuses still
counted, as the intake of their day parsed them.

- The rule here, a claim naming an unretired spec whose `touches` hold the
  file, matches 3 findings. None would be a wrong skip. One is batch 47's,
  above. Two are batch 73's, at `saffron/spec_review.py:20` and
  `saffron/cli.py:1704`. Both claims say `SA-0354`'s diff carries
  `SA-0353`'s feature. The first was drafted as `SA-0357`. Its own Context
  found the code was `SA-0353`'s, said "there is no scope violation to
  fix here", and turned to another defect. `SA-0357` ended `ORPHANED`. The
  second pooled for its draft's `depends_on`.
- A claim naming any unretired spec matches 6. The other 3 would be wrong
  skips. Batch 48's two claims cite `SA-0304` as a docstring's source, and
  batch 30's names `SA-0272` beside a different file.
- A file in any unretired spec's `touches` matches 34.

## Problem

Before a group meets the writer, decide each of its findings against the
spec files. A finding is owned when its claim names an unretired spec's id
as a whole word. That spec's `touches` must also hold the finding's file
by `scope.matches`. An unretired spec is one `intake.discover_specs` finds
directly in `specs_dir`, with its default refusals, less every layer of
the stack. Read the spec files once for the stack, not once a group.

Pool each owned finding alone, as its own one-finding `FollowUpGroup`, with
a reason naming the owning spec's id and the file. Call the owner an
unretired spec outside the stack in that reason, never a queued one. Do this first for each
group, before the halt and sub-cap checks, so an owned finding always
carries its owner's reason. The group's other findings go on as today. A
group with none left goes no further.

Add the new reason to the module docstring's list of what pools a group.

## Out of scope

- **The origin item's `specs:` list.** A spec whose `## Context` first
  cites a backlog item that does not list it fails this repo's records
  test (`records/check.py:413-433`). The judge already runs the finishing
  suite on each draft and pools it on a second failure
  (`saffron/follow_up.py:513-534`). Seven pooled findings in batches 73,
  81, 96 and 103 carry that test as their reason. The reason names the
  test, not which record rule failed. Writing the
  list host-side would make core read this repo's backlog format, against
  §2.1, and `FINISH_TOUCHES` admits only `.saffron/specs/*.md`
  (`saffron/finish.py:50`). The item keeps that half.
- **`qualify.py`.** It holds no `specs_dir`, and threading one in edits
  `saffron/cli.py`. The finding stays `qualified` on its ledger row, and
  `findings.json` shows it `pooled` with its reason.
- **Specs merged to the default branch after the pinned base.**
  `next_spec_id` reads those for ids (`main_head`), but ownership reads
  `specs_dir` alone.
- **A spec that fails discovery.** It cannot run, so it owns nothing.
- **A spec whose task already merged but which is not yet retired.** Its
  file still sits in `specs_dir`, so it counts as an owner. `SA-0353` was
  one in batch 73. Reading the ledger's task states as §4.2.1 does is
  left out.
- **A halt.** Problem orders the check before the halt check too, and no
  witness drives a halt.
- **ADR 7.** Its section on the end review's exceptions says a qualified
  `concern` feeds a follow-up spec. This spec's own commit adds a hand
  edit there, an amendment dated 2026-11-26 naming b-cc87b1 and
  `SA-0440`. It says a finding an unretired spec outside the stack owns
  goes to the backlog pool. `CONTEXT.md`'s Backlog pool entry stays as it
  is, since its list of reasons is illustrative.
- **A claim that names its owner only in words.** The id must appear.

## Notes for the agent

**No criterion declares a mutant.** The ownership check is new code, and
its spelling is yours. So `witness` will report `skip`.

**The witnesses' arrangement.** Both extend `_build`'s `specs_dir` with
unretired specs outside the stack. A prototype used `SA-0103` touching
`src/a.py` and `src/b.py`, `SA-0104` touching `src/*.py` and `SA-0106`
touching `src/c.py`. It rewrote `done/SA-0105` to touch `src/b.py`. It
rewrote both layers' files, `one.md` and `SA-0102-two.md`, to touch
`src/a.py` and `src/b.py`. It added `inline.md`, id `SA-0120`, touching
`src/b.py` with an inline mutant, which discovery refuses. Its file name
keeps `next_spec_id` on `SA-0108`, then `SA-0109` for the higher layer's
group. That group is the lower layer's, on `src/b.py`, and its claim
names `SA-0102`. The second witness records a `qualified`
row for each finding with `Ledger.record_qualification`, then calls
`finish.write_findings` over the `pooled` list. Patch
`spec_review.SPEC_WRITER_SESSION_USD` to 1.0 and pass a `cap_usd` of 1.2,
so one $0.25 session spends the sub-cap. Import `follow_up` and `finish`
inside each test body, as the module's own docstring asks.

**Wrong versions the prototype measured.** Each wrong version above was
applied to the prototype and run against its own witness alone. All
sixteen failed it.
