---
id: SA-0446
title: "A batch's spec review reads the host's check of each mutant on refs/saffron/mutants"
type: bug
priority: 2
depends_on: [SA-0445]
estimated_lines: 90
estimate_measured: true
touches:
  - saffron/mutants.py
  - saffron/cli.py
  - tests/test_spec_review_mutants.py
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
  - saffron/spec_review.py
  - saffron/batch.py
  - saffron/draft.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/follow_up.py
  - saffron/task.py
  - saffron/regate.py
  - saffron/qualify.py
  - saffron/end_review.py
  - saffron/events.py
  - saffron/parent_versions.py
  - saffron/report/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_cli.py
  - tests/test_mutants.py
  - tests/test_spec_review.py
  - tests/test_batch.py
  - tests/test_draft.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
  - tests/test_follow_up.py
  - tests/test_intake.py
  - tests/test_events.py
  - tests/test_package.py
  - tests/test_package_cell.py
  - tests/test_stack_view.py
  - tests/test_spec_id_lock_callers.py
  - tests/test_image.py
  - tests/test_corpus.py
  - tests/test_witness_gate.py
  - tests/test_suite.py
  - tests/test_session.py
  - tests/test_parent_versions.py
  - tests/test_regate.py
  - tests/test_report.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_record_migrate.py
budget_usd: 60
max_attempts: 3
max_turns: 210
risk: standard
acceptance:
  - claim: >-
      `mutants.review_lines` gives one line per criterion of the spec it is
      handed. The line names the criterion's witness and whether the
      mutants commit holds a mutant for it. A held mutant's line gives how
      many times its find text occurs in its file at the commit named as
      the base. The witness reads a criterion with no mutant three ways: a
      `None` commit, a commit with no file for the spec, and a file with no
      entry for that witness. It reads counts of 1 and 3, and of 0 for a
      file that lacks the text and for a file absent at the base. It reads
      the same mutants at two bases whose counts differ, and the same
      inputs twice to equal lines.
    witness: tests/test_spec_review_mutants.py::test_review_lines_count_each_criterions_find_at_the_base_named
    wrong_versions:
      - "The count reads each file at the mutants commit rather than at the base."
      - "A `None` commit returns no lines at all."
      - "The count says whether the find text is present, as 1 or 0, rather than how often it occurs."
      - "A file absent at the base leaves its criterion's line out."
      - "A criterion with no mutant on the ref gets no line."
    covers:
      - set: the ways a criterion has no mutant
        members:
          - member: a None commit
            driven_by: "A `None` commit returns no lines at all."
          - member: a commit with no file for the spec
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_count_each_criterions_find_at_the_base_named
          - member: a file with no entry for the witness
            driven_by: "A criterion with no mutant on the ref gets no line."
      - set: a find's count at the base
        members:
          - member: 0, the file lacks the text
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_count_each_criterions_find_at_the_base_named
          - member: 0, the file is absent at the base
            driven_by: "A file absent at the base leaves its criterion's line out."
          - member: "1"
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_count_each_criterions_find_at_the_base_named
          - member: 3, more than once
            driven_by: "The count says whether the find text is present, as 1 or 0, rather than how often it occurs."
      - set: the commit a count reads
        members:
          - member: the base handed in, at two bases whose counts differ
            driven_by: "The count reads each file at the mutants commit rather than at the base."
      - set: the calls on one input
        members:
          - member: the same inputs read twice
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_count_each_criterions_find_at_the_base_named
    positive_case: >-
      The same witness first reads a count line for every criterion, from a
      commit whose file holds an entry for each witness. So each line that
      says no mutant comes from a reader that finds an entry when one is
      there.
  - claim: >-
      `mutants.review_lines` names each outcome below in fixed words, and
      no line carries a mutant's find, replace, file or case, or an
      exception's text. The witness reads thirteen outcomes for the whole
      spec. They are a check that passes and spec text that does not parse.
      Three are a mutants file that does not parse: an invalid entry,
      invalid YAML, and a list. One is a mutants commit the mirror lacks.
      Three are a mismatch: a witness no criterion declares, a witness two
      criteria share, and a subject with no mutant. Four are a find the
      spec holds, in its body, a claim, a wrong version, or a case. The
      witness also reads a criterion whose file is a directory at the base.
    witness: tests/test_spec_review_mutants.py::test_review_lines_name_each_refusal_in_fixed_words_and_no_mutants_text
    wrong_versions:
      - "The line for a mutants file that does not parse ends with the `MutantsError` text."
      - "The line for a disclosed mutant ends with the `DisclosedMutantError` text."
      - "A disclosed mutant falls into the same sentence as a file that does not match the criteria."
      - "A commit the mirror lacks raises out of the call."
      - "A criterion's line names its mutant's file."
      - "A criterion's file that `file_at` cannot read raises out of the call."
      - "Spec text that does not parse returns no lines."
      - "A subject with no mutant is let through, as though no criterion declared one."
    covers:
      - set: the whole-spec outcomes
        members:
          - member: the check passes
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_name_each_refusal_in_fixed_words_and_no_mutants_text
          - member: the spec text does not parse
            driven_by: "Spec text that does not parse returns no lines."
          - member: a mutants entry pydantic refuses
            driven_by: "The line for a mutants file that does not parse ends with the `MutantsError` text."
          - member: a mutants file of invalid YAML
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_name_each_refusal_in_fixed_words_and_no_mutants_text
          - member: a mutants file that is a list
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_name_each_refusal_in_fixed_words_and_no_mutants_text
          - member: the mirror lacks the mutants commit
            driven_by: "A commit the mirror lacks raises out of the call."
          - member: a witness no criterion declares
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_name_each_refusal_in_fixed_words_and_no_mutants_text
          - member: a witness two criteria share
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_name_each_refusal_in_fixed_words_and_no_mutants_text
          - member: a subject with no mutant
            driven_by: "A subject with no mutant is let through, as though no criterion declared one."
          - member: a find the body holds
            driven_by: "A disclosed mutant falls into the same sentence as a file that does not match the criteria."
          - member: a find a claim holds
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_name_each_refusal_in_fixed_words_and_no_mutants_text
          - member: a find a wrong version holds
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_name_each_refusal_in_fixed_words_and_no_mutants_text
          - member: a find a case holds
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_name_each_refusal_in_fixed_words_and_no_mutants_text
      - set: a criterion line's outcomes beyond a count
        members:
          - member: its file cannot be read at the base
            driven_by: "A criterion's file that `file_at` cannot read raises out of the call."
      - set: the mutant's text withheld
        members:
          - member: find
            driven_by: "The line for a disclosed mutant ends with the `DisclosedMutantError` text."
          - member: replace
            driven_by: "The line for a mutants file that does not parse ends with the `MutantsError` text."
          - member: file
            driven_by: "A criterion's line names its mutant's file."
          - member: case
            driven_by: tests/test_spec_review_mutants.py::test_review_lines_name_each_refusal_in_fixed_words_and_no_mutants_text
    positive_case: >-
      The same witness joins each outcome's lines and reads the criterion's
      witness in the passing outcome's join. Each wrong version above that
      appends an exception's text or names the file puts a sentinel into
      that same join, and the witness reads it there.
  - claim: >-
      A batch's spec review prompt carries `mutants.review_lines` for its
      candidate when `_stack_review` holds a ledger and the candidate a task
      id. It reads the mutants commit the ledger pins for the task, the
      revision's text when one is given and the queued file otherwise, and
      counts at the commit the cell is seeded at. The witness moves the ref
      past the pinned commit. It reviews a queued spec with no layer and on
      a layer whose head differs from the pinned base. It reviews a revision
      that discloses a mutant, then the queued spec again. It reviews a
      follow-up whose file is not queued at the base. A draft candidate with
      no task id, and a `_stack_review` built with no ledger, each get no
      such line.
    witness: tests/test_spec_review_mutants.py::test_a_batch_spec_review_prompt_carries_the_hosts_mutant_lines
    wrong_versions:
      - "The count reads the pinned `base_sha` rather than the seeded head."
      - "The mutants commit is read fresh with `mutants.ref_commit` rather than from the ledger."
      - "The queued file is always read, and a given revision is ignored."
      - "The queued file is read first, even when a revision is given."
      - "The lines are added whenever a ledger is held, a draft's read from `mutants.ref_commit`."
      - "The lines are cached per spec id, so a second review reads the first one's lines."
    covers:
      - set: the specs reviewed
        members:
          - member: a queued spec with no revision
            driven_by: tests/test_spec_review_mutants.py::test_a_batch_spec_review_prompt_carries_the_hosts_mutant_lines
          - member: a revision of it
            driven_by: "The queued file is always read, and a given revision is ignored."
          - member: a follow-up with no queued file
            driven_by: "The queued file is read first, even when a revision is given."
          - member: a draft with no task id
            driven_by: "The lines are added whenever a ledger is held, a draft's read from `mutants.ref_commit`."
          - member: a review built with no ledger
            driven_by: tests/test_spec_review_mutants.py::test_a_batch_spec_review_prompt_carries_the_hosts_mutant_lines
      - set: the commit the cell is seeded at
        members:
          - member: the pinned base, with no layer
            driven_by: tests/test_spec_review_mutants.py::test_a_batch_spec_review_prompt_carries_the_hosts_mutant_lines
          - member: a layer's fetched head
            driven_by: "The count reads the pinned `base_sha` rather than the seeded head."
      - set: the mutants commit read
        members:
          - member: the task's pinned commit, with the ref moved past it
            driven_by: "The mutants commit is read fresh with `mutants.ref_commit` rather than from the ledger."
      - set: the reviews of one spec
        members:
          - member: a second review after a revision
            driven_by: "The lines are cached per spec id, so a second review reads the first one's lines."
    positive_case: >-
      The same prompt spy reads the host's lines in the first review, of a
      queued spec with a task id. So the draft's and the no-ledger prompts
      that lack them come from the instrument that saw them.
  - claim: >-
      `saffron batch --stack` and `saffron finish` each build
      `_stack_review` with the ledger they hand `run_stack_batch` and
      `_stack_mint`.
    witness: tests/test_spec_review_mutants.py::test_a_stack_batch_and_a_finish_hand_their_ledger_to_the_spec_review
    wrong_versions:
      - "`_batch` builds `_stack_review` with no ledger."
      - "`_finish` builds `_stack_review` with no ledger."
    covers:
      - set: the commands that build a batch's spec review
        members:
          - member: saffron batch --stack
            driven_by: "`_batch` builds `_stack_review` with no ledger."
          - member: saffron finish
            driven_by: "`_finish` builds `_stack_review` with no ledger."
---

## Context

Backlog item **b-216235**, found in batch 101.
`SA-0419`'s notes named two mutants on `refs/saffron/mutants`. Its spec
review could not read that ref, so it routed the spec to `revise` on one
concern. The revision then needed more than the batch had left, and the
batch built nothing.

**The ref stays out of a review's cell on purpose**. The seed fetches
`refs/heads/*` alone, so the cell never holds the ref (DESIGN.md §5.4.1,
the paragraph on `refs/saffron/mutants`, and item 80). The host's mirror
does hold it.

**A batch's spec review prompt names no mutant**. `_stack_review`'s `run`
builds the prompt from the spec's path, the seeded head and the account
lines (`saffron/cli.py:1429-1435`). It adds a revision's or a draft's text
when one is given (`saffron/cli.py:1436-1444`). Nothing else reaches it.

**The commit the cell is seeded at is `head`**. `_stack_review` takes it from its
commit cache or resolves it afresh (`saffron/cli.py:1406-1409`).
`_stack_head` resolves a layer's fetched branch, else the pinned
`base_sha` (`saffron/cli.py:864-876`).

**The task row pins the mutants commit before the review**.
`run_stack_batch` mints the task before its first review and puts the id on
the candidate (`saffron/batch.py:700-715`). `_stack_mint` reads
`mutants.ref_commit` and stores it on the row (`saffron/cli.py:1626-1638`).
`Ledger.task_mutants_commit` reads it back (`saffron/ledger.py:1834-1840`).
`run_task` attaches mutants from that same commit
(`saffron/task.py:791-798`).

**The review is handed the text it reads**. `run_stack_batch` passes the
latest `spec_texts` row as `spec_text`, or none for a queued spec with no
revision (`saffron/batch.py:728-729`, `saffron/batch.py:768-773`). The
queued file at the pinned base is `_queued_spec_text`
(`saffron/cli.py:884-891`).

**The parts the check needs exist**. `read_mutants` reads `<spec id>.yaml`
at a commit, and gives none for a `None` commit or an absent file
(`saffron/mutants.py:83-96`). `attach_mutants` refuses a stray witness, a
shared one and a subject with no mutant, then repeats the disclosure check
(`saffron/mutants.py:99-128`). `file_at` reads a path at a commit, `None`
when absent, and raises `GitError` for a path it cannot read
(`saffron/repos/mirror.py:267-273`).

**Two of those errors quote a mutant's text, and a raise is recorded**.
`parse_mutants` puts pydantic's error, with its input values, into its
message (`saffron/mutants.py:74-77`). `refuse_disclosed_mutants` puts the
find in its message (`saffron/intake.py:586-593`). Whatever `review`
raises is recorded as its type and text (`saffron/batch.py:773-781`).

**Three sites build `_stack_review`**. `_batch` at `saffron/cli.py:2647-2653`,
`_finish` at `saffron/cli.py:2921`, and `_draft_adapters` at
`saffron/cli.py:1684`. A draft's candidate is a throwaway with no task id
(`saffron/cli.py:1662-1671`).

## Problem

1. **Add `review_lines(mirror, commit, spec_text, base) -> list[str]` to
   `saffron/mutants.py`**. Parse `spec_text` with `intake.parse_spec`.
   Read the mutants with `read_mutants`. Count each find with `file_at` at
   `base`, and judge the whole set with `attach_mutants`. Its lines, in
   order, are a first line, one line per criterion, and a last line. The
   witnesses pin each sentence, so write them exactly as below.
   - First line: `The host read this spec's mutants on refs/saffron/mutants,
     a ref your clone does not hold. Read the lines below for what it holds,
     and raise no finding only because you cannot read that ref.`
   - No mutant: `- <witness>: no mutant on the ref.`
   - A mutant: `- <witness>: a mutant whose find text occurs <n> time(s) in
     its file at this base.` A file absent at `base` counts 0.
   - A file `file_at` cannot read: `- <witness>: a mutant whose file cannot
     be read here.`
   - The check passes: `The host's check of these mutants against the
     criteria passes.`
   - `DisclosedMutantError`: `The host refuses these mutants: one names text
     the spec holds.`
   - Any other `MutantsError` from `attach_mutants`: `The host refuses these
     mutants: they do not match the criteria.`
   - In place of every criterion line and the last line, after the first:
     `The host could not parse this spec's text.` for a `SpecError` from
     `parse_spec`, `The spec's mutants file on the ref does not parse.` for
     a `MutantsError` from `read_mutants`, and `The host could not read the
     task's mutants commit.` for a `GitError` from it.
2. **Add the lines to `_stack_review`'s prompt**. Give `_stack_review` a
   keyword `ledger: Ledger | None = None`. When it is set and the candidate
   has a task id, take the text as `spec_text`, or `_queued_spec_text` when
   that is `None`. Read the commit with `ledger.task_mutants_commit`, call
   `review_lines` with `head`, and append each line with a newline. Put
   them after the account lines and before a revision's or a draft's
   sentence.
3. **Hand the ledger over** at the `_batch` and `_finish` sites. Leave
   `_draft_adapters` as it is.
4. **Correct the sentences the change makes false**. The module docstring
   of `saffron/mutants.py` lists every reader of the ref
   (`saffron/mutants.py:1-12`), and `review_lines` joins them.
   `_stack_review`'s docstring says what `run` seeds and reads
   (`saffron/cli.py:1389-1397`), and gains the ledger.

## Out of scope

- **The extraction cap and its retry**. `SA-0445` owns them, in
  `saffron/cli.py` and `saffron/spec_review.py`.
- **A draft's review**. `_draft_adapters` holds no ledger and its candidate
  no task id. `_draft` takes a fresh id from `follow_up.next_spec_id` and
  mints its task with no mutants commit (`saffron/cli.py:1790-1799`).
  Criterion 3 reads its prompt unchanged.
- **The spec review's system prompt**.
  `saffron/agents/prompts/spec-review.md` says nothing about mutants. The
  instruction rides in the user prompt's first line instead.
- **A refusal**. The check tells the reviewer and refuses nothing.
  `run_task` still refuses a spec whose mutants fail `attach_mutants_at`.
  So `retired_first` is empty.
- **Whether the reviewer heeds the lines**. No witness can measure a
  route, and this change to what the reviewer reads is unmeasured.

## Notes for the agent

**No criterion declares a mutant**. `review_lines` and the prompt block are
new code whose spelling is yours. `witness` will report `skip`.

**Reach every new name by attribute inside a test body**. The witness file
is new. A module-scope import of `review_lines` would make the reverted
tree a collection error, which `revert` reads as `skip`.

**Build the review rig in the witness file**. Fake `end_review.layer_cell`
with a context manager yielding a name, and `spec_review.run_spec_review`
with a spy on `prompt`. Fake `package.fetch_parent_branch` to return a real
commit. A bare mirror built with `mktree` and `commit-tree` holds the base,
the head and two mutants commits, as `tests/test_mutants.py:13-50` builds
one. A small object with a `task_mutants_commit` method can stand in for
the ledger in criterion 3.

**Import the command helpers, never edit `tests/test_cli.py`**.
`tests/test_adopt_stack_layer.py:10` imports helpers from `tests.test_cli`.
Criterion 4's witness can import `_readiness_passes`,
`_fake_batch_resolution` and `_deferred_finish_home` the same way. Wrap
`cli._stack_review` and `cli._stack_mint` in spies that call the real ones,
and fake `cli.run_stack_batch`. `saffron finish` needs
`CLAUDE_CODE_OAUTH_TOKEN` set, which `tests/test_cli.py`'s autouse fixture
sets only for its own module.

**Name no constant with a `_PROMPT` suffix**. The `prompt-is-a-file`
rule refuses a `_PROMPT` constant that loads no Markdown file
(`.saffron/rules/prompt-is-a-file.yml:19`). `_DRAFT_REVIEW_SENTENCE` holds
prompt text under another name (`saffron/cli.py:1646-1649`).

**Read the secrets from one join**. Put a distinct sentinel in a mutant's
find, replace, file and case. Join each outcome's lines and assert none is
in it. A disclosing revision's own text holds the find, so assert on the
lines, never on the whole prompt.

**What the prototype measured**. It was cut from `main` at `a13d8890`,
since `SA-0445`'s branch is not pushed yet. It changed 79 lines of
`saffron/mutants.py` and `saffron/cli.py`, 361 changed tokens by the
`size` gate's own count. With it applied, `tests/test_mutants.py`,
`tests/test_cli.py`, `tests/test_batch.py`, `tests/test_draft.py` and
`tests/test_spec_review.py` passed.
