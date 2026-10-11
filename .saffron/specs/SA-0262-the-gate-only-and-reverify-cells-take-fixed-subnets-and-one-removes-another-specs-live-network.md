---
id: SA-0262
title: The gate-only cell and reverify's cells take fixed subnets, and the gate-only cell's pre-clean removes another spec's live network
type: feature
priority: 3
depends_on: [SA-0261]
consumes:
  - saffron/cell/runtime.py:allocate_network
estimated_lines: 480
estimate_measured: true
touches:
  - saffron/cell/runtime.py
  - saffron/cell/session.py
  - saffron/cell/runtimes/podman.py
  - saffron/phases/package.py
  - saffron/preflight.py
  - tests/conftest.py
  - tests/test_session.py
  - tests/test_package.py
  - tests/test_runtime.py
  - tests/test_preflight.py
  - tests/test_events.py
  - tests/test_proxy.py
  - tests/test_worktree.py
  - tests/test_agent_runner.py
  - tests/test_review_cells.py
  - tests/test_two_tasks_beside_each_other.py
  - docs/evidence/scripts/2026-08-28-egress-nat-order.py
  - docs/evidence/scripts/2026-10-01-critic-cell-peer-reach.py
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
  - docs/backlog/**
  - docs/appendices/**
  - docs/adr/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/scheduler.py
  - tests/test_scheduler.py
budget_usd: 36
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      Two gate-only cells of two specs can be up at once. Each claims its
      network from the pool with `allocate_network`, so their names and
      subnets are disjoint and each subnet lies inside `SUBNETS["pool"]`.
      The second one's pre-clean and its teardown leave the first one's
      network in place. A leftover under the second one's own name is still
      removed before its claim, and each one's teardown removes its own
      network. The witness brings both up through `critic_cell` with
      `network=None`, one inside the other, over a model of the runtime's
      networks.
    witness: tests/test_session.py::test_two_gate_only_cells_at_once_hold_disjoint_networks_and_neither_removes_the_other
    mutant:
      file: saffron/cell/session.py
      find: runtime.allocate_network(network)
      replace: runtime.create_network(network, "10.90.0.0/24")
    wrong_versions:
      - The gate network created on one fixed subnet, so the second create collides with the first.
      - The sweep kept, now over the pool, removing every `saffron-` holder on it before the claim.
      - The by-name pre-clean dropped, so a leftover under the cell's own name makes its claim raise.
      - The teardown's network removal dropped, so the second cell's network outlives it.
  - claim: >-
      Two reverify runs for two packaged commits can overlap. Each of
      reverify's two gate-only cells, baseline and head, claims its network
      from the pool with `allocate_network`, inside `SUBNETS["pool"]`, and
      disjoint by name and subnet from every network the other run holds.
      The second run's pre-clean and teardown leave the first run's live
      network in place. A leftover under either cell's own network name is
      removed before that cell's claim, and every cell's teardown removes
      its own network. The witness starts the second run from inside the
      first run's baseline cell, over a model of the runtime's networks.
    witness: tests/test_package.py::test_two_reverify_runs_at_once_hold_disjoint_networks_and_neither_removes_the_other
    mutant:
      file: saffron/phases/package.py
      find: runtime.allocate_network(network)
      replace: runtime.create_network(network, "10.88.0.0/24")
    wrong_versions:
      - The network created on one fixed subnet, so the second run's create collides with the first's.
      - A pre-clean that removes every `saffron-pkg-` network on the pool, so the first run's live one goes.
      - No pre-clean by name, so a leftover under a cell's own network name makes its claim raise.
      - The teardown's network removal dropped.
      - The head cell claiming from the pool and the baseline cell still on a fixed subnet.
  - claim: >-
      No subnet is assumed any more. Each of these five parameters is
      required, with no default: `create_network`'s subnet,
      `container_ip`'s subnet prefix, and the gateway of
      `probe_addresses`, `probe_host_bindings` and
      `assert_host_is_unreachable`. `runtime` defines none of
      `DEFAULT_SUBNET`, `SUBNET_PREFIX` and `GATEWAY`. `SUBNETS` has no
      "gate" key, and `session` defines no `_GATE_CELL_SUBNET`.
    witness: tests/test_runtime.py::test_every_network_call_names_its_subnet_and_no_default_subnet_is_left
    mutant:
      file: saffron/cell/runtime.py
      find: "def container_ip(name: str, subnet_prefix: str) -> str | None:"
      replace: "def container_ip(name: str, subnet_prefix: str = \"10.88.0.\") -> str | None:"
    wrong_versions:
      - One of the five parameters keeps a default, such as the gateway of `assert_host_is_unreachable`.
      - A default of `None` resolved to the old subnet inside the function.
      - "`DEFAULT_SUBNET`, `SUBNET_PREFIX` or `GATEWAY` kept as a constant nothing reads."
      - The "gate" entry left in `SUBNETS`.
---

## Context

Backlog item **b-ca3bc6**, with **b-6a692d**. It cites `DESIGN.md` §5.1
and §5.7. This is the last of three specs. `SA-0260` names the proxy and
every task network from the task. `SA-0261`, the parent, adds a pool to
`runtime.SUBNETS` and the function `allocate_network`. That function walks
the pool's /24s, claims one by creating the network on it, and returns the
subnet it claimed. It raises `CellRuntimeError` when the pool is spent. Read
both at the tree base before you start. Every line number below was read at
`60f8b3f5`, the parent's own base, in code the parent leaves alone.

**The gate-only cell takes one fixed subnet for every spec.** `critic_cell`
with `network=None` names its network from the spec id
(`saffron/cell/session.py:1393`). It creates it on `_GATE_CELL_SUBNET`
(`:1416`), which is `runtime.SUBNETS["gate"]` (`:1331`). Its pre-clean then
removes every `saffron-` network on that subnet (`:1405-1410`). So a second
spec's gate-only cell removes the first spec's live network. The test of
that sweep is
`test_the_gate_cells_pre_clean_removes_a_leftover_saffron_network_on_its_subnet_and_nothing_else`
(`tests/test_session.py:8314`).

**Reverify's cells take the default subnet.** `reverify`'s `_gate_cell`
names its network from the packaged commit (`saffron/phases/package.py:530-532`).
It creates it with `create_network(network)` (`:539`), so on
`DEFAULT_SUBNET`, `10.88.0.0/24` (`saffron/cell/runtime.py:161`, `:311`).
Any live network on that subnet makes the create fail. It pre-cleans
nothing, and removes the network in its `finally` (`:564-568`).

**The default subnet is still the default everywhere.** `create_network`
defaults its subnet to `DEFAULT_SUBNET` (`saffron/cell/runtime.py:311`).
`container_ip` defaults its prefix to `SUBNET_PREFIX` (`:618`).
`probe_addresses`, `probe_host_bindings` and `assert_host_is_unreachable`
default their gateway to `GATEWAY` (`saffron/preflight.py:158`, `:187`,
`:233`). In the last two it follows `ports`, which defaults to `None`
(`:186`, `:232`). `SUBNET_PREFIX` and `GATEWAY` are derived at
`saffron/cell/runtime.py:195-196`. `_NETWORK` is derived at
`saffron/cell/runtime.py:182`, and nothing reads it. At base, `start_proxy`
(`saffron/cell/proxy.py:51`) reads its own address with the default prefix
(`saffron/cell/proxy.py:69`). A comment names `DEFAULT_SUBNET` at
`saffron/cell/runtimes/podman.py:84`. A test reads `GATEWAY` at
`tests/test_events.py:1895` and `:1899`.

**What the parent leaves for you.** By its own text, `SA-0261` keeps
`DEFAULT_SUBNET`, `SUBNET_PREFIX`, `GATEWAY` and the "gate" entry. It makes
`start_proxy` take its subnet as a keyword. Its cell-marked callers of
`start_proxy` pass `DEFAULT_SUBNET`, since their networks are still
created on it. Its witness
`test_the_pool_is_declared_once_and_overlaps_no_fixed_subnet` checks that
the pool misses `DEFAULT_SUBNET`. Its `_stub_the_runtime` fake refuses a
create on a held subnet. Read each at the tree base.

**`census` fails a removed test name** (`saffron/gates/core/census.py:34-38`).
So an existing test whose subject goes keeps its name, and its body is
rewritten.

## Problem

Claim the gate-only cell's network with `allocate_network`, and delete the
sweep, `_GATE_CELL_SUBNET` and `SUBNETS["gate"]`. Keep the by-name pre-clean
of the cell's own network. Another spec's network is never removed.
Fix the docstring of `networks_on_subnet` (`saffron/cell/runtime.py:336`).
Its last lines say the Gate-only cell's pre-clean removes nothing (`:342-344`).
Once the sweep goes, that cell never reads it.

Claim each of reverify's two networks with `allocate_network`. Remove the
cell's own network by name before the claim, since a leftover under that
name would make the claim raise.

Then delete `DEFAULT_SUBNET`, `SUBNET_PREFIX`, `GATEWAY` and `_NETWORK`, and
drop each default above, so each caller names its subnet. A parameter with
no default cannot follow one with a default. So in the two probe functions
the gateway moves ahead of `ports`, and every caller follows. Any reader
of a removed name that the parent leaves names its subnet instead. Rewrite the podman comment to name the subnet the
host refused, `10.88.0.0/24`. One evidence script,
`docs/evidence/scripts/2026-08-28-egress-nat-order.py`, keeps the setup it
measured. It calls `runtime.create_network(NETWORK)` with no subnet (`:57`).
Pass the literal `"10.88.0.0/24"` there.

In `allocate_network`, call `_admit()` once before the walk. A host refusal
then raises as itself, never as an exhausted pool. The exhaustion error also
carries the last refused create's own error text. The parent left this here
on size. Pin it in an existing `test_runtime.py` test of the walk.

## Out of scope

- **One spec in two cells at once.** The gate-only cell stays named from
  the spec id (b-d9ed45).
- **Batch concurrency.** b-a714d2, item 108, K above one and the spec loop
  driver.
- **Two `DESIGN.md` lines.** §5.1's worked example names `saffron-cells`,
  `saffron-proxy` and `10.88.0.0/24`. `DESIGN.md:680` says the one measured
  host refused `DEFAULT_SUBNET`, a name this spec deletes. Both are edited
  by hand with this spec.

## Notes for the agent

**Commit as each witness passes.** A cut-off attempt keeps the work.

**Each criterion edits code that exists**, so each declares a mutant.

**One claim per file.** Each of `critic_cell` and `_gate_cell` calls
`allocate_network` through `runtime` once. It passes the local `network` as
the only argument. A mutant's find
must match exactly once (`saffron/cell/worktree.py:731`). In `session.py`
that relies on `SA-0261` spelling `cell_up`'s claim as
`runtime.allocate_network(leg.network)`, with `leg.network` as the argument.

**A model of the runtime's networks.** Criteria 1 and 2 fake
`saffron.cell.runtime._call`, so the real `allocate_network` runs however
it reaches the runtime. Put the model in one fixture in `tests/conftest.py`,
not autouse. It keeps a name-to-subnet map. A create whose name is taken
fails with "already exists". A create whose subnet overlaps a held one
fails with a message holding "overlap". A listing prints a header row, then
one name and subnet per line, as `networks_on_subnet` parses them
(`saffron/cell/runtime.py:353-362`). A removal drops the name. Anything else
returns a clean success. `create_network` reads that wording at `:329-333`.

**Criterion 1** calls `critic_cell` directly, as
`test_critic_cell_creates_its_own_network_only_when_it_is_not_given_one`
does (`tests/test_session.py:7797`). Stub `prepare_worktree` and
`_apply_and_commit_patch`. Seed a leftover under the second spec's own
network name on a pool /24. Enter the first spec's cell, then the second's
inside it. Assert which names the model holds inside the second, after it,
and after the first.

**Criterion 2** drives `reverify` as `_reverify_stubbed` does
(`tests/test_package.py:261`), with its own stubs over the model in place
of `_stub_package_cells`. The first run's first `run_suite` call starts the
second run for another packaged commit. Guard that re-entry with a flag.
Seed a leftover under each of the second run's two network names.

**At the tree base each witness fails.** The sweep removes the first
cell's network. Reverify's second create overlaps the first on the default
subnet. The defaults exist.

**Existing tests that change.** The sweep test keeps its name and asserts
that another spec's networks survive and its own leftover does not. The
lens gate cell test asserts `10.90.0.0/24` (`tests/test_session.py:8146`).
Assert the pool there instead. `_stub_package_cells` stubs `create_network`
(`tests/test_package.py:227-234`). The real `allocate_network` creates
through that stub, so the first /24 succeeds with no runtime call. Stubbing
`allocate_network` as well is optional.
`test_every_subnet_saffron_allocates_is_declared_in_one_place`
(`tests/test_runtime.py:685`) keeps its name. It reads `SUBNETS["gate"]`
and `_GATE_CELL_SUBNET` at `:709`, and `DEFAULT_SUBNET` at `:707` unless the
parent changed that line. Its AST loop also looks up `"_GATE_CELL_SUBNET"`
by string at `:717`. `ty` cannot see that string or the dict key, and the
loop fails only at run time, on `(value,) = []`. Drop the gate entry from
both. `test_critic_cell_creates_its_own_network_only_when_it_is_not_given_one`
(`tests/test_session.py:7797`) asserts no overlap with `DEFAULT_SUBNET` at
`:7847`. Assert the subnet lies inside the pool instead. Every test or evidence
script that relied on a removed default now names a subnet. A `cell`-marked
test claims its network with `allocate_network`, so a by-hand run beside a
live task never collides with it. `test_the_subnet_is_the_only_place_the_network_is_written`
(`tests/test_runtime.py:502`) keeps its name and asserts `subnet_prefix` and
`gateway` over one pool /24. The parent's pool test keeps its name and
drops its `DEFAULT_SUBNET` half. The `types` gate checks `tests/` and
`docs/`, so it names any attribute read you miss, but not a string.

**`cell`-marked tests, which you cannot run.**
Several change with the probe functions. In `tests/test_proxy.py`, the
`network` fixture's `runtime.create_network(NETWORK)` (`:30-34`) now
claims a subnet and yields it with the name. Each
`preflight.probe_host_bindings` call (`:101`, `:124`) passes the gateway
ahead of `ports`. The same holds for `tests/test_worktree.py` (`:26-29`, `:282`),
`tests/test_agent_runner.py` (`:422`, `:455`) and
`tests/test_review_cells.py`. Only `ty` checks these. Then write
`tests/test_two_tasks_beside_each_other.py`. Bring two tasks up at once
with `cell_up`, named as `_drive_cell` names them at the tree base, and tear
both down in a `finally`. From each implementer, connect to its own proxy
first, as the positive control. Then try the other task's proxy on each of
its networks, and the other implementer. Each must fail.
`tests/test_review_cells.py` has the probe program to copy. None of these is
a witness. The cell runs no `cell`-marked test, so the operator runs
`uv run pytest -m cell tests/test_proxy.py tests/test_worktree.py tests/test_agent_runner.py tests/test_review_cells.py tests/test_two_tasks_beside_each_other.py`
by hand before the pull request merges.

**`saffron/cell/**` is in `elevate_on`,** so this task runs `elevated` and
`size` blocks.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** A prototype over a stand-in for the parent's `allocate_network`,
at an emulated base, measured 1535 tokens with `size_gate`'s counter. It
measured the source edits, the three witnesses and the conftest model. The
rest was counted by hand: the new `cell`-marked file at about 90 lines, and
the existing test and evidence-script edits that rest on the parent's real
text at about 95. `estimated_lines` is 470, the measured part over four plus
those counts and a margin for comments. The `feature` ceiling is 3000.
