---
id: SA-0093
title: critic_cell and the gate cell are the same 80-line lifecycle written twice, and the first one's docstring says why there should be one
type: refactor
priority: 2
touches:
  - saffron/cell/session.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/phases/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/replay.py
budget_usd: 26
max_attempts: 3
max_turns: 150
risk: elevated
acceptance:
  - claim: >-
      `critic_cell` takes the network it runs on as an explicit argument,
      keyword-only and with no default. Given a name, it uses that network and
      removes no network in its teardown, as it does today. Given `None`, it
      creates a network of its own,
      on a subnet that does not overlap the one the task's own cell holds, and
      removes it in the same `finally` that removes its container and volumes.
      Today it has no such argument: it always runs on a network it did not
      create and never removes one.
    witness: tests/test_session.py::test_critic_cell_creates_its_own_network_only_when_it_is_not_given_one
    mutant:
      file: saffron/cell/session.py
      find: '= "10.90.0.0/24"'
      replace: '= "10.88.0.0/24"'
  - claim: >-
      `critic_cell` takes the container environment as an argument too, so the
      caller that wants a cell behind the proxy and the caller that wants one
      with the repo's declared gate env and nothing else both get it from the
      same function. Today the proxy address is read inside `critic_cell` and
      the environment is built there, so a caller that wants neither has to
      write the lifecycle again.
    witness: tests/test_session.py::test_critic_cell_carries_the_environment_its_caller_asked_for
  - claim: >-
      The gate suite REVIEW's lenses are shown is run in a container obtained
      by entering `critic_cell`, so the pre-clean, the `prepare_worktree` call,
      the patch apply and the teardown loop are written once in the file rather
      than twice.
    witness: tests/test_session.py::test_the_lens_gate_suite_runs_inside_the_one_cell_lifecycle
  - claim: >-
      The gate cell still carries the repo's declared gate env and nothing
      else, sits on a network that is not the implementer's, and is gone before
      the first lens turn.
    witness: tests/test_session.py::test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs
    preserves: true
  - claim: >-
      The gate cell is still torn down when its own suite raises.
    witness: tests/test_session.py::test_the_lens_gate_cell_is_torn_down_when_its_own_suite_raises
    preserves: true
  - claim: >-
      The critic cell is still built from the repo's image at the task's tree
      base, and every lens still runs in a container the implementer never ran
      in.
    witness: tests/test_session.py::test_every_lens_runs_in_a_container_the_implementer_never_ran_in
    preserves: true
---

## Context

Backlog item **140**, found reviewing `SA-0089` (PR #282) by diffing the two
bodies. `critic_cell` and `_gate_cell_suite` in `saffron/cell/session.py` are
73 and 81 lines with comments stripped, and everything they do differently is
the network, the environment and what they hand back. The gate cell names a
network of its own and touches it in three places — `runtime.remove_network` in
the pre-clean, `runtime.create_network` with the subnet inside the `try`, and a
fourth `("network", …)` entry in the `finally` teardown list — where
`critic_cell` runs on a network the caller already has and touches none of the
three. It passes `env=dict(thread_env)` where `critic_cell` reads the proxy's
address and passes `cell_env(proxy_ip, thread_env)`. And it runs the suite where
`critic_cell` yields its container.

Everything else is verbatim: the 13-line `prepare_worktree` call, the
container-and-volume half of the pre-clean, and the `finally` loop that reports
whatever a removal left behind.

`critic_cell`'s own docstring states the rule the copy breaks, in this repo's
words:

> `SA-0088` calls this again for REBUT's verdict lenses, which is why the whole
> lifecycle lives in one function rather than being inlined at this spec's one
> call site.

`SA-0089` did not force the copy. `saffron/phases/package.py` was `forbidden`
to it, so `reverify`'s nested `_gate_cell` was out of reach — but `session.py`
was in its `touches` and nothing forbade generalising `critic_cell`. This is
how item **134**'s duplication grew by a third copy in the same file, and the
teardown loop is now written there three times: `cell_down`, `critic_cell` and
`_gate_cell_suite`.

## Problem

One cell lifecycle is written twice in one file, and the copy that came second
was made by a spec that could have called the first.

## Out of scope

**`reverify`'s own `_gate_cell`** in `saffron/phases/package.py`, the fourth
copy. That file is `forbidden` here and collapsing it is item **134**'s, not
this spec's: it runs at PACKAGE, after the task's cell is down, and needs none
of the pre-clean this one exists for.

**`cell_up` and `cell_down`.** They bring up the implementer's cell, the proxy
and the task network together, and the lifecycle this spec unifies is the
short-lived one that runs *inside* a task those two already started. Folding
all four into one is a larger change than the item asks for.

**What the gate cell records.** That the lens gate table lands in no file is
item **141** and a spec of its own. Change nothing about where this suite's
results go.

**Which subnet the gate cell gets, and how subnets are declared.** Item **143**
is the tuple in `runtime.py` and the pre-clean by value; `runtime.py` is
`forbidden` here. Keep the subnet exactly where and what it is today — move it
if the code around it moves, but do not change its value and do not add
another. Write it exactly once in `saffron/cell/session.py`: a second copy of
the literal, as a parameter default beside the constant, makes this spec's one
mutant ambiguous and so unrunnable.

## Notes for the agent

**Read `_gate_cell_suite` and `critic_cell` side by side before planning.**
The differences named in `## Context` are the whole of the difference, and the
plan should name how each is parameterised. `git diff` will not show you this —
both functions are at base.

**The network is pre-cleaned on the branch that creates it, not only torn
down.** This is the easiest thing to get wrong here, and a declared criterion
of this spec catches it:
`test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs`
counts removals rather than testing membership, and asserts each of the gate
cell's four names — container, both volumes **and its network** — is removed
exactly twice, once by the pre-clean and once by the teardown. Its counterpart
for the critic cell asserts exactly three names removed twice each, so the
branch that is *given* a network must not pre-clean one either. A unified
pre-clean that always removes a network, or never does, fails one of the two.

**The unification is the deliverable, not one of two options.** Item 140's
"done looks like" offers a recorded decision that three copies is the price of
the `touches` boundary. That escape is for a spec whose `touches` forbids the
change. This one's does not: both functions are in `session.py`, which is in
`touches`. Write the one lifecycle.

**Criteria 1–3 carry one mutant between them, and that is deliberate.**
Criterion 1's absent-network branch, criterion 2's environment argument and
criterion 3's delegation are all new control flow, so no text exists at base
that a mutant could pin honestly, and `witness` will report `skip` for 2 and 3.
Criterion 1 is the exception: the gate cell's subnet is a module constant today
and must survive the move unchanged, so its mutant pins text this repo already
determines rather than text this spec dictates.

**Criterion 1's witness must not assert the subnet equals the module's own
constant.** A test that reads the constant and compares the created network
against it passes whatever the constant says, including a value that collides
with the implementer's — which is the failure the criterion is about. Assert
instead that the subnet the gate cell's network is created on does not overlap
`runtime.DEFAULT_SUBNET`, the one the task's own `saffron-cells` network holds
for the length of the task. `ipaddress.ip_network(...).overlaps(...)` is the
comparison; `_stub_the_runtime` already records every create as a
`(name, subnet)` pair in `cell.networks_created`, added by `SA-0089` for
exactly this.

**Criterion 1's witness calls `critic_cell` directly, both branches, and that
is what makes it red at base.** Driven through `_drive`, the assertion about
subnets is already true at base — `_gate_cell_suite` creates its own network on
its own subnet today, and the `preserves` witness already asserts it — so a
`_drive`-level test of it passes with `session.py` reverted and `revert` blocks
the task. Call `session.critic_cell` itself: given a network name and an `env`,
assert it creates no network at all; given `None`, assert it creates exactly one
whose subnet does not overlap `runtime.DEFAULT_SUBNET`. At base `critic_cell`
has neither parameter, so both halves raise `TypeError` — red at base, and red
again under `revert`.

**Criterion 3's witness reaches for `critic_cell` by name.** The claim is that
one function serves both callers, and the honest observation of it is that the
gate suite's container came out of `critic_cell` — patch or wrap
`session.critic_cell` and assert the gate suite ran inside what it yielded.
Reverted, `_gate_cell_suite` builds its own container and never calls it, so
the test fails, which is what `revert` requires.

**Three `preserves` criteria are the safety net, and they are the point.**
A refactor whose behaviour changed is a failed refactor. Those three tests
exist at base — `git grep` them — and must be green at head without being
rewritten to accommodate the new shape. If one of them cannot pass unchanged,
the refactor is wrong; do not edit the test.

**Both new arguments are keyword-only and neither gets a default.** §5.1 and
Appendix I: `network` and `env` are *required* arguments where a cell is
created, because v0.5 shipped one created without either — every mechanism
reported success and applied to a different container. `DESIGN.md` states it as
"omission is an error, not a default", so `network: str | None = None` is the
defaulted omission that rule refuses, and a REVIEW lens quoting it at the diff
would be right. Write `network: str | None` with no default, have every caller
pass it explicitly, and have the branch that creates one pass the network it
created on to `prepare_worktree` exactly as the caller-supplied branch does.
The value may be absent; the argument may not.

**The environment argument is a `Mapping[str, str]`, and the proxy read moves
with it.** Today `critic_cell` reads `runtime.container_ip(proxy.PROXY_NAME)`
and raises `CellRuntimeError` when it is `None`, because `cell_env` cannot turn
`None` into a `str`. That read belongs to the caller that wants a proxied
environment, not to the lifecycle.

`critic_cell` has **two** call sites in `_drive_cell`, not one: REVIEW's, and
REBUT's verdict lenses, which `SA-0088` added and which needs the same proxied
environment. Read the proxy address once in `_drive_cell`, ahead of REVIEW,
build the `cell_env(...)` mapping from it and pass that mapping at both sites —
do not read it twice and do not leave the second site without an `env` to pass.

Keep the raise that read performs when the address is `None`: it is
infrastructure, not a task outcome, and `cell_env` cannot turn `None` into a
`str`. Nothing at base observes it — `container_ip` is stubbed to a constant in
`tests/test_session.py` and no test overrides it — so no criterion here can
witness it and no gate will catch its loss. It survives by your care alone.

**Keep both callers' names and teardown reporting.** The gate cell's container,
volumes and network are `saffron-gate-*` keyed by `spec_id`; the critic's are
`saffron-critic-*`. Both record every name in the caller's `created` ledger
immediately before the call that creates it, and both call `note` only when a
removal leaves something behind — REVIEW's green path prints nothing new.
`tests/test_events.py::test_watch_output_matches_the_golden_fixture` compares
every printed line against a fixture and both files are outside `touches`.

**The network is removed last.** `_gate_cell_suite`'s teardown removes the
container, then the volumes, then the network, in that order, because a network
with a container still on it will not go. Whatever branch creates a network has
to remove it after the container, not with it.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The ceilings are set against `history`'s worst refactor row, not against this
change's size.** The `ceilings:` line compares a `refactor` spec against
`SA-0031`, which was cut off at 141 turns with a $19.17 pre-REVIEW spend across
16 `touches`. This spec has two. The ceilings clear that row because the rule
is at-or-below, not because this change is expected to cost anything like it —
`SA-0089`, the closest cell in shape, peaked at 88 turns and $9.13 — read
off its own `history` row directly, since it is a `feature` and so is not
printed in a `refactor` comparison at all.

**The `size` gate counts tests.** A `refactor` gets 1000 changed lines, tests
included, and the source side of this one should be net negative.
