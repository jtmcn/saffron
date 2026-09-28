---
id: SA-0187
title: A spec's wrong versions are prose in its notes, so no session turns them into edits the host could run
type: feature
priority: 1
depends_on: []
touches:
  - saffron/intake.py
  - saffron/agents/context.py
  - saffron/agents/prompts/wrong-version.md
  - saffron/agents/prompts/turns/wrong-version.md
  - saffron/phases/review.py
  - tests/test_intake.py
  - tests/test_context.py
  - tests/test_review.py
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
  - saffron/cell/**
  - saffron/gates/**
  - saffron/probe.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/phases/rebut.py
  - saffron/phases/implement.py
  - saffron/phases/package.py
  - saffron/agents/findings.py
  - saffron/agents/artifacts.py
  - saffron/agents/prompts/implement.md
  - saffron/agents/prompts/criterion-probe.md
  - saffron/agents/prompts/review-adequacy.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/rebut-verdict.md
  - saffron/agents/prompts/turns/criterion-probe.md
  - saffron/agents/prompts/turns/implement.md
  - saffron/agents/prompts/turns/review.md
  - tests/test_session.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 22
max_attempts: 3
max_turns: 180
estimated_lines: 360
pending_symbols:
  - saffron/phases/review.py::run_wrong_versions
  - saffron/phases/review.py::describe_wrong_versions
acceptance:
  - claim: >-
      A criterion may declare `wrong_versions`, a list of strings that parse
      keeps in declared order. A criterion that omits it reads as an empty
      list. Parse refuses four shapes as a `SpecError`. They are an explicit
      empty list, an empty string, a string of whitespace alone, and two
      entries with the same text in one criterion. The same text in two
      different criteria parses. The witness drives each refusal in its own
      spec and the three parsing criteria in one.
    witness: tests/test_intake.py::test_a_criterion_declares_its_wrong_versions_and_parse_refuses_an_empty_or_repeated_one
  - claim: >-
      `context.witnesses_block` follows each criterion's line with its wrong
      versions, and a criterion that declares none gets no added line. The
      witness compares the whole block with an exact string, for a
      `preserves` criterion with two wrong versions and a plain criterion
      with none. `context.criteria_section`, the lenses' view, shows no wrong
      version. The witness compares its output with an exact string too.
    witness: tests/test_context.py::test_the_implementer_reads_each_criterions_wrong_versions_under_its_line
  - claim: >-
      `review.run_wrong_versions` buys one fresh session per criterion that
      declares wrong versions, in the spec's order, and none for one that
      declares none. Each system prompt ends with the diff, that criterion's
      wrong versions numbered from 1, and its claim, under their own
      headings. No system prompt or turn prompt holds a witness node id, and
      none holds another criterion's claim. Each session holds
      `review.REVIEW_TOOLS` and the `max_turns` and `budget_usd` the call was
      given. Each entry holds the criterion's witness and claim, the
      session's cost, a null `error`, and one `versions` object per declared
      version in order. That object holds the version's text, the edit named
      or null, and the reason. A version the session could not express keeps
      its place with a null edit and its reason. The criterion-probe prompt
      for the same criteria holds no wrong version. `describe_wrong_versions`
      over the entries reads `wrong versions: 3 declared, 2 expressed`.
    witness: tests/test_review.py::test_each_criterion_with_wrong_versions_gets_one_session_that_turns_each_into_an_edit
  - claim: >-
      A wrong-version session that raises `AgentFailed`, one whose reply
      holds no output block, one answering fewer versions than declared and
      one answering more each leave an entry for its criterion. Every
      declared version keeps its text there, with a null edit and an empty
      reason. The `error` is the failure's own text, `not the schema: no
      <output> block in the response`, `not the schema: 1 answers for 2 wrong
      versions` and `not the schema: 3 answers for 2 wrong versions`. Each
      entry carries its session's cost, and every later criterion is still
      asked.
    witness: tests/test_review.py::test_a_wrong_version_session_that_answers_nothing_usable_keeps_every_version
---

## Context

Backlog item **b-7e69d0** is
`docs/backlog/b-7e69d0-the-host-probes-no-wrong-version-a-spec-lists-for-its-criteria.md`, tier 1.
The operator ranked it first in the spec loop's run 20. It follows
b-2750d5, which `SA-0113` and `SA-0120` closed, and b-2dea1c, which took
running wrong versions away from the implementer (`SA-0130`).

This spec is the parent half of a split. `SA-0190` is the child. It runs
the sessions this spec adds inside REVIEW, applies each edit in a gate-only
cell, runs that criterion's witness, and records every outcome. This spec
adds the declaration, the session and its record's entries. Nothing in
`saffron/cell/session.py` calls them until `SA-0190` merges.

Every sentence below about current code was read at `a4299786` on
2026-09-28.

**A spec's wrong versions are prose today.** A spec lists them as bullets
under "These fail it" in its notes. The retired spec for SA-0180 holds
three such lists, at lines 415, 436 and 452 of
`.saffron/specs/done/SA-0180-an-end-reviews-layer-findings-reach-no-follow-up-because-nothing-anchors-probes-or-groups-them.md`.
The implementer reads them as part of the body. Nothing in the cell turns one into an edit or runs it.
The IMPLEMENT prompt tells the implementer not to run them
(`saffron/agents/prompts/implement.md:68-74`).

**A criterion carries four fields and refuses a fifth.** `Criterion`
(`saffron/intake.py:110-130`) holds `claim`, `witness`, `preserves` and
`mutant`, with `extra="forbid"` at `saffron/intake.py:117`. So a spec declaring
`wrong_versions` is refused at parse today. `parse_spec` wraps every
`ValidationError` as a `SpecError` (`saffron/intake.py:255-258`).

**The implementer and the lenses see the claims through two renderers.**
`context.witnesses_block` (`saffron/agents/context.py:89-117`) renders one
line per criterion for the IMPLEMENT prompt: the witness, a `*(preserves)*`
tag, and the claim. `context.criteria_section` (`saffron/agents/context.py:120-131`) renders the
claims alone as a checklist, and REVIEW appends it to the body the lenses
read (`saffron/cell/session.py:2665-2667`).

**A criterion probe is the precedent for this session.**
`review.run_criterion_probes` (`saffron/phases/review.py:434-479`) buys one
fresh session per criterion. `criterion_probe_prompt` (`saffron/phases/review.py:376-394`)
substitutes the claim alone for `{spec}` in `criterion-probe.md`, so the
session never sees the spec body or a witness node id.
`run_criterion_probe` (`saffron/phases/review.py:397-431`) runs it with `review.REVIEW_TOOLS` and
the given ceilings. It returns an `AgentFailed`'s own text as the error, and
`not the schema: ` plus the parse error for a reply it cannot read. It never
re-prompts. The entry holds `witness`, `claim`, `edit`, `reason`,
`cost_usd` and `error` (`saffron/phases/review.py:470-478`).
`describe_criterion_probes` (`saffron/phases/review.py:482-487`)
counts that record for REVIEW's watch line.

**Every turn prompt is enumerated.** `tests/test_context.py:485-498`
lists each file under `saffron/agents/prompts/turns/` beside the constant
that loads it. `tests/test_context.py:502-504` fails when a file has no entry.

## Problem

Declare wrong versions per criterion in a form the host reads, and add the
session that turns each into an edit.

1. **The field.** Add `wrong_versions` to `Criterion`, a list of strings
   whose default is an empty list. An omitted field parses exactly as today.
   Refuse an explicit empty list, an empty or whitespace-only string, and
   two entries with the same text in one criterion. A validator on the field
   does all four, because pydantic runs it only on a declared value. The
   same text in two different criteria is not a duplicate.
2. **The implementer's view.** `witnesses_block` follows a criterion's line
   with one lead line and then one line per wrong version, in declared
   order. The lead line is two spaces and then
   `Wrong versions the host runs after GATE. This witness must fail on each:`.
   Each version line is two spaces, `- `, and the version's text. A
   criterion that declares none renders exactly as today.
3. **The lenses' view stays as it is.** `criteria_section` shows no wrong
   version, for the reason §5.4.1 gives a criterion probe. An edit is
   evidence when its author could not see what would kill it. The adequacy
   lens names vacuity probes of its own (§5.5.1). Shown the author's list,
   it would name the edits the host already runs, and its probes would stop
   adding coverage. The criterion-probe session keeps its view for the same
   reason: it sees one claim and the diff.
4. **The session.** `review.run_wrong_versions` takes the arguments
   `run_criterion_probes` takes, with the same keywords. For each criterion
   whose `wrong_versions` is non-empty, in the spec's order, it runs one
   fresh session. The session sees the claim, the list and the diff, and
   never the witness or the spec body. Build its system prompt the way
   `criterion_probe_prompt` does, from a new `wrong-version.md`, with the
   claim substituted for `{spec}` and the list for a `{wrong_versions}`
   slot. The list renders one line per version, `1. ` and its text first,
   numbered from 1 in declared order. Its turn prompt is a new `turns/wrong-version.md`, loaded once by
   `context.turn_prompt("wrong-version")` into a module constant. Add that
   constant to `TURN_PROMPTS` in `tests/test_context.py`. Run the session as
   `run_criterion_probe` does, with `REVIEW_TOOLS` and the given ceilings,
   and with no re-prompt.
5. **The answer.** The session replies with one `<output>` block holding
   `{"versions": [...]}`, one object per listed version in listed order.
   Each object holds `edit` and `reason`, the shape `_ProbeAnswer` gives one
   criterion probe (`saffron/phases/review.py:363-370`). Pair answers with
   versions by position. When the count differs from the declared count,
   the error is `not the schema: {got} answers for {declared} wrong
   versions`, with both numbers as digits.
6. **The entry.** One dict per criterion that declares wrong versions,
   holding `witness`, `claim`, `cost_usd`, `error` and `versions`. Each
   member of `versions` holds `version`, `edit` and `reason`. `edit` is a
   `Mutant`'s `model_dump()` or `None`. On any failure, keep every declared
   version with a `None` edit and an empty reason, and set `error`. The
   failures are an `AgentFailed`, a reply the parser or the model refuses,
   and a count that differs. The cost is the session's, as
   `run_criterion_probe` charges a failed one.
7. **The line.** `review.describe_wrong_versions(entries)` returns
   `wrong versions: {declared} declared, {expressed} expressed`. It counts
   every member of every entry's `versions`, and the ones whose edit is not
   `None`. `SA-0190` emits it on REVIEW's watch line.

## Out of scope

- Calling the session from REVIEW, applying its edits, and filing a
  survivor. `SA-0190` does all three in `saffron/cell/session.py`.
- The survivor's wording. `SA-0190` gives `survivor_finding` the version.
- The source a survivor is filed under. It stays `adequacy`, and item
  b-9ed36d stays open.
- `criteria_section`, `criterion_probe_prompt` and `criterion-probe.md`.
  Problem step 3 says why none changes.
- The IMPLEMENT prompt's own text. `saffron/agents/prompts/implement.md:68-74` already says the
  host runs wrong versions and the implementer does not.
- This spec's own wrong versions. The parser refuses the field until this
  spec merges, so the lists below stay in the notes.
- The glossary and the design record. `CONTEXT.md`, `DESIGN.md` and
  `docs/agents/issue-tracker.md` are edited by hand in this spec's pull
  request.

## Notes for the agent

**This change is new code, so no criterion declares a mutant** (§5.4.1).
The `witness` gate reports `skip` for this spec. No text at the tree base
spells the new field, its validator, the session or its record.

**Each witness fails at the tree base without a collection error.**
`Criterion(wrong_versions=...)` raises there, and `review.run_wrong_versions`
is a missing attribute. Reach every new name through its module inside the
test body, never by a module-scope `from` import. A module-scope import of a
new name makes `revert`'s reverted run a collection error, which it reads
as `skip`.

**Assert exact values.** Compare whole strings, whole lists and whole
dicts. Never assert a substring, a prefix or an `index()` order. A slice is right in one place, the tail of a system prompt.
There, compare the whole tail with `endswith` on a string you build in full.

**Criterion 1's witness.** Build each spec text with `parse_spec`, as
`test_a_criterion_may_declare_the_edit_that_falsifies_it` does
(`tests/test_intake.py:381-402`). Table the four refused specs and loop
over them in one plain `def`, asserting `SpecError` for each. The parsing
spec has three criteria. The first declares `["v one", "v two"]`, the
second `["v one"]`, and the third omits the field. Assert each criterion's
`wrong_versions` list exactly. These fail it:

- a default of `None` for an omitted field
- a refusal of `""` that lets `"   "` through
- a duplicate check across the whole spec, which refuses the second
  criterion
- a set in place of a list, which loses the declared order
- an explicit `[]` read as omitted

**Criterion 2's witness.** Two criteria: a `preserves` one with
`["a first wrong version", "a second wrong version"]`, then a plain one with
none. Write the expected block in full as a string literal, every line of
it, and compare with `==`. Compare `criteria_section` over the same list
with its own exact literal. These fail it:

- the versions rendered under the wrong criterion, or under every criterion
- the lead line printed for a criterion that declares none
- one version rendered, or the versions reversed
- the versions added to `criteria_section`

**Criterion 3's witness.** Reuse `_probe_agent` and `_turn`
(`tests/test_review.py:30-38` and `tests/test_review.py:544-558`). Give each turn its own cost.
Three criteria, in order:

| criterion | witness | wrong versions | the session answers |
|---|---|---|---|
| A, claim "the guard rejects a negative amount" | `t.py::test_a` | "the guard accepts zero", "the guard is removed" | an edit, then null with a reason |
| B, claim "the total is logged" | `t.py::test_b` | none | no session |
| C, `preserves`, claim "the total stays unchanged" | `t.py::test_c` | "the total is doubled" | an edit |

Record each call's prompt and options. Assert two calls. Assert each
system prompt's exact tail. It holds the diff, the numbered list and the
claim under `## The diff`, `## The wrong versions` and `## The claim`. Keep
the blank lines `wrong-version.md` puts there. Assert that neither system prompt
nor turn prompt holds any of the three witness ids. Assert A's prompt holds
neither B's nor C's claim, and C's holds neither A's nor B's. Assert each
options dict's `tools`, `max_turns` and `max_budget_usd` exactly. Assert the
two entries as whole dicts. Then run `review.run_criterion_probes` over the
same three criteria with a scripted agent. Assert that none of its three
system prompts holds any of the three wrong versions. Last, assert the
`describe_wrong_versions` line. These fail it:

- a session bought for criterion B
- the witness id or the whole acceptance list in the prompt
- the versions in `{spec}` beside the claim, which puts them under the
  claim's heading
- a null edit dropped from `versions`, or its reason dropped
- the versions added to `criterion_probe_prompt`
- the lens ceiling in place of the one passed
- one cost shared by every entry, or the sum of the costs on each
- a line that counts entries in place of versions

**Criterion 4's witness.** Four criteria, each declaring two wrong
versions, in the order the claim lists them. Script an `AgentFailed`
carrying a turn with its own cost, then `"not a block at all"`, then a block
with one answer, then a block with three. Assert every entry whole. These
fail it:

- a failed session that returns `versions: []`
- a count check that passes three answers for two versions by truncating
- a stop after the first failure
- a re-prompt on a bad reply
- a failed session charged nothing

**Where the code lives.** The field and its validator go in
`saffron/intake.py`. The renderer goes in `saffron/agents/context.py`. The
session, its answer model and the line go in `saffron/phases/review.py`,
beside the criterion-probe functions. Share the prompt-building and session
code with `run_criterion_probe` only where the result stays plain. A
second copy of six lines is cheaper than a helper both must bend around.

**The `dead` gate.** `run_wrong_versions` and `describe_wrong_versions`
are in `pending_symbols`, because only `SA-0190` calls them. Call every
other new name from one of them.

**The `prose` gate.** It reads `saffron/agents/prompts/` and every comment
and docstring. A new file starts at zero hits. Write no em dash, semicolon,
contraction, perfect tense, hedge or sentence over 25 words there. Keep
each docstring within ten lines. Run
`python3 hooks/prose_limit.py --file <path>` on each new prompt file.

**The prompt.** Model `wrong-version.md` on `criterion-probe.md`. Keep its
emit section's edit rules, since the same host applies the edit. Tell the
session that each wrong version is a sentence a person wrote about this
change. Its task is to turn each into the smallest source edit that makes
the code behave that way. A version it cannot express as one edit gets a
null edit and a reason. End the file with the diff, the numbered wrong
versions and the claim, in that order, under the three headings criterion 3
names.

**Size.** No path this spec touches is in `elevate_on`, so `size` is
advisory at the `feature` ceiling of 3000 tokens
(`saffron/gates/core/size.py:26`). `SA-0113` built the criterion-probe
session, and its cell commit `b9d8f39b` measured 1923 changed tokens. Of
those, 990 were its prompt, `review.py` and `tests/test_review.py`. The
parser, the renderer and their tests add about 450. So expect about 1440,
and keep the tests to shared helpers and tabled rows.

**Commit as each witness passes**, before the full suite runs.
Uncommitted work dies with the cell.

**Rename no existing test.** `census` reads a rename as a removal.
