---
id: SA-0301
title: A stack batch cannot end before its end review, so the end review grades heads from before the loop's review commits
type: feature
priority: 2
depends_on: [SA-0300]
estimated_lines: 270
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
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/batch.py
  - saffron/end_review.py
  - saffron/follow_up.py
  - saffron/qualify.py
  - saffron/finish.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/spec_review.py
  - saffron/repos/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/record/**
  - tests/test_batch.py
  - tests/test_end_review.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 29
max_attempts: 3
max_turns: 135
acceptance:
  - claim: >-
      `saffron batch --stack --defer-end-review` hands `run_stack_batch` an
      `end_review` callable that opens no cell and never calls
      `end_review.run_end_review`. It hands `follow_ups=None` and
      `finish=None`. It still hands `review`, `cite`, `mint`, `revise`,
      `open_prs` and `stack_base_alive`, and the same `reserve_usd` and `writer_usd` a batch
      without the flag holds back. When readiness fails it hands
      `end_review=None` and writes no deferral file.
    witness: tests/test_cli.py::test_a_deferred_stack_batch_hands_run_stack_batch_no_end_review_follow_ups_or_finish
    wrong_versions:
      - The deferring callable is `_stack_end_review`'s own, so the end review still runs in the batch.
      - "`follow_ups` is still handed, so the writer reads an empty review and the batch still writes follow-ups."
      - "`finish` is still handed, so the finishing layer commits before the review commits land."
      - "`reserve_usd` is handed as 0.0 when deferring, so the order's tasks spend the reserve."
      - "`writer_usd` is handed as 0.0 when deferring, so the order's tasks spend the writer's share."
      - "`review`, `cite` or `stack_base_alive` is dropped along with `follow_ups`."
      - The deferring callable is built before readiness passes, so a failed night still writes a deferral file.
  - claim: >-
      Called with a batch key, a reserve and a specs map, the deferring
      callable writes `deferred.json` into the batch tree's directory for
      that batch key, where `_stack_finish` writes `findings.json`. Its keys are exactly `batch_id`, `reserve_usd`, `writer_usd`,
      `base_sha`, `url`, `mirror`, `repo` and `specs`. `batch_id` is the
      key as an integer. `reserve_usd` is the reserve it was handed.
      `writer_usd` is the writer's share `_batch` held. `base_sha`, `url`
      and `mirror` are the pinned base's. `repo` is the resolved `--repo`.
      `specs` maps each spec id it was handed to an object that
      `intake.Spec.model_validate` turns back into an equal `Spec` with
      the same `model_fields_set`. It
      then prints one line naming the batch id, the reserve and the
      command `saffron finish <batch id> --repo <repo>`.
    witness: tests/test_cli.py::test_a_deferred_end_review_writes_what_saffron_finish_reads_and_names_the_command
    wrong_versions:
      - "`reserve_usd` recomputed as `--budget` times `RESERVE_SHARE` instead of the reserve handed."
      - "`batch_id` written as the string key."
      - "`specs` written as spec ids alone, with no spec fields."
      - "Each spec dumped with every default included, so a criterion with no `wrong_versions` dumps an empty list that `model_validate` refuses."
      - "Each spec dumped with `exclude_defaults`, so a field declared at its default value drops out of `model_fields_set`."
      - "`writer_usd` written as the reserve instead of the writer's share."
      - The file written under the operator's checkout instead of the batch tree.
      - The printed command names no `--repo`.
      - A key added or missing, such as the batch's budget.
  - claim: >-
      `saffron batch --defer-end-review` without `--stack` exits 2 with an
      error naming both flags. No readiness probe runs and no batch row is
      created.
    witness: tests/test_cli.py::test_defer_end_review_without_stack_is_refused_before_readiness
    wrong_versions:
      - The flag is accepted without `--stack` and a plain batch runs.
      - The refusal comes inside `_batch` after the readiness probe.
  - claim: >-
      A deferral file that cannot be written does not end the batch. The
      guard catches any `Exception`. That covers an `OSError` creating the
      batch key's directory, an `OSError` writing `deferred.json` inside a
      directory that exists, and a `ValueError` encoding the JSON. In each
      the deferring callable prints one line naming the
      exception's type and prints no `saffron finish` command. `saffron
      batch` then exits on its own stop reason.
    witness: tests/test_cli.py::test_a_deferral_file_that_cannot_be_written_is_named_and_the_batch_ends_on_its_own_stop
    wrong_versions:
      - The write's `OSError` propagates out of the callable, so the batch closes `INFRASTRUCTURE`.
      - The guard wraps creating the directory alone, so a raise writing the file closes the batch `INFRASTRUCTURE`.
      - The guard catches `OSError` only, so a `ValueError` encoding the JSON closes the batch `INFRASTRUCTURE`.
      - The failure is swallowed in silence.
      - The `saffron finish` command is printed although no file exists for it to read.
  - claim: >-
      Without the flag, `saffron batch --stack` still hands
      `run_stack_batch` the `end_review` callable `_stack_end_review`
      builds, over the reserve it holds.
    witness: tests/test_cli.py::test_a_stack_batch_holds_a_quarter_of_its_budget_and_reads_its_stack_at_the_pinned_base
    preserves: true
  - claim: >-
      Without the flag, `saffron batch --stack` still hands
      `run_stack_batch` the follow-up writer and the writer's share.
    witness: tests/test_cli.py::test_a_stack_batch_holds_the_writer_share_and_passes_its_follow_up_writer
    preserves: true
  - claim: >-
      Without the flag, `saffron batch --stack` still hands
      `run_stack_batch` the `finish` callable `_stack_finish` builds.
    witness: tests/test_cli.py::test_a_stack_batch_commits_its_finish_and_survives_a_raise
    preserves: true
---

## Context

Backlog item **b-8a0c9a**. A stack batch's end review grades the heads
PACKAGE pushed. The delegate's review commits land after PACKAGE, so the
end review grades code the loop already changed. Runs 32, 33, 35, 44 and
45 each found most of its findings fixed on the branches by then. Two
follow-ups cost $6.06 in run 32 and both were wasted.

The operator chose a separate finish command. A `--stack` batch gains a
way to end after its order drains without running the end review. A new
`saffron finish <batch id> --repo .` later runs the end review on each
layer's current branch head, with the reserve the batch held. It then
runs the follow-ups and the finishing layer as the batch would have. The
work is split into five specs. This is the parent.

**`run_stack_batch` runs three callables after its order.** It hands
`end_review` the batch key, the reserve and a specs map. It calls
`end_review` whenever one is handed, whatever the stop reason
(`saffron/batch.py:852`, `:863`). It calls `follow_ups` only when one is handed (`:866`). It calls
`finish` only when one is handed (`:908-909`). The batch row closes after
all three. A `None` `follow_ups` needs nothing else, and a `None` `finish`
is skipped.

**`_batch` builds all three under `--stack`, once the scan resolves.** It
holds back `reserve_usd` and `writer_usd` through
`_stack_admission_shares(args.budget)` (`saffron/cli.py:1984-1985`). It
builds `_stack_end_review`, `_stack_follow_ups` and `_stack_finish` inside
the readiness and scan guard (`saffron/cli.py:2116`, `:2139`, `:2148`). It
hands them as `end_review=`, `follow_ups=` and `finish=`
(`saffron/cli.py:2198`, `:2203`, `:2205`). Each stays `None` when
readiness or the scan fails.

**The flag parser refuses a bad pairing with `error`.** `main` calls
`watch_parser.error` for a flag that needs another (`saffron/cli.py:272`,
`:274`). At base `saffron batch --defer-end-review` exits 2 with
`unrecognized arguments`, from the top parser, whose usage names no
`--stack` (measured on the host).

## Problem

Nothing lets a stack batch end before its end review. So no later command
can grade the heads the loop's review commits produce.

Add a `--defer-end-review` flag to `saffron batch`. Refuse it without
`--stack` through the batch parser's `error`, before the ledger opens.

Under both flags, build a deferring `end_review` callable beside where
`_stack_end_review` is built today, and hand it in that one's place. Hand
`follow_ups=None` and `finish=None`. Leave every other keyword as it is,
so the order still holds back the reserve and the writer's share.

The callable writes `deferred.json` into `finish/<batch key>/` under the
batch tree (`out_dir`). That is the directory `_stack_finish` writes
`findings.json` into. It then prints the `saffron finish` line. The file
is the contract `SA-0305` reads. A write that raises is printed and
swallowed, as `_stack_end_review` swallows its own raise.

## Out of scope

- **Grading current heads.** `SA-0302` makes the end review read each
  layer's current branch head. `SA-0303` makes qualification and the
  follow-up writer read the same heads.
- **Resuming the batch.** `SA-0304` lets `run_stack_batch` resume a closed
  stack batch's tail on its own batch id.
- **The command.** `SA-0305` adds `saffron finish <batch id> --repo .`.
- **Making deferral the default.** The operator kept the in-batch end
  review as the default (see the notes).
- **`DESIGN.md` §4.2.1, `CONTEXT.md` and the spec loop's skill.** The
  operator edits them by hand in this spec's pull request.
- **An `end_reviews` row for a deferred batch.** The deferring callable
  records none. `SA-0305` refuses a batch whose layers hold one, so a row
  written here would refuse every deferred batch. No witness drives it,
  because the batch rigs hold no layer.
- **`saffron/batch.py`.** It needs no change. A `None` `follow_ups` and
  `finish` already skip both.

## Notes for the agent

**The chain this spec heads.** Each child is its own spec.

- `SA-0302` (depends on this one). `LayerFields` gains `diff_base`, and
  a resolver fetches each layer's branch. A layer's base is its
  predecessor's current head when its own head contains it, else the
  predecessor's recorded head when contained. A bottom layer's base is
  its merge base with the fetched default branch, bounded below by the
  commit PACKAGE built it on. A layer containing no candidate, or whose
  branch is gone, gets `error` on both lenses at cost 0. `run_end_review`
  takes the resolver, and `StackReview.fields` holds every layer either
  walk resolved.
- `SA-0303` (depends on `SA-0302`). Qualification and the follow-up
  writer read the graded fields from `StackReview`.
- `SA-0304` (depends on this one). `run_stack_batch` takes a resume that
  carries a closed batch's id, budget, recorded status, top layer and
  specs. It runs the tail on that id, leaves the row as the night
  closed it, and returns the tail's reason. It runs follow-ups only when the recorded status is `DRAINED`. So a
  deferred batch closed `INCOMPLETE` skips them, where the in-batch path
  would run them. That is a stated, conservative difference (see below).
- `SA-0305` (depends on `SA-0303` and `SA-0304`). `saffron finish <batch
  id> --repo .` reads this spec's `deferred.json` and refuses a batch
  already reviewed. It builds the adapters `_batch` builds from the pinned
  base in the file, and calls `run_stack_batch` with the resume.

**`deferred.json` is the contract `SA-0305` reads.** One JSON object with
these eight keys and no others.

- `batch_id`: the batch key, as an integer.
- `reserve_usd`: the reserve the callable was handed, as a number.
- `writer_usd`: the writer's share `_batch` held back, as a number.
- `base_sha`, `url`, `mirror`: the pinned base's three fields. `mirror` is
  a path string.
- `repo`: the resolved `--repo` path, as a string.
- `specs`: each spec id the callable was handed, mapped to that `Spec`'s
  fields as JSON.

The batch's budget and status stay on its ledger row. The row closes after
this file is written, so the file cannot hold the status. The row holds
`_stop`'s result, not the reason the order's own drive returned. `_stop`
turns any reason but `INFRASTRUCTURE` into `INCOMPLETE` when a task was
left in flight (`saffron/batch.py:935`). The in-batch path gates
follow-ups on the drive's own reason (`saffron/batch.py:872`). `Ledger`
has no reader for a batch's status, and a folded ledger has no `batches`
row at all (`saffron/record/fold.py:9-13`). `SA-0304` and `SA-0305` own
those gaps. This spec records nothing of the status.

**Dumping a `Spec` so it validates again.** A plain
`model_dump(mode="json")` writes an empty `wrong_versions` for a criterion
that declares none, and `Spec.model_validate` refuses it. With
`exclude_unset=True` every spec in `.saffron/specs/done/SA-02*.md` round
trips to an equal `Spec` with the same `model_fields_set`, over 85 specs
(measured on the host). Give one of the second witness's `Spec`s a
criterion with no `wrong_versions`, so the plain dump fails it. Give the
other a field declared at its default, such as `priority=3`. An
`exclude_defaults` dump then loses it from `model_fields_set` (measured).

**Why a flag and not the default.** The launchd night runs `saffron
batch` without `--stack` (`docs/host/dev.saffron.batch.plist:29`). An
unattended `--stack` night has nobody pushing review commits. So its
packaged heads are its current heads, and its end review is right today.
The spec loop is the one caller that pushes review commits, and its skill
passes the flag. The flag also keeps every existing
`--stack` test, which the three `preserves` witnesses hold.

**Why the batch tree.** `batches` rows append no fact
(`saffron/record/fold.py:9-13`). A new fact kind needs an ontology entry
a cell cannot land, and a ledger column touches `saffron/ledger.py`, which
`elevate_on` lists.

**New code, so no criterion declares a mutant.** The flag, the deferring
callable and its wiring do not exist at base. `witness` will report
`skip` for the first four criteria.

**At base each new witness fails in its body.** None imports a name the
change adds. Each calls `main` with `--defer-end-review`. At base argparse
exits 2 with no error naming `--stack`. So the third witness fails on its
message, and the other three fail on `SystemExit`.

**The witnesses reuse the batch rigs.** Use `_readiness_passes`,
`_fake_batch_resolution` and a faked `run_stack_batch`, as
`test_a_stack_batch_holds_the_writer_share_and_passes_its_follow_up_writer`
does. In the first two, patch the follow-up module's share to 0.125, as that
test patches `WRITER_SHARE` (`tests/test_cli.py:8503`). With `--budget 42` the batch then
holds a reserve of 10.50 and a writer's share of 5.25. Unpatched, both
shares are 0.25 (`saffron/follow_up.py:32`), so the two values coincide
and neither witness could tell them apart.

- **The first** fakes `_stack_end_review` and `end_review.run_end_review`,
  each recording its calls. The faked `run_stack_batch` calls the handed
  `end_review` once. Assert neither fake ran and that both `follow_ups`
  and `finish` are `None`. Assert `review`, `cite`, `mint`, `revise`,
  `open_prs` and `stack_base_alive` are not `None`. Assert `reserve_usd == 10.5` and
  `writer_usd == 5.25`. Then fail readiness, as that test's second case
  does, and assert `end_review` is `None` and no `deferred.json` exists
  under the home.
- **The second** has the faked `run_stack_batch` call the handed
  `end_review` with `"7"`, `3.25` and two `Spec`s. The reserve handed then
  differs from 10.50. Load the file and assert its key set and each value.
  Assert each validated `Spec` equals the one handed, and that its
  `model_fields_set` equals the original's. Assert the printed line holds
  `7`, `3.25` and `saffron finish 7 --repo <repo>`.
- **The third** calls `main` with `batch --defer-end-review` and no
  `--stack`, with `check_readiness` replaced by a recorder. Assert
  `SystemExit` with code 2, stderr naming both flags, no readiness call
  and no batch row in the home ledger.
- **The fourth** runs three arrangements, each with a fresh home. In the
  first, a plain file at `<home>/batches/v0/finish` makes creating the
  directory raise. In the second, `<home>/batches/v0/finish/7/deferred.json`
  is created beforehand as a directory. The directory step then succeeds
  and the write itself raises. In each, the faked `run_stack_batch` calls
  the handed `end_review` with `"7"` and returns `"DRAINED"`. Assert `main`
  returns 0, prints `batch: DRAINED`, prints a line naming the exception's
  type, and prints no `saffron finish`. Keep the guard as broad as
  `_stack_end_review`'s, which catches `Exception` (`saffron/cli.py:869`).
  A third arrangement raises a `ValueError` inside the guard. The faked
  `run_stack_batch` patches `dump` and `dumps` on the `json` module to
  raise it. It patches them right before it calls the handed `end_review`
  and restores them after. `saffron/cli.py` imports no `json` at base, so the cell adds
  `import json`, and that binds the same module object. Patch both,
  because `json.dump` never calls `json.dumps` (its source names no
  `dumps`, measured). Assert the printed line names `ValueError`.

**Four tests call `cli._batch` with a hand-built `Namespace` that has no
`defer_end_review`** (`tests/test_cli.py:5918`, `:6915`, `:6942`,
`:6998`). Each sets `stack=False`. Read `args.defer_end_review` only
inside the `--stack` branch, or add the field to those four tests.

**`SA-0300` is not under you.** It adds a separate read-only command to
`saffron/cli.py`. This spec depends on it only because both edit that
file. Rely on nothing it adds.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** The estimate covers about 55 lines in `saffron/cli.py` and four
witnesses of about 215 lines.
