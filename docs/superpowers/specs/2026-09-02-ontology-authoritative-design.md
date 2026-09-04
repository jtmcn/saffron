# The ontology becomes authoritative — design

The run record has a vocabulary (`ontology/saffron.ttl`) and a glossary
(`CONTEXT.md`). Where they overlap they are asserted equal, and a core gate
declared on one side alone fails the test suite with no repair a cell can make.
This design generates the glossary's run-record half from the vocabulary, and
then asks — by the experiment `DESIGN.md` Appendix O already specifies, not by
argument — whether the vocabulary should also become executable.

> **Citations:** a bare `§` cites `DESIGN.md`, per repo convention. This
> document's own sections are cited as *part N*; the operator-visibility plan's
> parts are always named as *the plan's part N*.

**Read part 1 first.** An earlier draft of this document proposed superseding
`ontology/RATIONALE.md` by argument. §9 and Appendix O forbid exactly that, and
part 1 is what changed as a result.

## What was measured

Run, not reasoned — and the extraction rule is stated for each, because the
first draft of this section got four numbers wrong by leaving the rules
implicit.

- **Rule: a line beginning `` `**Term**` `` in `CONTEXT.md` lines 189–379
  (its §4 Verification, §5 Review, §6 Outcomes — that file's own numbering, not
  `DESIGN.md`'s). Presence in the graph means a `saffron:` IRI local name **or
  an `rdfs:label`** matches, case- and separator-insensitively.** Under that
  rule: **32 definitions, 13 present, 19 absent.** By local name alone, 11 are
  present — `Implementer` and `Lens` are present only as `rdfs:label`s
  (`saffron.ttl:53`, `:56`). The 19 absent: `Gate contract`, `` `tool` ``,
  `Status`, `Blocking / advisory`, `Baseline`, `New failure`, `Pre-existing
  failure`, `Repair`, `No-progress`, `Critic`, `Anchored`, `Verdict`,
  `Adjudication`, `Ratify`, `Approve`, `Trailing accept rate`, `Merge train`,
  `Stacked branch`, `Tree base`.
- **Rule: terms as the repo's own `declared_terms()` counts them**
  (`tests/ontology/test_no_dead_terms.py`), which excludes the ontology IRI:
  **92 terms**, of which **9 carry an `rdfs:comment`**. A tenth comment is on
  the ontology IRI, which that test says is not a term.
- **The graph is the side that has already drifted.** `saffron.ttl:126`'s
  comment says *"CONTEXT.md §6 lists six of these and DESIGN.md §3.3 lists
  nine"*. `CONTEXT.md` now lists nine, and a test asserts it.
- **Declaring one gate on one side alone breaks four checks, not one.**
  Appending `saffron:probe a saffron:CoreGate ; saffron:blockingAt
  saffron:alwaysBlocking .` to `ontology/saffron.ttl` at this branch's HEAD —
  which this branch leaves untouched — and running `tests/ontology/`: **`4 failed, 70 passed`** —
  `test_no_dead_terms::test_no_term_exists_without_a_reader`,
  `test_no_dead_terms::test_the_check_would_catch_a_new_dead_term`,
  `test_shapes::test_the_lifecycle_graph_conforms`, and
  `test_vocabulary_agrees_with_context` (*"Extra items in the right set:
  'probe'"*). Scoped to that last file alone it is `1 failed, 6 passed`; the
  first draft quoted the scoped number as if it were the directory's.
- **`revert` is no longer the instance to measure on, and why that matters.**
  The first draft measured with `saffron:revert`, which `73c2b9f` (PR #112) has
  since declared in all three surfaces by hand. So the defect is not
  hypothetical and was not cheap: closing one gate took three coordinated edits
  by the operator, which is the cost this design removes. A gate name that is
  still undeclared everywhere — `saffron:probe` above — is what any mutant here
  must use; re-running the first draft's `revert` mutant today appends a
  duplicate triple and the test suite stays green.
- **The closed sets are closed in three places, not two.**
  `ontology/shapes/saffron-shapes.ttl:81-90` re-enumerates core gates and gate
  roles as SHACL `sh:in` lists, and `.saffron/gates/shacl.py` is a **blocking**
  repo-defined gate that validates every tracked `.ttl` against them.
- **`saffron/` has two runtime dependencies**, `pydantic` and `pyyaml`.
  `pyproject.toml`: *"pyoxigraph and pyshacl are test-only … nothing under
  `saffron/` imports either (the emitter is a later, conditional task)."*
- **The ledger has no `criteria` table.** It holds `repos, runs, tasks,
  attempts, gate_results, failures, findings`.
- **`saffron/report/render.py` does not exist.** `saffron/report/` holds
  `__init__.py`, `index.py`, `pr_body.py`. (That `SA-0035`–`SA-0039` all write
  to `render.py` is a fact about the plan, not about this repo — the plan says
  so at its line 1352, and none of those specs exist as files.)
- **`ontology/RATIONALE.md` last changed at `71722ec`** (2026-08-26) and is
  **exactly at** the 40-line cap that `SA-0001` names as an acceptance
  criterion.

## 1. The record, and what it permits

The first draft argued that `ontology/RATIONALE.md` should be superseded. That
was the wrong document to argue with, and argument was the wrong method.

**§9 v2.5 and Appendix O govern, and RATIONALE is downstream of them.** §9 says
the emitter is built *"only if `ontology/RATIONALE.md` says the queries are
worth reading"*, records that it says otherwise, and concludes: **"Appendix O's
spike is the only thing that reopens an emitter."** Appendix O adds the sentence
that the first draft walked straight into:

> an ontology that controls execution needs the emitter the RATIONALE said not
> to build. That is not incoherent — it would be built for a reason the RATIONALE
> never tested — but the reason must be the new one, argued on its own evidence,
> **and not the analytics case arriving through a side door**.

Two of the first draft's three grounds — that Q1 and Q3 rest on unmet
conditions, and that a query-and-render layer is a sixth consumer — *are* the
analytics case. Principle 56 names the error exactly: *"the honest response to
'then let's make it operational' is a different experiment, not a re-reading of
the first one."*

So this design splits along what the record already permits.

**Phase A needs no reopening of anything.** §9 names the vocabulary's two
readers as *"the `shacl` gate and the `CONTEXT.md` cross-check"*. Generating the
cross-checked half rather than hand-maintaining it strengthens an existing
reader; it builds no emitter and makes nothing executable. Nothing in §9,
Appendix O or RATIONALE speaks against it, and the defect it closes is measured
above.

**Everything past Phase A goes through Appendix O's spike, unchanged.** Not a
re-reading of `SA-0001`, and not this document's argument. Appendix O specifies
it: build §4.2.1's refusal predicate twice — once as the Python `intake` already
needs, once as shapes over a hand-authored graph of in-flight tasks — and answer

1. Does the shape form state a refusal the Python form leaves implicit?
2. Does either catch a case the other misses, on the same fixtures?
3. What does the graph cost to keep current, per scheduled task?
4. Can the shape form be read by someone who has not read the Python?

**"A yes on 1 and 4 with an acceptable 3 reopens §1.4. Anything else closes
it."** This design does not predict that outcome and does not depend on it.

**What a knowledge-graph goal does and does not change.** It is a genuinely new
reason, of the kind Appendix O contemplates — but Appendix O already anticipated
a new reason and still routed it through the spike. A goal changes what the
spike is *for*, not whether it runs.

## 2. Two authorities, not one

- **The ontology is authoritative for vocabulary** — what the words mean.
- **The ledger is authoritative for facts** — what happened in a run.

Conflating them is what made the first draft read as a bid to replace
`CONTEXT.md`, which RATIONALE had refused on its own evidence. Separated, the
two axes share the ontology and nothing else.

## 3. If the spike reopens it: a derived read model

Conditional on part 1's gate. Recorded now so the spike is run against a
concrete proposal rather than an open question.

The emitter runs **on the control plane**, against `ledger.db`, and never
inside a cell: it reads the audit trail a cell cannot reach and its output is a
control artifact. That is the same rule §2 states for everything that matters.

```
cells ──▶ ledger.db  (SQL, write path, unchanged)
              │
              └─ emitter ──▶ run-record graph (N-Triples) ──▶ SPARQL ──▶ report
ontology/saffron.ttl (vocabulary) ──▶ generator ──▶ CONTEXT.md (+ drift gate)
```

**The ledger stays the system of record.** RATIONALE's case was that SQL serves
the write path, and nothing here disputes it: a read model is additive, so
abandoning it costs one module and no data.

**The emitter needs no new dependency; the *reader* does, and it is not a
wording problem.** N-Triples is line-based, so *writing* it needs no library.
Reading needs an engine, and that is where the cost lands. `pyoxigraph` and
`pyshacl` sit in `[dependency-groups] dev`; `[project] dependencies` is
`pydantic` + `pyyaml`; and `[tool.hatch.build.targets.wheel] packages =
["saffron"]`. So a `saffron/report/render.py` that imports `pyoxigraph` makes it
a **runtime dependency of the shipped package**, not a broken sentence — which
this plan's first global constraint forbids outright. Part 3's own fix does not
avoid it either: loading SPARQL from `ontology/queries/*.rq` still needs an
engine to execute it. Phase C therefore has a real choice to price — promote the
engine to a runtime dependency, ship the renderer outside `saffron/`, or emit
a shape the renderer can read without SPARQL — and it is not a drafting one.

**`test_no_dead_terms` is a weaker mechanism than the first draft claimed.**
`tests/ontology/ontology_paths.py:referenced_terms()` — the function the
dead-term test reads — scans only `ontology/queries/*.rq` and
`ontology/shapes/*.ttl`. A renderer under `saffron/` is **not** scanned, so a
committed `.rq` satisfies the gate whether or not anything calls it — which is
the shape of the thin query this design forbids one sentence later. A rule with
no check behind it, in a document arguing for mechanism over assertion, is a
defect. **Fix: the renderer loads its SPARQL from `ontology/queries/*.rq`**, so
the file that satisfies the dead-term test is the same file the renderer
executes.

## 4. Sequencing — one plan, gated

**Phase A — vocabulary. Unconditional.**
A generator and a drift check over the five sets part 6 names, located by the
bold term already committed above each one and with **no markers**. An earlier
draft of this part proposed marker-delimited regions: `CONTEXT.md` is injected
into every agent prompt (`saffron/agents/context.py`), so a marker comment is
prompt text, and the plan forbids scaffolding outright. The check is a pytest
test on the blocking `tests` gate rather than a new gate executable — the plan
gives the reason, and says which word it uses.
**And the `sh:in` lists in `ontology/shapes/saffron-shapes.ttl`**,
which are the third copy of the same closed sets and are enforced by a blocking
gate — without them the success criterion in part 7 is unreachable. Migrate the
five already-asserted sets first: a faithful generator produces a **zero-line
diff**, which proves it before it is trusted with new content.

**The zero-line diff is reachable, but only because the wrap was measured.**
Three of the five sets wrap across source lines (`CONTEXT.md:201-202`,
`:208-209`, `:331-333`), so a generator that emits each set on one line cannot
reproduce the committed bytes — the first draft's did not. Greedy wrapping the
rewritten span at the committed continuation indent reproduces all five exactly
at **width 82, 83 or 84, and at no other width** (76-92 searched). The plan
takes 83 and **commits** a test over 81-85 asserting exactly that band, because
a number found by search is a fact about the committed file that a later hand
edit can invalidate silently — and a boundary probed once during authoring, then
restored, leaves no witness against that edit.

**Phase A is an operator-side fix plus a gate, not a cell-side repair.**
`CONTEXT.md` is `protected` repo-wide in `.saffron/policy.yaml` and
`ontology/shapes/**` is in `integrity.gate_config`, so after Phase A a cell that
declares a core gate still cannot write the two derived surfaces —
`protected_touch_refusal` (`saffron/scheduler.py:302`) refuses the task at plan
time, by design. What Phase A changes is that the operator's three coordinated
hand edits become one command, and that forgetting it becomes a **failing gate
instead of silent drift**. That is the whole claim; it is worth making, and it
is not "the cell can now fix it".

**Phase B — Appendix O's spike.** Its four questions and its pass condition are
taken unmodified. One premise of it is not: Appendix O says *"§4.2.1's scheduler
is decided in full and unbuilt … Build it twice"*, and it is now built
(`saffron/scheduler.py:302`, `:374`, `:497`, `:572`, `:675`). So only the shape
arm remains to write, and that biases the experiment in a direction the spike
must guard against — a shape arm authored by reading `scheduler.py` inherits the
Python form's blind spots, which are exactly what questions 1 and 2 ask about.
The plan therefore requires the shape arm to be written from §4.2.1's prose.
**This is a gate, not a formality.** Anything other than
yes-on-1-and-4-with-acceptable-3 closes §1.4, and Phases C–E do not happen.

**Phase C — the emitter.** Only if Phase B reopens it. Validated by the existing
SHACL shapes and their fixtures.

**Phase D — the query seam.** Port `Q1`–`Q5` to run against emitted graphs
rather than the hand-authored fixture, compared to the committed
`expected/*.csv`. A second off-ramp: if they are still better in SQL, stop and
keep the graph as an external analytical artifact.

**Phase E — the plan's part 3 on the graph.** `SA-0035` becomes *"the queue's
rows, from the graph"*.

**The deadline, and its honest weight.** `saffron/report/render.py` is unwritten,
so building it graph-first is free today and a rewrite once `SA-0035`/`SA-0036`
land against SQL. That is a real cost of ordering, and it is **not** a reason to
skip Phase B — a deadline is not evidence. If the plan's part 3 must ship first,
it ships on SQL and Phase E becomes a later migration.

**`2026-08-31-operator-visibility.md` is amended, not forked** — and only if
Phase B reopens the question.

## 5. Testing

- **Generator:** the committed `CONTEXT.md` and `saffron-shapes.ttl` equal the
  render. First migration must be a zero-line diff (part 4, Phase A).
- **Emitter (Phase C):** SHACL validation of emitted triples against the
  existing shapes; round trip from a known ledger fixture to the committed
  `expected/*.csv`.
- **Escaping is a security boundary.** Agent-authored findings become RDF
  literals, and a cell is untrusted: a claim containing a quote, a backslash or
  a newline must not forge a triple. Tested, in the same spirit as `SA-0038`'s
  requirement that an event carrying `<script>` render inert.
- **Absent inputs are normal.** Tasks predating `SA-0029` have no
  `events.jsonl`; the emitter projects them from SQL alone.
- **Off the critical path:** a failed emit never fails a task.

## 6. What stays open, and is stated rather than closed

- **`Status` cannot be promoted.** `test_vocabulary_agrees_with_context.py`
  asserts that `pass`/`fail`/`skip`/`error` are deliberately **not** `saffron:`
  terms — EARL's outcomes stand for them, and the test fails if `saffron:pass`
  is added. It is in the 19 above and generating `CONTEXT.md`'s Status line
  means generating from EARL, not from `saffron:`. **It does not block Phase
  A** — `Status` is not one of the five cross-checked sets and nothing generates
  it — so this is settled only before anything tries to.
- **The 56 `_Avoid_` lists stay hand-written, and are essentially
  unenforced.** The `retired-vocabulary` prek hook is a single pattern —
  `(?i)gate[ -]runs?\b` — and `.pre-commit-config.yaml` says why in as many
  words: *"A retired term, not the whole `_Avoid_` list: most of those words are
  ordinary English elsewhere."* It also excludes `docs/superpowers/`, so it does
  not read this document. Phase A does not change that and should not be read as
  claiming to.
- **Whole-system vocabulary stays in `CONTEXT.md`.** What is generated is the
  **five sets `test_vocabulary_agrees_with_context.py` already cross-checks**,
  which is not the same as "the run-record sections": `Risk tier`
  (`CONTEXT.md:179`) is in §3 Scope, outside §4-§6. The cross-check is the rule,
  because a set that is generated but unasserted has no witness.
- **`CLAUDE.md` says something Phase A makes false, and must be amended with
  it.** It reads *"`CONTEXT.md` is authoritative for what the words mean"*.
  After Phase A that holds for the file as a whole but not for those five sets,
  where the vocabulary is authoritative and `CONTEXT.md` is its render. One
  sentence in `CLAUDE.md`, in the same commit as the generator — an
  authoritative file that is quietly no longer authoritative is the defect this
  design exists to remove, not one to introduce.
- **IRI minting is unspecified.** Phase C must mint stable IRIs for ledger rows
  and `prov:qualifiedAssociation` nodes — `lifecycle.ttl` uses named nodes, no
  blanks — stable across re-emits, since `Q4`'s chain depends on it. Where the
  emitted graph lives, and whether it is rebuilt whole, is also unstated.
- **~~A superseded document that does not say so.~~ Settled in this PR.** Part 1
  retracts the supersession — RATIONALE's verdict stands and is downstream of §9
  and Appendix O — so the real gap was narrower: nothing in `RATIONALE.md`
  pointed at Appendix O, the one thing that reopens the question it closed. It
  is a spike verdict, not an ADR, and it is at its 40-line cap
  (`test_vocabulary.py:64` asserts `<= 40`, an `SA-0001` acceptance criterion).
  Raising the cap to 41 would weaken a shipped spec's witness to fit a later
  document in. Unnecessary: `RATIONALE.md:22` **already** carries a revisit
  clause — *"Revisit at v2.5 (§9) only if reconstructibility must be enforced
  continuously"* — and §9 v2.5 is exactly where Appendix O's spike lives. This
  PR edits that existing sentence in place to name the spike, at **zero net
  lines**. No cap change, no `SA-0001` amendment.
- **`SA-0044`'s note** not to declare `saffron:revert` is a workaround PR #112
  discharged and Phase A retires. **Append that it was discharged; do not delete
  it.** `SA-0044` is a completed spec, and deleting the paragraph edits the
  record of why a shipped task was scoped as it was.

## 7. Success criterion

**Phase A:** a new core gate is declared in `ontology/saffron.ttl` alone, and
`CONTEXT.md` **and** `saffron-shapes.ttl` update from it with all four checks
green — `test_vocabulary_agrees_with_context`, both `test_no_dead_terms` cases,
`test_shapes::test_the_lifecycle_graph_conforms` — and the blocking `shacl`
gate passing. (The dead-term cases still require the new term to have a reader;
Phase A does not exempt it, and must not.)

**Phase B:** Appendix O's four questions answered in writing, and §1.4 either
reopened or closed on that evidence.
