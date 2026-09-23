---
id: SA-0135
title: A stacked child starts its cell whether or not its tree base holds the names it consumes
type: feature
priority: 2
depends_on: [SA-0134]
touches:
  - saffron/intake.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - tests/test_consumes.py
  - tests/test_task.py
  - tests/test_cli.py
  - tests/fixtures/consumes/FX-0001-a-child-names-what-it-consumes.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - saffron/repos/**
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - tests/test_mirror.py
  - tests/test_batch.py
  - tests/test_intake.py
  - tests/test_scheduler.py
budget_usd: 25
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      A spec may declare `consumes`, a list of entries, each a path or a
      `path:name`. It loads as written and in order, and a name may hold a
      colon. A spec that omits it, leaves it empty or declares an empty list
      loads with an empty list. A spec whose `consumes` is not empty while
      its `depends_on` is omitted or empty is refused at load. `parse_spec`
      and `load_spec` raise `SpecError`, and `discover_specs` returns the
      file as a `DiscoveryFailure` and not as a spec.
    witness: tests/test_consumes.py::test_a_spec_declares_what_it_consumes_and_needs_a_parent_to_consume_from
  - claim: >-
      The fixture spec
      `tests/fixtures/consumes/FX-0001-a-child-names-what-it-consumes.md`
      declares a `depends_on` and a `consumes` holding a path entry and a
      `path:name` entry. `load_spec` reads it with both lists as the file
      writes them.
    witness: tests/test_consumes.py::test_the_fixture_spec_declares_what_it_consumes_and_loads
  - claim: >-
      When an entry does not resolve at the tree base, `run_task` returns a
      `Refused` and never calls `run_one_cell`. It leaves no row in `tasks`
      or `runs`. It prints one line, the spec id padded to ten, then
      ` refused  `, then the refusal's `reason`. The reason names the tree
      base's first twelve characters and every unresolved entry as written,
      in the order given, and no entry that resolved. A name resolves as a
      whole word wherever it occurs, so one found only in a comment or only
      in a docstring resolves too. An entry whose path holds a colon reads
      as the part before the first colon, so it is refused even when the
      tree holds a file of that name. When every entry resolves,
      `run_one_cell` is called once.
    witness: tests/test_consumes.py::test_run_task_refuses_an_unresolved_consumed_entry_before_the_cell
  - claim: >-
      Entries resolve at the task's tree base. That is `stacked_on` when
      the task stacks on its parent, and the run's `base_sha` when it does
      not. A name that only the parent's head holds resolves for a stacked
      task and refuses an unstacked one. A name only `base_sha` holds
      refuses a stacked task whose parent removed it. A name that only the
      mirror's `HEAD` or the repo's working copy holds refuses an unstacked
      task.
    witness: tests/test_consumes.py::test_consumed_entries_resolve_at_the_tasks_tree_base
  - claim: >-
      A tree base the mirror does not hold makes `run_task` raise
      `GitError`. It prints no refused line, returns no `Refused` and never
      calls `run_one_cell`.
    witness: tests/test_consumes.py::test_a_tree_base_the_mirror_lacks_is_an_error_and_not_a_refusal
  - claim: >-
      `saffron cell` on a spec whose entry does not resolve exits 1. The
      refused line appears once in its output, and no row is left in
      `tasks`.
    witness: tests/test_consumes.py::test_saffron_cell_exits_1_on_a_consumes_refusal
  - claim: >-
      A batch whose runner returns a `Refused` attaches no run to the
      batch. The refusal neither counts toward the breaker nor resets its
      count. The batch rescans and starts the next candidate, and the
      refused spec does not start again that night. Two refusals in a row
      followed by a task that runs end `DRAINED` with that task run. An
      abort, a refusal and an abort end `INFRASTRUCTURE` before a fourth
      candidate starts.
    witness: tests/test_consumes.py::test_a_batch_steps_over_a_refused_task
  - claim: >-
      A spec that consumes nothing runs as before, and no git command reads
      the mirror for it.
    witness: tests/test_task.py::test_a_task_that_never_packaged_still_reaches_the_index
    preserves: true
---

## Context

Backlog item **b-602d00**, filed 2026-09-21. It cites `DESIGN.md` §4.2.
ADR 6 names it as the check on a composite's first join
(`docs/adr/0006-work-larger-than-one-cell-is-a-composite-spec.md`, its
last paragraph).

A stacked child's tree base is its parent's branch head (§4.2). Its
criteria name what the parent adds. If the parent built those under other
names, the child's cell finds out after its first turn is paid for. §4.2's
rule is to check without starting a cell whatever can be checked without
starting a cell.

**This spec is the second of three.** `SA-0134` built the reader,
`unresolved_consumes(mirror, sha, entries)` in `saffron/repos/mirror.py`.
This spec adds the `consumes:` field and the refusal before the cell.
`SA-0136` stacks on this one. It refuses nine malformed entry shapes at
load and turns an unreadable entry into a refusal that names it. This
spec keeps every exception the reader raises as an error. Whole, the two
came to about 600 changed lines against the `feature` ceiling of 600
(`saffron/gates/core/size.py:25`), so they split.

**What the gap until `SA-0136` costs.** Until then a malformed entry
reaches the reader, and `SA-0134`'s notes give what git does with each.

- An empty entry, an empty path, an absolute path and a bare `..` make the
  reader raise `GitError`. `run_task` raises, `saffron cell` exits 2, and
  a batch counts the task as an abort toward its breaker.
- A `path:name` whose path ends in `/` resolves against the directory's
  listing, and an empty name resolves against any file. Each is a false
  pass, and the cell runs. At worst that costs one cell.
- Some entries raise from the reader: a submodule, a symlink that leaves
  the tree, dangles, or points at a directory or another symlink, and a
  file that is not UTF-8. They are errors here. `SA-0136` makes them
  refusals.

This spec stacks on `SA-0134`. Its tree base carries `SA-0125` through
`SA-0129`, which change `saffron/intake.py`'s `Spec`. So `Spec` is cited
by symbol below. Every other sentence about current code was read at
`02af122a`.

**Where the refusal goes.** `run_task` resolves `stacked_on` from
`_resolve_stacked_on` (`saffron/task.py:286-294`). It builds the
`CellSpec` with `base_sha` and `stacked_on` (`saffron/task.py:303-318`)
and calls `run_one_cell` (`saffron/task.py:319`). That is the first point
where the tree base is known, and `saffron cell` and `saffron batch` both
reach it. The module's docstring says the refusals stay outside
`run_task` (`saffron/task.py:17-21`). That stops being true.

**How a refusal leaves `run_task`.** `run_task` returns a `CellOutcome`
(`saffron/task.py:230`). `saffron cell` exits with
`CELL_EXIT.get(outcome.state, 1)` (`saffron/cli.py:416`). A batch's
`_drive` calls `ledger.attach_run_to_batch(outcome.run_id, batch_id)`
after every returned outcome (`saffron/batch.py:233`), and that raises
for a run that does not exist (`saffron/ledger.py:865-866`). An exception
from the runner counts as an abort toward the breaker
(`saffron/batch.py:209-221`). So a refusal can be neither a raise nor an
outcome with made-up ids. `CONTEXT.md` defines a **Refusal** as a task
rejected before any cell starts (`CONTEXT.md:201`). Every refusal today
writes no ledger row and ends in no state. The attended ones print
`f"{spec.id:<10} refused  {reason}"` and return 1 (`saffron/cli.py:385`,
`:395`).

**Where `Spec` reads a key.** `Spec` sets `extra="forbid"` and declares
`depends_on` as a list defaulting empty (`saffron/intake.py`, class
`Spec`). `parse_spec` drops a key whose value is `None` before it
validates, and turns a `ValidationError` into `SpecError`
(`saffron/intake.py`, function `parse_spec`). `discover_specs` turns a
`SpecError` into a `DiscoveryFailure` (`saffron/intake.py:346-347`).

## Problem

A spec cannot say what it consumes from its parent, and no host code
checks it before the cell. Build four things.

1. **The field.** `consumes: list[str]` on `Spec`, defaulting empty.
   Refuse a non-empty `consumes` with an empty `depends_on` at validation,
   so every load path refuses it.
2. **The refusal type.** `Refused` in `saffron/task.py`, a frozen dataclass
   holding only `reason: str`. `run_task` returns `CellOutcome | Refused`.
3. **The check.** In `run_task`, after `_resolve_stacked_on` and before the
   `CellSpec`, take the tree base as `stacked_on` or else `base.base_sha`.
   When `spec.consumes` is not empty, call `unresolved_consumes` on it at
   that tree base. When any entry comes back, print the refused line and
   return a `Refused`. When `spec.consumes` is empty, call nothing.
4. **The two callers.** `cli._run_cell` returns 1 for a `Refused` and prints
   nothing more. `cli._batch_runner`, `cli._batch`'s `runner` variable
   (`saffron/cli.py:769`) and `run_batch`'s and `_drive`'s `runner`
   parameters (`saffron/batch.py:61`, `:147`) widen to
   `CellOutcome | Refused`. `_drive` skips the attach and the breaker's
   count for a `Refused`, and rescans as it does after any task.

## Out of scope

- **The nine malformed shapes and the exception mapping.** `SA-0136` adds
  them.
- **The vocabulary and the refusal count.** `CONTEXT.md` has no entry for
  a consumed name (backlog item b-343c21), and §4.2.1 counts the refusals
  gate 0 makes. The operator changes both by hand.
- **The authoring docs.** `docs/agents/issue-tracker.md` lists each
  frontmatter field (`docs/agents/issue-tracker.md:13-16`), and
  `create-saffron-spec`'s pre-flight check 4 asks the writer to name what a
  child keys by. The operator updates both by hand.
- **An event for the refusal.** The refused line is printed, as the
  attended refusals are. No event kind carries it, and `saffron/events.py`
  is forbidden.
- **`SA-0131`'s overlap.** `SA-0131` also edits `saffron/cli.py` and
  `tests/test_cli.py`, in `_resolve_queue` (`saffron/cli.py:494`) and
  the batch's rescans (`saffron/cli.py:788-814`). This spec edits `_run_cell`,
  `_batch_runner` and one line of `tests/test_cli.py`. Whichever runs
  second is refused on the other's open pull request until it merges, so
  no `depends_on` orders them.

## Notes for the agent

**Every change here is new code.** The new branches in `cli.py` and
`batch.py` have no existing text a mutant could pin. So each criterion
declares a witness and no mutant, and `witness` will report `skip` for
the seven new ones. Criterion 8 is `preserves` and names a test that
passes now.

**Two existing tests change type, not behaviour.** `ty` checks `tests/`
too. Widening `run_task`'s return fails it at two lines, measured on
2026-09-23 with a prototype of the signatures. `tests/test_task.py:59`
returns `run_task`'s value from a helper annotated `-> CellOutcome`.
`tests/test_cli.py:2931` reads `.state` from `_batch_runner`'s result.
Narrow each with an `assert isinstance(..., CellOutcome)` and change
nothing else in either file.

**`batch.py` imports `Refused` from `saffron.task`.** Its docstring says it
takes `run_task` as the runner rather than importing it
(`saffron/batch.py:17-19`). Importing the type is not importing the driver.
Add a clause saying so. The prototype showed no import cycle.

**Update `task.py`'s docstring.** Lines 17-21 say the refusals stay
outside. Say which refusal now lives inside and why: the tree base is
known only after `_resolve_stacked_on`. Keep `run_task`'s own docstring
within ten lines of change.

**The witnesses.** All seven new ones go in `tests/test_consumes.py`.
Import `Refused` and `unresolved_consumes` inside each test body, never at
the top of the module. With the source reverted, a module-scope import of
a new name fails collection, and `revert` reads that as `skip`. Import
the helpers that exist at base at the top. Take `git` and
`_plain_repo` from `tests.test_mirror`, and `_local_origin` and
`_namespace` from `tests.test_cli`. Take `_candidate`, `_outcome`,
`_spend`, `FakeRunner` and `_ready` from `tests.test_batch`. Build the
ledger and repo id as that module's fixtures do
(`tests/test_batch.py:15-24`), because a fixture is not imported with its
module.

**Driving `run_task`.** Build a real repo and a real mirror with
`ensure_mirror`. Replace `run_one_cell` with a double that records its
call and returns a `CellOutcome`. Replace `push_unpackaged_work` as
`tests/test_task.py:89-90` does. Pass `repo_id=None`, so
`_resolve_stacked_on` returns `(None, None)` at once
(`saffron/task.py:179-180`). For a stacked task, monkeypatch
`saffron.task._resolve_stacked_on` to return the parent's head and branch.

**Criterion 1's witness** calls `parse_spec` on frontmatter that:

- declares `saffron/task.py`, `saffron/task.py:run_task` and
  `lib.rs:Foo::bar` with a `depends_on`, and gets that list back
- omits `consumes`, leaves it empty, and declares `[]`, each with no
  `depends_on`, and gets an empty list each time
- declares an entry with `depends_on` omitted, and with `depends_on: []`,
  and gets `SpecError` each time

It writes the last case to a file for `load_spec`, and into a directory
for `discover_specs`, and checks each refuses it. These fail it: a check
placed only in `load_spec`, a check that reads `depends_on` as present
when it is `[]`, and a field that refuses an empty list.

**Criterion 2's fixture** is a spec in the shape of this repo's own, with
`## Context`, `## Problem`, `## Out of scope` and `## Notes for the agent`.
It is new Markdown, so the `prose` rules hold for its body from zero. Its
witness reads the file with `load_spec` and compares both lists with the
literal lists the test writes out.

**Criterion 3's witness** commits a tree of four files.

- `code.py` holds `run_task` in code.
- `comment.py` holds `helper` only in a `#` comment.
- `doc.py` holds `Widget` only in a docstring.
- A file is named `weird:name.py`.

It drives one spec whose `consumes` holds, in order,
`gone_b.py`, `code.py:run_task`, `comment.py:helper`, `doc.py:Widget`,
`weird:name.py` and `gone_a.py:run_task`. It asserts a `Refused` and no
call to the double. It asserts no rows in `tasks` or `runs`. It asserts
exactly one refused line, equal to the prefix plus the returned reason. The reason holds
`gone_b.py`, `weird:name.py` and `gone_a.py:run_task` in that order, and
the tree base's first twelve characters. It holds none of the three
resolving entries. A second spec with only the three resolving entries
calls the double once. These fail it:

- a check that runs after `run_one_cell`
- a refused line printed by `cli.py` alone
- a reason that sorts the entries or drops one
- a reason naming a resolved entry
- a check that skips a name found only in a comment

**Criterion 4's witness** builds `main` with a commit `C1` holding
`old.py` with `old_name`. A second commit `C2` adds `head.py` with
`head_name`, and the working copy then adds an uncommitted `wc.py` with
`wc_name`. A branch `saffron/SY-0`, cut from `C1`, holds a commit `P` that
deletes `old.py` and adds `new.py` with `new_name`.

- Unstacked at `base_sha` `C1`, `old.py:old_name` resolves.
  `head.py:head_name`, `wc.py:wc_name` and `new.py:new_name` refuse, and
  the reason holds `C1`'s first twelve characters.
- Stacked on `P` with `base_sha` `C1`, `new.py:new_name` resolves and
  `old.py:old_name` refuses. The reason holds `P`'s first twelve.
- Stacked on `P` with only `new.py:new_name`, the double is called.

These fail it: a check always at `base_sha`, a check that resolves at
either base, a read of `HEAD`, and a read of the working copy.

**Criterion 5's witness** passes forty zeros as `base_sha`, unstacked,
with one entry. It expects `GitError`, no refused line and no call to the
double. A check that turns every `GitError` into a refusal fails it.

**Criterion 6's witness** follows
`test_a_spec_whose_touches_are_protected_refuses_before_the_cell_starts`
(`tests/test_cli.py:1226-1265`). It sets the token with `monkeypatch`,
since that module's autouse fixture does not apply here. Its spec declares
`depends_on: [SY-0]` and `consumes: [missing.py]`. It asserts
`cli._run_cell` returns 1, the refused line appears once in the captured
output, and `tasks` is empty. A second print in `cli.py` fails it, and so
does `CELL_EXIT.get` reached with a `Refused`.

**Criterion 7's witness** drives `run_batch` twice with `FakeRunner`.
Abort outcomes use `_outcome` with a run from `_spend`. The rescan returns
the whole candidate list each time and counts its calls.

- `R1`, `R2`, `C3`, where `R1` and `R2` return a `Refused` and `C3`
  returns `READY_FOR_REVIEW`. It expects `DRAINED`, calls to `R1`, `R2`
  and `C3` in order, and three rescans.
- `A1`, `R`, `A2`, `C4`, where `A1` and `A2` return `GATE_ERROR`. It
  expects `INFRASTRUCTURE` and calls to `A1`, `R` and `A2` only.

These fail it: a refusal counted as an abort, a refusal that resets the
count, an attach for a refusal, and no rescan after one.

**Criterion 8** guards the empty case. That test hands `run_task` a mirror
path that does not exist (`tests/test_task.py:76-80`), so any git call for
a spec with no `consumes` fails it.

**Size.** About 95 changed lines of source and fixture, and 280 of test.
The batch witness follows the breaker tests, which run 35 to 42 lines each
(`tests/test_batch.py:276-352`).

**Measured.** On 2026-09-23 a prototype of the signatures ran at
`02af122a`. It gave `Refused` a `reason` and widened `run_task`,
`_batch_runner`, `cli._batch`'s `runner` and `run_batch`'s `runner`. `ty`
then reported the two test lines above and nothing else. `tests/test_batch.py`
and `tests/test_task.py` passed. The witnesses themselves were not run,
because `SA-0134`'s reader does not exist at `02af122a`. The operator's
loop runs the wrong versions above before the cell. Do not run them
yourself.
