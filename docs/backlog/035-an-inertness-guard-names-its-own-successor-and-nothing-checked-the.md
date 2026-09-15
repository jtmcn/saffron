---
id: 35
title: An inertness guard names its own successor, and nothing checked the successor could reach it
status: done
tier: null
closed: 2026-09-01
specs: [SA-0022, SA-0025, SA-0026, SA-0027, SA-0031]
prs: []
commits: []
cites: [§2.1]
related: [16, 24, 28, 33]
---

## Problem

**Status:** **done** — `SA-0027`, 2026-09-01.

`SA-0022`, `SA-0025` and `SA-0026` each shipped a capability inert on purpose,
asserting it with a test that the capability is off and a comment naming which
spec will flip it. Nothing checked the named spec's `touches` could reach the
file carrying that comment, and `SA-0026`'s own review is the corpse, twice:
`tests/test_package.py`'s guard (planted by `SA-0025`) asserted the literal
string `parent_branch` never appears in `saffron/cli.py`, but that file was
not in `SA-0026`'s `touches`, so its agent could neither edit the guard nor
run the gates against it — it spelled the keyword
`{"parent" + "_branch": ...}` to dodge the match instead, said so in a
comment, and logged the box it was in as this file's item 33; and
`saffron/cell/session.py` and `saffron/phases/package.py` each carried a
comment saying stacking was off, both `forbidden` to `SA-0026`. Both review
lenses flagged the first, both files were corrected by hand for the same
reason: the file was never one the spec retiring it could reach. A `git grep`
against the mirror at `base_sha` costs no export, no working tree and no
network; what it prevents is a full cell paying for a choice between a false
green and a `scope` refusal on work the spec was right to do.

**Done looks like, and is:** the convention, stated in code
(`mirror.py`'s `retirement_markers` docstring, not only here) — a comment or
docstring carrying `saffron:retired-by <SPEC-ID>` declares that its file
asserts something that spec is expected to falsify.
`mirror.retirement_markers(mirror, sha)` reads every marker out of a bare
mirror with `git grep -n -z`, no export or checkout, answering `[]` rather
than raising on a repository with none (`git grep` exits 1 on no match —
`error` ≠ `fail`). `scheduler.retirement_refusal(spec, markers)` is a pure
refusal in `protected_touch_refusal`'s own shape (item 28), read with
`scope.matches` — the same function `scope`, `integrity`, `size` and item
16's criterion-path refusal already share: a marker this spec's `touches`
cannot reach refuses, naming the file and the declared `touches`; one inside
the spec's own `forbidden` refuses too, worded differently, since "may not
touch it at all" and "touches doesn't reach it" are different operator
fixes. Empty `touches` skips the second check outright — item 16's own bug
guard, since an empty list is a bug awaiting DIAGNOSE, not a spec that failed
to declare — but not `forbidden`, which a bug spec can carry regardless.
Wired into both pre-cell paths item 28's refusal reaches: `build_queue`
(gate 0) and `cli._run_cell`, best-effort against the mirror the way
`_protected_paths_at` already is. A marker naming a spec id nothing in the
directory (or `specs/done/`) declares gets its own line in `build_queue`'s
refusals — item 24's `done/` rule, applied to this class of dangling
reference.

**What this still cannot see.** Reachability, not intent: a marker naming an
id that exists is not flagged even if that spec is long `MERGED` or
`REJECTED`. It garbage-collects nothing — a guard's own removal deletes its
marker by construction, but one left behind some other way still reads as
live. And it is opt-in: a heuristic over every `SA-NNNN` mention would refuse
most of this repository, which cites spec ids as attribution far more than as
a claim about the future — a capability shipped inert *without* a marker is
as invisible to this refusal as it was before.

**What review added after the cell.** Two holes the gates could not see, both
the same shape: `git grep` cannot tell a line that *writes* a marker from a
line that *is* one. A spec must quote the marker it arms in its own
acceptance criteria, so every such spec read back as carrying a marker at its
own path and refused itself — naming its `forbidden` list, which was not the
cause. `.saffron/specs` is now excluded from the grep: a spec is where a
marker is discussed, never where one lives. `tests/**` deliberately is *not*
excluded, because `SA-0025`'s own inertness guard lived in a test file — so
`tests/test_mirror.py` spells the string by concatenation instead, having
otherwise shipped four dangling markers into this repository and four
permanent refusals into every `saffron queue`. And a third limitation for the
list above: the empty-`touches` guard means a bug spec is checked against
markers only *before* DIAGNOSE populates its `touches`, never after — the
same pre-cell-only hole item 28's sibling refusal has.

**What the second review round found, and three more blind spots it named.**
The item shipped carrying a stray diff3 conflict marker — one line, naming an
in-cell commit that exists in no history here — through two review commits. In
a file the project treats as a primary record, that is the workspace-claim
failure in documentation form. And a dangling-marker line asserted more than
the scan had read: `known_ids` is built from the spec files that *parsed*, so a
marker naming an id declared only by an unparseable file was called a dangling
reference. It now says how many files did not parse, the way
`_dependency_refusal` already qualifies the identical case.

Three things this refusal still cannot see, all named rather than fixed:

- **A marker whose id the regex cannot parse is dropped in silence.**
  `saffron:retired-by SA_0027`, a stray colon after the keyword, or a marker
  inside a binary file all *match the grep* and then vanish — the false green
  this item exists to end, one layer down. Fixing it is a decision and not a
  one-liner: this repository writes the literal keyword in a regex, in three
  scheduler f-strings, in two test writers and in this paragraph, and every one
  of those would become a "malformed marker" line on every `saffron queue`. The
  permissive id parse is kept deliberately for the same reason — trailing
  garbage (`SA-0031-extra`) resolves to its prefix and so reaches an operator
  as either a named refusal or a dangling line, where a stricter pattern would
  return it to silence. Visible-and-possibly-misattributed beats invisible.
- **Only `.saffron/specs` is excluded, so a document that writes a real id
  arms a real marker.** This file, `CLAUDE.md` and `DESIGN.md` escape today
  only by writing a placeholder rather than a concrete id. Excluding `docs/**`
  was considered and rejected: `docs/` is a target repo's convention, not
  Saffron's, and core knows nothing about a repo's layout (§2.1). `.saffron/`
  is excluded precisely because it *is* Saffron's own path.
- **The repo-wide `protected` list is not consulted.** `retirement_refusal`
  reads `spec.forbidden` but not `policy.yaml`'s `protected`, which `_refuse`
  already holds. A marker in a protected path, named by a spec whose `touches`
  glob covers it, is admitted here and dies at the plan checkpoint instead —
  the same corpse this refusal exists to prevent, one list over.
