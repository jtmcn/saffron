---
id: H
title: "rev 9: what v0 found"
revisions: [9]
question: "What v0 found, being the first revision that ran: three merged pull requests replayed agent-free"
---

Every previous revision was a document reading a document. Appendices F and G each
ended by arguing the next artifact should be executable; §9 made it a rule. v0 is
the first revision that ran — three merged `thermal-edge` pull requests replayed
through the agent-free harness (#172, #169, #165, as `TE-9001`–`TE-9003`) — and it
is worth recording what that bought and what it did not.

**The criterion was met, and by the intended mechanism.** `TE-9001`'s rendered PR
body states that the settled-high defect understated 7 of 108 stored days, that two
of the seven are invisible to the obvious METAR proxy check, and why — none of
which is derivable from reading the diff, because it came from an audit against
external settlement data. That is the artifact doing the job §0 claims for it.

**The mechanism v0 existed to test held.** `(gate, file, code, normalized message)`
with `line` excluded survived three real diffs, one of them +1905/−49. Two files
already carrying `format` debt at base, still failing at head, correctly stayed off
the new-failure table. That is §5.4's rev-7 fix confirmed against real tool output
rather than reasoned about.

### The headline finding: a green gate suite that never ran

The first replay of `TE-9001` reported `format` and `lint` as `pass` in 0.3s each,
with `types` clean — against a repository carrying 402 files needing reformatting
and 57 type errors. Saffron's own process environment had leaked into the gates it
shells out to, so every gate resolved a different Python environment than the one it
was written for, and the shell scripts swallowed the resulting failures into an
empty `failures[]`.

The defect worth recording is not the leak. It is that **nothing in the gate
contract could express the difference.** `{"status":"pass","failures":[]}` is
bit-for-bit identical whether the tool ran and found nothing or never ran at all,
and `duration_ms` is no help — genuine `ruff` against that whole repository also
finishes in 0.3s. It was caught only because someone remembered a baseline figure
from a week earlier and noticed 0 was not 396. An incidental catch, unattended, at
03:00, is not a catch.

Hence §5.4's `tool` field, obtained by executing the tool, and the two `error` rules
beside it. Three of the four defects below collapse into one shape once stated that
way, which is the argument for fixing it at the contract rather than in four gates.

### The other three

- **`tests` cannot say a worker crashed.** A lost `pytest-xdist` worker puts the
  test's own name in `code`, exactly like a real assertion failure. A repair loop
  consuming that JSON cannot tell "your change broke this" from "the runner lost a
  process, re-run it" without pattern-matching free text. Resolved by rule rather
  than by schema: partial results are not results, and the gate returns `error`
  (§5.4).
- **`format`'s parser is coupled to an unversioned CLI string.** A `ruff` release
  rewording one line makes every match vanish and the gate reports a false `pass` —
  the same failure shape as the environment leak, from a different cause. Covered by
  the same two guards.
- **`scope` has one severity for every kind of escape.** A new file the acceptance
  criteria required and three unrelated docs files rendered identically. Recorded as
  a thing to watch rather than fixed; §11 says why.

### And two the replays did not find

Both were found by review afterwards, and both are the more interesting half of this
appendix, because they are the shapes three green runs happened not to contain:

- **Baseline subtraction was a set difference.** `normalize_message` collapses digit
  runs — correctly, since messages embed the coordinate the identity exists to
  exclude — which means two failures of one rule in one file differing only in their
  numbers share an identity legitimately. Under set semantics one pre-existing
  failure then cancelled *every* head failure sharing it. The subtraction is now a
  multiset operation (§5.4), and so is no-progress detection, for the same reason.
- **`M^1` is not the branch point.** Resolving a merge commit's base as its first
  parent takes `main` as of the merge, so where `main` advanced while the pull
  request was open, commits the task never touched entered both the diff and the
  baseline. The base is the merge base of the two parents.

Three principles, and the first is the general one:

34. **A green result and an absent result are the same bytes.** Any contract that
    reports outcomes must carry evidence that the thing which produces outcomes ran.
    Absence renders as success in every schema that does not ask, and the failure is
    silent by construction — which makes it exactly the kind that survives an
    unattended night.
35. **When identities can legitimately collide, subtraction has to count.** A
    normalization that erases a distinguishing field is usually right and always
    turns set difference into cancellation. If two rows can be the same key on
    purpose, the operation over them is arithmetic, not membership.
36. **Partial results are not results.** A mechanism that broke half way through
    produces output shaped exactly like output. Give the producer the vocabulary to
    disown its own run, and prefer one re-run charged to nobody over a consumer
    reasoning about a truncated set.

**The method note, since three appendices in a row now predict it.** Rev 7 found
nine defects by reading and said the next artifact should be executable. Rev 8 found
that rev 7's central fix was not implementable on this machine and said it again,
this time as principle 33. Rev 9 is the first one that ran, and the defect it found
first — a whole gate suite reporting green while doing nothing — is not visible to
any amount of rereading, because the document was never wrong about it. It simply
never asked. **The next artifact should be v0.5**, and the four-assertion runtime
spike is what it starts with.

### The decision, made

Run ahead of v0.5, as `spikes/cell-runtime.sh`, on 2026-08-19 against
`apple/container` **1.2.2** (not the 1.0.0 this appendix was written against; the
frozen-API-across-1.0.x claim no longer covers what installs today). All four
assertions hold:

```
1. the cell sees only the CPUs it has     nproc = 3 for --cpus 2, host has 11
2. egress to an unlisted host fails       example.com unreachable
3. the proxy is reachable, by IP          10.88.0.3:3128 reachable
4. host services are not reachable        127.0.0.1-bound unreachable, gateway and LAN
```

**Take it.** Every flag §5.1 needs exists — `--internal`, `--subnet`, `--cpus`,
`--memory`, `--cap-drop`, `--network`, `--mount`, `--rm` — and the two that do not
(`no-new-privileges`, seccomp) are the deviation this appendix already argued for.
§5.1 is rewritten in the runtime's own vocabulary and is shorter for it.

Three things the run found that reading could not:

- **`--cpus n` allocates n+1 vCPUs, deterministically** — 1→2, 2→3, 4→5, 6→7. The
  count is honest about the VM the cell is in, which is the property that matters;
  the VM just gets one more than requested. A calibration constant, not a defect,
  and §5.1 now carries it as one.
- **Both no-DNS predictions were right.** The proxy answers on its IP and its name
  does not resolve on an internal network. `HTTPS_PROXY` by hostname would have
  failed at v0.5 with a DNS error nobody would have connected to this page.
- **The `0.0.0.0` hazard is real on two paths, not one.** A host service bound to
  the wildcard address is reachable from inside a cell at the gateway *and* at the
  machine's LAN address, never touching the proxy. The `127.0.0.1`-bound one is
  unreachable from both. N1 rests on a binding choice, and the preflight probe that
  checks it is not optional.
- **What that probe covers is enumerated, not remembered** (added 2026-08-20). It
  first shipped against seven ports somebody thought of, so its clean result meant
  "no host service answered on seven ports" while the docstring and this page both
  said "no host service is reachable" — and the v0.5 run that caught a service on
  8000 had four more on 8001+ that no such list would have named. `lsof -nP -iTCP
  -sTCP:LISTEN` now supplies the ports, every listener not bound to loopback, and
  enumeration that cannot run raises rather than quietly narrowing the probe to
  nothing — the `_lan_address` defect, one function over. An empty result is still
  a real pass; it now means what it says. Measured on the machine v0.5 ran on: four
  macOS services (ARD 3283, Control Centre 5000 and 7000, rapportd 49152) are
  wildcard-bound and answer from inside a cell, and none is in the old seven.

### One tolerated listener, and what it costs (2026-08-21)

**This is an accepted risk, not a fix.** The operator turned Handoff off, which
closed two of `rapportd`'s three sockets; `*:49152` stays up regardless, and
AirDrop going back on will reopen the others. So the probe correctly refuses to
start a cell, permanently, for a daemon the operator has decided to keep.

**Tolerated:** the process `rapportd`, by the COMMAND `lsof` reports —
`SAFFRON_ALLOW_HOST_PROCESS=rapportd saffron cell …`.

**Why it is judged acceptable:** it is Apple's own Continuity daemon doing
link-local discovery for Handoff, Universal Clipboard, Sidecar and AirDrop. It
is not a general-purpose service surface, it holds no repo data, and it is not
something a cell can be given credentials to.

**What it costs, plainly:** an agent inside a cell can open a TCP connection to
that socket, at the gateway and at the LAN address, without traversing the
proxy. N1 is *not* satisfied on this machine; it is satisfied except for one
named process, which is a weaker claim and should keep reading as one. A
`rapportd` remote-reachable bug is a hole Saffron has chosen to live with, and
revisiting it means turning Continuity off, not editing this paragraph.

Three properties the mechanism has, and each is load-bearing:

- **Nothing is tolerated unless it is named.** The default is empty and an
  unnamed listener fails exactly as before — measured with a second wildcard
  listener up: `rapportd` tolerated, the stranger still fails the probe.
- **It is matched by process name, never by port.** `rapportd`'s ports are
  dynamic — 49152, 60215 and 60216 have all been seen — so a port allowlist
  would be wrong the next time it restarts. A port drops out of the probe only
  when *every* listener on it is a tolerated process, so a second process
  sharing the port is not tolerated by association.
- **It is reported on every run, not the first.** §7's hazard row exists
  because a host service reachable from a cell is invisible, and an exception
  that goes quiet recreates that invisibility. The preflight line always ends
  `; tolerating rapportd:49152` — or `; tolerating nothing`, so the absence of
  a tolerance is stated rather than inferred.

An environment variable rather than a CLI flag: the probe has two entrypoints —
`saffron cell` and the `-m cell` suite — and one relaxation should not need two
knobs. It does **not** belong in `policy.yaml`, which is the repo's; this is a
property of the host. The cost of the env var over a flag is that it can be
exported into a shell profile and forgotten, which is exactly what the
every-run report is there to catch. Enumeration that cannot run still raises
with a tolerance named: tolerating a *listener* must never become tolerating a
probe that covered nothing.

### What the spike did to itself

Its first run reported `3 passed, 2 failed` against a runtime with **no kernel
configured**, so no container ever started. "Egress blocked" and "host unreachable"
both passed — by absence. That is principle 34, committed inside the spike written
to test the runtime, hours after the principle was written down in Appendix H.

The fix is the one §5.4 already specifies for gates, applied to the spike: a
liveness gate before any assertion, a probe that reports the *probe's* exit code
rather than the runtime's, and a third outcome — `error` — that refuses to print a
verdict at all. Which is the useful part of the story:

37. **Every harness that reports on something else needs the check it imposes.**
    The gate contract grew `tool` because a gate could report green without running;
    the spike grew a liveness gate for exactly the same reason, and did not inherit
    it automatically from having been written by someone who had just fixed it
    elsewhere. A rule about verification is not self-applying. Ask, of any reporting
    harness: *what does this print when it does nothing at all?*

---

