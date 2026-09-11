# What a cloud session can and cannot give a cell

Taken 2026-09-11, in a Claude Code remote session on Ubuntu 24.04 (kernel
6.18.44, x86_64, 4 CPUs, root). The question was whether Saffron could run its
own development through its own workflow somewhere other than the operator's
Mac, and the honest answer turned out to be two answers: the cell runtime is
replaceable, and this particular environment still cannot start a cell.

Appendix G's spike is the artifact that decides a runtime, and it takes
`[container|docker|auto]`. Nothing here extends it — these are its four
assertions run by hand against a fourth candidate, so that a later spike arm has
something to reproduce or contradict.

## The host

| | |
|---|---|
| `container` | absent — `apple/container` is macOS on Apple silicon |
| `docker` | client 29.3.1 present, **no daemon**: `/var/run/docker.sock` does not exist |
| `podman` | absent, **installs from apt** (4.9.3) — daemonless, so there is no socket to lack |
| user namespaces | `unshare -Ur` and `unshare -Urn` both succeed; `max_user_namespaces` 64230 |
| `/dev/kvm` | absent — no VM per cell is available at any price |
| `/sys/fs/cgroup` | **tmpfs, no `cgroup.controllers`** |

Architecture A of Appendix G — a shared VM behind a Docker socket — is not
available here, and not because it was rejected. There is no daemon and no way
to start one. Podman is a third shape the appendix did not consider: the CLI
shell-out and structured `inspect` that made `apple/container` cheap to drive,
with no VM under it.

## The four assertions

Run against a 2.27 MB image built locally with `podman import` over a
`busybox-static` rootfs, because no image could be pulled (below).

**1. The cell sees only the CPUs it has.** This is the one that moves.

```
host nproc = 4
--cpus 1        -> nproc 4      the whole machine
--cpus 2        -> nproc 4      the whole machine
--cpuset-cpus 0-1 -> nproc 2
```

§5.1 wrote the requirement rather than the flag, and the requirement is what
decides here: `--cpus` is a CFS quota and leaves the visible count untouched,
which is the oversubscription mode §5.1 names. `--cpuset-cpus` satisfies it.
So a podman arm carries offset 0 and a different flag, not a recalibrated
`CPU_OFFSET`.

**This reopens a struck requirement.** Appendix G struck rev 7's P-core pinning
because "on macOS that kernel is always inside a VM, so the mask indexes
*virtual* CPUs". Principle 31 says a resource control means whatever the kernel
reading it can see — and here that kernel is a real Linux kernel, so the mask
indexes real cores. The control rev 7 wanted exists on this host. Whether it is
worth having is a separate question from whether it is reachable; it is now
reachable.

**2. Egress to an unlisted host fails.** Holds, and not vacuously — the first
draft of this record said it was vacuous and that was the broken instrument
talking (see below). Re-measured with `wget`: from a cell, `1.1.1.1` is
unreachable, while `api.anthropic.com` returns an HTTP response. Something
answers, so the path exists and is being filtered rather than severed.

**3. The proxy is reachable by IP.** Still unproven, but not for the reason
first recorded. The stand-in listener was fine; the *probe* was broken.

### The instrument was wrong, and it answered uniformly

`busybox nc -z` returns 1 against a listener that is demonstrably up — measured
against a local `http.server` that `wget` fetched from the same shell, in the
same container, a line apart:

```
nc -z  127.0.0.1:5599   rc=1      # a listener that is there
wget   127.0.0.1:5599   rc=0      # the same listener, same container
```

A broken probe does not report noise. It reports the same answer every time, and
a uniform answer reads like a finding — "nothing is reachable" looked exactly
like strong isolation. Every `nc`-based line in the first draft of this record
is withdrawn; every `wget`-based one stands, which is why assertions 1 and 4 are
unaffected. Principle 34 is usually read as *a probe that never ran is `error`*;
this is its other half, and the more dangerous one: **a probe that cannot
succeed reports `pass` for a negative assertion.** Both isolation assertions here
are negative.

**4. A host service is not reachable from inside a cell.** The hazard
reproduces exactly as Appendix G describes it:

```
network gateway 10.99.0.1
host listener 0.0.0.0:5434, from inside an --internal cell   -> reachable
host listener 127.0.0.1:5433, from inside an --internal cell -> refused
```

An `--internal` network still routes to the host gateway. `preflight.py`'s lsof
enumeration is as necessary under podman as under `apple/container`, and `lsof`
is present here, so it works unchanged.

## What else the runtime seam would have to absorb

Everything below worked and is named so a port has a list rather than a memory.

- `--internal` network with a pinned subnet: yes. `10.88.0.0/24` was refused as
  already in use on this host, so `DEFAULT_SUBNET` is not portable — the
  collision handling `create_network` already has is the right shape, and the
  default is not.
- Named volume mounted at `/work`, written from inside: yes.
- `exec` with a working directory: yes, spelled `-w`, not `--cwd`.
- `--cap-drop ALL`: yes.
- `inspect` for the cell's own address: yes, and `_first_address`'s regex over
  the JSON works unchanged — it found `10.99.0.7` and skipped the `.1` gateway.
- `--memory`: accepted without error. **Enforcement unverified**, and with no
  cgroup controllers mounted it should be assumed absent. A ceiling that is not
  enforced has to report as absent rather than as set (§4.3).

## What stops a cell starting here anyway

**No image can be pulled.** Every registry tried is refused by the session's
egress policy, at the blob CDN rather than at the manifest:

```
docker.io       403  production.cloudfront.docker.com
quay.io         403  quay.io/v2/
public.ecr.aws  403  d2glxqk2uabbnd.cloudfront.net
ghcr.io         403  pkg-containers.githubusercontent.com
```

Alpine's package CDN is refused too (`dl-cdn.alpinelinux.org`). This is an
egress policy, not a defect, and the proxy's own documentation says to report a
blocked host rather than route around it.

### Correction — a pull is not the only way to get an image

The first version of this record concluded from the above that "a working
runtime here has nothing to run". **That was wrong, and it was wrong in the way
this repository names most often: a measurement of one thing reported as a
conclusion about another.** Every pull is refused; no measurement had been taken
of whether an image could be *built*. Taken the same day:

```
archive.ubuntu.com                      200
debootstrap --variant=minbase noble     ok, 135 MB rootfs, no registry
podman import                           ok
apt (universe added)  python3 3.12.3, git 2.43.0, squid 6.6
pip   claude-agent-sdk 0.2.142
      bundled binary  .../claude_agent_sdk/_bundled/claude
      and it runs     2.1.237 (Claude Code)
```

The last line is the one that matters, and it is asserted rather than located
for the reason `images/cell-base.python.Dockerfile` already gives: a present and
unrunnable binary reads identically to a working one (principle 39). The wheel's
bundled Claude Code binary — the whole reason that image is Debian rather than
Alpine — is present and executes on a base built here from nothing but the
Ubuntu archive and pypi.

So the real blocker is narrower and still real: **all three images are written
against registries, and none of the substance needs one.**

| Image | Registry dependency | Reachable substitute |
|---|---|---|
| `images/cell-base.python.Dockerfile` | `FROM python:3.12-slim-bookworm` | debootstrap + apt python3 (3.12.3) |
| `images/proxy.Dockerfile` | `FROM alpine:3`, apk | apt squid (6.6) on the same base |
| `.saffron/Dockerfile` | `COPY --from=ghcr.io/astral-sh/uv:latest` | uv from pypi |

**What that costs is worth stating before anyone reaches for it.** The cell image
is the toolchain (§5.1), and a repo whose image is assembled differently
depending on which host built it has given up the property that makes a gate
result comparable between hosts. A locally-built base is a way to *run* here; it
is not the same image the operator's Mac builds, and two hosts disagreeing about
the toolchain is the kind of difference that surfaces as a flaky gate rather
than as an error. Pinning that — one base image, built once, carried between
hosts by some means that is not a public registry — is the actual question, and
this record does not answer it.

### The cell cannot reach the API, and the reason is structural

This is the deepest of them and it is not a missing package. Measured from a
cell on an `--internal` network, with `wget`:

```
cell -> 1.1.1.1                    unreachable
cell -> api.anthropic.com          HTTP 403        (something answers, and refuses)
cell -> <gateway>:<agent proxy>    connection refused
host -> api.anthropic.com:443      OK
host -> 127.0.0.1:<agent proxy>    OK
```

The host has egress. The cell does not, because this environment's egress runs
through an agent proxy bound to the host's **loopback**, and assertion 4 already
established that loopback is the one host address a cell cannot reach. So
Saffron's squid would need that proxy as a `cache_peer` parent, and cannot see
it.

**Putting it within reach means a host listener on a non-loopback address —
which is precisely what `preflight.py` refuses.** N1's host probe exists to
enumerate exactly that and fail the run. The two requirements are in direct
opposition: the environment says *the only way out is a loopback proxy*, and
Saffron says *a cell must not be able to reach a host service*. Nothing about a
cell runtime resolves it.

The repository already has the shape of an answer and is honest about what it
is: `SAFFRON_ALLOW_HOST_PROCESS` tolerates a named host process per invocation,
"an accepted risk, not a fix, and reported on every run so it cannot go quiet"
(Appendix G). A relay bound to the cell network's gateway, named in that
variable, is a cell that can reach exactly one host port. That is a weaker N1,
and it is the kind of weakening that has to be written into §5.1 rather than
configured around.

Two others, neither about the runtime: `CLAUDE_CODE_OAUTH_TOKEN` is absent; and
the session container is reclaimed on idle, which takes `~/.saffron/ledger.db`
and the batch tree with it. The second is survivable for one attended task whose
output is a pull request and fatal for a night, whose whole product is the audit
trail. `gh` is *not* on this list: it installs from apt (2.45.0), and only needs
a credential.

## The boundary this would trade away

Appendix G took `apple/container` on four grounds and called the per-cell VM
"the single largest point in its favour". Podman keeps three of them — honest
CPU count, internal networks, `--cap-drop ALL` — and gives up that one. It is a
shared kernel.

That is not a detail to absorb quietly. §5.1 declines `no-new-privileges` and
seccomp *because* the VM is offered as the boundary instead; with no VM, that
sentence has no subject and both must come back on. A second runtime is a second
safety argument, weaker and worth stating, not a port of the first.

## What this record does not establish

That podman can run a Saffron cell. Nothing here started the agent runtime, the
proxy, or a gate — only the mechanics underneath them, and the base image's
ingredients separately. Assertions 2 and 3 are unproven. The spike is still what
would decide it, and it now needs an arm rather than a reachable registry.

Nor does it establish that a locally-built base is a *good* idea — only that the
"nothing to run" conclusion it replaces was not measured. The reproducibility
cost above is real and unpriced.
