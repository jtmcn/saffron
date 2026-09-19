---
id: J
title: "rev 12: what the first live runs found"
revisions: [12]
question: "What the first live runs found — four agent sessions in real cells, $2.47"
---

Appendix I recorded what building v0.5 found. This records what *running* it
found — four live agent sessions inside real cells, $2.47 total. The pattern from
rev 9 onward holds and sharpens: each artifact finds a class of defect the
previous one structurally could not.

### It works

`SA-0002` — implement the `size` core gate — run end to end, twice. The agent,
inside a cell with no target-repo credentials and no route but the proxy,
produced a plan that passed `validate_plan` on the first attempt, wrote
`saffron/gates/core/size.py` and `tests/test_size.py`, ran its own tests, watched
them fail, fixed them, ran the formatter, and committed. `commits_ahead` measured
the commit; the gate suite returned zero new failures against the baseline;
the run ended `READY_FOR_REVIEW`.

The code it wrote cites §2.1 and §5.4 for why `size` can be core, draws §5.6's
advisory/blocking line in the right place, and — for the spec types §5.4 gives no
ceiling for — defaults rather than returning `error`, reasoning that "`error`
means the gate itself broke." That is this document's most load-bearing
distinction, applied correctly by an agent that met it only through §5.3's
per-phase vocabulary injection. The injection works.

### The first run destroyed its own output

Teardown removed the worktree volume, and the commit ceased to exist — the mirror
had never heard of it, and the batch tree held only `plan.json` and
`baseline.json`. `worktree.export_patch()` was already written, and had no caller.

§0 says the product of this factory is **not code, it is a reviewable artifact**.
The run satisfied §9's success criterion and produced nothing anybody could read.

42. **A pipeline that verifies work and then discards it has not finished; it has
    failed expensively.** The last step of any producing stage is the one that
    makes the product outlive the machinery — and it is the step most easily
    mistaken for cleanup. §4.3 already said a bound firing must never discard
    committed work; teardown does the same thing on the *success* path, which is
    where nobody thinks to look.

The export now runs as the first statement of the `finally`, from every path that
produced commits — green, `EXHAUSTED`, budget-stopped, or raised. A task that
could not go green with commits in it is the most informative artifact the system
makes; exporting only the green ones would discard exactly the runs worth reading.

### Three things `allowed_tools` and its neighbours do not do

- **`allowed_tools` governs auto-approval, not availability.** With it set to
  `[]`, the live session offered the model all twenty-one built-in tools —
  `Task`, `CronCreate`, `ScheduleWakeup`, `SendMessage`, `WebFetch` among them.
  `dontAsk` denies the call, so the boundary holds, but §5.3's claim that omitting
  a tool "saves the turns spent discovering that" was false. The fix is a positive
  `tools` allowlist rather than a denylist: a denylist needs every name and stops
  protecting the moment the runtime grows one more, while an unrecognised name in
  an allowlist is dropped rather than granted. Twenty-one tools became six.
- **A target repo configured the agent working on it.** A planted
  `.claude/agents/` and `.claude/skills/` under `/work` both loaded into the
  session. `/work` is the tree the task edits, so a repo — or a previous
  attempt — could supply subagent definitions and skills to the agent reviewing
  it. `setting_sources: []` closes it.
- **The cost of that fix is §8's bucket 2.** Pinning `setting_sources` also stops
  the repo's `CLAUDE.md` loading, and `CLAUDE.md` is the flywheel's middle bucket
  and §2.1's named learning surface. It is inert until v1 injects it host-side
  from the mirror, the way `CONTEXT.md` already is — which is the right shape
  anyway, since a file under `/work` is rewritable mid-attempt.

43. **A configuration surface is an input, and every input from the workspace is a
    claim.** §5.3 established this for control artifacts the agent writes. The
    runtime's own configuration search path is the same hole one level lower: it
    is read before any of the harness's checks run, by machinery the harness does
    not own.

### A no-credential session reports `subtype: "success"`

Measured on the no-key path, before any real run: a cell whose agent cannot
authenticate returns `{"subtype": "success", "is_error": true,
"total_cost_usd": 0.0}`. Code keying on `subtype` — which the cost reconciliation
did, and which a review had approved — records a session that did nothing as a
clean $0 run. Unattended, that is a budget that stops counting. Both now key on
`is_error`.

This is principle 34's seventh disguise, and the cheapest one to have found: it
cost nothing, because it lives on the path you exercise when you have no money.

### The proxy allowlist and the diagram disagree

§2's diagram shows the egress proxy allowing `api.anthropic.com` **and a package
mirror**. The implementation allows one host, so `uv run`, `pip install` and
`npm install` all fail inside a cell. The implementation is the better answer —
§5.1 already requires services, fixtures and dependencies to bake in at *image
build* time, so a cell that needs a package index at run time is a repo that has
not finished onboarding. The diagram's package mirror is vestigial, exactly as
§2.1's "gate-runner shim" was: a component drawn in a design, never built, and
unnecessary once the surrounding decisions were made. Struck.

### The cost model was high

| | §7.1 estimate | Measured |
|---|---|---|
| Plan turn | *(inside Implement)* | ~$0.44 |
| Implement | $2–6 | $0.85 |
| Plan + Implement, total | $2–6 | **$1.01–1.29** |

Two runs of the same spec, one commit each, no repair attempts. Not enough data to
rewrite §7.1 — a task needing four repair attempts is the row that matters and has
not been run — but the first real numbers land under the estimate rather than over
it, which is the direction that lets `--budget 50` buy more nights than it was
sized for.

### What is still unproven

**The repair loop has never run.** Both live runs went green on attempt one, so
GATE ⇄ REPAIR — resuming a session with structured failures — remains untested
against a real model. So does no-progress detection, and so does the question of
whether `total_cost_usd` on a resumed session reports that turn's cost or the
whole session's, which decides whether the spend accounting over-counts. That is
the next thing worth paying for.

44. **The path that has never run is the one your estimate is about.** Two green
    runs measured the cheap half of a loop whose expensive half is the reason the
    loop exists. A cost model validated only on the happy path is a cost model of
    something else.

---

