---
id: 80
title: The mutant a witness is judged by is withheld from the prompt and left in the worktree
status: open
tier: 1
filed: 2026-09-06
specs: [SA-0056, SA-0063, SA-0064]
prs: []
commits: []
cites: [§5.4.1]
related: [85, 109, 117]
---

## Problem

Found writing `SA-0063`, 2026-09-06 — the first spec in this repo to declare a
mutant, so the first for which this is reachable at all.

`agents/context.py:76` hands the implementer each criterion's `witness` and
`claim` and never its `mutant`. That is deliberate and `SA-0056` gives the
reason: *"a cell is untrusted, and a mutant it authored is a mutant chosen to be
killed."* A mutant it can merely *read* is the same defect one step removed —
the test still gets written to kill that exact edit and nothing else.

**But the spec is a file in the worktree the agent is working in.** `.saffron/**`
is `forbidden`, and `forbidden` is the `scope` gate reading a diff: it says what
an agent may not *change*. It says nothing about what an agent may read, and
`cat .saffron/specs/SA-0063-*.md` is one turn.

So the withholding is a prompt-level control standing in front of the
anti-theater mechanism, and this repo's own governing line already settles what
that is worth: prompts and in-agent hooks shape behaviour; they are never the
boundary. The failure it admits is the exact one `witness` exists to refuse —
the gate reports `pass` because the test killed the mutant, over a test written
to kill that mutant and nothing else, and `run_witness`'s pre-flight probe
cannot tell those apart because from outside they are identical.

~~Tier 3, and it moves on evidence rather than on argument.~~ No run had yet had
a mutant to read, so the likelihood was unmeasured while the consequence is
tier-1 shaped. `SA-0063` is the first run that could produce the datapoint, and
its `## Notes for the agent` asks the implementer to say so if it reads the file
— an honour system named as one, which is the measurement available before the
fix exists. **A run that shows an agent reading its own spec moves this to tier
1 without further argument.**

**Done looks like** the copy of the spec the cell can reach not carrying
`mutant:` at all. The host already reads its own authoritative copy — preflight
exports `.saffron` from the mirror at `base_sha` — so the two readers are
already distinct and only the worktree copy needs stripping. The alternative is
not placing the spec in the worktree at all, which is cleaner and costs the
agent a file it is otherwise given for context. What this needs is not code so
much as a decision about which copy is authoritative for whom; either shape is
cheap once that is settled.

## Done looks like

`DESIGN.md` §5.4.1 saying where a mutant lives, written by hand and first; the
seed fetch naming its refspec rather than relying on git's default; a
cell-marked test that starts a cell the way production does and proves the
mutant's blob is absent; intake reading mutants from the ref, with the ref's
commit recorded beside `spec_sha`; and a `saffron mutant` command to write and
push them. Item **109** comes first: it leaks a surviving mutant to the
implementer wherever the mutant is stored. And once mutants live on the ref,
spec authoring declares one for every criterion whose witness pins code that
already exists at `base_sha`. Stack #251 (2026-09-14) is why: seven of its eight
specs declared none, so `witness` skipped on every attempt, and the review round
found a witness that could not fail in most of them. Until this item lands that
rule would hand every mutant to the cell, so it is recorded here and not enforced.
A criterion over new code still cannot declare one (§5.4.1); item 117 covers it.

## Record

**Tier 1 as of 2026-09-07 — the evidence arrived.** `SA-0064`'s implementer
reasoned in its notes about a criterion's `mutant` field, which the prompt
withholds and which the host's own copy of that spec no longer contained: it had
read the worktree copy. Item **85** carries the measurement. The paragraph below
is kept as filed, because what it predicted is what happened.

**Decided 2026-09-12: neither shape works, and mutants move to a ref the cell
never fetches.** Both shapes assumed the worktree copy is the only one the cell
holds. It is not. `prepare_worktree` checks the cell out at `base_sha` from a
fetch of the mirror, and a batch runs committed specs, so the spec is in
`HEAD`'s tree and `git show HEAD:<spec>` reads its mutant whatever the working
copy says. Stripping the working copy also leaves the tree dirty, which
`committed` fails on every attempt. A salted hash of the edit does not work
either: the host has to apply the edit, so it would have to search the file for
the span matching the hash, and the cell holds the same file and the same salt.
Keeping the salt on the host makes it a host secret, and then encrypting the
whole mutant is simpler.

**Chosen:** mutants as plain YAML under a non-branch ref in the same repository
(for example `refs/saffron/mutants`). The mirror fetches `+refs/*:refs/*`
(`saffron/repos/mirror.py`) and so holds it. The cell's seed fetch takes git's
default refspec, branches and the tags on them, and does not. Measured in a
scratch repository with the host's git 2.54, seeded the way `prepare_worktree`
seeds a cell: the mirror held the mutant's blob and the cell did not. Not yet
measured with the cell image's git. **Rejected:** a host-held key encrypting the
mutant inside the spec. It keeps the spec one file, but it is one more secret
that must never reach a cell and must be handed to every cloud host.
