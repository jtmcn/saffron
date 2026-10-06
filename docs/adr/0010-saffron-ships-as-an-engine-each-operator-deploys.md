---
id: 10
title: "Saffron ships as an engine that each operator deploys"
status: accepted
date: 2026-10-06
supersedes: []
superseded_by: []
appendices: [C, G]
principles: [4, 12, 14, 23, 25, 30, 31, 32, 33, 62]
---

## Context

§1.3 constrains Saffron to one machine and one operator. §1.4 refuses
multi-tenancy, and it refuses cloud runners "until throughput actually binds".
Two things changed, at the operator's request of 2026-10-06.

Other operators are now expected to run Saffron on their own repos. And the
laptop binds before throughput does. §11 already names the cost: "Mac must be
awake". Nights run under launchd, and a night stops when the laptop sleeps.

Saffron today is one host process run from a checkout. It reads each target
repo's `.saffron/` and keeps one store under `~/.saffron`. Each command takes
one `--repo`, and nothing schedules across repos yet (§9, v2).

The obvious shape for many operators is a package installed into each target
repo. That shape bundles three choices. They are how the engine ships, where
state lives, and what one process arbitrates.

## Decision

Saffron ships as an engine, a versioned artifact that an operator deploys. A
deployment is one engine, one operator, one home, and the target repos that
operator configures. The operator stays singular per deployment. So §2's trust
model holds unchanged. The operator trusts their own repos and distrusts their
own cells.

The engine is never a dependency of a target repo. A target repo carries
`.saffron/` and no engine.

Each deployment arbitrates its operator's shared resources. These are the model
credential, the budget and the review queue.

A deployment runs on a host that meets one contract. The host runs the cell
runtime on Linux or macOS. It holds the token outside every cell, and it pulls
the engine by digest. Two hosts are supported. The first is the operator's own
Mac, as today. The second is a Linux host VM running rootless podman. GCP is
this operator's instance of the second.

A deployment that runs inside a target repo's CI stays refused. It would hold
the credential as a repo secret, beside branches that cells write. And two
such deployments would split one operator's queue.

A hosted service that runs other operators' repos stays refused. It adds a
boundary between operators that §2 does not draw.

## Options considered

- **A package installed into each target repo.** Each repo pins its own
  version and holds narrow credentials. One operator's queue splits across
  repos, and nothing arbitrates their shared credential. A Python dependency
  cannot enter a Rust repo either, which breaks N8.
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
- **12** upholds. The boundary is `.saffron/` and the gate contract. No
  deployment adapter is built before a second host needs it.
- **14** departs. Another operator's repo widens the claim that §2.1 holds,
  and no test measures it yet. Item b-a9ec4b states the pass condition. A
  second operator onboards a repo with an empty diff to `saffron/`.
- **23** upholds. Two §1.4 refusals change, and each change is written beside
  the refusal it narrows.
- **25** upholds. Engine and deployment enter `CONTEXT.md` with this ADR.
- **30** upholds. §1.3, N6, the §2 diagram, §9's v3 and §11's runtime row
  each say where this ADR changes them.
- **31** departs. A Linux host shares its kernel with podman cells. There
  `thread_env` is the only CPU control, and nothing requires a repo to
  declare it. Item
  b-0569f7 makes a shared-kernel deployment refuse such a policy.
- **32** upholds. The host contract is the decision, and GCP is one instance
  of it.
- **33** departs. No night has run on a Linux host VM, and §5.1 states the
  podman safety argument as weaker. The isolation stays a hypothesis until
  item b-da550a measures it.
- **62** upholds. The cloud-runner refusal gave throughput as its reason. The
  laptop binding is a different reason, outside the one the refusal named.

## Consequences

- §1.4 narrows its multi-tenant refusal and withdraws its cloud-runner
  refusal. `CONTEXT.md` defines the engine and the deployment, and the
  operator as singular per deployment.
- The engine ships as an image built from `main` and pinned by digest. Each
  task records the engine commit that judged it (item b-2e0b97).
- `.saffron/` becomes an interface that other operators write against. Its
  formats declare a schema version, and the engine refuses a field it parses
  and never reads (item b-0569f7).
- Saffron becomes a target repo like any other. Its nights run on a released
  engine, and a merge reaches the engine only through a release.
- The Linux host is a module the operator applies in their own GCP project.
  This repo's nights move onto it first (item b-da550a).
- Onboarding and spec writing ship as a Claude Code plugin. An operator then
  writes `.saffron/` without this checkout (item b-a9ec4b).
- Items 170, 108 and b-ca3bc6 come before the Linux host. The record on
  `refs/saffron/*` lets a host VM be discarded. Podman must run a night, and
  two concurrent cells must not share a network.
