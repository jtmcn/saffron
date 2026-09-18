# What a cell can reach when state lives on git refs

Measured 2026-09-17, against `git 2.50` on macOS and against GitHub. Two probes,
both in `scripts/`:

- `2026-09-17-refs-a-cell-can-reach.sh` — fully local, no remote, no side effects.
- `2026-09-17-refs-on-a-remote.sh` — writes a ref to a real remote and leaves it.
  Run against a throwaway private repo, since deleted.

## The one question

Saffron's state lives in SQLite at `~/.saffron/ledger.db`, and `DESIGN.md` §4.6
rule 1 says so deliberately: *"SQLite remains the system of record. The graph is
a projection with no write path back."*
`docs/superpowers/specs/2026-09-02-ontology-authoritative-design.md` says it
twice more — *"The ledger is authoritative for facts"* (§2) and *"The ledger
stays the system of record"* (§3).

The proposal this spike was run against inverts that: the authoritative record
becomes commits on `refs/saffron/*` in each target repo, pushed to the real
remote, and the ledger becomes a deletable index folded out of it. The motive is
§6's own open question — *"there are two records of a night and the authoritative
one is the file, not the database"* — plus a cloud runtime, where a SQLite file
on one host is the wrong shape.

That proposal is only admissible if it does not breach the one line that governs
everything: **a cell is untrusted, and every control that matters lives outside
it.** So: *can a cell reach state kept on a non-branch ref of the repository it
is working in?*

## The answer: no, by two independent mechanisms

The local probe reproduces `saffron/cell/worktree.py`'s seed sequence verbatim —
`git init`, `git remote add origin /mirror`, `git fetch -q origin`,
`git checkout -b <branch> <base_sha>`, `git remote remove origin` — against a
bare mirror carrying both `refs/heads/main` and
`refs/saffron/tasks/SA-0099`.

```
refs present in the mirror:     refs/heads/main
                                refs/saffron/tasks/SA-0099

refs the cell can see:          refs/heads/saffron/SA-0099

state commit object in cell:    absent
state ref in cell:              absent
```

**The state commit's object is absent, not merely unreferenced.** A cell that
knew the sha could not `git cat-file` it. The reason is principled rather than
incidental: `git fetch origin` with no refspec uses the configured
`+refs/heads/*:refs/remotes/origin/*`, so negotiation asks for branch tips only,
and an orphan commit is reachable from no branch. Nothing sends it.

**The second mechanism is the mount set.** `worktree.py:66-68` already states the
rule — *"The mirror is bind-mounted read-only for the clone and is not among the
mounts the cell keeps — a cell that could write the mirror could rewrite the
history the host is about to read."* The mirror appears only in the ephemeral
seed container. The running cell's mounts are `mounts(volume, state, gates_dir)`.
So a cell that tried `git fetch 'refs/*:refs/*'` has no remote to fetch from.

Either mechanism alone suffices. Both hold.

## What GitHub does with the namespace

Nine probes against a throwaway private repo, then the load-bearing ones
repeated against `jtmcn/saffron` itself.

| probe | result |
|---|---|
| push `refs/saffron/tasks/SA-0099` | accepted — `* [new reference]` |
| `git ls-remote` | visible |
| API `repos/:slug/git/refs` | listed beside `refs/heads/main` |
| API `repos/:slug/branches` | **not** listed — `main` only |
| `gh pr list` | unaffected |
| default `git clone` | brings neither the ref nor the object |
| explicit refspec fetch | round-trips, content intact |
| fast-forward update | lands at the expected sha |
| non-fast-forward push | **refused** without `--force` |

**The last row is the finding that moves.** Git supplies compare-and-swap for
free:

```
! [rejected]  refs/saffron/tasks/SA-0099 (non-fast-forward)
error: failed to push some refs
```

A writer whose view is stale is rejected and must re-read before retrying. That
is the primitive a shared budget counter needs, and it is the thing
`batch.py:167` — `remaining = budget_usd - ledger.batch_spend(batch_id)` — cannot
provide across hosts, because a SQLite file is local to one. The cross-repo
budget was the strongest objection to per-target state when this was first
sketched; git answers it better than the ledger does, rather than merely
deferring it.

### Against the real repository

`jtmcn/saffron` has no rulesets (`[]`) and `main` is unprotected, so the probe
below tests a repository with history, seven branches and four open pull
requests, and nothing more.

```
before:  refs/saffron/* = 0    branches = 7    open PRs = 4
push:    * [new reference]  -> refs/saffron/spike-probe    accepted
          absent from branch listing
delete:  - [deleted]
after:   refs/saffron/* = 0    branches = 7    open PRs = 4
```

The namespace was empty beforehand and the remote was restored exactly.

## Two costs, confirmed rather than supposed

**The trail becomes visible to anyone with read access.** `git/refs` lists it, so
on a public repository the costs, findings and critic claims are public. Not a
hypothetical: the API returned the probe ref immediately.

**A local clone of a mirror carries the objects.** `git clone mirror.git` copies
the object store by hardlink, so the state objects arrive unreferenced even
though the refs do not. No cell takes that path, and it means *"clone the
mirror"* is not a way to hand somebody a scrubbed copy.

## One correction to the instrument

The first version of probe 9 put the push inside a pipeline and tested the
pipeline's status, which is `sed`'s. It printed `RESULT: accepted` over git's own
`! [rejected]`. The committed script captures the output and tests git's exit
code. The reported result above is the corrected one, and git's stderr was
unambiguous either way.

## Three §6 claims that have gone stale, found on the way

These bear on §6's open question and are not what the spike was run for.

**"nothing anywhere records whether a task was merged, which is the trailing
accept rate's whole input."** Backlog item **29** closed this on 2026-08-30
(`SA-0019`, PR #70). Measured against `~/.saffron/ledger.db`: **65 of 99** tasks
are `MERGED`. The trailing accept rate has a source.

**"`tasks.risk` was never written for tasks that ran before `SA-0007`."** The
column is `risk TEXT NOT NULL DEFAULT 'standard'`, so those rows do not read as
absent — they read as a measured `standard`. All 99 are non-NULL. That is §4.1's
own *"a column named for a measurement it cannot make"* failure, in a second
column, and it is invisible rather than merely open.

**The deeper reason the ledger cannot reproduce `queue.json` is not a missing
column.** `tasks.risk` is the tier the *spec declared*, written at task creation
— `session.py:1336-1340` says so: *"The spec-declared tier only… `_suite` below
computes the real, per-attempt effective tier from the diff."* `_finish` writes
`risk=outcome.effective_risk`. So the two stores hold different quantities under
one name. Reconstructing all 68 stored rows from the ledger: **risk disagrees on
1** (`SA-0085`, which declares no `risk:` at all, so the ledger has the default
`standard` while the store has the earned `elevated`), and a naive
`REPAIRING + 1` reconstruction of `attempts` **disagrees on 4**.

## What this record does not establish

**Rulesets.** Neither repository probed had any. Whether a target repository with
ref-creation restrictions accepts `refs/saffron/*` is untested, and §2.1's
onboard-any-repo ambition is where that lands.

**Survival.** Minutes were measured, not weeks. Whether server-side gc ever
prunes objects held only by an orphan ref is unproven.

**Push rights.** A contributor working from a fork has no push access for
non-branch refs on the upstream. Untested, and it bounds which repositories this
can serve.

**Concurrency beyond the primitive.** That a stale push is refused is measured.
That a retry loop over it is correct under real contention is not — one repo and
sequential cells today, so there was nothing to contend.

## The clause that would reopen it

A target repository whose rulesets refuse ref creation, or a measured case of gc
pruning an orphan ref's objects. Either makes the per-target arrangement
unavailable for that repository and forces the state somewhere Saffron owns
outright.
