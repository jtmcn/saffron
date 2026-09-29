---
id: SA-0195
title: The conventions lens reads no line past its hunks and no `_Avoid_` list, and its one-source question reaches a test's pinned value
type: feature
priority: 2
estimated_lines: 289
touches:
  - saffron/agents/prompts/review-conventions.md
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-adequacy.md
  - saffron/agents/context.py
  - saffron/phases/review.py
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
  - records/**
  - harness/**
  - saffron/phases/rebut.py
  - saffron/end_review.py
  - saffron/cell/**
  - saffron/agents/prompts/rebut-verdict.md
  - saffron/agents/prompts/end-review-standards.md
  - saffron/agents/prompts/end-review-spec.md
  - saffron/agents/prompts/end-review-join.md
  - tests/test_context.py
  - tests/test_end_review.py
  - tests/test_rebut.py
budget_usd: 24
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      The conventions prompt carries a section headed `## Past the hunk`,
      right after its `## Its edges` section and before its severity
      section. It asks for any comment, docstring, count or string outside
      the hunks that the change makes false. It widens the fourth question
      to message, log and prompt strings. It exempts a test's literal
      expected value from the third question. It makes a word on an
      `_Avoid_` line a finding where the standing instructions enforce the
      vocabulary. No other prompt file carries the section.
    witness: tests/test_review.py::test_the_conventions_prompt_reads_past_the_hunk
    mutant:
      file: saffron/phases/review.py
      find: '"conventions": "review-conventions.md",'
      replace: '"conventions": "review-correctness.md",'
    wrong_versions:
      - The new section placed after the severity section, or after the slot the task fills.
      - The new section with its paragraph on a test's expected value left out.
      - An exemption reworded so that any restated constant in a test file is exempt.
      - The new section copied into the end review's Standards prompt as well.
  - claim: >-
      The conventions lens's vocabulary keeps each `_Avoid_` paragraph of
      the sections REVIEW receives, in place under its entry. That holds for a
      one-line paragraph, an `_Avoid_ also` paragraph and a paragraph wrapped
      onto a second line. A section REVIEW does not receive stays out. The
      correctness, contract and adequacy prompts carry no `_Avoid_`
      paragraph. Neither do the criterion-probe and wrong-version prompts,
      nor REVIEW's vocabulary built without the conventions lens's switch.
    witness: tests/test_review.py::test_only_the_conventions_lens_reads_the_avoid_lists
    mutant:
      file: saffron/agents/context.py
      find: '_AVOID = re.compile(r"^_Avoid_'
      replace: '_AVOID = re.compile(r"^_Never_'
    wrong_versions:
      - Every REVIEW lens keeps the `_Avoid_` paragraphs, not only conventions.
      - The default for every phase keeps them, so IMPLEMENT reads the banned words.
      - A wrapped paragraph keeps its first line and loses its second.
      - The paragraphs gathered into one block after the vocabulary, away from their entries.
      - The conventions lens given every numbered section of the file, not REVIEW's.
      - The criterion-probe or wrong-version session given the switch as well.
  - claim: >-
      The correctness, contract and adequacy prompts each end their Not-yours
      list with a bullet handing the conventions lens "a type, constant or
      helper restated rather than imported". No prompt file under
      `saffron/agents/prompts/` still says "a constant or helper restated".
    witness: tests/test_review.py::test_the_other_three_lenses_hand_a_restated_type_to_conventions
    mutant:
      file: saffron/phases/review.py
      find: '"adequacy": "review-adequacy.md",'
      replace: '"adequacy": "review-conventions.md",'
    wrong_versions:
      - Two of the three prompts updated and the third left as it was.
      - The new bullet appended beside the old one, so the old wording stays in the list.
      - The bullet reading "a type or helper", dropping the constant.
  - claim: >-
      The conventions prompt's remit still asks its four questions of every
      hunk, word for word as it did before this change.
    witness: tests/test_review.py::test_the_conventions_prompt_asks_its_four_questions_against_the_base_standards
    preserves: true
  - claim: >-
      The adequacy prompt's remit list ends with a bullet naming a witness
      whose expected value is the constant or file under test, compared
      directly or through a helper built from it. It is a finding only when
      no test pins that value as a literal. A routing check beside a literal
      pin is not one. No other lens prompt carries the bullet. The
      prompt's edge sentence asks a test to derive the value under test by
      running the code, never to derive its expected value from that code.
    witness: tests/test_review.py::test_the_adequacy_prompt_names_a_witness_pinned_to_its_own_constant
    mutant:
      file: saffron/phases/review.py
      find: '"adequacy": "review-adequacy.md",'
      replace: '"adequacy": "review-correctness.md",'
    wrong_versions:
      - The bullet with its routing-check sentence left out, so a pinned routing check reads as a finding.
      - The bullet placed in the Not-yours list rather than the remit list.
      - The bullet added to the conventions prompt as well as the adequacy prompt.
      - The bullet with no edit to name, so its finding carries no probe.
      - The edge sentence left as it was, still asking a test to derive a value instead of writing it out.
---

## Context

Backlog items **b-78ccc7** and **b-5b1f8a**. The first cites `DESIGN.md`
§5.5 and §5.6. It lists
what the Standards seat found on #580 (`SA-0191`) and #581 (`SA-0192`)
that the conventions lens's prompt would miss. ADR 8 declared the lens.
Its evidence section is in
`docs/evidence/2026-09-29-spec-loop-skill-feedback-run-21.md:80-98`. Every
line number below was read at `60510037`, and none of those files
changed by `4d7c19b9`.

**The prompt reads each hunk and nothing past it.** The remit asks "four
questions of every hunk" (`saffron/agents/prompts/review-conventions.md:28`).
`SA-0191` left two test comments counting three lenses and seven turns.
They sat about 2,600 lines from the nearest hunk, and the Standards seat
filed them as a blocker. A finding on such a line still anchors when the
line shares a word with the diff's changed lines
(`saffron/agents/findings.py:149-166`). `SA-0194` takes common English
words out of that match, and a count or a renamed term still anchors.

**Its fourth question names comments, docstrings and citations only**
(`saffron/agents/prompts/review-conventions.md:37-40`). `SA-0192`'s constant said no `CLAUDE.md`
stood while serving a blank one. That was a string, and the remit does not
reach it.

**Its third question reads a test's literal as a restated constant**
(`saffron/agents/prompts/review-conventions.md:34-36`). Read that way, it pushes a test to import
the constant it checks, which is the shape of item b-5b1f8a.

**No lens flags a witness pinned to its own constant** (item b-5b1f8a).
At `07e0ad21`, on `SA-0192`'s own branch, its criterion 2 compared the conventions prompt with
`review.NO_STANDING_INSTRUCTIONS`, the constant under test. Any wording
passed, and the adequacy lens passed the witness. Its remit list names five
shapes and not this one (`saffron/agents/prompts/review-adequacy.md:42-58`).
Its edge sentence counts "deriving a value instead of hard-coding it" as
the lens's own remit (`saffron/agents/prompts/review-adequacy.md:83-86`).
Beside the new bullet, it reads as asking a test to derive its expected
value from the code under test. That is the shape the bullet files.
A structure rule cannot hold it. The operator counted 62 base asserts in
`tests/` comparing with a module constant, most of them routing checks
beside a literal pin. `tests/test_cli.py:5142-5143` is one: the literal
`1800`, then each call's timeout against `SPEC_REVIEW_TIMEOUT_S`. The two
prompt changes are complements. Conventions stops asking a test to import
its constant, and adequacy files a test that did.

**The `_Avoid_` lists never reach the lens.** `sections_for` strips each
`_Avoid_` paragraph from every phase's vocabulary
(`saffron/agents/context.py:38-59`, item 162).
`build_system_prompt` computes the vocabulary itself from the phase
(`saffron/agents/context.py:195-219`). So `lens_prompt` has no way to ask
for the lists (`saffron/phases/review.py:190-213`). The first question asks
the lens to "avoid every term they rule against"
(`saffron/agents/prompts/review-conventions.md:30-31`), with none of those
terms in front of it. The strip's stated reason is that a prohibition puts
the banned word in the prompt (`saffron/agents/context.py:38-40`,
`CONTEXT.md:20-23`). That cost falls on a session that writes the words.
The conventions lens writes no code, and it reads for those words.

**The other three prompts say "a constant or helper".** Each ends its
Not-yours list with a bullet for the conventions lens. It names "a constant
or helper restated rather than imported"
(`saffron/agents/prompts/review-correctness.md:58-60`,
`saffron/agents/prompts/review-contract.md:63-65`,
`saffron/agents/prompts/review-adequacy.md:79-81`). The conventions remit
says "a type, constant or helper"
(`saffron/agents/prompts/review-conventions.md:34`).

## Problem

1. **Past the hunk.** Insert a section into `review-conventions.md` right
   after `## Its edges` and before `## Severity, three levels and the third
   one matters`. It holds the text under **The new section** in the notes,
   word for word.
2. **The `_Avoid_` lists.** Give `context.sections_for` and
   `context.build_system_prompt` each a keyword-only `keep_avoid: bool =
   False`. With it true, `sections_for` keeps each `_Avoid_` paragraph where
   it stands, and selects the same sections. `build_system_prompt` passes it
   through. `review.lens_prompt` sets it for the conventions lens alone.
   Every other caller keeps the default, `criterion_probe_prompt` and
   `wrong_version_prompt` included (`saffron/phases/review.py:389-407`,
   `saffron/phases/review.py:507-531`).
3. **The three bullets.** In `review-correctness.md`,
   `review-contract.md` and `review-adequacy.md`, the last Not-yours bullet
   becomes the text under **The new bullet** in the notes.
4. **The pinned witness.** Append the text under **The adequacy bullet** in
   the notes as the last bullet of `review-adequacy.md`'s remit list. That
   list opens under `## Your remit, and its edges`, and the paragraph
   opening "For every one of these" follows it.
5. **The adequacy edge.** In `review-adequacy.md`, replace the paragraph
   that opens "The test at the edge". Its new text is under **The adequacy
   edge** in the notes, word for word.

## Out of scope

- **REBUT's verdict prompt.** Item b-78ccc7 says it gets an empty
  standing-instructions section (`saffron/phases/rebut.py:280`). That is
  stale for any repo with a `CLAUDE.md`. `verdict_prompt` passes
  `context.standing_instructions(claude_md)`
  (`saffron/phases/rebut.py:287`), as it did from `0d5f8e63` on. The
  session caller hands it `claude_md` (`saffron/cell/session.py:2915`).
  `test_the_verdict_prompt_carries_the_repo_s_claude_md` covers it (`tests/test_rebut.py:543-563`). For a repo with none the
  section is empty. The verdict prompt never tells its lens to judge against
  it (`saffron/agents/prompts/rebut-verdict.md:75`), so no heading sits over
  nothing. `SA-0193` edits `rebut.py`, and this spec forbids it.
- **The spec's own directives.** The item's Problem names them, and its
  "Done looks like" does not.
- **The end review's Standards lens.** It keeps the stripped vocabulary
  (`saffron/end_review.py:170`).
- **ADR 8's measured pass.** Scoring the prompt against run 20's five
  Standards defects with `harness/lens_scoring.py`, before and after, is
  hand work. The operator's delegate runs it at review time and names it
  in the pull request's Verification section. No criterion here depends on
  it.
- **The protected text.** The spec's pull request makes three edits by
  hand, listed under **Protected edits** below. The cell makes none.

## Notes for the agent

**The mutants.** Criteria 1, 3 and 5 add prompt text this spec spells
out, and criterion 2 adds a switch it names. Intake refuses a mutant whose
`find` the spec body carries (`saffron/intake.py`, item 82). So criteria 1, 3
and 5 mutate `review.LENSES`, as `SA-0191` did. Criterion 2 mutates the
pattern at `saffron/agents/context.py:41`, which this change leaves exactly as it
stands. Criterion 4 is `preserves` and names a test that passes now.

**Literals only.** Write each new witness's expected text as a literal in the
test. Do not compare a prompt with the template file, the module constant or
the `context` function it was built from (item b-5b1f8a). Import nothing new at
module scope: `revert` reads a module-level name the change adds as a
collection error. Call `review.lens_prompt` and `context` inside each test
body.

**Rename no test, and change no parametrise row.** `census` fails any test
collected at base and absent at head.

### The new section

```text
## Past the hunk

A change can make a line false that no hunk touches. For each count, name
or behaviour the diff changes, search the repository for a comment,
docstring, count or string still stating the old one. That line is yours
wherever it sits. File it at its own line.

The fourth question reaches strings as well. A message, log line or prompt
string that says what the code does not do is yours, inside a hunk or
outside one.

The third question has one exception. A test states the value it pins as a
literal, on purpose. A test that imports the constant it checks passes
whatever that constant holds. A literal expected value in a test is never a
restated constant.

An `_Avoid_` line in the vocabulary above names the words ruled out for
its term. Where the standing instructions enforce that vocabulary, a word on
one of those lines is yours.
```

### The new bullet

```text
- A comment, docstring or citation that misstates its own code or the text
  it cites, or a type, constant or helper restated rather than imported.
  That is the conventions lens.
```

### The adequacy bullet

```text
- **A witness pinned to the constant it tests.** It compares the output
  with that constant or file, or with a helper that builds from either. Give
  the constant a wrong value and both sides of the assertion move together.
  It is yours only when no test in the suite pins that value as a literal. A
  routing check beside a literal pin of the same value is not a finding. The
  edit to name is a wrong value for that constant.
```

### The adequacy edge

```text
The test at the edge: if fixing the defect means changing what the code
computes or what it promises, it is not yours. If it means changing what the
*test* proves, it is yours. That covers strengthening an assertion, deriving
the value under test by running the code rather than restating it, and
exercising the actual changed path.
```

### The witnesses

- **Criterion 1.** Build the conventions prompt with `review.lens_prompt`,
  with a one-line `CLAUDE.md`. `_section_after(prompt, "## Its edges")`
  (`tests/test_review.py:509-520`) must return `## Past the hunk`, and a
  body equal to the new section's body when both are joined on whitespace.
  `_section_after(prompt, "## Past the hunk")` must return `## Severity,
  three levels and the third one matters`. Then read every `*.md` under
  `PROMPTS`, `turns/` included. Only `review-conventions.md` contains the
  line `## Past the hunk`.
- **Criterion 2.** Pass `review.lens_prompt` this `context_md`, for each of
  the four lenses:

  ```text
  ## 1. Core

  **Cell**: One isolated container.
  _Avoid_: "box", "pod".

  **Gate**: One declared check.
  _Avoid_ also: "linter" for a gate that
  runs the suite, "checker".

  ## 6. Outcomes

  **Verdict**: A lens's answer.
  _Avoid_: "ruling".
  ```

  The conventions prompt must contain `**Cell**: One isolated
  container.\n_Avoid_: "box", "pod".` and `**Gate**: One declared
  check.\n_Avoid_ also: "linter" for a gate that\nruns the suite,
  "checker".` as exact substrings. It must contain neither `**Verdict**`
  nor `"ruling"`. The correctness, contract and adequacy prompts must each
  contain `**Cell**: One isolated container.` and contain none of
  `_Avoid_`, `"box"`, `"checker"` and `runs the suite`. Then build
  `context.sections_for("REVIEW", <the same text>)` with no switch, and
  assert it contains no `_Avoid_`. Build `review.criterion_probe_prompt`
  and `review.wrong_version_prompt` over the same text. Each must contain
  `**Cell**: One isolated container.` and no `_Avoid_`. Last, build the conventions and the
  correctness prompts over the real `CONTEXT.md`. The first must contain
  the line `_Avoid_: "reviewer", "pass", "check", "critic #2".` and the
  second must not (`CONTEXT.md:503`).
- **Criterion 3.** For each of `correctness`, `contract` and `adequacy`,
  read `PROMPTS / review.LENSES[lens]` and split its list with
  `_not_yours_bullets_and_edge` (`tests/test_review.py:523-548`). The last
  bullet must equal the new bullet above, without its `- `, joined on
  whitespace. Then read every `*.md` under `PROMPTS`, joined on whitespace.
  None contains `a constant or helper restated`.
- **Criterion 4** names
  `test_the_conventions_prompt_asks_its_four_questions_against_the_base_standards`
  (`tests/test_review.py:417-445`). It compares the whole remit with `_CONVENTIONS_REMIT` word for word
  (`:392-414`), so a reworded question fails it as surely as a dropped one.
  Put no new text in the remit.

- **Criterion 5.** Read `PROMPTS / review.LENSES["adequacy"]`. Take the
  text after `## Your remit, and its edges` and before `For every one of
  these`. Split it into bullets, each joined on whitespace. The last must
  equal the adequacy bullet above, without its `- `. Then read each other
  lens's prompt through `review.LENSES`, joined on whitespace. None contains
  `A witness pinned to the constant it tests`. Last, the adequacy edge
  sentence from `_not_yours_bullets_and_edge` must equal the adequacy edge
  above, joined on whitespace.

**Two existing tests change in body only.**
`test_the_four_lenses_declare_disjoint_remits` asserts each of the three
lists ends with `_APPENDED_BULLET` (`tests/test_review.py:464-468`,
`:569`). Update that constant to the new bullet.
`test_the_conventions_lens_says_a_repo_without_claude_md_declares_none`
builds its expected prompt with `context.build_system_prompt`
(`:603-611`). Build its four conventions rows with `keep_avoid=True`. Keep
its seven cases, in their order.

**Tests that stay green unedited.** `test_avoid_lists_stay_out_of_the_injected_sections`
(`tests/test_context.py:48-63`) and
`test_real_context_md_never_leaks_settled_or_open_naming_decisions`
(`:169-176`) call `sections_for` with no switch. The end review's prompts
compare against that default (`tests/test_end_review.py:318`).

**The prose gate** counts every new line of a prompt and fails a hit the
base lacks. The four edited prompts, with every text above in place,
measured zero new hits.
`build_system_prompt`'s docstring runs to thirteen lines
(`saffron/agents/context.py:195-210`). A docstring's hit is keyed on its
length, so leave that one exactly as it is. Put any note on the switch in
`sections_for`'s docstring or a one-line comment.

**Size.** A prototype of this change measured 1156 tokens under
`size_gate`'s counter, four new tests and two edited ones included.
`estimated_lines` is that over four, with no overrun added. In that
prototype each declared mutant failed its witness, and so did each wrong
version listed above. Each new witness failed with the four prompts,
`context.py` and `review.py` restored to base.

**Protected edits**, made by hand in this spec's pull request, not by the
cell:

- `CONTEXT.md:20-23` says the `_Avoid_` lists are stripped at injection,
  so a cell sees only the headword. The conventions lens now sees them.
- `DESIGN.md` §5.5's fourth lens says it catches "a constant or helper
  restated". It now says a type as well, and names strings and lines
  outside the hunks.
- ADR 8's Decision lists the remit as "the hunk". Whether the widening
  earns a sentence there is the operator's call.
