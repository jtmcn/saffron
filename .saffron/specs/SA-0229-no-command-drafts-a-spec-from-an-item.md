---
id: SA-0229
title: No command drafts a spec from an item, so the spec chain still runs outside the record
type: feature
priority: 2
depends_on: [SA-0227, SA-0224]
consumes:
  - saffron/draft.py:draft_spec
  - saffron/draft.py:seed_spec_id
estimated_lines: 407
estimate_measured: true
touches:
  - saffron/cli.py
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
  - records/**
  - hooks/**
  - images/**
  - saffron/agents/**
  - saffron/record/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/draft.py
  - saffron/ledger.py
  - saffron/spec_review.py
  - saffron/follow_up.py
  - saffron/end_review.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/preflight.py
  - tests/test_draft.py
  - tests/test_batch.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 34
max_attempts: 3
max_turns: 150
risk: standard
acceptance:
  - claim: >-
      `saffron draft` exits by how the draft ended. `SPEC_DRAFTED` exits 0
      and `SPEC_WITHHELD` exits 1. Both write the task's last recorded text
      at its recorded path in the `--repo` working tree, untracked, with
      `HEAD` unmoved. `GATE_ERROR`, `RATE_LIMITED` and an adapter's raise
      each exit 2 and write no file. The witness drives a draft that is
      clean after a revision, one withheld after a revision, and one
      withheld at its first review. It drives a review with no block, a
      writer and a review each at a rate limit, and a review that raises.
    witness: tests/test_cli.py::test_saffron_draft_writes_the_last_recorded_text_and_exits_by_how_the_draft_ended
    wrong_versions:
      - The first recorded text is written rather than the last.
      - The file is written whenever a text was recorded, so a `GATE_ERROR` after a recorded text writes one.
      - A withheld draft exits 0.
      - A withheld draft exits 2 and writes nothing.
      - A rate-limited draft exits 1.
      - The file is named for the spec id alone, not the recorded path.
      - The written file is staged with `git add`.
      - The file is written under the batch tree rather than `--repo`.
      - A raise from an adapter is caught and exits 1.
  - claim: >-
      The drafted spec's id is one more than the highest number of its
      prefix among the `--repo` working tree's specs, their `done/` and
      this repo's own tasks. Another repo's tasks do not count. The task
      carries that id and the sha256 of the item file's bytes, on a run at
      the pinned `base_sha`. The witness drives a prefix other than `SA`,
      three digits wide. It drives each of the three sources as the
      highest in turn, and a higher id in another repo.
    witness: tests/test_cli.py::test_saffron_draft_numbers_its_spec_past_the_working_tree_its_retirees_and_this_repos_tasks
    wrong_versions:
      - The specs are read from the export at the pinned base rather than the working tree.
      - The repo is upserted under the working tree's path rather than the pinned url, so this repo's tasks do not count.
      - The seed is a fixed `SA-0001` rather than the helper's answer.
      - The task's `spec_sha` hashes the item's path rather than its bytes.
      - "`next_spec_id` is passed a repo id that names no repo, so the ledger is left out."
  - claim: >-
      `saffron draft` exits 2 with no run, no task and no adapter built
      when readiness fails, and when the working tree's specs hold no id
      prefix or more than one. A failed readiness prints its step and
      detail. The witness drives all three.
    witness: tests/test_cli.py::test_saffron_draft_mints_nothing_without_readiness_or_a_single_id_prefix
    wrong_versions:
      - The run is minted before the seed id is read, so a raise leaves a run behind.
      - A failed readiness exits 2 without printing its step and detail.
      - A raise from the seed helper falls back to the first spec file's id.
  - claim: >-
      `_draft_adapters` returns `write`, `review` and `revise`, and each
      runs one spec session cell seeded at the pinned `base_sha`, with
      gates from that base's export. `write` sends `draft_spec`'s prompt,
      then a base line and a snapshot line each on a line of its own,
      under the writer's system prompt and timeout. `review` sends the recorded path and text under
      a sentence saying no file is queued there. `revise` sends the
      recorded text and the review's text. Neither parses the text. The
      stack batch's own review prompt keeps its revision sentence
      unchanged. The witness drives all three adapters on a text with no
      frontmatter, and the stack batch's review on a recorded text. It
      drives `write` on a prompt ending in a newline and on one without.
    witness: tests/test_cli.py::test_a_draft_writes_reviews_and_revises_in_spec_cells_at_the_pinned_base
    mutant:
      file: saffron/cli.py
      find: 'that revision: review that text, and treat a change '
      replace: 'that revision: review that text, and treat any change '
    wrong_versions:
      - The writer's export is read at the mirror's `HEAD` rather than the pinned `base_sha`.
      - The writer's cell is not a spec session, so its Bash keeps its privileges.
      - The writer's agent is given the review's timeout.
      - The writer sends `draft_spec`'s prompt alone, with no base line.
      - The base line is appended straight after the prompt, so a prompt with no final newline runs into it.
      - A newline is always put before the base line, so a prompt ending in one gains a blank line.
      - The writer runs under the spec review's system prompt.
      - The draft's review keeps the stack batch's revision sentence.
      - The draft's sentence replaces the revision sentence for every caller, the stack batch included.
      - The revision is passed no text, so it reads a queued file that does not exist.
      - The review is passed no text, so it reads the path alone.
      - The candidate is parsed from the recorded text, so a draft with no frontmatter raises.
      - The candidate's path is named for the id alone rather than the recorded path.
---

## Context

Backlog item **b-98a3be**, under `DESIGN.md` §3.4. §3.4 says
"`saffron draft <item> --repo <repo>` runs the spec chain as a task." Its
parent `SA-0227` builds the chain. This spec builds the command that drives
it.

Line numbers below were read at `c9411946`. No file under `saffron/` differs there from `3d594729`.

**No command drafts a spec.** `main` registers `replay`, `cell`, `queue`,
`batch`, `reconcile`, `watch`, `fold`, `chains` and `serve`
(`saffron/cli.py:106-203`). None of them takes an item.

**What `SA-0227` adds.** Its spec sits beside this one
(`.saffron/specs/SA-0227-no-task-drafts-a-spec-so-the-spec-chain-runs-outside-the-record.md`).
It adds `saffron/draft.py` with two names this spec calls.

- `draft_spec(ledger, task_id, *, spec_id, item, write, review, revise)`
  drives the chain on a task its caller minted with `spec_id`. It calls
  `write(prompt)` once. That prompt's first line begins `context:`, it
  holds an `id:` line, and it quotes the item between `<item>` and
  `</item>` lines. It calls `review(path, text)` with the recorded path,
  `.saffron/specs/<spec_id>-<slug>.md`, and the latest recorded text. It
  calls `revise(path, text, review_text)` at most once. It sets the task's
  end state itself. An adapter's raise sets `GATE_ERROR` and propagates.
- It returns a frozen `Drafted(state, path, text)`. `state` is one of
  `SPEC_DRAFTED`, `SPEC_WITHHELD`, `GATE_ERROR` and `RATE_LIMITED`. `path`
  and `text` are the last recorded spec text's, or `None` when none was
  recorded. It carries no detail.
- `seed_spec_id(specs_dir)` returns the highest-numbered spec id among the
  `*.md` names in `specs_dir` and its `done/`, digits as written. It
  raises `ValueError` on no prefix or more than one.

`SA-0227` says nothing of the task's `spec_sha`. Its caller mints the task,
so this spec sets it.

**The parts this command reuses.**

- `_batch` runs `preflight.check_readiness` and builds a `PinnedBase` from
  its `mirror`, `url` and `base_sha` (`saffron/cli.py:1554-1604`).
- `follow_up.next_spec_id(origin_id, specs_dir, ledger, repo_id)` returns
  one more than the highest number of the origin's prefix. It reads the
  live files, their `done/` and this repo's tasks
  (`saffron/follow_up.py:50-78`).
- `_stack_mint` upserts the repo at the pinned url. It opens a run at
  `base_sha` and a task on it (`saffron/cli.py:1036-1061`).
- `_stack_review` (`saffron/cli.py:878-949`) and `_stack_revise`
  (`:952-1033`) each run one spec session cell. Given no layer, each seeds
  it at `base_sha`. Each reads its prompt and gates from that base's export
  (`:900-903`, `:986-989`). Each reads only `candidate.spec.id` and
  `candidate.path.name` from its candidate.
- A follow-up's writer runs one spec session cell through
  `end_review.layer_cell` and `spec_review.run_spec_writer`
  (`saffron/cli.py:1126-1150`).

**The review's sentence is wrong for a draft.** Given a spec text, the
review prompt says a revision replaces the queued file
(`saffron/cli.py:923-931`). A draft has no queued file in either review.

**A task at a spec's own sha reads as done.** `build_queue` skips a spec
whose id and sha have a task in `DONE_STATES`
(`saffron/scheduler.py:905-908`). `SPEC_DRAFTED` and `SPEC_WITHHELD` are in
that set (`:69-83`). A draft task carrying the drafted file's sha would
hide that spec from every batch once the operator commits it unchanged.

## Problem

1. **The subcommand.** `saffron draft <item> --repo <repo>`. `--repo`
   defaults to the current directory, as `batch`'s does. The command runs
   inside the handler that maps any raise to exit 2
   (`saffron/cli.py:271-279`). Add `draft` to the module docstring's list.
2. **Readiness.** Run it as `_batch` does, then build the `PinnedBase`. A
   failed readiness prints `draft: readiness failed at <step>: <detail>`
   and exits 2.
3. **The id.** Call `seed_spec_id` over `--repo`'s working tree
   `.saffron/specs`. Then upsert the repo at the pinned url, as
   `_stack_mint` does. Then call `follow_up.next_spec_id` over the same
   directory and that repo id. A spec the operator has not committed still
   holds its id. A raise from `seed_spec_id` reaches `main` before any run
   or task exists.
4. **The mint.** Open one run at the pinned `base_sha` and one task on it.
   The task carries the new id, `_branch` of it and `context.prompt_sha()`.
   Its `spec_sha` is the sha256 of the item file's bytes, never the drafted
   text's.
5. **The adapters.** Add `_draft_adapters(*, pinned, repo, out_dir,
   spec_id)`. It returns `write`, `review` and `revise` in `draft_spec`'s
   shapes.
   - `write` runs one spec session cell at the pinned `base_sha`, as a
     follow-up's writer does. It exports `.saffron/` at `base_sha` under
     `out_dir / "spec-write" / <id>`, the directory `_stack_revise` uses.
     Its system prompt is `spec_writer_system_prompt` of that export's
     policy. Its agent is named for the id, with `SPEC_WRITER_TIMEOUT_S`.
     Its prompt is the prompt it is given, then the `base:` line and the
     snapshot sentence a revision prompt sends (`saffron/cli.py:1005-1006`).
     Each added line stands alone, with no blank line before them. That
     holds whether or not the given prompt ends in a newline.
   - `review` calls `_stack_review`'s callable with a candidate, no layer,
     and `spec_text` set to the recorded text.
   - `revise` calls `_stack_revise`'s callable with a candidate, no layer,
     the recorded text and the review's text.
   - The candidate carries the recorded path, the minted id and the
     text's sha. It never parses the text. A draft whose frontmatter does
     not parse is still the review's to judge.
6. **The review's sentence.** `_stack_review` takes an optional sentence
   that stands in for its revision sentence. The draft passes one saying
   no file is queued at that path, and that the text below is the drafted
   spec to review. With none given, the stack batch's prompt is unchanged
   byte for byte. Leave its three string literals as they are.
7. **The end.** Print one line naming the id and the state.
   On `SPEC_DRAFTED` or `SPEC_WITHHELD`, write `Drafted.text` to
   `Drafted.path` under `--repo`, then print that path. `SA-0227` makes
   both the last recorded spec text's, so no ledger read is needed. Exit 0 for
   `SPEC_DRAFTED` and 1 for `SPEC_WITHHELD`. Every other state exits 2 and
   writes nothing. Commit nothing, stage nothing, and open no pull request.

The item file is read as bytes and decoded once. Nothing parses it. Core
imports nothing from `records`.

## Out of scope

- Rendering a backlog record to an item file. The operator passes a file
  (§3.4).
- Closing the run. `_stack_mint` leaves its runs open too
  (`saffron/cli.py:1036-1061`).
- The `runtime.unattended_refusal()` check a batch makes first
  (`saffron/cli.py:1529-1533`). An operator starts a draft, so it is
  attended.
- A budget over the whole draft. Each session keeps its own caps in
  `saffron/spec_review.py`.
- `CLAUDE.md`'s command list. The operator adds the line by hand.

## Notes for the agent

**Most of this change is new code.** The command and the adapters are not
at base. So criteria 1 to 3 declare a witness and no mutant. The
`witness` gate reports `skip` for them. Criterion 4 also edits
`_stack_review`, so it declares a mutant on the stack batch's revision
sentence. Its witness must compare that whole sentence, not a fragment.
The wrong versions under each criterion are what its witness must kill. Do
not run them yourself.

**Every witness must fail at base.** At base `main` has no `draft`
subcommand, so `main([... "draft" ...])` raises `SystemExit`.
`cli._draft_adapters` does not exist. Import nothing at module scope that
this change adds.

**One rig drives criteria 1 to 3.** Build it once in a helper.

- Make `--repo` a git repository holding the arranged spec files, with
  one commit. Use `--allow-empty`, since one arrangement holds no spec.
- Fake readiness with `_readiness_passes`. Its pinned `base_sha` is
  `"a" * 40` and its url is `https://github.com/o/r.git`.
- Monkeypatch `cli._draft_adapters` to record its calls and return three
  scripted callables. Let the real `draft.draft_spec` run over them.
- Use the prefix `TE` with three digits, so a fixed `SA` seed fails.
- Give each `main` call its own `--home`, except where criterion 2 needs
  the ledger to carry tasks across calls.
- Build each session with its fields as keywords. The `types` gate reads a
  dict unpacked into a session as every field's union, and fails it.

**Criterion 1.** Use one `--repo` per case. Assert the exit code, and the
exact file list under `.saffron/specs`. For a written case, assert the
file's text, that `HEAD` is unmoved, and that `git status --porcelain`
shows the file alone, untracked. A review whose findings hold a `blocker`
tagged `scope` escalates at once. A `blocker` tagged `build` revises.

**Criterion 2.** Seed one `--home` ledger first with a `TE-011` task under
the pinned url, and a `TE-040` task under another url. Then run three
drafts in order on that home. In the first, the ledger holds the highest
id, so the draft is `TE-012`. In the second, a live `TE-020` is highest. In
the third, a retired `TE-030` is highest. Read every task's `spec_id`,
`spec_sha` and `state`, and every run's `base_sha`, after the last call.

**Criterion 3.** Assert the `runs` and `tasks` tables are both empty after
each case, and that `_draft_adapters` was never called.

**Criterion 4.** Reuse `_spec_session_rig`. Fake `implement.run_agent`,
`spec_review.run_spec_writer` and `spec_review.run_spec_review`. Each fake
session calls its `agent` once and records its container, system prompt
and prompt. Drive `write`, then `review` and `revise` on a recorded text
with no frontmatter, at a path whose file is absent at base. Then drive
`_stack_review` with no sentence given on a recorded text. Assert the
writer's whole prompt, and each review and revision prompt's `spec:`,
`base:`, sentence and tag lines. Assert no layer was fetched, every cell's
`tree_base`, and the draft cells' branch, `thread_env` and `cap_add`.
Assert each agent's spec id and timeout.

**Measured on a prototype.** A prototype at this spec's commit, with
`SA-0226`'s and `SA-0227`'s revised prototypes applied under it, passed all
four witnesses. Each failed with `saffron/cli.py` reverted. Its diff
measured 1626 changed tokens. Each of the 30 wrong versions above was
applied to it as an edit under a fresh bytecode cache. Each failed its own
criterion's witness. So did criterion 4's mutant.
