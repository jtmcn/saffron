---
id: b-da550a
title: No deployment runs a night anywhere but the operator's laptop
status: open
tier: 2
filed: 2026-10-06
by_hand: true
specs: []
prs: []
commits: []
cites: [§1.4, §4.1, §5.1]
related: [b-2e0b97, 170, 108, b-ca3bc6]
---

## Problem

ADR 10 names a VM in the operator's own GCP project as the second supported
deployment. None exists. Nights run under launchd on a laptop
(`docs/host/dev.saffron.batch.plist`). A night stops when the laptop sleeps.

Item 108 lists what a Linux cloud host lacked when measured. Four of those
gaps have a GCP answer, and nobody measured any of them yet.

- Images built once and carried between hosts. Artifact Registry, pulled by
  digest (item b-2e0b97).
- Enforced memory ceilings. A GCE VM has a real kernel with cgroup controllers.
- A host reclaimed on idle. The record on `refs/saffron/*` lets the VM be
  discarded (item 170).
- The token. Secret Manager, read into the `saffron batch` invocation alone.

Podman shares the host kernel, so §5.1 states its safety argument as weaker.
Item 108 records that podman gives up the VM per cell. A spike on this host
decides whether gVisor or a VM per cell gets it back.

## Done looks like

A Terraform module creates the VM in an operator's project. It installs
rootless podman, reads the token from Secret Manager, pulls the engine by
digest, and starts `saffron batch` on a timer.

This repo's own nights run there first. `docs/HOST-HARDENING.md` gains a
section for the GCP host, and a night's record survives the VM being deleted
and recreated.
