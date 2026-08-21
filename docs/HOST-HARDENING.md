# Hardening the host

Setup for a machine dedicated to running Saffron, before it runs a batch.

Saffron's safety argument (`DESIGN.md` §2) is that a cell is untrusted and every
control that matters lives outside it. Several of those controls are only as
strong as the machine underneath: N1 says "zero writes to real infrastructure,
enforced structurally, not by prompt", and on a general-purpose laptop that is
enforced by the operator remembering what is installed. On a dedicated host it is
enforced by nothing being installed.

**That is the point of a separate machine.** It converts a set of conventions
into a set of facts.

Every item below is here because something on a real machine tripped the probe or
cost a live run — none is generic macOS advice.

---

## 1. Nothing real on the host

The cell holds exactly one credential — the agent's own API key (§5.1) — and gets
no target-repo credentials at all. On a dedicated host, make that true one layer
out: there is nothing to leak even by mistake.

- No cloud profiles: `~/.aws`, `~/.config/gcloud`, `~/.azure`.
- No SSH keys that can push anywhere. Saffron pushes with a token it is given; a
  key on the host is a key an agent's diff could exfiltrate.
- No signed-in iCloud account, no password manager, no browser profile.
- No production database clients configured, no `.pgpass`, no `.env` files for
  anything but the factory key itself.
- The repos it works on arrive as **local bare mirrors** (§5.1). The host needs
  push access to the real remote; the cell never sees it.

Check what a fresh account actually has before assuming it is clean.

## 2. Nothing listening

`saffron`'s preflight probe enumerates the host's non-loopback TCP listeners and
tries to reach each one **from inside a cell** — because an `--internal` network
still routes to the host gateway (Appendix G), so a service bound to `0.0.0.0` is
reachable without ever traversing the proxy.

**On a dedicated host the expected result is an empty list.** That turns the
probe from a judgement call into a binary.

What tripped it on a working laptop, all of which should be off here:

| Found | Turn off |
|---|---|
| `ARDAgent *:3283` | System Settings → General → Sharing → **Remote Management** |
| `ControlCe *:5000`, `*:7000` | Sharing → **AirPlay Receiver** |
| `rapportd *:60215`, `*:60216` | General → AirDrop & Handoff → **Handoff**, and **Sidecar** |
| `rapportd *:49152` | Survives every toggle — see below |
| a dev server on `*:8000` | Bind it to `127.0.0.1`, or do not run it here |

Also disable, though they did not appear on the test machine: File Sharing,
Screen Sharing, Remote Login (SSH), Printer Sharing, Internet Sharing, Content
Caching, Media Sharing.

### `rapportd`

Apple's Continuity daemon (`/usr/libexec/rapportd`). It keeps `*:49152` open at
boot regardless of Handoff, AirDrop and Sidecar being off — those toggles only
close its *other* sockets. It is not in any Sharing pane.

On a dedicated host, disable the daemon:

```
sudo launchctl disable system/com.apple.rapportd
sudo launchctl bootout system/com.apple.rapportd
```

`disable` persists across reboots; `bootout` stops it now and may need a reboot
to take. **A major macOS update can reset the disable database** — re-run the
probe after every upgrade rather than assuming.

### The allowlist is a development affordance, not a host setting

`SAFFRON_ALLOW_HOST_PROCESS` lets a named process be tolerated, and reports it on
every run. It exists so a laptop that also does Handoff can still run cells.

**Leave it unset here.** The realistic failure is someone copying a working
invocation from a dev machine to this one, bringing `SAFFRON_ALLOW_HOST_PROCESS`
along, and quietly widening the control on the machine where it matters most. If
the probe fails on this host, the answer is to turn the service off, not to name
it.

## 3. What the host does need

- **`apple/container`** (`brew install container`), plus its kernel:
  `container system kernel set --recommended`.
- **Rosetta** — `container build` does not work without it on Apple silicon
  (`softwareupdate --install-rosetta`). Measured, not assumed.
- **git**, and `uv` for Saffron itself.
- **A factory API key, separate and capped.** §5.1: use a different key from your
  interactive work so it can be revoked independently, and set a provider-side
  monthly cap on it — that is the only spend ceiling that holds without the
  cell's cooperation, because N2's bounds are an accounting sum over numbers the
  cell reports.
- **`launchd`** for the nightly batch, not `cron` — it handles wake and will not
  silently skip a sleeping Mac (§4.4).

## 4. Verify, do not assume

```
# Nothing non-loopback should be listening.
lsof -nP -iTCP -sTCP:LISTEN | awk 'NR>1 && $9 !~ /^127\.0\.0\.1|^\[::1\]/'

# The probe's own view, from inside a real cell.
uv run pytest -m cell tests/test_proxy.py -q
```

`test_no_host_service_answers_from_inside_a_cell` passing with
`SAFFRON_ALLOW_HOST_PROCESS` **unset** is the acceptance criterion for this
document.

Re-run both after any macOS update, and after installing anything.

## 5. What this does not cover

The cell's own isolation — the internal network, the allowlisting proxy, the
mirror-only remote, `--cap-drop ALL` — is Saffron's job and is tested in
`tests/test_proxy.py` and `tests/test_worktree.py`. This document is only about
the machine those controls sit on.

Nor does it make the host trustworthy against a determined attacker; it makes the
blast radius of an agent doing something stupid small enough to reason about,
which is what §2 actually claims.
