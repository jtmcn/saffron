---
id: SA-0350
title: A spec whose own new refusal refuses specs still queued at its base is admitted to the same night, so its cell spends its budget on a precondition no stack can meet
type: feature
priority: 2
depends_on: [SA-0339]
estimated_lines: 360
touches:
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/cli.py
  - tests/test_intake.py
  - tests/test_scheduler.py
  - tests/test_cli.py
  - tests/test_refusal_count.py
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
  - saffron/task.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/repos/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/cell/**
  - tests/test_queued_specs.py
  - tests/test_task.py
budget_usd: 52
max_attempts: 3
max_turns: 230
acceptance:
  - claim: >-
      A spec may declare `retired_first`, a list of spec ids. It loads as
      that list, in its declared order, and as an empty list when omitted.
      It loads with no `depends_on`. A bare string in place of the list is
      refused at load. The witness drives all four: a list of two ids out of
      sorted order, the omitted key, the list with no `depends_on`, and the bare string.
    witness: tests/test_intake.py::test_retired_first_loads_as_a_list_of_ids_with_no_depends_on
    wrong_versions:
      - The `consumes` rule copied, so a `retired_first` with no `depends_on` does not load.
      - A field typed to accept a bare string, so a bare `SA-0001` in place of the list loads.
      - The list sorted at load, so the declared order is lost.
  - claim: >-
      The queue scan refuses a candidate whose `retired_first` names an id
      not retired to `done/` in the scanned directory, under the
      `depends_on` kind, in one refusal row. The witness drives each mode,
      with and without `stack=True`. In each mode it drives five named ids
      in one candidate's list. One is queued with no task. One is queued
      with a task at `READY_FOR_REVIEW` that records a branch, a pushed sha
      and a pull request URL, and the candidate's `depends_on` names it, so
      under `stack=True` it qualifies as the order's stack base. One is
      queued with a `MERGED` task. One is declared by no spec anywhere. One
      is retired to `done/`. The reason names each of the first four and
      never names the retired one. It names `retired_first` and `done/`,
      holds the text `not retired`, and never holds the text `depends_on`. A candidate whose
      `retired_first` names only the retired id is a candidate in both
      modes. With one more file in `done/` that does not parse, the reason
      also carries the text `could not be read as a spec`, the suffix
      `_dependency_refusal` appends for the same blindness.
    witness: tests/test_scheduler.py::test_a_spec_whose_retired_first_is_not_retired_is_refused_naming_each
    wrong_versions:
      - The check made only where `_refuse` checks `depends_on`, which `stack=True` skips, so a stack night admits the candidate.
      - The id read through `_dependency_refusal`, so the parent waiting at `READY_FOR_REVIEW` is credited.
      - The order's stack base credited, so under `stack=True` the parent at `READY_FOR_REVIEW` is credited.
      - A reason with no suffix for an unreadable `done/` file, so a spec sitting in `done/` is reported as not retired.
      - A `MERGED` task credited, as `merged_anywhere` or `on_default_branch` is, so a merged parent whose spec still sits queued is credited.
      - A reason that names only the first id not retired.
      - A reason that lists every `retired_first` entry, the retired one included.
      - A reason holding `depends_on`, so the spec loop's own `_order` re-admits the spec into the night.
      - A refusal kind of its own, which `RefusalKind` and the count in §4.2.1 do not name.
      - Any non-empty `retired_first` refused, so a list naming only a retired id is refused.
  - claim: >-
      `SA-0279`'s night, replayed under `stack=True`. Three queued specs
      form a chain, each depending on the one before it. A fourth depends on
      the third and names all three in `retired_first`. The stack order
      takes the three, in chain order, and refuses the fourth before any
      cell. Its one refusal names all three ids. The same four specs with
      the three moved to `done/` take the fourth as the one candidate.
    witness: tests/test_scheduler.py::test_a_stack_night_refuses_the_spec_whose_retired_first_parents_are_in_its_order
    wrong_versions:
      - Ids credited once they are taken into the stack order, so the fourth stacks on the third.
      - The fourth dropped from the order with no refusal row, so the night's queue never says why.
  - claim: >-
      `saffron cell` refuses a spec whose `retired_first` names a spec still
      queued in `.saffron/specs/` at `base_sha`, before any cell starts. It
      exits 1 and writes no task row. Its one line starts with the spec id,
      says `refused` and names the queued id. That base also holds a
      file in `done/` that does not parse, and the line carries the text
      `could not be read as a spec`. The working copy has the queued
      spec moved to `done/`, uncommitted. The same spec, with that id
      retired at `base_sha` and queued again in the working copy, reaches
      the cell. On a repo with no `.saffron` at `base_sha`, where the export
      raises `GitError`, the same spec exits 2, the code a setup failure
      takes, with no task row and no cell. Its one line starts with the
      spec id, names the failed read of `done/` at `base_sha`, and never
      says `not retired`.
    witness: tests/test_cli.py::test_a_spec_whose_retired_first_is_queued_at_base_refuses_before_the_cell_starts
    wrong_versions:
      - The check added to the queue scan's `_refuse` alone, so `saffron cell` starts the cell.
      - Retired ids read from the working copy, `repo`, rather than the export at `base_sha`.
      - Any non-empty `retired_first` refused, so the spec whose id is retired at `base_sha` never reaches the cell.
      - The `GitError` swallowed as `_protected_paths_at` does, so the line reports the id as not retired.
      - The `GitError` swallowed, so the command exits 1 or says not retired.
      - The count of unreadable `done/` files passed as zero on this path, so the line carries no suffix.
  - claim: >-
      This repo's measured queue is unchanged. No queued spec declares
      `retired_first`.
    witness: tests/test_scheduler.py::test_saffron_queue_smoke_reproduces_this_repos_measured_queue
    preserves: true
---

## Context

Backlog item **b-e7898b**, filed from the spec loop's run 44. It cites
`DESIGN.md` §4.2.1. Every line number below was read at `747cdc8f`.

**Cited lines move on the cell's base**. The cell is cut from
`SA-0339`'s branch. `SA-0338` and `SA-0339` edit `saffron/intake.py`,
`saffron/scheduler.py`, `saffron/cli.py` and the matching test files, so
their cited line numbers move there. Find each by the function or text
named beside it.

**What happened**. `SA-0279` made `protected_touch_refusal` refuse a
`touches` entry with a `.claude` component
(`saffron/scheduler.py:451-488`). `SA-0280`, `SA-0282` and `SA-0283`
touch `.claude/` and sat below it in the same stack, still queued.
`test_no_queued_spec_is_refused_on_its_own_text` calls that function on
every queued spec (`tests/test_queued_specs.py:95-101`). So the new rule
failed it three times. Its spec's `forbidden` list barred that test
and `.saffron/**`. The task ended `EXHAUSTED`, by the item's record. The ledger
holds task 314 at $17.26 spent of a $22 budget, now `MERGED` after the
delegate adopted it.

**The precondition was prose**. `SA-0279`'s spec said it waits for its
three parents to be merged and retired to `done/` on its base
(`.saffron/specs/done/SA-0279-a-spec-touching-claude-reaches-a-cell-whose-agent-cannot-write-there.md:154-158`
and `:254-258`). Nothing read that sentence. Its `depends_on` named the
three, and a stack batch counts a parent in its own order as met. That
is what `depends_on` is for.

**How the scan credits a parent today**. `_dependency_refusal` credits a parent
on any of three facts. It is in `merged_anywhere`
(`saffron/scheduler.py:686`). It is retired to `done/`
(`saffron/scheduler.py:690`). Or it has a task in a waiting state
(`saffron/scheduler.py:727`). `build_queue` reads `retired` from
`_retired_ids` over the scanned directory (`saffron/scheduler.py:1345`).
Under `--stack` it passes `check_dependencies=not stack`
(`saffron/scheduler.py:1395`). So `_refuse` returns before its
`depends_on` loop (`saffron/scheduler.py:971`). The stack order then
counts `retired | merged_anywhere` as on the default branch
(`saffron/scheduler.py:1412`). So no path in the scan tells
"stacked on" from "retired at base".

**The refusals `_refuse` makes before that return**. The protected-touch
refusal comes first, then the open pull request checks, the criterion
path and the retirement marker (`saffron/scheduler.py:949-969`).
Everything above `saffron/scheduler.py:971` runs in both modes.

**The attended path**. `_run_cell` loads the spec from the given path
(`saffron/cli.py:637`). It refuses on the protected list and on a
retirement marker, each read at `base_sha`, and prints
`{spec.id:<10} refused  {reason}` and returns 1 (`saffron/cli.py:664-689`).
The ceilings are resolved next (`saffron/cli.py:695`).

**The spec loop's own order reads refusal text**. Its `_order` treats a
refusal whose reason holds `depends_on` as a deferral. It admits that
spec once every `depends_on` entry is in the order or in `done/`
(`.claude/skills/run-saffron-spec-loop/driver.py:302` and `:321`).

**The count**. `tests/test_refusal_count.py:46` pins four sites for the
`depends_on` kind in `scheduler.py`.

## Problem

Add a frontmatter field, `retired_first`, a list of spec ids. Each one
must be retired to `done/` at this spec's base before its cell runs. A
spec whose own change would refuse specs still queued declares them
here. The field makes `SA-0279`'s prose precondition a fact the host
checks.

Add one function to `saffron/scheduler.py` that takes a spec, the set
of retired ids and the count of unreadable `done/` files. It returns a
reason or `None`. The reason names `retired_first` and every id not in
that set, in declared order. Credit nothing else: not a `MERGED` task,
not a waiting task, not a place in the stack order, not the stack base.
When the count is not zero, end the reason with the suffix
`_dependency_refusal` appends (`saffron/scheduler.py:699-709`). Pass the
count, or move that suffix into a helper both call. `_refuse` already
receives `unreadable_retired`.

Call it from `_refuse`, above the `check_dependencies` return, so both
modes run it. Return its reason under the `depends_on` kind. Raise the
`depends_on` count in `tests/test_refusal_count.py` by one, and add the
new site to its comment.

Call it from `_run_cell` after the retirement-marker refusal. Read the
retired ids from `.saffron/specs/done/` as exported at `base_sha`, never
from the working copy. Pass the count of `done/` files that did not
parse. Print the line the other two refusals print, and return 1. The
export raises `GitError` when `base_sha` holds no `.saffron` or the
mirror cannot be read, and the two look alike
(`saffron/cli.py:519-531`). Then print one line starting with the spec
id that names the failed read of `done/` at `base_sha`. Never say
`not retired` there, and return 2. `saffron/cli.py:92-93` gives a setup
failure 2, never 1. Skip the export and the line for a
spec that declares no `retired_first`.

`test_no_real_spec_is_refused_on_its_own_acceptance_criteria` promotes
every retired spec to the top level, then asserts each refusal outside
two named shapes holds `depends_on` (`tests/test_scheduler.py:4769-4795`).
The first retired spec that declares `retired_first` would fail it. Add
the new reason there as a third named shape, beside `disclosed` and
`claude_touching`, selected by the text `retired_first`. Assert its ids
as a literal list, empty at your base, and leave the shape out of the
`depends_on` assert.

Add a sentence on the field to the module docstring of
`saffron/scheduler.py`, beside the paragraph on b-e773d9, and one to
`build_queue`'s docstring.

## Out of scope

- **Discovering the refused specs**. The host cannot run a cell's new
  rule over the queue, since the control plane never executes
  model-authored code (§2). The spec's author names them. The item's
  "every spec queued at its base" is met for the specs the author names.
- **A stack batch's recorded spec text**. `_recorded_spec_text`
  (`saffron/task.py:632`) re-checks a recorded text before its cell. A revision
  that adds `retired_first` is not checked there. The order already
  refused or admitted the spec on its committed text.
- **The shape of an id**. An entry is not validated against the `id`
  pattern. A typo refuses the spec, and the reason names the typo.
- **Hand edits in the spec's own pull request**. `DESIGN.md` §4.2.1
  gains a sentence under the sixth refusal. `docs/agents/issue-tracker.md`
  gains a `retired_first` entry beside `removes`. The spec writer and spec
  reviewer agent files under `.claude/agents/` each gain a line. It tells
  an author to declare the field for a spec that adds or widens a refusal.
  `CONTEXT.md` gets its entry by hand under b-7c118b.

## Notes for the agent

**Every criterion but the last is new code**, so each declares a
witness and no mutant, and `witness` will report `skip`. The last is
`preserves`, and its test exists at base. The refusal count test needs
its pinned number raised by one in the same diff, which is why
`tests/test_refusal_count.py` is in `touches`.

**At base each new witness fails in its body**. None imports a name the
change adds at module scope. Load refuses the unknown key, so a spec
declaring `retired_first` is a parse failure there. Assert on the parsed
spec, the candidate list and the refusal rows, so that failure reads as
red rather than as a collection error.

**Why a declared field**. Three designs were in scope. The new rule
cannot run on the host. Running it in a gate-only cell over the queue
needs a second cell per spec, which is the largest surface. A declared
rule, such as a set of refused `touches` patterns, reaches only
touches-shaped refusals. It also needs glob-against-glob matching, which
`protected_touch_refusal`'s own `ponytail:` note says this module does
not do (`saffron/scheduler.py:468-475`). A list of ids is one field, one
function and two call sites. `SA-0279`'s author already wrote the three
ids in prose, so the field refuses that spec at batch start.

**The scan witness** writes specs with `_write_spec`
(`tests/test_scheduler.py:175`), which gains a `retired_first` keyword.
A retired spec goes in `directory / "done"`. Tasks come from `_task_at`
with `_sha` of the file. Map each refusal to its spec by reading the
refused file with `load_spec`, as the removed-name tests do. Use ids no
one of which holds another as a substring, such as `TE-1` to `TE-5` and
`TE-9`. Assert `"depends_on" not in reason`. Give the `READY_FOR_REVIEW`
parent its branch, a 40-character pushed sha and a pull request URL with
`set_task_package` (`tests/test_scheduler.py:58`). Without all three it
never qualifies as a stack base (`saffron/scheduler.py:1033-1060`), and
a check that credits the stack base passes. The unreadable file is a
`done/broken.md` with no frontmatter. Of the waiting states the
witness drives `READY_FOR_REVIEW` alone. The new function reads no task
state at all, so the other four waiting states are left to that design.

**The stack base is measured**. At `6e224412` a host probe ran
`build_queue(..., stack=True)` on this arrangement with no
`retired_first` anywhere. `TE-1` and `TE-3` were queued, `TE-3` with a
`MERGED` task, and `TE-5` sat in `done/`. `TE-2` had a
`READY_FOR_REVIEW` task with a branch, a pushed sha and a pull request
URL. `TE-9` declared only `depends_on: [TE-2]`. The candidates came back
as `TE-1` and `TE-9`, each with `StackBase(spec_id='TE-2')`, and no
refusals. So `TE-2` is the order's stack base with `TE-1` kept beside it.

**The stack witness** builds the chain with `depends_on`, so the three
parents lie on one chain as one stack's layers do. Assert the taken ids
as an exact list, and the fourth's refusal rows as exactly one.

**The `saffron cell` witness** copies
`test_a_spec_whose_touches_are_protected_refuses_before_the_cell_starts`
in `tests/test_cli.py`. `_repo_with_spec` commits `extra_specs` into
`.saffron/specs/` before it cuts the bare clone. It does not create a
`done/` directory, so make one or extend the helper. Move the file in
the working copy after the clone. For the admitted half,
`_capture_cell_spec` reaches the stubbed `run_one_cell`. For the
`GitError` half, `_local_origin` (`tests/test_cli.py:491`) commits no
`.saffron`. Many existing tests run `_run_cell` on such a repo with specs
that declare no `retired_first`, which is why that case skips the
export. Those existing tests are the witnesses for a spec with no
`retired_first`. One is `test_a_specs_own_ceilings_reach_the_cell`
(`tests/test_cli.py:642`) on `_local_origin`, and the callers of
`_repo_with_spec` are the rest.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size**. `SA-0290` added `removes` and its scan refusal. It landed at
184 changed lines outside `tests/` and 520 under it. This change has a
smaller refusal and one more call site. The estimate is 72 lines of
source and 288 of tests, with no overrun added. That covers the
unreadable suffix, the `GitError` line and the corpus test's third shape.
