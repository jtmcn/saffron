---
id: SA-0270
title: Every task's networks take the same fixed subnets, so two tasks up at once collide on them
type: feature
priority: 3
depends_on: [SA-0269]
consumes:
  - saffron/cell/proxy.py:proxy_name
estimated_lines: 396
touches:
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/cell/session.py
  - tests/test_runtime.py
  - tests/test_proxy.py
  - tests/test_session.py
  - tests/test_events.py
  - tests/fixtures/watch-golden.txt
  - tests/test_worktree.py
  - tests/test_review_cells.py
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
  - docs/adr/**
  - docs/appendices/**
  - docs/agents/**
  - docs/backlog/**
  - docs/evidence/fixtures/**
  - docs/evidence/passes/**
  - docs/host/**
  - docs/HOST-HARDENING.md
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/end_review.py
  - saffron/preflight.py
  - saffron/phases/**
  - saffron/cell/runtimes/**
  - saffron/cell/worktree.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/gates/**
  - tests/test_end_review.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 37
max_attempts: 3
max_turns: 200
risk: standard
acceptance:
  - claim: >-
      `runtime.allocate_network(name)` walks the /24s of `SUBNETS["pool"]`
      in address order, from the pool's first /24, and claims each by
      creating network `name` on it. A create the runtime refuses, while
      `networks_on_subnet` names another network on that /24, moves the walk
      to the next /24. That move turns on the listing and never on the
      refusal's wording. Both apple/container's wording and a wording unlike
      it move the walk on. It returns the /24 whose create succeeded. A
      refused create with no other network on that /24 raises
      `CellRuntimeError` after that one create, and walks no further.
    witness: tests/test_runtime.py::test_allocate_network_skips_each_held_slash24_whatever_the_refusal_says
    wrong_versions:
      - It lists the networks first and creates once on the first /24 the listing leaves free, so no refused create is ever seen.
      - It moves to the next /24 on any non-zero exit, so a broken runtime walks all 256 before it raises.
      - It moves on only when the refusal's text contains `overlap`.
      - It starts the walk at the pool's second /24.
      - It returns the /24 it tried before the one whose create succeeded.
  - claim: >-
      When every /24 of the pool is refused with a holder listed,
      `allocate_network` raises `CellRuntimeError` after exactly one create
      per /24, in order. The error names every network that held one.
    witness: tests/test_runtime.py::test_allocate_network_names_every_holder_once_the_pool_is_exhausted
    wrong_versions:
      - The error names only the holder of the last /24 it tried.
      - It gives up after a fixed number of refusals short of the pool's 256 /24s.
      - It walks the pool's /24s a second time before it raises.
  - claim: >-
      `runtime.SUBNETS` declares one `"pool"` entry, the /16 at 10.200.0.0, and
      no `"cells"` or `"critic"` entry. The pool overlaps no other entry,
      and not `DEFAULT_SUBNET`, which PACKAGE's re-verification still
      creates its network on.
    witness: tests/test_runtime.py::test_the_pool_is_declared_once_and_overlaps_no_fixed_subnet
    wrong_versions:
      - The pool is added and the `"cells"` and `"critic"` entries are kept beside it.
      - The pool is declared as the /16 at 10.88.0.0, which holds `DEFAULT_SUBNET`.
      - The pool is declared as one /24.
    mutant:
      file: saffron/cell/runtime.py
      find: '"gate": "10.90.0.0/24",'
      replace: '"gate": "10.90.0.0/24", "critic": "10.91.0.0/24",'
  - claim: >-
      `proxy.start_proxy` takes the subnet of the network its address is
      read on as a required keyword argument, `subnet`. Given a /24 of the
      pool other than its first, it returns the proxy's address on that /24.
    witness: tests/test_proxy.py::test_start_proxy_reads_its_address_on_the_subnet_it_is_given
    wrong_versions:
      - It keeps reading the address with `container_ip`'s default prefix, `10.88.0.`.
      - It reads the address on the pool's first /24 whatever `subnet` it is given.
      - '`subnet` defaults to `runtime.DEFAULT_SUBNET`, pinned by `SA-0271`''s criterion 3.'
  - claim: >-
      A task's `cell_up` hands `start_proxy` the subnet it claimed for the
      task's cells network. Each leg's upstream probe is given the proxy's
      address on the subnet claimed for that leg's network. Each leg's host
      probe runs at that subnet's gateway. REVIEW's critic cells then carry
      the proxy's address on the subnet claimed for the task's critic
      network. Those two subnets differ, and hold whichever /24s of the
      pool were free.
    witness: tests/test_session.py::test_a_tasks_proxy_is_addressed_on_the_subnets_cell_up_claimed
    wrong_versions:
      - REVIEW reads the critic cells' proxy address on the pool's first /24.
      - REVIEW reads the critic cells' proxy address on the pool's second /24.
      - The probes keep each leg's subnet from before the claim.
      - REVIEW reads the critic cells' proxy address on the cells network's subnet.
      - '`cell_up` hands `start_proxy` the critic network''s subnet.'
  - claim: >-
      Two tasks brought up at once by `cell_up`, keyed `SY-1` and `SY-2`,
      and an end-review layer cell for `SY-3` brought up beside them, hold
      five networks on five distinct /24s of the pool. Those five are each
      task's cells and critic networks, and the end review's cells network.
      Each task's `cell_up` returns every network it created, mapped to the
      subnet it claimed for it.
    witness: tests/test_session.py::test_two_tasks_and_an_end_review_cell_hold_disjoint_subnets
    wrong_versions:
      - '`cell_up` claims the cells network from the pool and keeps the critic network on a fixed subnet.'
      - '`cell_up` creates each network a second time on `DEFAULT_SUBNET` after `allocate_network` returns.'
      - '`cell_up` returns its subnets keyed by preflight step rather than by network name.'
      - '`cell_up` returns only the cells network''s subnet.'
---

## Context

Backlog items **b-ca3bc6** and **b-6a692d**, tier 3. They cite
`DESIGN.md` §4.2, §4.2.1, §5.1 and §5.5. Lines below were read at
`60f8b3f5`, which is before `SA-0269`.

**This spec is the second of three.** `SA-0269` names the proxy and every
task network from the task. It leaves every subnet fixed. This spec moves
the task networks onto subnets allocated per task. `SA-0271` then retires
the Gate-only cell's fixed subnet and PACKAGE's re-verification on
`DEFAULT_SUBNET`.

**What `SA-0269` gives this spec.** `proxy.proxy_name(key)` returns
`saffron-proxy-<key lower>`. `start_proxy`, `denied_egress`,
`failed_egress` and `stop_proxy` take that proxy name. So does
`session.proxy_address(proxy_name, subnet)`. `cell_up` and `cell_down`
take a required keyword `proxy_name`. `_drive_cell` names its
networks `saffron-cells-<id lower>` and `saffron-critic-net-<id lower>`.
`session.CRITIC_NETWORK` is gone. `end_review.layer_cell` names its
network `saffron-cells-endreview-<id lower>`. Read each at your base
before you edit near it.

**The subnets, as the base declares them.** `runtime.SUBNETS` is the one
declaration of every subnet Saffron allocates (backlog item 143,
`saffron/cell/runtime.py:163-170`). It holds `"cells"` as
`DEFAULT_SUBNET`, `"egress"` as `10.89.0.0/24`, `"gate"` as
`10.90.0.0/24` and `"critic"` as `10.91.0.0/24`. `DEFAULT_SUBNET` is
`10.88.0.0/24` (`saffron/cell/runtime.py:161`). `SUBNET_PREFIX` and
`GATEWAY` derive from it (`saffron/cell/runtime.py:195-196`).
`create_network` raises `CellRuntimeError` on any non-zero exit
(`saffron/cell/runtime.py:311-333`). It adds the holders from
`networks_on_subnet` only when the error text says `overlap`
(`saffron/cell/runtime.py:329-332`). `networks_on_subnet` lists every
network whose subnet overlaps the one asked about
(`saffron/cell/runtime.py:336-363`). It returns an empty list when the
listing exits non-zero (`:346-347`). When the binary cannot be run at
all, `_call` raises `CellRuntimeError` (`:288-291`). `create_network`
reaches `_admit` first, which raises `CellRuntimeError` on a host the
runtime refuses, before any create (`saffron/cell/runtime.py:105-116`).

**Where a task's subnets are read.** One `_Leg` per internal network is
built at `saffron/cell/session.py:1046-1055`. The cells leg takes
`runtime.DEFAULT_SUBNET` and the critic leg takes `_CRITIC_SUBNET`
(`:980`, drawn from `SUBNETS["critic"]`). It creates each at `:1063-1065`,
then starts the proxy at `:1072`. It probes the upstream per leg through
`proxy_address(leg.subnet)` at `:1074-1078`. It probes the host from each
leg at `runtime.gateway(leg.subnet)` (`saffron/cell/session.py:1095-1111`).
`cell_up` returns `None`. REVIEW reads the
critic cells' environment through `proxy_address(_CRITIC_SUBNET)` at
`:2778`. `start_proxy` reads its own address with
`runtime.container_ip(PROXY_NAME)` at `saffron/cell/proxy.py:69`. That
reads with `container_ip`'s default prefix, `SUBNET_PREFIX`
(`saffron/cell/runtime.py:618`). So a proxy whose cells network leaves
`10.88.0.0/24` returns no address, and `start_proxy` times out.

**The end review.** `layer_cell` brings a whole cell up through
`session.cell_up` with `critic_network=None`
(`saffron/end_review.py:597-626`). It ignores what `cell_up` returns.

**What the runtime does on a held subnet.** Measured on 2026-10-11 on
apple/container 1.3.0. `network create --internal --subnet
10.200.0.0/24` succeeds. A second create of that /24 under another name
exits 1 with "Error: IPv4 subnet 10.200.0.0/24 overlaps an existing
network with subnet 10.200.0.0/24". A /25 inside it is refused the same
way. `10.200.1.0/24` beside it succeeds. The host's LAN is `10.0.0.x`,
and apple/container's default network is `192.168.64.0/24`. So
`10.200.0.0/16` overlaps neither. Podman is unmeasured.

## Problem

Every task network takes a fixed subnet. A second task brought up beside
a first asks the runtime for a /24 the first one holds, and its create
fails. Names alone, from `SA-0269`, do not let two tasks run at once.

1. **The pool.** In `runtime.SUBNETS`, replace the `"cells"` and
   `"critic"` entries with one `"pool"` entry, `10.200.0.0/16`. Keep
   `"egress"` and `"gate"`. Keep `DEFAULT_SUBNET`, `SUBNET_PREFIX` and
   `GATEWAY` as they are. PACKAGE's re-verification still creates on
   `DEFAULT_SUBNET` until `SA-0271`. Rewrite the comment above
   `SUBNETS` to say so.
2. **`allocate_network(name: str) -> str`**, new in
   `saffron/cell/runtime.py`. It walks the pool's /24s in address order.
   The create is the claim, so it never lists first and then creates.
   Create through `create_network(name, subnet=...)`, looked up on the
   module, so a test that replaces `runtime.create_network` reaches it.
   On a refused create, ask `networks_on_subnet(<that /24>,
   exclude=name)`. A holder moves the walk on. No holder raises the
   create's own error. Exhaustion raises `CellRuntimeError` naming every
   holder it met. `SA-0271` calls this exact name and signature. It also
   moves `_admit()` ahead of the walk. Leave that to it.
3. **`start_proxy`** takes a required keyword argument `subnet` and reads
   its address with that subnet's prefix (`runtime.subnet_prefix`).
4. **`cell_up`** claims each leg's subnet with `allocate_network`, after
   its pre-clean by name and in place of `create_network`. It hands
   `start_proxy` the cells leg's subnet. Every per-leg probe reads the
   claimed subnet. It returns a `dict[str, str]` from each network it
   created to the subnet it claimed. Rewrite the docstring sentence that
   says nothing bound in it outlives the call.
5. **REVIEW** reads the critic cells' proxy address on the subnet
   `cell_up` returned for the critic network. Delete `_CRITIC_SUBNET`.
6. **The tests the change makes false.** Section "Tests at base" in the
   notes lists them.

## Out of scope

- The Gate-only cell's fixed `"gate"` subnet and PACKAGE's
  re-verification on `DEFAULT_SUBNET`. `SA-0271` owns both.
- More than one task at a time in a batch (K > 1, `DESIGN.md` §4.2.1).
  This spec makes the networks able to hold two tasks, and starts no
  second one.
- The spec loop's driver, and backlog items b-a714d2, b-d9ed45 and 108.
- A cell-marked test that starts two tasks and probes between them. The
  item asks for one. The witnesses here are unit tests over a fake
  runtime, so the isolation between two live tasks stays unmeasured.
- The walk on podman. `networks_on_subnet` reads a subnet from the
  listing's second column, and `podman network ls` prints none (backlog
  item 108). So on podman it names no holder, and the walk raises at the
  first held /24 and never moves on. Podman nights are refused today.
- `DESIGN.md` §5.1's sketch at `DESIGN.md:626` creates `saffron-cells`
  on `10.88.0.0/24`. After this spec a task's cells network takes a /24
  of `10.200.0.0/16` instead. `DESIGN.md` is protected, so the operator
  updates it.

## Notes for the agent

**Your base.** `SA-0269` lands first. Its proxy name, network names and
the `proxy_address(proxy_name, subnet)` signature are in your base. Read
`saffron/cell/proxy.py`, `cell_up`, `_drive_cell` and REVIEW's
`critic_env` line at your base before you edit them.

**Commit as each witness passes.** One commit per criterion keeps a
cut-off attempt's work.

**Edit or new.** `allocate_network` is new code. The edits to
`start_proxy`, `cell_up` and REVIEW land on lines `SA-0269` rewrote after
this spec was written. So criteria 1, 2, 4, 5 and 6 declare a witness and
no mutant, and `witness` reports `skip` for them. Criterion 3 is an edit
to `runtime.SUBNETS`, which `SA-0269` leaves alone. Its mutant puts the
critic entry back beside the gate entry.

**Each witness fails at your base.** `allocate_network`, `start_proxy`'s
`subnet` and the `"pool"` entry do not exist there, and `cell_up` returns
`None`. Reach each through its module inside the test, never by a
module-scope import. A module-scope import of a name the change adds
makes the reverted run a collection error, which `revert` reads as
`skip`.

**The runtime witnesses (criteria 1 and 2)** replace `runtime._call`, as
`test_an_overlapping_network_names_the_one_already_holding_the_subnet`
does at `tests/test_runtime.py:641-663`. Record every create argv. Answer
`network list` with a header row and one line per holder, as that test
does.

- Criterion 1 lists holders on the pool's first two /24s. The first /24
  is refused with apple/container's measured text, quoted in the
  context. The second is refused with stderr holding no `overlap`, such
  as "Error: netavark: refused". The stderr is the only wording a test
  can vary. `create_network`'s error always carries the argv's
  `--subnet`, and never `overlap`, so a build keyed on `overlap` still
  fails here. It asserts
  the creates ran on the first three /24s in order and the third came
  back. Its second half refuses the first create with no holder listed.
  It asserts `CellRuntimeError` and exactly one create.
- Criterion 2 lists two holders, one on each /17 of the pool, and refuses
  every create. It asserts 256 creates, in address order, and both
  holder names in the error.

**The session fake must model a claim.** `_stub_the_runtime`'s
`_create_network` at `tests/test_session.py:1032-1041` records every
create and refuses none. Make it hold a claim per live network. A create
whose subnet overlaps a live network of another name raises
`CellRuntimeError`, as the runtime does. A create of a live name raises
too. `remove_network` releases the name's claim. `networks_on_subnet`
reports live claims that overlap the subnet asked about, beside the
holders a test passes in. Keep `networks_created` as it is.

**Criterion 4's `subnet` is required, but its witness always passes
it.** `SA-0271`'s criterion 3 checks that it has no default. Until
`SA-0271` lands, a defaulted `subnet` would pass here.

**Criterion 4's witness** replaces `runtime.call`, `run_detached`,
`remove_container` and `container_ip`. Its `container_ip` answers only for
the prefix of the /24 it hands `start_proxy`. Pass a short `timeout_s`, so
a wrong version fails in under a second.

**Criterion 5's witness** runs `_drive` to `READY_FOR_REVIEW` over that
fake. Before `_drive`, it creates a network named `held` on the pool's
first /24 through the fake. The task then claims the second and third,
so neither its cells nor its critic network is on a /24 a fixed reading
would guess. It replaces `proxy.start_proxy` with a recorder of its
keyword arguments. It replaces `preflight.assert_proxy_reaches_upstream`
and `preflight.assert_host_is_unreachable` with recorders of the network
and the address each was given, as
`test_cell_up_puts_the_proxy_on_the_critic_network_and_probes_it` does.
Assert both legs' probes against the subnets the fake recorded. It replaces `container_ip` with one returning
`f"{subnet_prefix}9"`, as
`test_the_critic_cell_is_not_on_the_implementers_network` does at
`tests/test_session.py:7541-7544`. Take each network from the worktree it
was given, and each subnet from `networks_created`.

**Criterion 6's witness** calls `session.cell_up` twice with a critic
network, keyed `SY-1` and `SY-2`. Name each network and proxy the way
`_drive_cell` does at your base. It then opens
`end_review.layer_cell` for `SY-3`, imported inside the test, and reads
`networks_created` inside the `with` block. Assert each subnet lies in
the pool and no two overlap. Compare each task's returned mapping with
what `networks_created` recorded for its two names.

**Tests at base that the change makes false.** Update each and keep its
name. A test's name is in the census, so none is removed.

- Every test `SA-0269` added that calls `start_proxy`, or replaces
  `start_proxy` or `container_ip` with a fake. Pass `subnet=` to the one,
  and let each fake take `subnet=` and a prefix. Read them at your base.
- `test_the_preflight_line_reports_what_was_tolerated`
  (`tests/test_session.py:1640-1647`) expects the probe line to start at
  `10.88.0.1`. Over the claim model it starts at the gateway of the
  pool's first /24.
- `test_normalise_replaces_exactly_the_three_volatile_substrings`
  (`tests/test_events.py:1893-1901`) expects `runtime.GATEWAY` to survive
  `_normalise`. `_GATEWAYS` is built from `SUBNETS.values()`, which loses
  `DEFAULT_SUBNET`. Keep `DEFAULT_SUBNET`'s gateway in `_GATEWAYS`.
  `SA-0271` deletes it.

- `test_every_subnet_saffron_allocates_is_declared_in_one_place`
  (`tests/test_runtime.py:685-728`) asserts the `"cells"` and `"critic"`
  entries and reads `_CRITIC_SUBNET`. Drop those, and keep its check that
  `proxy.py` and `session.py` spell no subnet.
- `test_cell_up_puts_the_proxy_on_the_critic_network_and_probes_it`
  (`tests/test_session.py:7556-7612`) expects `SUBNETS["critic"]` and
  `runtime.GATEWAY`. Expect the subnets the fake recorded instead.
- `test_the_critic_cell_is_not_on_the_implementers_network`
  (`tests/test_session.py:7533-7553`) reads `SUBNETS["critic"]`.
- The golden fixture. `tests/fixtures/watch-golden.txt:8` and `:43` read
  "probing 1 host ports at 10.88.0.1, 10.91.0.1". Over the claim model
  those become the gateways of the pool's first two /24s.
  `_GATEWAYS` at `tests/test_events.py:1875` keeps only the gateway of
  each `SUBNETS` value, so the second one would read `<LAN-ADDR>`. Keep
  the gateway of every /24 in the pool there too.
- `start_proxy`'s cell-marked callers pass `subnet=runtime.DEFAULT_SUBNET`,
  since their network is created on it: `tests/test_proxy.py:39`, `:122`
  and `:140`, and `tests/test_worktree.py:282`.
- `tests/test_review_cells.py:193` reads the proxy's address with the
  default prefix. `tests/test_review_cells.py:231` reads
  `SUBNETS["critic"]`. Read both from the mapping `cell_up` returns.
- Two evidence scripts, which the `types` gate reads because `ty` covers
  `docs/` (`pyproject.toml:55-58`).
  `docs/evidence/scripts/2026-08-28-egress-nat-order.py:61` calls
  `start_proxy` on a network created on `DEFAULT_SUBNET`, so it passes
  that subnet. `docs/evidence/scripts/2026-10-01-critic-cell-peer-reach.py:127`
  reads the proxy's address with the default prefix.
  `docs/evidence/scripts/2026-10-01-critic-cell-peer-reach.py:131` reads
  `SUBNETS["critic"]`. Read both from the mapping `cell_up` returns there
  too. Change nothing else in either script.

**The `prose` gate** reads every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Size.** The `feature` ceiling is 3000 changed tokens. `saffron/cell/**`
is in `elevate_on`, so `size` blocks.
