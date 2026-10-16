---
id: SA-0295
title: A stack batch's citation check has no adapter that reads the commit its spec review reads, so `saffron batch --stack` never runs it
type: bug
priority: 2
depends_on: [SA-0279, SA-0294]
estimated_lines: 90
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
  - saffron/task.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/end_review.py
  - saffron/spec_review.py
  - saffron/repos/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/record/**
  - tests/test_batch.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 22
max_attempts: 3
max_turns: 110
acceptance:
  - claim: >-
      The cite adapter resolves the commit a spec review reads for each of
      the three seeds. With a layer it fetches that layer's branch, even
      when the batch has a stack base. With no layer it fetches the stack
      base's branch. With neither it uses the pinned `base_sha` and fetches
      nothing. It hands the citation check that commit and the spec text.
      The text is a recorded `spec_text` when one is given, read from no
      tree. Otherwise it is the queued file read at the pinned `base_sha`,
      never at a fetched head and never from the operator's checkout. A
      queued file absent at `base_sha` raises `ValueError` naming the path,
      and the check is never called.
    witness: tests/test_cli.py::test_a_stack_batchs_citation_check_resolves_at_the_commit_its_review_reads
    wrong_versions:
      - The check handed the pinned `base_sha` whatever the seed, so a layer's citations resolve at the wrong commit.
      - The queued file read at the fetched head instead of the pinned `base_sha`.
      - The queued file read from the operator's checkout.
      - The queued file read even when a recorded `spec_text` is given.
      - The stack base's branch fetched when a layer is given, so a predecessor no longer outranks it.
      - A fetch made with no layer and no stack base, instead of the pinned `base_sha`.
      - The check called with `None` for an absent queued file.
  - claim: >-
      A cite and the review after it share one fetch. For a candidate with
      a layer, and for one with no layer under a stack base, the cite
      adapter fetches once. The review then fetches nothing, and its cell
      starts at the commit the check was handed. A review after a cite still
      fetches its own branch when its layer differs, or when its candidate
      differs on the same layer. A second review with no cite between them
      fetches again.
    witness: tests/test_cli.py::test_a_stack_batchs_citation_check_and_spec_review_read_one_fetch
    wrong_versions:
      - The cite adapter fetches through its own call and `_stack_review` fetches again, so the two can read different commits.
      - The review takes the shared commit and leaves it in place, so a later review with no cite before it reads that commit without a fetch.
      - The shared commit keyed by spec id alone, so a review with another layer reads the first layer's commit.
      - The shared commit keyed by layer alone, so a review of another candidate on that layer reads the first candidate's commit.
      - The commit shared only for a layer, so the stack base's seed still fetches twice.
  - claim: >-
      `saffron batch --stack` builds the cite adapter once readiness passes. It passes the pinned base and the order's stack base, and it
      hands `_stack_review` and the cite adapter one shared `heads` object.
      It passes the adapter to `run_stack_batch` as `cite`. A failed
      readiness builds none and passes `cite=None`. A batch without
      `--stack` never builds it.
    witness: tests/test_cli.py::test_a_stack_batch_passes_run_stack_batch_its_citation_check
    wrong_versions:
      - "`_batch` builds the cite adapter and `_stack_review` each with its own `heads`, so the two fetch separately."
      - The cite adapter built without the order's stack base.
      - The cite adapter built when readiness fails.
  - claim: >-
      `_stack_runner`, `_stack_review` and `_stack_revise` still seed on a
      predecessor's branch, else the stack base's, else the pinned
      `base_sha`.
    witness: tests/test_cli.py::test_a_stack_batchs_spec_with_no_predecessor_is_seeded_on_the_pull_request_its_order_stacks_on
    preserves: true
  - claim: >-
      `_stack_review` still seeds its cell at a layer's fetched head, or at
      the pinned `base_sha` with no layer, and still reads its prompt and
      gates from the `base_sha` export.
    witness: tests/test_cli.py::test_a_spec_review_fills_cores_prompt_from_its_base_policy_in_a_cell_at_its_predecessors_head
    preserves: true
---

## Context

Backlog item **b-d31930**, filed from the spec loop's run 40. It cites
`DESIGN.md` §3.2. `SA-0273` was written against one commit and ran after
nine landed specs had moved the files it cited. The batch's spec review
found 15 citations pointing at the wrong code and blocked it, at a cost of
$2.32. `driver.py cite` finds that shape in seconds.

The operator split the fix in two. `SA-0294` adds the citation check to
core and a `cite` keyword on `run_stack_batch`. With `cite` given, the
batch calls it before each spec review and refuses the candidate on any
defect. This spec is the second half. It builds the callable `saffron
batch --stack` passes as `cite`, bound to the commit the review reads.

**Only `_stack_review` knows that commit.** In `saffron/cli.py`,
`_stack_review`'s callable picks a branch with `_seed_branch(layer,
stack_base)`. It fetches that branch fresh with
`package_phase.fetch_parent_branch(pinned.mirror, pinned.url, branch)`.
With no branch it uses `pinned.base_sha`. It seeds the review's cell at
that commit through `end_review.LayerFields`' `head`, and the prompt names
`.saffron/specs/{candidate.path.name}` in that tree. `_stack_revise`
holds a second copy of the same four lines.

**`_seed_branch` orders the three seeds.** A predecessor's branch outranks
the stack base's, and neither means `None` (`saffron/cli.py`, the
function `_seed_branch`).

**A branch moves between two fetches.** `fetch_parent_branch` reads a
parent's head fresh every call, because a predecessor's branch does not
hold still (`saffron/phases/package.py:173-177`). So a check and a review
that each fetch can read two different commits.

**`_batch` builds every stack callable once the scan resolves.** Under
`--stack` it builds `_stack_review`, `_stack_revise` and the rest inside
`if readiness.ok`. They sit in the `else:` of the `try` around
`_resolve_queue`.
`stack_review`, `stack_revise` and the rest stay `None` until then.
`stack_runner` keeps its `_no_stack_candidate_should_run` default. It
passes them to `run_stack_batch` by keyword (`saffron/cli.py`, the
function `_batch`).

**A queued spec's text is read at `base_sha`.** ADR 7 says every spec the
operator queued is first read at `base_sha`. A stack batch runs other text
only as a revision or a follow-up. `_stack_revise` follows it. Handed
no text, it reads `.saffron/specs/{candidate.path.name}` with
`git_mirror.file_at(pinned.mirror, pinned.base_sha, path)`. It raises
`ValueError` naming the path before any cell when that returns `None`
(`saffron/cli.py`, the function `_stack_revise`). `file_at` returns `None`
when the tree lacks the path (`saffron/repos/mirror.py:245-251`).

## Problem

Nothing hands `SA-0294`'s check the commit a spec review reads, so
`saffron batch --stack` never runs it.

Add one helper to `saffron/cli.py` that resolves the commit from the
pinned base, a layer and a stack base, as `_stack_review` does today.
`_stack_review`, `_stack_revise` and the new cite adapter all call it, so
the resolution exists once.

Add the cite adapter, a factory beside `_stack_review` named
`_stack_cite`. It takes the pinned base, an optional stack base and an
optional `heads`. Its callable takes a candidate, a layer or `None`, and
a recorded `spec_text` or `None`, as three positional arguments. It resolves the commit and takes the text
as `_stack_revise` does, so a queued file is read at `base_sha`. It calls
`SA-0294`'s check with the text and the commit, and returns what the check
returns. So citations resolve in the tree the review's cell starts in.

`heads` is a dict that `_batch` builds once and passes to both factories.
The cite callable stores the commit it resolved under the candidate's spec
id and the layer's spec id, or `None`. `_stack_review` gains the same
optional `heads` keyword. Its callable pops a matching entry and seeds
there with no fetch. With no entry it resolves its own commit as today.

In `_batch`, build the adapter under `--stack` beside `_stack_review`. Pass
it to `run_stack_batch` as `cite`, `None` until the scan resolves.

## Out of scope

- **The check itself, the `cite` keyword and how `run_stack_batch` acts on
  a defect.** Those are `SA-0294`'s.
- **`driver.py check`.** The item names it as one home for the check. The
  operator chose the batch's own check.
- **`_stack_revise` and the draft path sharing `heads`.** A revision is
  followed by a fresh cite and review. `_draft_adapters` passes no `heads`
  and runs no check.
- **`_stack_runner`'s fetch.** The cell's own seed is fetched at build time
  as today.

## Notes for the agent

**The one call into `SA-0294`.** This spec was written beside `SA-0294`'s
draft. That draft adds `citation_defects(mirror, commit, text)` to
`saffron/spec_citations.py`, returning a list of defect lines. It declares
`cite` as a callable of the candidate, its predecessor and the recorded
text or `None`, returning that list. Call
`citation_defects(pinned.mirror, head, text)`. If `SA-0294` landed another
name or shape at your base, match it and keep each criterion's behaviour.

**Why the queued text is read at `base_sha`.** The text a cell runs is the
queued file at `base_sha` (ADR 7). The commit is the head the cell is cut
from. A stack base's branch cut before the spec was queued lacks the file at
its head. Reading the text at `base_sha` checks the spec that will run against
the tree it will run in.

**New code, so no criterion declares a mutant.** The adapter, the `heads`
handoff and the `cite` wiring do not exist at base. `witness` will report
`skip` for the first three criteria. The helper extraction is an edit, and
the two `preserves` witnesses hold it. Both exist at base.

**At base each new witness fails in its body.** None imports a name the
change adds. The first two call `cli._stack_cite`, which raises
`AttributeError` at base. The third sets `cli._stack_cite` with
`monkeypatch.setattr`, which raises on a missing attribute.

**The first two witnesses** use `_spec_session_rig` with
`.saffron/specs/SY-1-x.md`. That file reads differently at the rig's base
commit, at its head commit and in the operator's checkout. Leave
`_spec_session_rig` unchanged, since both `preserves` witnesses assert its
`"d" * 40` fetch. Inside each new witness, monkeypatch
`package.fetch_parent_branch` over the rig's double with one that records
each branch and returns the mirror's `HEAD` commit. A fetched commit is
then real and readable. Monkeypatch `SA-0294`'s check, at the name `cli` calls it by, with a double
that records what it was handed. Run the witness with `monkeypatch.chdir(rig.repo)`, so a read from the
checkout is caught by its text. Drive a layer through an adapter built
with a stack base and through one built without. Drive no layer on each
too: `cite(c, None, None)` with a stack base hands the check the fetched
`HEAD` after one fetch of the stack base's branch. Without one it hands
the check `base_sha`, fetches nothing, and reads the text queued there. Pass a candidate whose
file is absent to drive the `ValueError`. Pass that same candidate with a
recorded `spec_text` too, which must reach the check with no raise.

**The second witness** runs five sequences. Each builds a fresh `heads`
dict and a fresh cite and review pair over it, and clears the fetch log
first. Take the cell's start commit from the rig's `cell_up_calls`.

- **A layer, no stack base.** `cite(c, A, None)`, then `review(c, A)`.
  One fetch of `A`'s branch, and the cell starts at the commit the check
  was handed.
- **No layer, a stack base.** Build the pair with a stack base.
  `cite(c, None, None)`, then `review(c, None)`. One fetch of the stack
  base's branch, and the same start commit.
- **Another layer.** `cite(c, A, None)`, then `review(c, B)`. Two fetches,
  `A`'s branch then `B`'s.
- **Another candidate.** `cite(c, A, None)`, then `review(d, A)`. Two
  fetches of `A`'s branch.
- **A second review.** `cite(c, A, None)`, then `review(c, A)` twice. Two
  fetches of `A`'s branch.

A prototype over this rig failed one sequence for each wrong version.
Keyed by spec id alone fails the third. Keyed by layer alone fails the
fourth. Leaving the entry in place fails the fifth. Sharing only for a
layer fails the second. Fetching in both fails the first.

**The third witness** takes its two `--stack` cases from
`test_a_stack_batch_passes_run_stack_batch_its_spec_revision`, where
readiness passes and then fails. It takes the third case, a batch
without `--stack`, from
`test_a_stack_batch_wires_its_spec_review_and_mint_once_readiness_passes`.
That case fakes `run_batch` too and asserts no `_stack_cite` call. Fake
`_stack_cite` and `_stack_review`, each recording its keywords. Assert the
same object reaches both as `heads`, by identity, and that it is a
`dict`, so `heads=None` to both fails. Give the order a stack
base, as
`test_a_stack_batch_reads_its_stack_base_as_gone_only_when_its_ref_is_missing`
does.

**Where `SA-0294` sits.** The cell is cut from `SA-0279`'s branch. A
stack batch cuts each layer from the one below, so `SA-0294` is under it
whenever both run in one stack or `SA-0294` merged first. If neither
holds, `cite` is missing at your base. Stop and say so.

**Why a remembered commit is safe here.** §5.7 fetches a parent's head
and never trusts a recorded one. The cite adapter fetches fresh, and the
review that follows reads that same fetch, never the ledger's
`pushed_sha`. A review with nothing left for it fetches as before.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** `saffron/cli.py` is the only counted file, since the `size`
gate skips `tests/**`. The estimate covers the helper and its two callers,
the adapter, the `heads` pop and the `_batch` wiring.
