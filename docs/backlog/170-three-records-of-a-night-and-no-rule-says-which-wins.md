---
id: 170
title: Three records of a night and no rule says which wins, so the ledger's claim to be authoritative is already false of the page an operator reads
status: open
filed: 2026-09-17
by_hand: true
specs: []
prs: []
commits: []
cites: [§4.1, §4.6, §6]
related: [43, 160, 165, 166, 167]
---

## Problem

§6 states this as an open fork and leaves it open. `DESIGN.md:1204` reads: "The
queue reads `queue.json`, not the ledger, and that is currently undecided rather
than chosen." It ends with the fork. "Either the ledger gains what it is missing,
or this section stops implying the ledger is the source."

Today a night is recorded in three places. `~/.saffron/ledger.db`, which
`CONTEXT.md` §8 calls authoritative for state. `~/.saffron/batches/v0/`, which
holds the artifacts and `queue.json`, and which the morning index renders from.
And the repository with GitHub, which holds branches, pushed shas, pull requests
and spec retirement into `.saffron/specs/done/`. No rule says which wins.

They already disagree. Reconstructing all 68 stored rows from the ledger on
2026-09-17: `risk` differs on 1 row and a naive reconstruction of `attempts`
differs on 4.

**The deeper reason is not a missing column.** `tasks.risk` holds the tier the
spec declared, written at task creation, and `saffron/cell/session.py:1336-1340`
says so: "The spec-declared tier only… `_suite` below computes the real,
per-attempt effective tier from the diff." `_finish` writes
`risk=outcome.effective_risk`. So the two stores hold different quantities under
one name, and `SA-0085` is the row that shows it. That spec declares no `risk:`
at all, so the ledger carries the default `standard` while the store carries the
earned `elevated`.

**The proposal this item exists to decide.** The authoritative record becomes
commits on `refs/saffron/*` in each target repository, pushed to the real remote.
The ledger becomes an index folded out of that record, deletable at any time. The
index renders from the record rather than from a second store, so divergence
stops being managed and becomes impossible. A cloud runtime is the second driver:
a SQLite file on one host is the wrong shape once a night spans machines.

**The spike that makes it admissible** is
`docs/evidence/2026-09-17-state-on-git-refs.md`. A cell reaches neither a state
ref nor its objects, by two independent mechanisms. GitHub accepts the namespace,
keeps it out of branch listings and default clones, and refuses a
non-fast-forward push. That refusal supplies compare-and-swap, which is what a
shared budget needs and what `saffron/batch.py:167` cannot give across hosts.
Rulesets, gc survival over weeks, push rights from a fork, and contention
behaviour are all recorded there as unproven.

**What this reverses, recorded in three places.** §4.6 rule 1: "SQLite remains
the system of record. The graph is a projection with no write path back."
`docs/superpowers/specs/2026-09-02-ontology-authoritative-design.md` says it
twice more. Its section 2 reads "The ledger is authoritative for facts". Its
section 3 reads "The ledger stays the system of record". §4.1's founding argument for SQLite is that a dependency-free
state store is what lets Saffron recover from Saffron. That argument now cuts
both ways. A git repository is dependency-free in the same sense, and carries no
schema to migrate.

**Three §6 claims about this fork have gone stale**, which is why the section
reads worse than the situation is. Item 29 closed "nothing anywhere records
whether a task was merged" on 2026-08-30, and 65 of 99 tasks are `MERGED`.
`tasks.risk` is `NOT NULL DEFAULT 'standard'`, so the rows §6 calls unwritten
read as measured rather than absent. That is §4.1's own failure of a column named
for a measurement it cannot make. And the diff stat is not discarded. It reaches
`queue.json` from `saffron/phases/package.py:792`, and lands in no ledger
column.

**A narrower change stands whichever way this goes.** `added` and `removed` have
no home in any store but the file. §6's own mock renders them. That is true of
the git record as much as of the ledger.

## Done looks like

One authoritative record of a night, and one rule saying so. §4.6 rule 1 is restated
rather than contradicted, and §6's fork is closed rather than left open.
`CONTEXT.md` §8's **Ledger** entry says what the ledger is once it stops being
the system of record. The 2026-09-02 design document is amended in place, since
its sections 2 and 3 assert the opposite.

The morning index renders from the record. `queue.json` either disappears or is
named as a render rather than a store. The budget is a compare-and-swap on a ref,
so a stale writer is refused rather than trusted.

A command rebuilds the index from the record, and the suite proves the fold loses
nothing. Deleting the index and rebuilding it produces the same rows.

Items 43, 166 and 167 land first. A record with no terminal outcome, no per-gate
result, and a write failure nothing reports is not a record. Those three specs
fix one each.

The unproven items in the spike are either closed by measurement or accepted in
writing with what each costs if wrong.

## Record

**Filed 2026-09-17 by hand**, from §6's open question and a decision to move
toward a cloud runtime. By hand because it edits `DESIGN.md` and `CONTEXT.md`,
which are both `protected`, and because it amends a design document under
`docs/superpowers/specs/`. A cell can land none of that.

The approach was chosen before filing: per-target refs, pushed to the remote,
with the index folded out of them. Two probes ran the same day and their verdict
is `docs/evidence/2026-09-17-state-on-git-refs.md`. The sectioned design is not
written yet, and two questions open it. Whether the existing 99 tasks are
migrated or abandoned. A faithful migration imports a `risk` value that is
sometimes a default wearing a measurement's clothes. And whether `queue.json`
goes at once or becomes a render first.
