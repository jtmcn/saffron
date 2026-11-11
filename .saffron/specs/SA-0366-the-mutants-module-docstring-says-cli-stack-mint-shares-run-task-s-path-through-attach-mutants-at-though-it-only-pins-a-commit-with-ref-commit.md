---
id: SA-0366
title: The mutants module docstring says cli._stack_mint shares run_task's path through attach_mutants_at, though it only pins a commit with ref_commit
type: bug
priority: 3
estimated_lines: 24
estimate_measured: false
touches:
  - saffron/mutants.py
  - tests/test_cli.py
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
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/end_review.py
  - saffron/task.py
  - saffron/regate.py
  - saffron/commit_review.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/cell/**
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_regate.py
  - tests/test_commit_review.py
  - tests/test_task.py
  - tests/test_mutants.py
budget_usd: 20
max_attempts: 3
max_turns: 120
risk: standard
acceptance:
  - claim: >-
      `saffron/mutants.py`'s module docstring (`saffron/mutants.py:4`)
      names, in one sentence, every caller that reads a spec's mutants
      through `attach_mutants_at`: `run_task`, `run_regate`,
      `package_ready_task` and `run_commit_review`. It names
      `cli._stack_mint` only in a separate sentence, saying that it reads
      this module solely to pin a commit on a fresh task's row, through
      `ref_commit`, and never through `attach_mutants_at`. `cli._stack_mint`
      (`saffron/cli.py:1593-1622`) in fact calls only
      `mutants.ref_commit(pinned.mirror)`; it never calls
      `attach_mutants_at`, which only `run_task` (`saffron/task.py`),
      `run_regate` (`saffron/regate.py`), `package_ready_task`
      (`saffron/task.py`) and `run_commit_review`
      (`saffron/commit_review.py`) call.
    witness: tests/test_cli.py::test_the_mutants_module_docstring_names_stack_mints_own_path_through_ref_commit
    wrong_versions:
      - "The docstring keeps its SA-0363 wording unchanged: \"The reader is `run_task` and `cli._stack_mint`'s shared path in, through `attach_mutants_at`.\""
      - "The rewritten sentence still names `_stack_mint` alongside `run_task`, `run_regate`, `package_ready_task` and `run_commit_review` as sharing one path through `attach_mutants_at`."
      - "The sentence about `attach_mutants_at`'s callers drops `run_commit_review` from the list, so only three names remain."
      - "The sentence about `cli._stack_mint` says it reads the module through `attach_mutants_at` too, dropping the distinction from `ref_commit`."
      - "The `cli._stack_mint` sentence names no reader function at all, so `ref_commit` never appears."
---

## Context

Reviewing `SA-0363` (head `80f41af06f318a54442c07aa978ce3419233310b`), the
module docstring `saffron/mutants.py` carries today reads:

> The reader is `run_task` and `cli._stack_mint`'s shared path in, through
> `attach_mutants_at`. `run_regate`, `package_ready_task` and
> `run_commit_review` read it the same way, with no implementing cell
> (`b-c5da95`).

That groups `cli._stack_mint` with the four callers of `attach_mutants_at`,
as if it reached the module the same way. It does not. `cli._stack_mint`
(`saffron/cli.py:1593-1622`) opens a fresh run and task for `run_stack_batch`'s
`mint` adapter, and reads this module exactly once, at
`saffron/cli.py:1614`:

```
mutants_commit = mutants.ref_commit(pinned.mirror)
```

That commit is only ever passed to `ledger.create_task(... ,
mutants_commit=mutants_commit)` (`saffron/cli.py:1616-1622`) to pin the
value on the task's row. `cli._stack_mint` never calls
`attach_mutants_at`, and no spec in its path is ever attached a mutant at
mint time: that happens later, when `run_task` (or `run_regate`,
`package_ready_task`, `run_commit_review`) reads the row's own pinned
commit. `attach_mutants_at`'s only callers are `run_task`, `run_regate`,
`package_ready_task` and `run_commit_review`. `saffron/task.py`,
`saffron/regate.py` and `saffron/commit_review.py` each confirm the call,
added by `SA-0363`.

So the docstring's claim that `run_task` and `cli._stack_mint` share one
path "through `attach_mutants_at`" is false for `cli._stack_mint`. A reader
of `saffron/mutants.py:1-12` alone would believe minting a task already
attaches its mutants, when minting only pins a commit for later.

## Problem

1. Rewrite `saffron/mutants.py`'s module docstring (`saffron/mutants.py:4`
   through the paragraph's end) into two sentences in place of the current
   one:
   - One sentence naming `run_task`, `run_regate`, `package_ready_task`
     and `run_commit_review` together as the readers that go through
     `attach_mutants_at`, with no implementing cell outside `run_task`
     itself.
   - A second, separate sentence naming `cli._stack_mint`: it reads this
     module too, but only to pin a commit on a fresh task's row, by
     calling `ref_commit` directly, never `attach_mutants_at`.

   Keep the `b-c5da95` citation on the first sentence, and cite this spec
   (`SA-0366`) on the second. Leave the rest of the docstring untouched:
   the writer paragraph about `saffron mutant`, `SA-0339`, and
   `saffron/repos/mirror.py`.

2. Add one witness test to `tests/test_cli.py`, near its existing
   `cli._stack_mint` tests (for example beside
   `test_the_stack_mint_records_the_mutants_refs_commit_and_null_without_one`).
   It reads `saffron.mutants.__doc__`, normalizes its whitespace, and
   splits it into sentences. It finds the sentence mentioning
   `_stack_mint` and asserts `attach_mutants_at` is absent from it while
   `ref_commit` is present. It finds the sentence mentioning
   `attach_mutants_at` together with `run_task`. That sentence must also
   contain `run_regate`, `package_ready_task` and `run_commit_review`,
   while `_stack_mint` stays absent from it.

## Out of scope

- Any change to `cli._stack_mint`'s own behavior, or to `attach_mutants_at`
  or any of its four callers: the finding is about the docstring's prose,
  not about the code paths it describes, which `SA-0363` already built and
  tested correctly.
- Any other docstring, comment or `DESIGN.md`/`CONTEXT.md` prose. Only the
  one paragraph at `saffron/mutants.py:4` is in scope.

## Notes for the agent

**Edit, not new.** The docstring's rewritten sentences are an edit to
existing lines. Nothing here is unreachable until a later spec, so there
are no `pending_symbols`.

**The witness.** A plain `def`, importing `saffron.mutants` inside the
test body. Split the normalized docstring on `". "`, or any splitting
that reliably separates the two sentences in question. Raw newlines will
not work, since the docstring's own line wrapping does not line up with
sentence boundaries.

**Size.** This is prose-only inside one module docstring, plus one new
test function. It sits far under the `bug` ceiling of 1300 changed
tokens.
