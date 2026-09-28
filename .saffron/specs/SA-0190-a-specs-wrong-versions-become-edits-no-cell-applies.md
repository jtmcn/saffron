---
id: SA-0190
title: A spec's wrong versions become edits that no cell applies, so a witness they survive still ships
type: feature
priority: 1
depends_on: [SA-0187]
consumes:
  - saffron/phases/review.py:run_wrong_versions
  - saffron/phases/review.py:describe_wrong_versions
  - saffron/agents/prompts/wrong-version.md
touches:
  - saffron/cell/session.py
  - saffron/phases/review.py
  - saffron/intake.py
  - tests/test_session.py
  - tests/test_review.py
  - tests/test_intake.py
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
  - saffron/gates/**
  - saffron/probe.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/agents/**
  - saffron/phases/rebut.py
  - saffron/phases/implement.py
  - saffron/phases/package.py
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - tests/test_context.py
  - tests/test_worktree.py
  - tests/test_witness_gate.py
  - tests/test_probe_check.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 26
max_attempts: 3
max_turns: 200
risk: elevated
estimated_lines: 368
acceptance:
  - claim: >-
      `review.survivor_finding` takes an optional keyword `version`. Given
      one, the finding's claim is the sentence the notes give, naming the
      witness, the version, the edit's file and the criterion's claim.
      Without it, the claim is the sentence the function builds today. The
      witness compares both findings whole, every field included.
    witness: tests/test_review.py::test_a_wrong_versions_survivor_names_the_version_it_came_from
  - claim: >-
      A wrong version whose criterion's witness stays green under its edit
      is filed as an `adequacy` `blocker` whose claim names that version.
      Its probe is the edit, its `probe_verdict` is `survived`, and its line
      is where the edit's `find` begins at head. It anchors, so the task
      stops at `REBUTTING` and it is the one blocker in `rebuttal.json`. The
      witness drives two versions of one criterion, the first killed and
      the second surviving. The host ran that criterion's own witness node
      id alone for each. `wrong-versions.json` records `killed` and
      `survived`.
    witness: tests/test_session.py::test_a_wrong_version_its_witness_survives_is_rebutted_as_a_blocker
  - claim: >-
      After REVIEW applies every edit, `wrong-versions.json` holds each entry
      `review.run_wrong_versions` returned, in the spec's order. Every
      version there carries an `outcome` and a `summary`. The witness drives
      six versions over three of four criteria, with a criterion that
      declares none between the first two. The first criterion's versions are one the
      session could not express and an edit on a declared test path. The
      second's are an edit under which the `tests` gate answers `error`,
      then an edit the witness kills. The third's session fails, so both its
      versions are `unproven` with the entry's `error` as their summary.
      Each summary is compared whole, and each witness run's subset too.
      REVIEW emits `wrong versions: 6 declared, 3 expressed` after the
      criterion-probe line, and the task ends `READY_FOR_REVIEW`. A spec
      whose criteria declare no wrong version buys no such session, writes
      no such file and emits no such line.
    witness: tests/test_session.py::test_every_wrong_version_is_recorded_with_its_outcome_beside_the_criterion_probes
  - claim: >-
      Each wrong-version session runs in the critic cell after the criterion
      probes, with the tools, turn ceiling and budget cap a criterion-probe
      session holds. REVIEW enters one gate-only cell for criterion probes
      and wrong versions together, and applies the criterion probes first.
      It enters it when either list holds an edit, and none when neither
      does. The witness drives three cases: both lists with an edit, only
      the wrong versions with one, and neither. The sessions' cost is added
      to the task's spend.
    witness: tests/test_session.py::test_criterion_probes_and_wrong_versions_share_one_gate_only_cell_and_the_spend
  - claim: >-
      Parse refuses a mutant whose `find` text appears inside any wrong
      version of any criterion, its own or another's, as a
      `DisclosedMutantError` that carries the parsed spec. The message is
      the one a disclosing claim gets, with `the wrong versions of` and the
      holding criterion's witness in place of where the text sits. The
      witness drives two specs, one where the mutant's own criterion holds
      the text and one where a sibling does. In each, the holder comes
      before a later criterion. The witness compares each message whole.
    witness: tests/test_intake.py::test_a_mutant_a_wrong_version_discloses_is_refused_too
  - claim: >-
      A criterion probe its criterion's witness survives is still filed as a
      host-filed `adequacy` blocker and rebutted.
    witness: tests/test_session.py::test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker
    preserves: true
  - claim: >-
      Criterion-probe entries nothing could answer are still recorded
      `unproven` and file nothing.
    witness: tests/test_session.py::test_a_criterion_probe_nothing_could_answer_is_unproven_and_files_nothing
    preserves: true
---

## Context

Backlog item **b-7e69d0** is
`docs/backlog/b-7e69d0-the-host-probes-no-wrong-version-a-spec-lists-for-its-criteria.md`,
tier 1. This spec is the child half of a split. `SA-0187` is the parent. It
adds each criterion's `wrong_versions`, the session
`review.run_wrong_versions` that turns them into edits, and
`review.describe_wrong_versions`. Nothing calls either function until this
spec merges.

Every sentence below about current code was read at `a4299786` on
2026-09-28. `SA-0187` lands first and moves line numbers in
`saffron/phases/review.py`. Find each cited name by its name at the base
you are cut from.

**What `SA-0187` hands you.** `run_wrong_versions` takes the keywords
`run_criterion_probes` takes. It returns one dict per criterion whose
`wrong_versions` is non-empty, in the spec's order. Each holds `witness`,
`claim`, `cost_usd`, `error` and `versions`. Each member of `versions` holds
`version`, `edit` and `reason`, with `edit` a `Mutant`'s `model_dump()` or
`None`. `describe_wrong_versions(entries)` returns
`wrong versions: {declared} declared, {expressed} expressed`. Read both at
your base before relying on this paragraph.

**Where the criterion probes run.** REVIEW computes one `probe_budget`
(`saffron/cell/session.py:2635`). Inside the critic cell it calls
`review.run_criterion_probes` with `max_turns=spec.max_turns` and that
budget (`saffron/cell/session.py:2684-2698`). After the cell is torn down
it calls `_apply_criterion_probes` (`saffron/cell/session.py:2745-2760`). It
writes `criterion-probes.json` and emits `review.describe_criterion_probes`
when the list is non-empty (`saffron/cell/session.py:2762-2772`). Then it adds
the lenses' and the probe sessions' cost to `spent`
(`saffron/cell/session.py:2774-2779`). The list is bound early at
`saffron/cell/session.py:2531-2533`.

**How the edits are applied.** `_apply_criterion_probes`
(`saffron/cell/session.py:1561-1708`) pairs `spec.acceptance` with the
entries by position, strictly (`saffron/cell/session.py:1591`). An entry with no
edit is recorded `unproven`, with the summary "this session named no edit".
So is an edit `probe.probe_refusal` refuses, with that refusal as its summary
(`saffron/cell/session.py:1602-1612`). It enters no cell when nothing is
left. Otherwise it enters one gate-only cell through `critic_cell` with
`network=None` (`saffron/cell/session.py:1629-1647`). For each edit it calls
`witness_gate` over that one criterion, with the edit in its `mutant` field. It
reads the status into `outcome` and the summary into `summary`
(`saffron/cell/session.py:1678-1686`). A raise stops every later edit. A
survivor is built by `review.survivor_finding`, anchored against the
reviewed diff, and appended to the `adequacy` review
(`saffron/cell/session.py:1692-1708`).

**The survivor's claim names no wrong version.** `survivor_finding`
(`saffron/phases/review.py:506-528`) takes the criterion, the edit and the
file's content at head. Its claim starts with `HOST_FILED` and says the
witness "stayed green with the criterion's own edit". For a wrong version
that sentence hides which version survived. REBUT shows the implementer the
claim and the edit (`saffron/phases/rebut.py:151-163`).

## Problem

Run each wrong version's edit the way a criterion probe's edit runs, record
every outcome, and file a survivor as a blocker for REBUT.

1. **The session.** Call `review.run_wrong_versions` inside the critic cell,
   right after `run_criterion_probes`, with the same keywords and values.
   Bind its result early, beside `criterion_probes`, to an empty list.
2. **One gate-only cell.** Change `_apply_criterion_probes` to take a list
   of (criterion, entry) pairs in place of `entries` and its strict zip.
   Build that list at the call site. First pair each criterion-probe entry
   with its criterion. Then pair each member of each wrong-version entry's
   `versions` with its criterion. Pair the wrong-version entries with
   `[c for c in spec.acceptance if c.wrong_versions]`, strictly. Pass the
   version dicts themselves, so the outcome and summary written on each
   land in the record. Everything the function does to a pair stays as it
   is: the refusals, the one cell, the stop on a raise. A wrong-version
   entry whose `error` is set is not paired. Record each of its versions
   `unproven` at the call site, with that `error` as its summary. The
   summary "this session named no edit" is then left for a version its
   session answered with no edit.
3. **The survivor's claim.** Add a keyword `version: str | None = None` to
   `survivor_finding`. The call in `_apply_criterion_probes` passes
   `entry.get("version")`. A criterion-probe entry holds no such key, so its
   claim stays as it is.
4. **The record.** Write a non-empty wrong-version list to
   `wrong-versions.json` in the task directory, after the application and
   beside `criterion-probes.json`. Write nothing for an empty one. Emit
   `review.describe_wrong_versions(...)` as a REVIEW line after the
   criterion-probe line.
5. **The spend.** Add every wrong-version entry's `cost_usd` to `spent`,
   beside the criterion-probe sessions' cost.
6. **The disclosure check.** `parse_spec` refuses a mutant whose `find`
   appears in the body or in any claim (`saffron/intake.py:281-303`).
   `context.witnesses_block` now hands the implementer every wrong version
   too, so a `find` spelled there is disclosed the same way. After the
   claims, scan each criterion's `wrong_versions` in the spec's order. The
   first criterion holding a version that contains the `find` sets `where`
   to `the wrong versions of {witness}`, with that criterion's witness. The
   refusal and its message are otherwise unchanged. Between `SA-0187`'s
   merge and this one, no spec declares `wrong_versions`. The tracker rule
   that tells authors to use the field lands with this spec, so the gap
   never opens.

## Out of scope

- The session, its prompt and the entry's shape. `SA-0187` owns them.
- The source a survivor is filed under. It stays `adequacy`, and item
  b-9ed36d stays open. So a wrong version's survivor is credited to the
  `adequacy` lens in the ledger and the pull request body, as a criterion
  probe's is.
- A cap on sessions or witness runs. A spec with many wrong versions buys
  one session per criterion and one witness run per expressed version.
- `saffron/gates/**`. `witness_gate` is reused unchanged.
- The glossary and the design record. `CONTEXT.md`, `DESIGN.md`,
  `docs/agents/issue-tracker.md` and `.claude/agents/spec-writer.md` are
  edited by hand in this spec's pull request.

## Notes for the agent

**This change is new behaviour, so no criterion declares a mutant**
(§5.4.1). The call, the pairing, the record and the new scan have no
spelling at the tree base to pin. The `witness` gate reports `skip` for this spec.

**Each witness fails at the tree base without a collection error.** The
`version` keyword raises a `TypeError` there, and no `wrong-versions.json`
is written. A wrong version holding a mutant's text parses there too. Import any name this change adds inside the test body.

**Assert exact values.** Compare whole strings, whole dicts and whole
lists. Never assert a substring, a prefix or an `index()` order. Assert
every member of a set, and every argument a double records.

**Criterion 1's witness** goes in `tests/test_review.py`. Build one
criterion, one `Mutant` and a content string. Call `survivor_finding` twice,
without and with `version="the guard is removed"`. Compare each whole
`Finding` with one you build in the test. The claim with a version is
exactly this, with each name replaced by its value:

```
f"{review.HOST_FILED}{criterion.witness} stayed green with the spec's "
f"wrong version {version!r} applied to {edit.file} as an edit. The claim "
f"was {criterion.claim!r}, and only that witness ran under the edit."
```

The claim without one is the sentence at `saffron/phases/review.py:520-524`,
unchanged. These fail it:

- the version appended to today's sentence
- the version quoted without `!r`
- today's sentence changed as well

**The session witnesses.** Put criteria 2 to 4 in `tests/test_session.py`,
after the criterion-probe witnesses. Drive each through `_drive` with
`_PROBE_POLICY` and `gates=("tests",)`. Script the turns with
`_probe_turns`, the criterion-probe turns first and then the wrong-version
turns. Stub the probe cell with `_stub_probe_gates` and `subsets=`, and
the collected set with `_stub_the_runtime`'s `gate_cell_suite`. Build
criteria inside each test body. Write one small helper for a wrong-version
answer beside `_probe_answer`. It returns the text of one `<output>` block
holding `{"versions": [...]}`. Table the rows a witness drives and loop
over them in one plain `def`.

**Criterion 2's witness.** One criterion, witness `t.py::a`, two wrong
versions. Its criterion-probe session names no edit. Its wrong-version
session names two edits. The probe cell's `tests` runs answer `fail` for
the first and `pass` for the second. The second edit anchors by the token
rule, as
`test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker`
places one (`tests/test_session.py:7363-7478`). That is `find` on line 3 of
`src/x.py`, outside `_ANCHORING_DIFF`'s hunk. Reuse that test's
`_read_at_head` override and `_rebuttable`. Script REBUT as it does, with
`rebut_commits=0` and `_CLAIMED_FIX`. Assert
`subsets == [["t.py::a"], ["t.py::a"]]`, the state, and the whole blocker
in `rebuttal.json`, its claim built from criterion 1's literal. Assert the
whole entry in `wrong-versions.json`. These fail it:

- the survivor filed with the criterion probe's wording
- a claim that quotes the criterion's first wrong version, not the one
  that survived
- the survivor filed under a lens other than `adequacy`, or as a `concern`
- the whole suite run in place of the one witness
- the survivor left unanchored, or anchored with the critic cell's reader

**Criterion 3's witness.** Four criteria, in order:

| criterion | witness | wrong versions | the wrong-version session answers |
|---|---|---|---|
| A | `t.py::a` | two | null with a reason, then an edit on `spec/t.py` |
| B | `t.py::b` | none | no session |
| C | `t.py::c` | two | an edit on `src/x.py`, then another on `src/x.py` |
| D | `t.py::d` | two | `"not a block at all"` |

Every criterion-probe session names no edit. The probe cell's `tests` runs
answer, in order, `error` and then `fail` on `t.py::c`. Assert
`subsets == [["t.py::c"], ["t.py::c"]]`. Assert the whole list read from
`wrong-versions.json`. Build each expected summary at your base as the code
builds it, from these sources:

- the unexpressed summary, "this session named no edit"
- the refusal, built at saffron/probe.py:165-166
- the error summary, built at saffron/gates/core/witness.py:228-239
- the killed summary, built at saffron/gates/core/witness.py:284-293
- D's two summaries, each "not the schema: no <output> block in the
  response", the entry's own `error`

Take every line of `cell.watched` that starts with `REVIEW: criterion
probes:` or `REVIEW: wrong versions:`. Assert that list whole, the
criterion-probe line first. Then drive a spec whose
criteria declare no wrong version. Assert no such file, no such line, and
a system prompt count of five plus one per criterion. These fail it:

- the record written before the edits are applied
- a stop after the `error`
- a version the session could not express dropped from the record
- an edit on a declared test path applied
- the versions flattened into one list in the file
- a zip of `spec.acceptance` with the wrong-version entries, which pairs
  C's versions with B's witness
- a failed session's versions summarised as "this session named no edit"
- the wrong-versions line emitted before the criterion-probe line
- an empty file written for a spec with no wrong versions

**Criterion 4's witness.** Wrap `session.critic_cell` in a spy that
records each call's `network` and then calls the real one. The precedent
is `tests/test_session.py:3793-3803`. The list below was derived by
reading, not by a run. The lens gate table's cell is the first entry
(`saffron/cell/session.py:1350-1353`). REVIEW's critic cell is the second,
on the network bound at `saffron/cell/session.py:1748`.
The adequacy probe path enters no cell here. With no probe left it
returns first (`saffron/cell/session.py:1440-1441`). The apply cell is the
third (`saffron/cell/session.py:1629-1640`). Every `tests` run in the probe
cell answers `fail`, so every edit is killed. No survivor routes the task
to REBUT, so no verdict cell joins the list. For each of the three cases,
assert the whole list. With either list holding an edit it is
`[None, "saffron-cells", None]`, and with neither it is
`[None, "saffron-cells"]`. In the first case the criterion probe and the
wrong version each name an edit, and `cell.mutated` lists the criterion
probe's edit first. Compare each wrong-version session's `tools`,
`max_turns` and `max_budget_usd` with the criterion-probe session's, and its
container with the critic container. Give the wrong-version turn its own
cost, and assert `outcome.spent_usd` with `pytest.approx` against the sum
of every turn's cost. These fail it:

- a second gate-only cell for the wrong versions
- the wrong versions applied before the criterion probes
- a cell entered for two lists that hold no edit
- the session asked after the critic cell is torn down
- the lens's own budget in place of `probe_budget`
- the sessions' cost left out of `spent`

**Criterion 5's witness** goes in `tests/test_intake.py`, beside
`test_a_mutant_a_sibling_claim_discloses_is_refused_too`
(`tests/test_intake.py:492-513`). Table the two specs and loop over them
in one plain `def`. In each, one criterion declares a mutant whose `find`
is `CEILING = 60`. In the first, that criterion's own `wrong_versions`
holds `"a CEILING = 60 that stays at 60"`, and a trailing criterion holds
no version. In the second, the holding sibling comes first and the
mutant's own criterion last, declaring a version without the text. So
naming the last criterion's witness fails both rows. Neither body nor claim holds the text. Catch the error, and
assert its type is `DisclosedMutantError`, its `spec.id`, and `str()` of
it whole. Build the expected message from the literal at
`saffron/intake.py:298-302`. These fail it:

- a scan of the mutant's own criterion alone
- a version compared with `==` in place of containment
- a plain `SpecError`, which loses the spec `scheduler._retired_ids` reads
- `the wrong versions of` naming the mutant's witness for a sibling's text

**The existing witnesses stay green.** Criteria 6 and 7 name
`SA-0120`'s witnesses. The nine `_spec(acceptance=` calls declare no wrong
version, so they buy no new session and write no new file.

**What the witnesses leave undriven.** A raise that stops later edits,
where a criterion probe's raise leaves every wrong version `unproven`. A
cell that never comes up. A repo with no `tests` gate. These follow
`SA-0120`'s paths unchanged, and its own notes leave them undriven too.

**What the added work costs.** Each criterion that declares wrong
versions adds one session at the criterion-probe session's cap and turn
ceiling. 246 criterion-probe sessions recorded under
`~/.saffron/batches/v0/` on 2026-09-28 cost $0.23 at the median and $0.68
at most. A spec with five such criteria then adds about $1.15 to $3.40.
Each expressed version adds one run of one witness in the gate-only cell
the criterion probes already enter. That costs wall time, not money, and
no second cell starts.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense, a hedge or
a sentence over 25 words. Keep each docstring within ten lines.

**Size.** `saffron/cell/**` is in `.saffron/policy.yaml`'s `elevate_on`, so
`size` blocks at the `feature` ceiling of 3000 tokens
(`saffron/gates/core/size.py:26`). `SA-0120` built the application path.
Its cell commit `c8615d8b` measured 1928 changed tokens with `size_gate`'s
own count on 2026-09-28, run as below. `size._token_counts` splits that as
569 in `session.py`, 325 in `review.py` and 1034 in `tests/test_session.py`.

```
git show --format= c8615d8b | uv run python -c "import sys; from saffron.gates.core import size; print(size._changed_lines(sys.stdin.read()))"
```

This change adds about 55 lines to `session.py` and `review.py` and about
275 to the tests. The disclosure scan adds about 7 lines to `intake.py` and
31 to `tests/test_intake.py`. Sibling cells landed at 1.4 to 1.7 times
their estimates, so expect 2050 to 2500 tokens. Keep the intake test to
its two tabled rows. Share one helper across
the three session witnesses, table their rows, and keep comments to one or
two lines.

**Commit as each witness passes**, before the full suite runs.
Uncommitted work dies with the cell.

**Rename no existing test.** `census` reads a rename as a removal.
