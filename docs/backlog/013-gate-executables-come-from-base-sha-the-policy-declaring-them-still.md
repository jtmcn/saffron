---
id: 13
title: Gate executables come from `base_sha`; the policy declaring them still comes from the working copy
status: done
tier: null
closed: 2026-08-24
specs: []
prs: []
commits: [1b670c3]
cites: [§5.4]
related: [11]
---

## Problem

The same asymmetry item 11 raised for a task's base, in a second place, left
half-closed by the fix that closed the first. `session.py` calls
`load_policy(repo)` — reading and validating `.saffron/policy.yaml` and the
gate executables in the operator's working copy — then resolves
`gate_executables(Path("/gates"))` against `export_gates`'s archive of
`base_sha`, the remote's default-branch head. Before this branch those were
the same tree; now they can diverge on any branch that touches `.saffron/`.

Two concrete consequences. An operator on a branch that adds a gate role gets
a `PREFLIGHT_FAILED` whose watch line reads *"the toolchain is broken, not the
code"* — a wrong diagnosis for a policy/export mismatch, not an infrastructure
failure. And `policy_sha` in the ledger names the working-copy policy rather
than the one that actually governed the exported gates, so the ledger's record
of what ran is not the record of what was declared.

A repo adding its *first* gate lands somewhere else again, and worse. There is
no `.saffron/gates` at `base_sha` at all, so `export_gates` raises on the
unmatched pathspec at `session.py:572` — after the image build, the host probe
and the proxy — and the run exits 2 as infrastructure rather than reaching
`PREFLIGHT_FAILED`. `export_gates_for`'s guard covers the opposite case,
`gates: {}`, where the policy declares nothing to export.

This is the ordinary workflow, not an edge case: writing or renaming a gate
means being on a branch that adds it, and running `saffron cell` from that
branch is how you would test it. The run reaches `PREFLIGHT_FAILED` before the
agent starts, so it costs nothing but the wrong diagnosis. Until it is closed,
the workaround is to land the gate on the default branch first — `base_sha` is
the remote's head, so the export sees a gate only once it is pushed there.

## Done looks like

`load_policy` reading from the same export
`gate_executables` already resolves against, rather than from `repo`.
`export_gates` already archives a subtree with `git archive <sha> .saffron`;
loading policy from that archive — `git archive <sha> .saffron` plus
`load_policy` pointed at the export instead of the working copy — is the shape
of the fix, not a new mechanism.

## Record

**Status:** **done**, in `1b670c3` (*fix(session): the policy declaring a
run's gates came from the working copy*). `session.py:800` reads
`load_policy(gates_dir)` — the same export the gate executables resolve
against.

**Done, 2026-08-24.** The shape held: the pathspec widened from
`.saffron/gates` to `.saffron`, and `_drive_cell` reads its policy back out of
that export. Three things the item did not say.

**The fix deleted a function rather than adding one.** `export_gates_for`'s
`gates: {}` guard existed *only* because the narrow pathspec made `git archive`
fail on a repo with no `gates/` — widening it removes the guard's reason, and
`export_gates` already cleared its own dest, which is the half of that guard
worth keeping (its staleness test moved onto `export_gates` with it). Renamed
with it: `export_gates` → `export_saffron_dir`, because a function that now
carries the policy the run is judged under cannot be named for the subdirectory
it used to copy.

**The export moved out of the try block, not just above `load_policy`.** It ran
after the image build, the host probe and the proxy; it now runs before all
three and before the ledger has a task row — so a `base_sha` carrying no
`.saffron` at all costs nothing and leaves no run behind. That case is still an
exit 2: a repo whose default branch is not onboarded cannot start a cell, which
is what pinning the policy to `base_sha` means and is stated in §5.4.

**`/gates` now also holds `specs/` and the `Dockerfile`** — everything under
`.saffron/`, because one archive is one pathspec. They are read-only and the
cell already has all of it at `/work`, so this leaks nothing; it is noted
because a mount named `/gates` holding specs is otherwise a surprise.
