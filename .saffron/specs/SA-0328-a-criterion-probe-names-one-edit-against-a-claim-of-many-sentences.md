---
id: SA-0328
title: "A criterion probe names one edit against a claim of up to twelve sentences, so the seats still find the sentences it left"
type: feature
priority: 1
estimated_lines: 290
depends_on: []
touches:
  - saffron/phases/review.py
  - saffron/cell/session.py
  - saffron/agents/prompts/criterion-probe.md
  - tests/test_review.py
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
  - saffron/probe.py
  - saffron/intake.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/gates/**
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/agents/context.py
  - saffron/agents/artifacts.py
  - saffron/agents/findings.py
  - saffron/agents/prompts/turns/**
  - saffron/agents/prompts/wrong-version.md
  - saffron/agents/prompts/review-adequacy.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-conventions.md
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/implement.md
  - saffron/agents/prompts/rebut-verdict.md
  - saffron/phases/rebut.py
  - saffron/phases/implement.py
  - saffron/phases/package.py
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/cell/proxy.py
  - tests/test_context.py
  - tests/test_rebut.py
  - tests/test_witness_gate.py
  - tests/test_probe_check.py
  - tests/test_intake.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 52
max_attempts: 3
max_turns: 220
risk: elevated
acceptance:
  - claim: >-
      `review.run_criterion_probes` keeps its keywords and buys one fresh
      session per criterion, in the spec's own order, a `preserves` one
      included. The system prompt it builds ends with `## The diff`, the
      diff, `## The claim` and the claim, names no witness node id and no
      other criterion's claim, names `probes` as the one key of the answer,
      states the value of `review.CRITERION_PROBE_CEILING`, which is 16, and
      carries no unfilled `{ceiling}` slot. Each entry carries `witness`,
      `claim`, `cost_usd`, `error` and `probes`. Each probe carries the
      `sentence`, the `edit` and the `reason` the session gave, word for
      word, in the session's own order. The witness drives one session
      answering three probes, two with an edit and one with a null edit, and
      one answering one probe with a null edit. It compares each entry whole
      and the prompt's tail whole.
    witness: tests/test_review.py::test_a_criterion_probe_session_names_one_edit_per_sentence_of_the_claim_it_is_shown
    wrong_versions:
      - The host splits the claim into sentences itself and asks one session per sentence.
      - The entry keeps the first answer alone, under `edit` and `reason` as today.
      - A probe with a null edit is dropped from `probes`.
      - The probes are recorded sorted by sentence rather than in the session's order.
      - The prompt states a ceiling other than the schema's.
      - A probe's `sentence` is not recorded.
      - The `{ceiling}` slot is left in the prompt as text.
  - claim: >-
      A criterion-probe session whose first answer is not the schema is
      resumed once, in that same session, with a prompt carrying that
      answer's own error and then `EXTRACTION_PROMPT`. The re-prompt keeps
      the first turn's system prompt and tools, its budget is what the first
      turn left of the ceiling, and it passes the first turn's cost as
      `last_cost_usd`. Its answer is the record, and the entry's cost is both
      turns'. That holds for six first answers: one with no `<output>` block,
      one whose JSON does not parse, one with no `probes` key, one whose
      probe carries no `sentence`, one with zero probes, and one with 17
      probes. A first answer with exactly one probe and one with exactly 16
      are the schema, so neither is re-prompted.
    witness: tests/test_review.py::test_a_criterion_probe_answer_that_is_not_the_schema_is_reprompted_once_in_its_own_session
    wrong_versions:
      - The re-prompt starts a fresh session instead of resuming the failed one.
      - The re-prompt sends the extraction prompt alone, without the error.
      - A report with zero probes is accepted.
      - A report with 17 probes is accepted.
      - A report with 16 probes is refused.
      - A probe with no `sentence` is accepted.
      - The re-prompt is given the whole ceiling, not what the first turn left.
      - The entry's cost is the re-prompt's alone.
      - The re-prompt's answer is read from the first turn's text.
  - claim: >-
      A criterion whose session gave nothing usable is recorded with `error`
      set and `probes` empty, and every later criterion is still asked. That
      holds for three sessions. One fails outright with `AgentFailed`, is
      never re-prompted, and its error is the failure's text. One answers
      outside the schema twice, and its error opens
      `not the schema, even after a re-prompt: ` and carries the second
      answer's own cause. One fails on its re-prompt, and its error opens
      `re-prompted once, then ` and its cost is both turns'. A fourth
      criterion after them is asked and answers. No re-prompt follows a first
      turn that left less of the ceiling than it spent, or one carrying no
      session id, and each is recorded with `error` set and `probes` empty.
    witness: tests/test_review.py::test_a_criterion_whose_session_answers_nothing_usable_is_an_error_with_no_probes_and_the_next_is_still_asked
    wrong_versions:
      - An `AgentFailed` first turn is re-prompted.
      - An errored criterion keeps a probe with a null edit, the way an unresolved wrong version keeps its versions.
      - The loop stops at the first errored criterion.
      - The error after a failed re-prompt names the first answer's cause, not the second's.
      - A first turn that left less than it spent is re-prompted anyway.
      - A first turn with no session id is re-prompted anyway.
  - claim: >-
      After REVIEW applies every edit, `criterion-probes.json` holds each
      entry `run_criterion_probes` returned, in the spec's order, and every
      probe there carries an `outcome` and a `summary`. The first run under
      each applied edit is that criterion's own witness node id alone. The
      witness drives three criteria. The first's session names three probes:
      one its witness kills and two it survives, one anchoring to the diff
      and one not. Each survivor is filed as a host-filed `adequacy` blocker
      carrying its own edit as `probe` and `survived` as `probe_verdict`,
      both reach `rebuttal.json`, and the task ends `REBUTTAL_UNJUDGED`. The
      second's session names three probes: one its own witness kills, one
      with a null edit and one on a declared test path. The last two are
      `unproven`, and the third carries its `refusal`. The third criterion's
      session fails, so its entry has `error` set and `probes` empty, and
      nothing of it is applied. The first criterion also declares one wrong
      version, whose edit its witness kills. Every summary is compared
      whole: a probe's names a `criterion probe` and the version's names a
      `wrong version`. REVIEW emits one line reading `criterion probes: 4
      named over 3 criteria, 1 unnamed, 1 refused; no session answered: `
      and the third criterion's witness, before the wrong-version line.
    witness: tests/test_session.py::test_every_probe_a_session_names_is_applied_under_its_own_criterion_and_each_survivor_blocks
    wrong_versions:
      - Only the first probe of each entry is paired with its criterion.
      - Every probe is paired with the first criterion.
      - A probe's outcome is written on the entry, so the last probe's outcome overwrites the others'.
      - An errored entry is paired as a probe with a null edit, so it is recorded `unproven`.
      - A second survivor of one criterion files no finding, since one already did.
      - A probe is judged under the noun `wrong version`.
      - The REVIEW line counts entries, not probes.
      - The REVIEW line names no unanswered witness.
  - claim: >-
      `review.describe_criterion_probes` returns `criterion probes: ` then
      the named count, ` named over `, the entry count, ` criteria, `, the
      unnamed count, ` unnamed, `, the refused count and ` refused`. A probe
      with an edit and no `refusal` is named, one with a null edit is
      unnamed, and one carrying a `refusal` is refused. The line then adds
      `; no session answered: ` and the witness of every entry whose `error`
      is set, in entry order, and adds nothing when none is. The witness
      drives four entries: one with two named probes and one unnamed, one
      with one refused probe, and two with `error` set and no probes. It
      compares that line whole, and a second line over the first entry
      alone.
    witness: tests/test_review.py::test_the_criterion_probe_line_counts_edits_over_criteria_and_names_the_unanswered
    wrong_versions:
      - A refused probe is counted as named too.
      - The entry count leaves out an entry with no probes.
      - An errored entry's witness is left off the tail.
      - "The tail is added with no errored entry, so the line ends in `no session answered: `."
      - The two errored witnesses are joined in reverse order.
  - claim: >-
      Each criterion-probe session still runs in the critic cell after the
      lenses, with a lens's tools and ceiling, and is shown one claim and the
      diff, never a witness node id or another criterion's claim.
    witness: tests/test_session.py::test_each_claim_is_asked_of_its_own_session_that_is_never_shown_a_witness
    preserves: true
  - claim: >-
      A criterion probe its criterion's witness survives is still filed as a
      host-filed `adequacy` blocker and rebutted, anchored or not.
    witness: tests/test_session.py::test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker
    preserves: true
  - claim: >-
      A probe its criterion's witness kills is still `killed` and files
      nothing. One under which the `tests` gate answers `error` is still
      `error`, with the gate's own summary, and stops nothing after it.
    witness: tests/test_session.py::test_a_killed_or_errored_criterion_probe_files_nothing_and_stops_nothing
    preserves: true
---

## Context

Backlog item **b-78a590**, under `DESIGN.md` §5.4.1 and §5.5.1. Every line
below was read at `2db95118`.

**What the loop measured.** The spec loop's runs 49 and 50 each ranked
this third (`docs/evidence/2026-10-27-spec-loop-skill-feedback-run-49.md:99`,
`docs/evidence/2026-10-29-spec-loop-skill-feedback-run-50.md:94`). Run 50
counted nine witness gaps the seats found and the in-cell critic missed,
five of them after REBUT. On #996 the critic raised six adequacy blockers
and REBUT fixed all six. The Spec seat then ran 43 probes over the same six
claims and five survived
(`docs/evidence/2026-10-29-spec-loop-skill-feedback-run-50.md:19-20`).
`SA-0327`'s six claims run 6, 2, 10, 10, 12 and 8 sentences. Each got one
edit (`~/.saffron/batches/v0/SA-0327/criterion-probes.json`, six entries,
one `edit` each, two `survived`). Each seat survivor was a sentence of a
claim the cell probed, at a different sentence.

**What one session is asked today.** `criterion-probe.md` asks for "the
smallest edit to the source that would make the claim false"
(`saffron/agents/prompts/criterion-probe.md:2-3`). It asks for one object
with two keys, `reason` and `edit`
(`saffron/agents/prompts/criterion-probe.md:31-36`). Its tail is
`## The diff`, `{diff}`, `## The claim`, `{spec}`
(`saffron/agents/prompts/criterion-probe.md:50-56`).
`criterion_probe_prompt` fills `spec` with the claim, `diff` and
`standing_instructions` (`saffron/phases/review.py:425-443`).
`build_system_prompt` formats every other slot by name
(`saffron/agents/context.py:316-321`), which is how `wrong_version_prompt`
fills `{wrong_versions}` (`saffron/phases/review.py:542-566`).

**How the answer is read today.** `_ProbeAnswer` is `edit` and `reason`,
with `extra="forbid"` (`saffron/phases/review.py:412-419`).
`run_criterion_probe` runs one turn, files an `AgentFailed` as the error,
and files an answer the schema refuses as `not the schema: ` with no
re-prompt (`saffron/phases/review.py:446-480`). Its docstring says why: a
criterion probe "costs one claim, where a lens costs a whole remit"
(`saffron/phases/review.py:458-459`). `run_criterion_probes` calls it once
per criterion and files `witness`, `claim`, `edit`, `reason`, `cost_usd` and
`error` (`saffron/phases/review.py:483-528`). `describe_criterion_probes`
prints `criterion probes: {named} named, {unnamed} unnamed`
(`saffron/phases/review.py:531-536`).

**The shape this spec mirrors.** `run_wrong_versions` buys one session per
criterion that declares versions (`saffron/phases/review.py:629-695`). An
`AgentFailed` turn is filed through `_unresolved_wrong_versions`
(`:676-679`). Any other turn goes through `_parse_or_reprompt` with
`_parse_wrong_version_report` (`:680-688`), and an error is filed through
`_unresolved_wrong_versions` too (`:689-691`). `_parse_or_reprompt` resumes
the same session once with the error and `EXTRACTION_PROMPT`, on the budget
the first turn left (`saffron/phases/review.py:235-291`). It refuses a
re-prompt given less than the failed turn spent, or one with no session id
(`:259-263`). Its docstring names `run_lens` and `run_wrong_versions` as its
callers (`:247`).
`_WrongVersionReport` holds `versions`, a list of `_ProbeAnswer`
(`saffron/phases/review.py:569-575`). `_parse_wrong_version_report` reads
the block, then the schema, then the count (`:617-626`).
`_resolved_wrong_versions` pairs each declared version with its answer by
position (`:593-614`). `describe_wrong_versions` counts every version across
every entry, then names the witness of each entry whose `error` is set
(`:698-719`).

**How the edits are applied.** REVIEW calls `run_criterion_probes` inside
the critic cell with `probe_budget` (`saffron/cell/session.py:3252-3264`),
then `run_wrong_versions` (`:3267-3279`). After the lens probes it pairs
`spec.acceptance` with the criterion-probe entries by position, strictly
(`saffron/cell/session.py:3323-3326`). It pairs each wrong-version entry's
`versions` with its criterion, and writes `error` on each version of an
entry whose `error` is set (`:3327-3336`). `_apply_criterion_probes` takes
the pairs (`saffron/cell/session.py:1942-1968`). A pair whose `edit` is
`None` is `unproven` with "this session named no edit" (`:1987-1989`). One
`probe.probe_refusal` refuses is `unproven` with its `refusal` written
beside (`:1990-1994`). For each remaining pair it runs `witness_gate` over
that one criterion, with the edit as its mutant (`:2063-2071`). The edit
noun is `wrong version` when the pair's dict has a truthy `version`, and
`criterion probe` otherwise (`:2068-2070`). The gate's summary names that
noun (`saffron/gates/core/witness.py:288-312`). The outcome and summary land
on the pair's own dict (`saffron/cell/session.py:2072-2073`). A survivor
becomes a finding through `survivor_finding` with `version=entry.get("version")`
(`:2087-2089`), then a second ask of the whole `tests` gate (`:2099-2110`).
REVIEW writes `criterion-probes.json` and emits `describe_criterion_probes`
when the list is non-empty (`saffron/cell/session.py:3361-3369`). It writes
the wrong-version record after it (`saffron/cell/session.py:3373-3381`), and
adds every entry's `cost_usd` to `spent` (`saffron/cell/session.py:3386-3390`).

**Who reads the record.** Only `saffron/cell/session.py:3362` names
`criterion-probes.json` under `saffron/`. `saffron/task.py:1276-1280` and
`saffron/report/pr_body.py:644-650` read `wrong-versions.json` alone.

**The tests that read it.** In `tests/test_session.py`, `_probe_answer`
builds one `{"edit", "reason"}` block (`:11621-11622`) and `_probe_turns`
puts one such turn per criterion after the lenses (`:11641-11653`). Six
tests read the record or pin its REVIEW line (`tests/test_session.py:11790`,
`:11807`, `:11916`, `:12122`, `:12187`, `:12748`, `:12977`). In
`tests/test_review.py`, `_probe_text` builds the same block (`:1239-1240`),
and one test drives `run_criterion_probes` on an `AgentFailed` and a
refused answer, asserting no re-prompt (`:1263-1296`). The wrong-version
test calls `run_criterion_probes` with three null answers (`:1467-1480`).

## Problem

A criterion probe names one edit against a claim of up to twelve sentences,
so the seats still find the sentences it left.

1. **The prompt.** Rewrite `saffron/agents/prompts/criterion-probe.md`.
   Keep the `{vocabulary}`, `{standing_instructions}`, `{diff}` and `{spec}`
   slots, and keep the tail `## The diff`, the diff, `## The claim`, the
   claim. Ask the session to list the sentences of the claim it is shown, in
   the claim's order, and to name one edit per sentence. Add a `{ceiling}`
   slot and state that the list holds at most that many answers. The answer
   is one object with one key, `probes`, a list with one object per
   sentence. Each holds `sentence`, the sentence quoted from the claim,
   `edit`, the `file`, `find` and `replace` object or null, and `reason`. A
   sentence the session cannot falsify with one edit gets a null edit and a
   reason, as a wrong version it cannot express does. The host does not
   split the claim. The sentence list is the session's own.
2. **The schema.** In `saffron/phases/review.py` add
   `CRITERION_PROBE_CEILING = 16` at module scope. Add `_SentenceProbe`, a
   `_ProbeAnswer` with a `sentence: str` field. Add `_CriterionProbeReport`
   with `extra="forbid"` and one field, `probes`, a list of
   `_SentenceProbe`. The list is refused when empty or longer than the
   ceiling. Add `_parse_criterion_probe_report(text)`, which reads
   the `<output>` block then the schema, raising `ValueError` or
   `ValidationError` as `_parse_wrong_version_report` does. Keep
   `_ProbeAnswer`, since `_WrongVersionReport` is built on it.
3. **The prompt fill.** `criterion_probe_prompt` fills `ceiling` with the
   constant's value, as a string, beside `diff` and `standing_instructions`.
4. **The session.** Rewrite `run_criterion_probes` on `run_wrong_versions`'s
   shape, with the same keywords it takes today, and delete
   `run_criterion_probe`. One fresh session per criterion, every entry, in
   the spec's order. An `AgentFailed` turn files an entry with `error` the
   failure's text, `probes` empty and the turn's cost. Any other turn goes
   through `_parse_or_reprompt` with `_parse_criterion_probe_report`. An
   error files an entry with that error, `probes` empty and the summed cost.
   An answer files `probes` as a list of `{"sentence", "edit", "reason"}` in
   the session's order, with `edit` the `Mutant`'s `model_dump()` or
   `None`. Every entry carries `witness`, `claim`, `cost_usd`, `error` and
   `probes`. Say in the docstring why the re-prompt is now paid for: the
   session covers a whole claim, not one edit. Name it in
   `_parse_or_reprompt`'s docstring beside the two callers it names today.
5. **The line.** Rewrite `describe_criterion_probes` to the line criterion 5
   gives, counted over every probe across every entry the way
   `describe_wrong_versions` counts versions.
6. **The pairing.** In `saffron/cell/session.py`, replace the strict zip
   that builds `pairs` with a loop. It walks `zip(spec.acceptance,
   criterion_probes, strict=True)` and appends `(criterion, probe)` for
   each member of the entry's `probes`. Pass the probe dicts themselves, so
   each outcome and summary lands in the record. An entry whose `error` is
   set has no probes, so it pairs nothing and needs no other write, unlike a
   wrong-version entry. Leave the edit noun expression as it is: a probe
   carries `sentence` and never `version`, so it reads `criterion probe`,
   and a version still reads `wrong version`. Leave `survivor_finding`'s
   call, the second ask and the record writes as they are. Several survivors
   of one criterion each file a finding, since each pair does.
7. **Docstrings.** `_apply_criterion_probes`'s docstring says `pairs` holds
   one pair per probe of each entry. `run_criterion_probes`'s says what step
   4 says. Each stays within ten lines.
8. **Existing tests.** Rewrite the helpers and the tests the notes list to
   the new shape, under their existing names.

## Out of scope

- A session shown the witness and asked for the edits it would not notice.
  The record names it as the next arm, and it waits on this one's number.
- The wrong-version session, its prompt, its schema and
  `wrong-versions.json`. They are the shape this spec mirrors, not its
  subject.
- The survivor path. `survivor_finding`, the second ask of the whole
  `tests` gate, `rebut._blocker_line` and `rebut._guarded_blockers` stay as
  they are. A probe's survivor claim still reads "the criterion's own edit".
- The turn prompt `saffron/agents/prompts/turns/criterion-probe.md`. Its
  text, "Name the edit now", still serves a session asked for a list.
- The pull request body. `pr_body.py` reads `wrong-versions.json` alone, and
  no body line reads `criterion-probes.json`.
- Any `saffron/gates/**` change. `witness_gate` is reused unchanged, one
  criterion and one edit per call.
- A ceiling on sessions or on witness runs beyond the 16 answers per claim.
  A spec with six claims of 16 sentences buys six sessions and up to 96
  witness runs.
- The glossary and the design record. See the notes.

## Notes for the agent

**This change is new behaviour, so no criterion declares a mutant**
(§5.4.1). The schema, the re-prompt, the pairing loop and the line have no
spelling at the tree base to pin. `witness` reports `skip` for this spec.

**Records amended by hand.** Two protected sentences were amended at
`2db95118`, ahead of this cell, so neither goes stale under it. `DESIGN.md`
§5.4.1's paragraph "An edit a spec could not declare" is at
`DESIGN.md:1118-1120`. It now reads: the host "asks one fresh session per
acceptance claim for one edit per sentence of that claim (`SA-0113`,
`SA-0328`). Each edit is the smallest that would make its sentence false,
and a session names at most sixteen". `CONTEXT.md` §4's **Criterion probe**
entry is at `CONTEXT.md:517-520`. It now opens "A find-and-replace edit a
fresh session names to make one sentence of an acceptance claim false". It
adds "It names one edit per sentence of the claim, at most sixteen
(`SA-0328`)". Both files are `forbidden`.

**Existing tests keep their names.** `census` reads a renamed or deleted
test as a removal on every attempt. Rewrite these to the new shape under
their existing names:

- `tests/test_session.py`: `_probe_answer` (`:11621`) returns one
  `{"probes": [...]}` block holding one probe, so the tests that script one
  answer keep working. Give it a `sentence` argument with a default. Then
  rewrite these six.
  `test_the_record_pairs_each_claim_with_the_edit_its_own_session_named`
  (`:11756`) reads the edit and the reason off the entry. It pins the old
  line at `:11807`.
  `test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker`
  (`:11846`) reads `outcome` off the entry at `:11916`. So do
  `test_a_killed_or_errored_criterion_probe_files_nothing_and_stops_nothing`
  (`:12064`, `:12122`),
  `test_a_criterion_probe_nothing_could_answer_is_unproven_and_files_nothing`
  (`:12136`, `:12187`) and
  `test_a_survivor_whose_whole_suite_cannot_answer_keeps_todays_blocker`
  (`:12639`, `:12748`).
  `test_every_wrong_version_is_recorded_with_its_outcome_beside_the_criterion_probes`
  (`:12816`) pins the old line at `:12977`. Each now reads
  `entries[i]["probes"][0]`, and each pinned line takes the new form:
  `criterion probes: 1 named over 2 criteria, 1 unnamed, 0 refused` at
  `:11807` and `criterion probes: 0 named over 4 criteria, 4 unnamed, 0
  refused` at `:12977`. Every other test that scripts a probe turn through
  `_probe_answer` keeps working once the helper returns the new block.
- `tests/test_review.py`: `_probe_text` (`:1240`) returns the same block.
  `test_a_session_that_answers_nothing_usable_is_recorded_and_the_next_is_still_asked`
  (`:1263`) scripts one refused answer and asserts no re-prompt. Under the
  new `run_criterion_probes` that answer is re-prompted, so script a second
  refused answer and assert the error after the re-prompt and `probes`
  empty. `test_each_criterion_with_wrong_versions_gets_one_session_that_turns_each_into_an_edit`
  (`:1467-1480`) scripts three null answers through `_probe_text`, and
  keeps working once the helper returns the new block.

**The prompt is living prose.** The `prose` gate blocks
(`.saffron/policy.yaml:24`) and counts Markdown under
`saffron/agents/prompts/` by the style rules (`.saffron/gates/prose.py:44`).
The base it subtracts is per file and per rule. Write the new text to the
rules: no em-dash, semicolon, contraction, perfect tense, hedge or sentence
over 25 words. `build_system_prompt` runs `str.format` over the
template's parts (`saffron/agents/context.py:316-321`), so a literal brace
in the prompt breaks it. Write the JSON shape in words and backticks, or
double the braces.

**Import inside the test body** any name this change adds, such as
`CRITERION_PROBE_CEILING`. `revert` re-runs each new test with the source
reverted. A module-scope import of a new name makes that run a collection
error, which `revert` reads as `skip`.

**Each new witness fails at the tree base.** Criterion 1's reads `probes`
off an entry that has none. Criterion 2's drives a re-prompt that never
fires. Criterion 3's reads `probes` and an error the base never writes.
Criterion 4's reads `probes` off the record and a line the base never
emits. Criterion 5's compares a line the base never prints.

**The witnesses.**
- Criterion 1 follows `_probe_agent` (`tests/test_review.py:1244-1260`) and
  records each session's `options`. It drives two criteria, and the second
  is `preserves=True`, as `tests/test_session.py:11669-11673` builds one.
  The first claim has three sentences, and the three probes quote them, one
  each. A host that split the claim would buy three sessions for it. Assert
  `len(record) == 2`: exactly two sessions, one per criterion. Script
  the three sentences out of alphabetical order, so a record sorted by
  `sentence` differs from the session's order. That is what excludes the
  sorted wrong version. Every probe test at base shows a one-sentence claim
  (`tests/test_review.py:1267-1270`), so this one is new. Compare the system
  prompt's tail the way `_expected_wrong_version_tail` does
  (`tests/test_review.py:1310-1320`). Compare each entry with `==` against a
  dict, with `pytest.approx` for `cost_usd`.
- Criterion 2 follows
  `test_a_wrong_version_answer_that_is_not_the_schema_is_reprompted_once_in_its_own_session`
  and asserts the re-prompt's recorded `prompt`, `options` and `kwargs`:
  `resume` is the first turn's session id, `last_cost_usd` its cost,
  `max_budget_usd` the ceiling less that cost. Drive six first answers that
  are re-prompted and two that are not, each on its own criterion, in one
  `run_criterion_probes` call or several.
- Criterion 3 drives one `run_criterion_probes` call over four criteria:
  the three errors, then the answering fourth. A second call drives the two
  turns no re-prompt follows: one with cost above half the ceiling, one with
  `session_id` empty. Compare each entry whole.
- Criterion 4 follows
  `test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker`
  (`tests/test_session.py:11846-11966`) for the two survivors, one on
  `src/x.py`'s third line and one on `src/y.py`. It follows
  `test_a_criterion_probe_nothing_could_answer_is_unproven_and_files_nothing`
  (`tests/test_session.py:12136-12205`) for the null edit and the test-path
  edit, and
  `test_a_killed_or_errored_criterion_probe_files_nothing_and_stops_nothing`
  (`tests/test_session.py:12064-12134`) for the two kills. The three
  criteria are `t.py::a`, `t.py::b` and `t.py::c`. The kill is the first
  probe in the first session's list, and the second session's kill is its
  first probe too. `_apply_criterion_probes` walks `pairs` in order, every
  probe of the first entry, then of the second, then the wrong version
  (`saffron/cell/session.py:3325-3338`). A pair with a null edit, or one on
  a test path, never joins `with_edit` (`:1986-1995`), so it asks no gate.
  A killed pair asks its witness once and `continue`s (`:2063-2080`). A
  survivor asks its witness, then the whole suite (`:2063`, `:2101-2110`).
  So script seven gate results, in this order. The first kill: a `fail` on
  `t.py::a`. The first survivor: a `pass` on `t.py::a`, then a `pass` on the
  whole suite. The second survivor: the same two. The second criterion's
  kill: a `fail` on `t.py::b`. The wrong version: a `fail` on `t.py::a`.
  Assert `subsets` whole, as the one list
  `[["t.py::a"], ["t.py::a"], [], ["t.py::a"], [], ["t.py::b"], ["t.py::a"]]`.
  The `["t.py::b"]` is the member a host pairing every probe with the first
  criterion gets wrong, since it would run `["t.py::a"]` there. Assert
  `criterion-probes.json`,
  `wrong-versions.json` and `rebuttal.json`'s blockers with `==`, and the
  REVIEW lines as a list in order, as `tests/test_session.py:12970-12979`
  does.
- Criterion 5 is a unit witness over `describe_criterion_probes` with
  hand-built entries. The refused probe carries a `refusal` string and an
  edit, as `_apply_criterion_probes` writes it.

**Size.** `saffron/cell/**` is in `elevate_on` (`.saffron/policy.yaml:35`),
so the task is `elevated` and `size` blocks. `estimated_lines` counts the
source and the prompt, about 1160 tokens. The witnesses sit under the
declared test paths, which `size` does not count
(`saffron/gates/core/size.py:276-301`). They are about 350 lines more.

**What the witnesses leave.** No witness drives a probe whose `sentence` is
the empty string, or one whose sentence is not in the claim. The schema
accepts both, and the record keeps what the session wrote. No witness
drives a claim of 16 sentences through a whole cell. A session that names
more edits than the claim has sentences is not refused below the ceiling.
The re-prompt is driven at the unit level, in criteria 2 and 3, and no
whole-cell witness scripts one. Criterion 8 drives the `killed` and
`error` outcomes, and criterion 4 the `survived`, `killed` and `unproven`
ones.

Commit after each coherent step. Uncommitted work dies with the cell.
