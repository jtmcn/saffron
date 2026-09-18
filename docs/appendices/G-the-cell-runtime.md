---
id: G
title: "rev 8: the cell runtime"
revisions: [8, 10]
question: "The cell runtime. \"Docker\" was never a decision — rev 8 names the candidates, rev 10 chooses by spike"
---

Every previous revision wrote **Docker** as though it were a decision. It was never made. §5.1's cell is described entirely in Docker's flag vocabulary, §4.2's concurrency arithmetic closes against a Docker Desktop VM allocation, and §7 has a row whose countermeasure is a Docker flag — while the actual intent was Colima, a different program that was never named anywhere. So the runtime was a proper noun standing in for a contract, which is the one mistake §2.1 exists to catch, committed in the section §2.1 does not cover.

Rev 8 names the candidates, finds the defect that naming them surfaced, and then **declines to choose**, because the choice binds at v0.5 and not before.

### Two architectures, three products

The first draft of this appendix listed three candidates and dismissed Docker Desktop on a licence and a menu bar. Both objections are wrong at this scale — Docker Desktop is free under Docker Personal for an individual, and `docker desktop start|stop|status` has been a CLI since 4.37, so it drives from `launchd` like anything else. Withdrawn. What matters is that **the choice is binary, and it is not a choice between three products:**

**A. Shared VM, Docker API — Docker Desktop *or* Colima.** One Linux VM on Apple's Virtualization.framework, one kernel, dockerd inside it, all cells sharing it, a Docker socket on the host. These two are *the same architecture*, and every line of §5.1 behaves identically on either — including the `cpuset` finding below, which is a property of the shared VM and not of the product managing it. They differ only in operator ergonomics: Colima idles at ~400MB against Docker Desktop's 2GB+ and is MIT-licensed with no account at all; Docker Desktop is the far more heavily exercised path, which is the argument that actually counts for an unattended eight-hour run, and Colima's occasional need for a restart is exactly the failure a 03:00 batch cannot absorb. Docker Desktop is also the only option anywhere on this page offering **user-namespace hardening** — Enhanced Container Isolation, container root mapped to an unprivileged host UID via Sysbox, holding even against `--privileged`. That is squarely aimed at §2's untrusted cell, and it is **Business-tier only** (~$24/user/month), which makes it a real option to price rather than a feature to assume.

**B. VM per cell — `apple/container`.** Apple's own runtime, **1.0.0 as of June 2026**, CLI and XPC API frozen across 1.0.x. A separate lightweight VM per container. No Docker socket: the supervisor shells out to a CLI that emits structured JSON.

**Nothing in this document distinguishes A-with-Docker-Desktop from A-with-Colima.** That is the useful result: pick between them on ops taste at v0.5, switch later for the price of a `DOCKER_HOST`, and record neither in the design. The decision that has design consequences is A versus B.

### What naming them found

**§5.1's rev-7 P-core fix does not work, on any of them.** Rev 7 caught that `--cpuset-cpus 4,5` indexes a hybrid core list and told preflight to enumerate the performance cores and pin to those. That is correct on Linux and meaningless on macOS: `cpuset` is interpreted by the kernel that reads it, and on macOS that kernel is always inside a VM, so the mask indexes **virtual** CPUs. Which physical core a vCPU thread lands on is macOS's scheduling decision and no flag reaches it. Under `apple/container` there is no pinning flag at all. So rev 7 fixed a real hazard with a control that does not exist on the machine Saffron runs on — and it read as fixed for one revision because nothing had been run.

The hazard is unchanged and now belongs to detection: vCPU threads are scheduled onto P-cores first and spill to E-cores under contention, so a cell can run its gates measurably slower than its siblings, and §7's countermeasure is now per-gate wall clock plus cross-cell variance rather than a flag.

**What survives is the requirement underneath it.** The reason §5.1 rejected `--cpus` was never affinity — it was that a CFS quota leaves the *visible* core count untouched, so thread pools size themselves from the host's core count and oversubscribe. Both candidates satisfy the real requirement, by different mechanisms: `cpuset` restricts the affinity mask the guest reports, and a per-cell VM configured with N vCPUs simply *has* N CPUs, so `nproc` is honest with no flag at all. The second is the stronger form — it is structural rather than declared — and it is the single largest point in `apple/container`'s favour.

### The comparison that actually matters

| | **A.** Shared VM (Docker Desktop *or* Colima) | **B.** VM per cell (`apple/container`) |
|---|---|---|
| Isolation | Shared kernel, one VM | **VM per cell** — a stronger structural boundary for §2's untrusted cell |
| Cell sees only its CPUs | Yes, via `cpuset` | Yes, structurally — the VM has that many vCPUs |
| Pin physical P-cores | **No** (indexes vCPUs) | **No** (no such flag) |
| Memory ceiling | One shared VM allocation to divide by K | No shared allocation; cells draw against the machine |
| Fast worktree storage | virtiofs mounts, or a volume | Named volumes: sparse ext4 over virtioblk, documented as faster than bind mounts |
| Isolated network | Docker `--internal` | `container network create --internal` |
| `--cap-drop ALL` | Yes | Yes (default set is already restricted) |
| `no-new-privileges`, seccomp, userns | Yes | **Not exposed** — the VM is offered as the boundary instead |
| Host integration | Docker socket; ordinary Python client | CLI shell-out, structured JSON `inspect`/`ls`; `exec` exists |
| Maturity | Years of use; Docker Desktop the most-exercised path on macOS | 1.0.0 in June 2026, API frozen for 1.0.x |
| User-namespace hardening | Docker Desktop only, **Business tier** (ECI/Sysbox) | No — the VM is offered instead |
| Idle overhead | ~400MB (Colima) to 2GB+ (Docker Desktop) | Per-cell VMs; nothing standing between batches |

Two operational facts that apply to **both**, and neither is in §5.1 today:

- **An `--internal` network still routes to the host gateway.** A host service bound to `0.0.0.0` — your Postgres — is reachable from inside a cell without ever traversing the proxy. N1 is the requirement this threatens, and the countermeasure is on the host: bind services to `127.0.0.1`, and prove it with a preflight probe rather than assume it. The `--internal` flag is not the whole boundary it reads as.
- **Isolated networks have no DNS.** `HTTPS_PROXY=http://saffron-proxy:3128` does not resolve. Pin the subnet at network creation and address the proxy by IP.

Missing `no-new-privileges` and seccomp is a real deviation, but it is the deviation §2 already argues for: a private kernel per cell is a *better* structural boundary than a shared one plus in-guest hardening, and §2's whole claim is that the controls that hold are the structural ones.

### The decision, and when it gets made

*(Superseded by "The decision, made" below. Kept because the spike it specifies is
the artifact that settled this, and because a prediction is only worth something
if it stays legible next to its result.)*

Deferred to **v0.5**, which is the first version where a cell exists at all — v0 is agent-free and touches no container. This is §9's rule about second implementations applied to a runtime: the *seam* gets written now because it is cheap, and it is one file. `saffron/cell/runtime.py` is the only module that knows which runtime, and the surface it hides is small enough to write down here: create a volume, run a container with a network, env, and CPU/memory limits, exec into it, collect artifacts, destroy it. Nothing above that file changes if the answer changes.

The spike that decides it is half an hour, and it is four assertions against a real cell on an internal network:

1. `nproc` inside the cell equals the CPUs it was allocated.
2. Egress to an unlisted host fails.
3. The proxy is reachable, by IP.
4. A Postgres on the host is **not** reachable.

Run it against `apple/container` first. If all four hold, take it — the isolation is better, the memory ceiling is better, and §5.1 gets shorter. Architecture A is the fallback and it is a good one: the Docker socket makes the supervisor duller to write, and dull is worth something at 03:00. If it wins, start on Docker Desktop rather than Colima — an unattended nightly batch weights *fewest surprises* over 1.6GB of idle RAM, and that ordering can be revisited the first night the idle footprint actually costs a cell.

Three principles, and the first is the one that generalizes:

31. **A resource control means whatever the kernel reading it can see.** `cpuset` pins host cores on Linux and virtual cores in a VM — same flag, same syntax, silently different guarantee. Every limit, mask, and quota needs verifying against the layer that actually enforces it, not the layer whose documentation you read.
32. **A product name in a design is an unmade decision wearing a decision's clothes.** "Docker" appeared in six sections and was never chosen; it survived four revisions and an adversarial review because a proper noun reads as settled. §2.1 catches this for languages and toolchains and did not catch it one layer down, for the runtime the whole cell is built on.
33. **A countermeasure written against an environment you have not run on is a hypothesis.** Rev 7's P-core enumeration was reasoned correctly from a false premise about where `cpuset` applies, and recorded as a fix. This is the third time an appendix has argued that the next artifact should be executable (§9); it is now also the reason.

---

