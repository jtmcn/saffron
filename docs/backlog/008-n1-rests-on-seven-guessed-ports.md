---
id: 8
title: N1 rests on seven guessed ports
status: done
tier: null
closed: 2026-08-20
specs: []
prs: []
commits: [8e6838a]
cites: []
related: []
---

## Problem

`preflight.PROBED_PORTS` is `5432, 5433, 3306, 6379, 8000, 8080, 27017`. The
probe raises rather than passing when it cannot run, which is right — but "no
host service answered on seven ports I thought of" and "no host service is
reachable" are different claims, and the code and `DESIGN.md` both currently make
the second.

This was not hypothetical: the host service that *was* exposed sat on 8000 and
was caught, while four more on 8001+ would have been invisible.

## Done looks like

enumerate the host's actual wildcard-bound listeners and
probe those.

## Record

**Status:** **done**, in `8e6838a` (*feat(preflight): a host process the
operator has accepted, named and reported*). `PROBED_PORTS` is gone.
`listening_sockets` parses `lsof -nP -iTCP`, `host_probe_ports` raises rather
than covering nothing when the enumeration fails, and `probed_ports` drops a
port only when *every* listener on it is a tolerated process.

**Done, 2026-08-20.** `preflight.host_listening_ports()` parses `lsof -nP -iTCP
-sTCP:LISTEN` and probes every listener not bound to loopback — a superset of
wildcard, because a service bound to the LAN address is reachable from a cell
too. Enumeration that cannot run raises; only lsof's own listing counts as
having run, so a listing with nothing but loopback rows is the real empty and a
silent lsof is not. Measured consequence on the machine v0.5 ran on: four macOS
services answer from inside a cell (ARD 3283, Control Centre 5000/7000, rapportd
49152), none of them in the old seven, so `preflight` now fails there until they
are turned off. That is the probe working.

**Amended 2026-08-21: one of the four is now tolerated, by name.** Three of
those services were turned off; `rapportd` remains, holding `*:49152` whatever
Continuity's settings say, and AirDrop going back on will reopen the two ports
it closed. So the probe was refusing to start a cell, permanently, for a daemon
the operator has accepted. `SAFFRON_ALLOW_HOST_PROCESS=rapportd` tolerates it
for that invocation: empty by default, matched by the COMMAND `lsof` reports
rather than by port (rapportd's ports are dynamic — 49152, 60215, 60216 all
seen), and a port drops out only when every listener on it is tolerated. The
preflight line names what was tolerated on every run, because an exception that
goes quiet is the hazard the probe exists for. Enumeration that cannot run
still raises. **This is an accepted risk, not a fix** — an agent in a cell can
reach that socket, and `DESIGN.md` Appendix G says so and says what it costs.
Renamed with it: `host_listening_ports()` → `host_probe_ports()`, which now
returns the ports probed *and* the listeners tolerated.

**Also 2026-08-21.** The probe enumerated a second time inside
`probe_host_bindings`, so the port list the operator was shown at the top of
preflight was not necessarily the one checked; it now takes that list as an
argument. It also connected serially at 1.5s per address-port pair, which puts
roughly a hundred listeners over the 300s cap — preflight failing for having
too much to check, and reporting it as a probe that did not run. The connects
go through a thread pool now; the timeout stays generous.
