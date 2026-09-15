---
id: 108
title: A second cell runtime, and the four things a cloud host still lacks
status: partial
tier: 3
specs: []
prs: []
commits: []
cites: [§4.2, §4.3, §5.1, §5.1.2, §5.4, §7]
related: [107]
---

## Problem

The images half has landed — `BASE_IMAGE` on both images,
`images/bootstrap-base.sh`, and a provenance file each (§5.1.2) — **without**
answering the question 1. below says to answer first: the provenance file makes
a difference between hosts legible and does not remove it, and one base carried
between hosts is still open. The egress half needed nothing (3. below). The
ledger column below is not started. Until a cell has started on podman end to end,
`saffron batch` refuses it, and a rootful podman is refused outright: no image
sets a `USER`, so a rootful cell is root on the host kernel (§5.1). What still
stands between podman and a first cell, none of it measured beyond the first:

- **`DEFAULT_SUBNET`** was refused as in use on the measured host.
- **`networks_on_subnet`** reads a subnet from the listing's second column, and
  `podman network ls` does not print one; the `overlap` match is
  `apple/container`'s wording.
- **Rootless** is now required, and whether rootless podman can apply
  `--cpuset-cpus` without a delegated cpuset controller is unasked.

**Tier 3.** Measured 2026-09-11 in
`docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md`, from a Linux
cloud session. Depends on **107** — there is nowhere to put a second backend
until the seam is split.

Appendix G's fallback was Architecture A, a shared VM behind a Docker socket. On
a container-hosted Linux runner that option is not available and not rejected:
there is a `docker` client, no daemon, and no way to start one. **podman** is a
third shape the appendix did not weigh — daemonless, so there is no socket to
lack, driven by CLI shell-out and structured `inspect`, which is the interaction
the seam is already written for.

What the four assertions returned, and it is not a clean sweep:

- **CPU visibility inverts the flag.** `--cpus` is a CFS quota and leaves
  `nproc` reporting the whole machine — §5.1's oversubscription mode.
  `--cpuset-cpus` satisfies the requirement. A podman arm carries offset 0 and a
  different flag, not a recalibrated `CPU_OFFSET`.
- **A struck requirement becomes reachable.** Appendix G struck rev 7's P-core
  pinning because on macOS the mask indexes virtual CPUs. Principle 31 says a
  control means what the kernel reading it can see, and here that is a real
  Linux kernel indexing real cores. Reachable is not the same as worth having;
  it is no longer impossible.
- **The host-gateway hazard reproduces.** A host service on `0.0.0.0` is
  reachable from inside an `--internal` cell; one on `127.0.0.1` is not.
  `preflight.py`'s lsof enumeration is as necessary here as on macOS and works
  unchanged.
- **One assertion returned nothing, and the probe that said so was broken.**
  `busybox nc -z` returns 1 against a listener `wget` fetches from a line
  earlier, so it reported "unreachable" uniformly and that read as isolation.
  Re-measured: egress-to-an-unlisted-host holds properly. Proxy-reachable-by-IP
  is still unproven and needs the real proxy image. **Principle 34's other
  half**: a probe that cannot succeed reports `pass` for a *negative*
  assertion, and both isolation assertions are negative.

**The boundary this trades away, and it is the one Appendix G bought.** Podman
keeps the honest CPU count, the internal network and `--cap-drop ALL`, and gives
up the VM per cell. §5.1 declines `no-new-privileges` and seccomp *because* the
VM is offered instead; with no VM that sentence has no subject and both come
back on. A second runtime is a second safety argument — weaker, and stated as
such in `DESIGN.md` rather than absorbed into the first.

**Also for the seam, found by the same probe:** `DEFAULT_SUBNET` is not
portable. `10.88.0.0/24` was refused as already in use on that host. The
collision handling `create_network` already carries is the right shape; the
constant is not.

**And a ledger column.** Which runtime ran a task is exactly the fact that later
explains a variance nobody can otherwise account for, the same argument that
makes a gate result carry the tool version it actually ran (§5.4). It is also
what would earn the cell runtime an entry in `ontology/factory.ttl`, which today
has none and correctly so (**107**).

**What blocks it there regardless of runtime**, all four measured the same day:

1. **No image can be *pulled*, and all three are written against registries.**
   `docker.io`, `quay.io`, `public.ecr.aws` and `ghcr.io` are all refused with
   403 at the blob CDN, and Alpine's package CDN with them. An egress policy,
   not a defect.
   **Every ingredient is reachable without a registry, and that was measured
   after an earlier draft of this item claimed otherwise**: `debootstrap`
   against `archive.ubuntu.com` builds a base, apt supplies python3 3.12.3, git
   and squid 6.6, pypi supplies `claude-agent-sdk` and uv, and the wheel's
   bundled Claude Code binary is present *and runs* (2.1.237) — asserted rather
   than located, principle 39. So the work is rebasing
   `images/cell-base.python.Dockerfile`, `images/proxy.Dockerfile` and
   `.saffron/Dockerfile` off their `FROM`s, not waiting for an egress change.
   **Price the reproducibility first.** The cell image is the toolchain (§5.1),
   and an image assembled differently per host gives up the property that makes
   a gate result comparable between hosts — a difference that surfaces as a
   flaky gate rather than as an error (§7). One base built once and carried
   between hosts by something that is not a public registry is the question to
   answer before the Dockerfiles move.
2. **No cgroup controllers.** `/sys/fs/cgroup` is a tmpfs with no
   `cgroup.controllers`, so `--memory` is accepted and unenforced. §4.3's
   ceiling would be a claim. A ceiling that is not enforced has to report as
   absent rather than as set, which is its own change.
3. ~~**The cell cannot reach the API.**~~ **Withdrawn 2026-09-12 — there was no
   such blocker.** It was measured with `busybox nc -z` and `busybox wget`, the
   instrument this same item records as broken, and the conclusion was carried
   forward after the instrument was discredited rather than re-taken with it.
   Re-measured end to end: a container on a normal network reaches
   `api.anthropic.com` directly; a container on an `--internal` network reaches
   nothing; and a dual-homed squid between them tunnels the one allowed host
   (`TCP_TUNNEL/200`, a real `405` from the API) while refusing every other
   (`TCP_DENIED/403`). **§5.1's egress architecture works here unmodified.**
   The weaker N1 approved on the strength of the original report is withdrawn
   with it: no relay, no `cache_peer`, no host process to tolerate, and
   `preflight.py` unchanged. A control must not be relaxed on a measurement
   nobody re-took.
4. **The host is reclaimed on idle**, taking `~/.saffron/ledger.db` and the
   batch tree with it. Survivable for one attended task whose product is a pull
   request; fatal for a night, whose product *is* the audit trail.
5. **`CLAUDE_CODE_OAUTH_TOKEN` is absent.** `gh` is no longer on this list: it
   installs from apt (2.45.0) and only wants a credential.

## Done looks like

a podman backend behind **107**'s protocol, its paired
structure rule and mutant, the spike grown a fourth arm so the assertions are
reproducible rather than recorded, and `DESIGN.md` carrying the second safety
argument. **Not** done by that alone: a cloud host still cannot start a cell
until the images question below is answered too, and that is the larger half.

## Record

**Status:** the **runtime half is done**, by hand, 2026-09-11 —
`saffron/cell/runtimes/podman.py` behind **107**'s `Dialect`, its own copy of the
structure rule with the mutant that proves it fires, the spike grown a `podman`
arm, and §5.1 carrying the second safety argument. Three findings from doing it:

- **The spike's own instrument needed a check first.** Every negative assertion
  is read through `nc`, and a `nc` that cannot connect reports what a refusing
  network reports. The spike now proves the probe can succeed before trusting it
  to fail, and refuses to report isolation otherwise.
- **`--cpuset-cpus` meets §5.1's CPU requirement only halfway.** The mask reaches
  `sched_getaffinity`, so `nproc` is honest; `os.cpu_count()` and
  `/proc/cpuinfo` still report the host's count. So `policy.thread_env` is belt
  and braces under a VM and *the* control under a shared kernel — a repo
  onboarded there declaring none has an uncapped thread pool.
- **Every cell would get the same mask.** `cpu_flags` is handed a count, not a
  placement, so K concurrent cells contend for cores `0..n-1` rather than being
  spread. §4.2's question, unanswered, and the reason this runtime is for one
  attended task before it is for a night. **That is what is left of this half.**
