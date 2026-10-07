---
id: 10
title: "Saffron ships as an engine that each operator deploys"
status: accepted
date: 2026-10-06
supersedes: []
superseded_by: []
appendices: [C, G]
principles: [4, 7, 12, 14, 21, 23, 25, 30, 31, 32, 33, 62]
---

## Context

§1.3 constrains Saffron to one machine and one operator. §1.4 refuses
multi-tenancy, and it refuses cloud runners "until throughput actually binds".
Two things changed, at the operator's request of 2026-10-06.

Other operators are now expected to run Saffron on their own repos. And the
laptop binds before throughput does. §11 already names the cost: "Mac must be
awake". `launchd` runs a missed night once the Mac wakes, so a closed lid moves
the night into the day (`docs/HOST-HARDENING.md` §4a).

Saffron today is one host process run from a checkout. It reads each target
repo's `.saffron/` and keeps one store under `~/.saffron`. Each command takes
one `--repo`, and nothing schedules across repos yet (§9, v2).

The obvious shape for many operators is a package installed into each target
repo. That shape bundles three choices. They are how the engine ships, where
state lives, and what one process arbitrates.

## Decision

Saffron ships as an engine, a versioned artifact that an operator deploys. A
deployment is one engine, one operator, one home, and the target repos that
operator configures. The home is the `--home` directory, `~/.saffron` by
default. The operator stays singular per deployment. So §2's trust model holds
unchanged. The operator trusts their own repos and distrusts their own cells.

The engine is never a dependency of a target repo. A target repo carries
`.saffron/` and no engine. A target repo belongs to one deployment, because
task branches and the record carry no deployment in their names.

Each deployment arbitrates its operator's shared resources. These are the model
credential, the budget and the review queue.

A deployment runs on a host that meets one contract. The host runs the cell
runtime on Linux or macOS. Its memory and CPU ceilings are enforced, and
measured on that host. It holds the token outside every cell, and it pulls the
engine by digest. Two hosts are supported. The first is the operator's Mac,
which meets the contract once item b-2e0b97 ships the engine. The second is a
Linux host VM running rootless podman. GCP is this operator's instance of the
second.

A deployment that runs inside a target repo's CI stays refused. It would hold
the credential as a repo secret, beside branches that cells write. And two
such deployments would split one operator's queue.

A hosted service that runs other operators' repos stays refused. It adds a
boundary between operators that §2 does not draw.

## Options considered

- **A package installed into each target repo.** Each repo pins its own
  version and holds narrow credentials. One operator's queue splits across
  repos, and nothing arbitrates their shared credential. A Python dependency
  cannot enter a Rust repo either, which breaks §1.3 and N8.
- **One hosted service for many operators.** Each operator's
  `.saffron/Dockerfile` and gates run as untrusted code on shared hosts. Every
  cell network shares one name today (item b-ca3bc6), so two operators' cells
  would share it too.
- **An engine each operator deploys (chosen).** One control plane per operator
  keeps one queue and one budget. The engine ships as an artifact, so another
  operator installs what this repo's nights run.

## Principles

- **4** upholds. Every control stays outside the cell on both hosts. The
  refusal of a CI deployment keeps the credential away from branches that
  cells write.
- **7** departs. The departure is accepted. A repo that declares no
  `thread_env` runs with an uncapped pool on a Linux host VM. Refusing it
  would block every repo whose tools size no pool. So item b-0569f7 warns, and
  records the uncapped pool on the task. A gate that flakes there is then
  attributable to the host, not the model.
- **12** upholds. The boundary is `.saffron/` and the gate contract. No
  deployment adapter is built before a second host needs it.
- **14** departs. Another operator's repo widens the claim that §2.1 holds
  across operators, and no test measures it yet. Item b-a9ec4b states that
  pass condition. The language claim stays with §9's v3 and its dissimilar
  third repo.
- **21** departs. One deployment per target repo keeps one writer per branch.
  Nothing enforces it yet. Item 170's compare-and-swap on a ref is where a
  deployment's claim on a repo would live, which is reasoned and not measured.
- **23** upholds. The §1.4 refusals that change, and the CI refusal this ADR
  adds, are each written beside the entry they amend.
- **25** upholds. Engine and deployment enter `CONTEXT.md` with this ADR.
- **30** upholds. §1.3, N4, N6, the §2 diagram, §9's v3 and §11's two runtime
  rows each say where this ADR changes them.
- **31** departs. It pairs with 7. On a shared kernel, `thread_env` is the only control
  over a pool sized from `sysconf` (§5.1).
- **32** upholds. The host contract is the decision, and GCP is one instance
  of it.
- **33** departs. No night has run on a Linux host VM, and §5.1 states the
  podman safety argument as weaker. The isolation stays a hypothesis until
  item b-da550a runs Appendix G's four assertions there.
- **62** upholds. The cloud-runner refusal gave throughput as its reason. The
  laptop binding is a different reason, outside the one the refusal named.

## Consequences

- §1.4 narrows its multi-tenant refusal, withdraws its cloud-runner refusal,
  and refuses a deployment inside a target repo's CI. `CONTEXT.md` defines the
  engine and the deployment, and the operator as singular per deployment.
- The engine ships as an image built from `main` and pinned by digest. Each
  task records the engine commit that judged it (item b-2e0b97).
- `.saffron/` becomes an interface that other operators write against. Its
  formats declare a schema version, and the engine refuses a field it parses
  and never reads (item b-0569f7).
- Saffron becomes a target repo like any other. Its nights run on a released
  engine, and a merge reaches the engine only through a release.
- The Linux host VM is a module the operator applies in their own cloud
  project. This repo's instance runs on GCP, and its nights move there first
  (item b-da550a).
- Onboarding and spec writing ship as a Claude Code plugin. An operator then
  writes `.saffron/` without this checkout (item b-a9ec4b).
- Items 170, 108 and b-ca3bc6 come before the Linux host VM. The record on
  `refs/saffron/*` lets a host VM be discarded. Podman must run a night, and
  two concurrent cells must not share a network.
