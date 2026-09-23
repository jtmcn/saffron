---
id: SA-0142
title: The queue has no stack order, so a child waits for its parent's task and a parent in another stack admits it
type: feature
priority: 1
depends_on: [SA-0136]
touches:
  - saffron/scheduler.py
  - tests/test_scheduler.py
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
  - saffron/batch.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/record/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_cli.py
  - tests/test_ledger.py
budget_usd: 18
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      With `stack=True`, `build_queue` returns its candidates in stack order.
      It takes one spec at a time. Each time it takes, from the specs not yet
      taken whose every `depends_on` entry is taken or on the default branch,
      the one with the lowest `priority`, then the lowest spec id as a
      string. So a spec
      follows each of its entries in the order, at `depends_on[0]` and at a
      later entry. A tie never falls back to filename order.
    witness: tests/test_scheduler.py::test_a_stack_order_takes_every_dependency_first_then_priority_then_id
  - claim: >-
      With `stack=True`, a spec is a candidate when each of its `depends_on`
      entries is in the stack order or on the default branch, whether or not
      the entry has a task. An entry is on the default branch when its id has
      a `MERGED` task at any `spec_sha`, a recorded push that `pushed_landed`
      accepts, or a spec retired to `done/`. The witness drives a chain of
      three specs with no task, each default-branch case, and a second entry
      that is in the order with no task.
    witness: tests/test_scheduler.py::test_a_stack_order_admits_a_spec_whose_dependencies_are_in_it_or_on_the_default_branch
  - claim: >-
      With `stack=True`, a spec with any `depends_on` entry neither in the
      stack order nor on the default branch is refused. Its reason names
      every such entry and no other entry. The witness drives five such
      entries. One waits at `READY_FOR_REVIEW` with a push `pushed_landed`
      rejects. One is refused for protected `touches`. One is `EXHAUSTED`.
      One is declared by no spec and no task. One is refused this way itself.
      It drives them at `depends_on[0]` and at a later entry, and drives two
      specs that depend on each other.
    witness: tests/test_scheduler.py::test_a_stack_order_refuses_a_spec_with_any_dependency_outside_it_and_names_each
  - claim: >-
      With `stack=True`, `build_queue` makes every refusal but the dependency
      refusal as it does without it, with the same reason. That covers eight:
      a spec that does not parse, a retired spec that does not parse, a
      dangling `saffron:retired-by` marker, protected `touches`, an open pull
      request from another task, a `touches` overlap with an open pull
      request, a criterion path outside `touches`, and a retirement marker
      outside `touches`.
    witness: tests/test_scheduler.py::test_a_stack_order_keeps_every_refusal_but_the_dependency_one
  - claim: >-
      Without `stack`, a parent waiting at `READY_FOR_REVIEW` still admits
      its child, and a parent at `REJECTED` still refuses it.
    witness: tests/test_scheduler.py::test_a_waiting_parent_is_admitted_where_a_dead_one_is_still_refused
    preserves: true
    mutant:
      file: saffron/scheduler.py
      find: "if any(state in DEPENDENCY_WAITING_STATES for state in states):"
      replace: "if False:"
---

## Context

Backlog item **b-792ab2**, step 1 of its Done. It cites `DESIGN.md` §4.2
and §4.2.1. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 1 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design
this step builds.

A stack batch runs the queued specs into one pull request stack. It fixes
its order once, when the batch starts. A child whose parent comes earlier in
that order is admissible, although the parent has no task yet. A spec with
a `depends_on` entry outside the order, and not on the default branch, is
refused. Cutting it from the task below would drop that entry's code.

**This spec is the first of four.** It builds the order and its refusals
as a mode of `build_queue`. Whole, step 1 was estimated at 4300 changed tokens
against the `feature` ceiling of 3000 (`saffron/gates/core/size.py:26`), so
it splits. The three after it:

- `SA-0143` hands each task's pushed branch and head to the next, in
  `run_stack_batch`, which runs this order once, with no rescan.
- `SA-0144` adds `saffron batch --stack` and `saffron queue --stack`.
- `SA-0145` records the stack's layers in the ledger. It is not written yet.

**What `build_queue` does today.** Every sentence here was read at
`5ee4dd76`.

- It sorts its candidates by `priority` alone, so a tie keeps
  `discover_specs`' filename order (`saffron/scheduler.py:778-780`,
  `:890`).
- `_refuse` runs the dependency check last, one entry at a time
  (`saffron/scheduler.py:709-725`). With two or more unmet entries, the
  reason is the first one's reason plus a count (`:724`).
- `_dependency_refusal` admits an entry with a `MERGED` task at any
  `spec_sha` (`saffron/scheduler.py:569`). A landed push the caller
  accepts joins that set (`:814-829`). It also admits a spec retired to
  `done/` (`saffron/scheduler.py:573`).
- It refuses an entry with no task at its current `spec_sha`
  (`saffron/scheduler.py:597-602`). So in one call a child is refused
  whenever its parent has not run.
- It admits an entry with any task in `DEPENDENCY_WAITING_STATES`
  (`saffron/scheduler.py:610-611`). So a parent at `READY_FOR_REVIEW` in
  another, unmerged stack admits its child.

**The spec loop orders by hand.** Its driver's `_order` admits a spec
refused only on `depends_on`
(`.claude/skills/run-saffron-spec-loop/driver.py:215-268`). It does so
once each entry is in the order.
`_sequence` puts parents first, then priority, then most descendants, then
id (`:271-303`). The decision for this spec leaves out the descendants key.

## Problem

`build_queue` has no mode that orders a stack. Add a keyword argument
`stack: bool = False` to it. With `stack=False` nothing changes.

With `stack=True`:

1. **The other refusals run as today.** `_refuse` makes several checks
   before its dependency check (`saffron/scheduler.py:639-706`). A
   candidate one of them refuses is refused with the same reason. So are
   the refusals `build_queue` makes outside `_refuse` (`:859-872`).
2. **One pass orders and admits the rest.** An entry in `retired` is on
   the default branch. So is one in `merged_anywhere`, once the landed
   pushes are folded in. Take specs one at a time.
   A spec is ready when each of its entries is taken or on the default
   branch. Each time, take the ready spec with the lowest `priority`, then
   the lowest id. Stop when no spec is ready. The taken specs are the candidates, in the order
   taken.
3. **Every spec left over is refused.** Its reason names each of its
   entries that is neither taken nor on the default branch. It says those
   entries are outside the stack order and not on the default branch. It
   names no other entry.

A spec is never admitted by a waiting task in stack mode. A cycle is never
taken, because neither spec is ever ready.

## Out of scope

- **Running the order.** The handoff through `run_task` and the refusal
  of a failed task's descendants are `SA-0143`'s. `saffron batch --stack`
  is `SA-0144`'s. Until it lands, stack mode has no production caller.
- **The record of the stack's layers.** That is `SA-0145`'s. A new fact
  kind needs `KINDS`, `ontology/factory.ttl` and `CONTEXT.md` to move
  together, and no cell can write `CONTEXT.md` (backlog item b-25766a).
- **Gate 0's overlap exemption for the batch's own tasks.** That is step 2
  of b-792ab2. The order is fixed at batch start, when none of the batch's
  own pull requests is open yet.
- **Composite members kept together.** ADR 6's composite spec is not built,
  so no spec declares members yet.
- **The vocabulary.** `CONTEXT.md` has no entry for a stack batch or its
  order. Backlog item b-466005 files it by hand.
- **The driver's `_order`.** It keeps its own rule and its descendants key.
  `.claude/**` is forbidden here.

## Notes for the agent

**Why this spec depends on `SA-0136`.** `SA-0143` edits `task.py`,
`batch.py` and `cli.py` after `SA-0136`'s chain, and only `depends_on[0]`
stacks (`saffron/task.py:133-136`). So this spec sits between the two, and
`SA-0143`'s tree holds its code.

**Every new criterion is new code.** Stack mode has no text at base a
mutant could pin. So criteria 1 to 4 declare a witness and no mutant, and
`witness` reports `skip` for them. Criterion 5 is `preserves`, and its
mutant pins the waiting-state admission, which stack mode must leave alone.
Leave `_dependency_refusal` exactly as it is. Stack mode uses its own rule.

**Where it goes.** Keep one pass over the candidates for the checks that
are not the dependency check. Do not copy them for stack mode. One way is
to let `_refuse` skip its dependency loop when the caller asks. Keep
`kept.sort` for the default mode.

**Name the witnesses exactly as the criteria do**, each a plain `def` in
`tests/test_scheduler.py`. Use the helpers already there: `_spec_dir`,
`_write_spec`, `_repo`, `_task_at`, `_sha` and `_fake_gh`. Pick spec ids so
that no id is a substring of another, such as `TE-11` and `TE-22`. A reason
check with `in` is otherwise vacuous.

**Criterion 1's witness** writes seven specs and asserts the exact order.

- `TE-5` at priority 3, with no `depends_on`.
- `TE-1` at priority 1, depending on `TE-5`.
- `TE-3` at priority 1, in a file that sorts first by name.
- `TE-2` at priority 1, in a file that sorts after `TE-3`'s.
- `TE-4` at priority 1, with `depends_on: [TE-3, TE-5]`.
- `TE-6` at priority 4, with no `depends_on`.
- `TE-7` at priority 2, with no `depends_on`.

The stack order is `TE-2`, `TE-3`, `TE-7`, `TE-5`, `TE-1`, `TE-4`, `TE-6`.
These fail it, each measured on this arrangement:

- a sort by priority alone, which puts `TE-1` before `TE-5`
- filename order for a tie, which puts `TE-3` before `TE-2`
- ordering by `depends_on[0]` alone, which puts `TE-4` before `TE-5`
- a depth-first walk that puts each parent right before its first child
- a layered order, which takes every ready spec in a round before it looks
  again, or sorts by depth first. It puts `TE-6` before `TE-1`.
- `driver.py`'s `_sequence`, which ranks most descendants before id. It puts
  `TE-3` before `TE-2`.
- a parent that takes its most urgent descendant's priority, which puts
  `TE-5` before `TE-7`

The comparison of ids is as strings. Real ids are zero-padded, so string
order is id order, as `driver.py`'s `_sequence` compares them.

**Criterion 2's witness** passes a `pushed_landed` that accepts one sha.

- `TE-11`, `TE-12` depending on it, and `TE-13` depending on `TE-12`. None
  has a task.
- `TE-21` with a `MERGED` task at a stale `spec_sha`, as the landed-push
  test does. `TE-31` depends on `TE-21` and `TE-11`, in that order.
- `TE-22` retired to `done/`. `TE-32` depends on it.
- `TE-23` at `READY_FOR_REVIEW` with a recorded push the callable accepts.
  `TE-33` depends on it.

It asserts `TE-11` and the five dependants are candidates and none is
refused. These
fail it:

- admitting an entry only once it has a task
- reading `MERGED` only at the current `spec_sha`
- ignoring a landed push, or a retired spec. A build that ignores the push
  and admits waiting tasks passes this witness, and criterion 3's `TE-51`
  fails it.
- the stack rule at `depends_on[0]` and today's rule at a later entry, which
  refuses `TE-31`

**Criterion 3's witness** passes a `pushed_landed` that accepts nothing,
and a `protected` list.

- `TE-41` at `READY_FOR_REVIEW` with a recorded push. `TE-42` touches a
  protected path. `TE-43` is `EXHAUSTED`. `TE-49` is declared nowhere.
  `TE-44` has no `depends_on`.
- `TE-51` depends on `TE-41`. `TE-52` depends on `TE-44` and `TE-41`.
  `TE-53` depends on `TE-42`. `TE-54` depends on `TE-43` and `TE-49`.
  `TE-55` depends on `TE-51`.
- `TE-61` depends on `TE-62`, and `TE-62` on `TE-61`.

It asserts `TE-44` is the only candidate. Each dependant is refused, and
its reason names the entries listed for it. `TE-52`'s reason does not name
`TE-44`. `TE-54`'s names both of its entries. These fail it:

- a waiting task that admits its dependant, as today
- a reason that names the first entry and counts the rest
- a reason that names every entry, `TE-44` included
- a check of `depends_on[0]` alone, which admits `TE-52`
- a rule that removes specs until nothing changes, which keeps the cycle
- a pass that admits `TE-55` because `TE-51` is a spec in the directory

**Criterion 4's witness** builds one directory that makes each of the
eight refusals once, and no dependency refusal. It follows the existing
test for each refusal. It calls `build_queue` with and without `stack`, on
the same arguments. It asserts the two refusal sets are equal as
`(path.name, reason)` pairs and hold eight entries. The two candidate lists
must hold the same set of ids. The assertion ignores their order, because a
tie breaks on id in one mode and on filename in the other. A stack path that skips one check, or rewords its
reason, fails it.

**Criterion 5** needs no new test. Its mutant makes a waiting parent refuse
its child without `stack`, which the named test catches.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.
`python3 hooks/prose_limit.py --file saffron/scheduler.py` checks one file.

**Commit as each witness passes**, before the full suite runs.

**Size.** About 85 changed lines of source and 230 of test. At this file's
6 tokens a line for source and 4 for test, that is about 1450 tokens of
the 3000 ceiling.
