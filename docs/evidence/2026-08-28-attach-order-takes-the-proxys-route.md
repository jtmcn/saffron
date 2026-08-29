# The probe container takes the proxy's route out

Taken 2026-08-28, on the first machine to run Saffron from a clean install.
`saffron cell` reached IMPLEMENT and then failed every attempt with an API error
that was neither the API's nor the allowlist's:

```
agent: system api_retry            (x10)
agent: API Error: ERROR: The requested URL could not be retrieved.
agent: success in 1 turns, $0.0 (api_error)
SA-0013    NOT_IMPLEMENTED
```

The page is squid's. **The allowlist was not what refused it**, and teardown said
so by staying silent — `denied_egress` reported nothing, because there was
nothing to report.

## What the proxy's own log said

Captured with `container logs saffron-proxy` while the run was still up. Teardown
does read the log before removing the container (`session.py`), so timing is not
what hid this — `denied_egress` greps `TCP_DENIED`, and none of these rows are.

```
1787975617.589  35022 10.88.0.4 TCP_TUNNEL/503 0 CONNECT api.anthropic.com:443 - HIER_NONE/- -
1787975617.589   5011 10.88.0.4 TCP_TUNNEL/503 0 CONNECT api.anthropic.com:443 - HIER_NONE/- -
1787975618.180      0 10.88.0.4 TCP_TUNNEL/503 0 CONNECT api.anthropic.com:443 - HIER_NONE/- -
```

`TCP_TUNNEL/503`, not `TCP_DENIED/403`: the ACL **allowed** the CONNECT and squid
could not complete it. `HIER_NONE` is squid never reaching a peer. The durations
are the whole diagnosis — `35022`ms and `5011`ms are DNS timeouts, and the `0`ms
rows after them are squid's negative DNS cache answering instantly.

From inside the proxy, during the run:

```
nameserver 10.89.0.1                       # resolv.conf, correct
default via 10.89.0.1 dev eth0             # route, correct
nslookup api.anthropic.com 10.89.0.1       # ;; connection timed out
nc -z 160.79.104.10 443                    # FAIL
```

Configured correctly and unusable. A fresh single-homed container on
`saffron-egress` failed the same way at that moment, so the fault was the
network, not squid, not the proxy image, and not the allowlist.

## The one variable

`docs/evidence/scripts/2026-08-28-egress-nat-order.py`, against
`container CLI version 1.3.0`:

| Order | Egress from the proxy |
|---|---|
| create internal network → start proxy | **OK** |
| create internal network → run one container on it → start proxy | **FAIL** |

The script runs the pair in both sequences and the result does not move, so the
difference is the order itself and not residue from whichever ran first. That is
the entire difference. Any container on the `--internal` network before
the dual-homed proxy starts, and the proxy comes up with a default route through
the egress gateway that carries nothing. What is measured is the route and the
timeouts; which layer the runtime loses — NAT, the bridge, the gateway itself —
is not, and the name of this file deliberately does not guess. Nothing about Saffron is required to
reproduce it: `alpine:3` running `true` is enough.

Two further measurements, same runtime:

- Reversing the proxy's own legs (internal first, egress second) is not a fix and
  never was: the container then takes `default via 10.88.0.1` and
  `nameserver 10.88.0.1` off the internal network, which is exactly the failure
  `proxy.py` already documents. Egress-first is correct.
- Dual-homing onto a second **non-internal** network is fine. `--internal` on the
  other leg is the trigger.

## Why production hit it and the suite did not

`tests/test_proxy.py::test_the_proxy_allows_anthropic_and_denies_everything_else`
asserts real reachability, and it passes — its fixture creates the network and
the proxy is the first thing on it. `session.py` ran
`assert_host_is_unreachable` first, and that probe is a container on the internal
network. The suite and production differed by one container, in one order, and
only production was wrong.

The fix is the order: the proxy starts before the probe. N1 is unchanged — the
probe still runs before any cell does, and the proxy is a sibling that holds no
credential and reaches nothing the allowlist does not name.

## The loop, closed

With the proxy started first, `saffron cell .saffron/specs/SA-0013-fixture-values-are-witnessed.md
--repo .` ran to `READY_FOR_REVIEW` at exit 0 for $0.63 and opened
[#51](https://github.com/jtmcn/saffron/pull/51) — the first cell this machine has
completed. The symptom the record opens with is the same command, on the same
machine, minutes earlier.

## Standing

This is an apple/container 1.3.0 observation, and `saffron/cell/runtime.py` was
measured against 1.2.2 — the ordering fix is a workaround for a runtime defect,
not a correction to Saffron's design. `CPU_OFFSET = 1` was re-measured on 1.3.0
and still holds (`spikes/cell-runtime.sh`: `nproc = 3` for `--cpus 2`). Whether
1.3.1 still has it is unmeasured.
