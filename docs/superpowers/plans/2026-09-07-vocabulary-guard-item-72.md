# `witness` in the Vocabulary, and a Guard That Can Fire — Implementation Plan

> **For agentic workers:** this plan is executed **by hand, by the operator**. Do
> not drive it through a cell. `CONTEXT.md` is `protected` and
> `ontology/shapes/**` is in `integrity.gate_config`, so a task that edits the
> vocabulary and regenerates its derived surfaces is refused at plan time — the
> point Task 3 writes down. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Declare `witness` in `ontology/factory.ttl`, give `mutant` and
`witness` entries in `CONTEXT.md`, make the guard that should have caught the
omission read the filesystem instead of the vocabulary it is checking, and
record the rule that stops this recurring a fourth time.

**Architecture:** Three commits. The first adds a test that reads
`saffron/gates/core/*.py` off disk and compares it to the declared `CoreGate`
set, watches it fail naming `witness`, then declares `witness` and gives it a
blocking level. The second adds the two glossary entries `CONTEXT.md` is
authoritative for and the vocabulary must not hold. The third writes the
process rule and updates the backlog.

**Tech Stack:** Python 3, pytest, `rdflib`/`pyoxigraph`, SHACL via `pyshacl`,
Turtle. Generator: `uv run python -m ontology.render`.

**Spec:** `docs/BACKLOG.md` item 72 (lines 3999–4067) — "**`witness` and
`mutant` exist in code and in no vocabulary, and the guard for that reads the
vocabulary**". Its **Done looks like** paragraph is the acceptance criteria;
read it before starting. Ordering context: `docs/superpowers/plans/2026-09-07-trusting-the-queue.md`
(item 72 is not one of its tracks — this is a tier-2 item taken ahead of
Track A by operator decision).

## Global Constraints

- `DESIGN.md` section numbers are an API. Cite `§5.4.1` for `witness`; never
  renumber.
- `ontology/factory.ttl` is authoritative for the closed sets. `CONTEXT.md` and
  `ontology/shapes/factory-shapes.ttl` are **generated from it** for those sets
  — run `uv run python -m ontology.render`, never hand-edit a generated span.
- **Every `factory:` term must be referenced by a shape or a query**
  (`tests/ontology/test_no_dead_terms.py`). A class with no reader ships dead
  and that test rejects it. This is why `mutant` gets a `CONTEXT.md` entry and
  **no** vocabulary triple.
- Commit subjects are lowercase `type(scope): what changed`, written as a
  sentence about the defect rather than the file.
- A new test is not trusted until it has been run against the unfixed code.
  Both red-then-green runs in Task 1 are required, not optional.
- Vocabulary is enforced, including `CONTEXT.md`'s `_Avoid_` lists. "Cell" not
  "sandbox", "gate result" not "gate run".
- Branch: `joel/vocabulary-guard-reads-the-vocabulary`.

---

### Task 1: The vocabulary declares `witness`, and a guard that would have said so

**Files:**
- Modify: `tests/ontology/test_vocabulary_agrees_with_code.py:9-11` (docstring), append new test
- Modify: `ontology/factory.ttl:67-83` (comment + the `factory:witness` triple)
- Modify: `ontology/shapes/factory-shapes.ttl:109-126` (two comments, `SizeTierShape` target)
- Regenerated, do not hand-edit: `CONTEXT.md:222-223`, `ontology/shapes/factory-shapes.ttl:90-94`

**Interfaces:**
- Consumes: `ontology_paths.ONTOLOGY`, `ontology_paths.NS`, `ontology_paths.VOCABULARY`; the module-private `_declared(class_name: str) -> set[str]` already defined at `tests/ontology/test_vocabulary_agrees_with_code.py:29`.
- Produces: `factory:witness a factory:CoreGate ; factory:blockingAt factory:blockingWhenElevated` — the triple Task 3's backlog note refers to. No Python symbol other tasks import.

- [ ] **Step 1: Write the failing test**

Append to `tests/ontology/test_vocabulary_agrees_with_code.py`. Note it imports
`ONTOLOGY` — add it to the existing `from ontology_paths import NS, VOCABULARY`
line, making it `from ontology_paths import NS, ONTOLOGY, VOCABULARY`.

```python
# `saffron/gates/core/` has no registry object — `session._suite` imports the
# gates by name — but the directory is a closed set all the same. Treating it as
# one is what this file previously declined to do, and `witness` shipped built
# and undeclared for three pull requests as a result (docs/BACKLOG.md item 72).
CORE_GATES = ONTOLOGY.parent / "saffron" / "gates" / "core"


def _core_gate_modules() -> set[str]:
    return {p.stem for p in CORE_GATES.glob("*.py") if not p.stem.startswith("_")}


def test_every_core_gate_that_exists_is_declared_in_the_vocabulary():
    """A core gate that is built and undeclared is invisible to its own guard.

    Subset, not equality: `secrets` is declared and not yet built, which is the
    ordinary direction — a gate specified before it exists. The direction this
    rejects is the other one.
    """
    built = _core_gate_modules()
    # A glob that finds nothing would satisfy the subset assertion trivially,
    # which is the exact failure mode this test exists to end.
    assert built, (
        f"no core gate modules under {CORE_GATES} — if the package moved, this "
        "assertion is the thing that noticed, and everything below it was "
        "about to pass by measuring nothing"
    )
    undeclared = sorted(built - _declared("CoreGate"))
    assert not undeclared, (
        f"core gates that exist and the vocabulary does not declare: "
        f"{undeclared}. A gate absent from ontology/factory.ttl is absent from "
        "vocabulary.subjects(rdf:type, factory:CoreGate), so test_shapes walks "
        "past it and CoreGateShape's sh:in does not reject it — the guard "
        "CLAUDE.md promises cannot fire for precisely the case it exists to "
        "catch. Declare the gate, give it a blocking level in "
        "factory:CoreGateBlockingShape (or factory:SizeTierShape if a risk tier "
        "moves it), and run `uv run python -m ontology.render`."
    )
```

- [ ] **Step 2: Run the test against the unfixed code**

Run: `uv run pytest tests/ontology/test_vocabulary_agrees_with_code.py::test_every_core_gate_that_exists_is_declared_in_the_vocabulary -v`

Expected: **FAIL**, with `core gates that exist and the vocabulary does not
declare: ['witness']`. This is the real defect, not a mutant — do not proceed
until you have seen `['witness']` in the output. If it passes, the glob is
wrong and you have written another vacuous guard.

- [ ] **Step 3: Declare `witness` in the vocabulary**

In `ontology/factory.ttl`, add one line after the `factory:revert` line
(currently line 83), matching the existing column alignment:

```turtle
factory:witness   a factory:CoreGate ; factory:blockingAt factory:blockingWhenElevated .
```

In the comment block immediately above the gate list (currently lines 67–75),
replace this sentence:

```
# repo's policy: §5.4 fixes them, and `size` at `elevated` is the only one a tier
# moves. A `policy.yaml` that declared otherwise would not be a different repo,
# it would be wrong.
```

with:

```
# repo's policy: §5.4 fixes them, and `size` and `witness` are the two a tier
# moves — both at `elevated`, for the same reason (§5.4.1). A `policy.yaml` that
# declared otherwise would not be a different repo, it would be wrong.
```

- [ ] **Step 4: Run the shapes guard and watch the promised guard finally fire**

Run: `uv run pytest tests/ontology/test_shapes.py -v`

Expected: **FAIL** with `core gates with no declared blocking level:
['witness']`. This is `CLAUDE.md`'s promise working for the first time — that
test computes `declared - covered`, so it was silent only because `witness` was
never in `declared`. Record that you saw it; it is the evidence that fixing the
entry also fixed the guard.

- [ ] **Step 5: Give `witness` its blocking level**

In `ontology/shapes/factory-shapes.ttl`, replace the `SizeTierShape` block and
its comment (currently lines 121–126) with:

```turtle
# The two core gates a risk tier moves, and the correction `SA-0001` forced on
# the design: §5.4 had `size` always-blocking and §5.6 had it becoming blocking
# at `elevated`, and both could not be true (Appendix B). `witness` takes the
# same two levels for the same reason (§5.4.1) — an elevated diff is where a
# claim guarded by nothing hurts most, and `contract.witness_blocking` is the
# function that says so. The shape's name is narrower than its target set; it is
# kept because renaming a shape is a `shacl` gate diff for a cosmetic gain.
factory:SizeTierShape a sh:NodeShape ;
    sh:targetNode factory:size, factory:witness ;
    sh:property [ sh:path factory:blockingAt ; sh:in ( factory:blockingWhenElevated ) ] .
```

Then, in the `CoreGateBlockingShape` comment just above it (currently lines
109–113), replace:

```
# Core gates' blocking levels are core-supplied: §5.4 fixes them, and `size` at
# `elevated` is the only one a tier moves. Stated as constraints rather than left
```

with:

```
# Core gates' blocking levels are core-supplied: §5.4 fixes them, and `size` and
# `witness` are the two a tier moves. Stated as constraints rather than left
```

- [ ] **Step 6: Regenerate the derived surfaces**

Run: `uv run python -m ontology.render`

This rewrites `CONTEXT.md`'s **Core gates** enumeration and `CoreGateShape`'s
`sh:in` list. Inspect the diff with `git diff CONTEXT.md ontology/shapes/` and
confirm **only** those two spans changed and that `witness` appears in both. If
the renderer touched prose, stop — `render_context` locating a wrong span is a
generator bug, and `test_render.py` is where it gets fixed.

- [ ] **Step 7: Amend the docstring that reasoned core gates out of scope**

In `tests/ontology/test_vocabulary_agrees_with_code.py`, replace lines 9–11:

```
Core gates have no Python registry (they are discovered), and the terminal
states the code names fall through to a documented default rather than a raise,
so neither is a closed set on the code side and neither is checked here.
```

with:

```
Core gates were once excluded here on the grounds that they "have no Python
registry (they are discovered)". That was true of the registry and false of the
set: `saffron/gates/core/` is a directory, and reading it is what the last test
below does. The sentence cost three pull requests with `witness` built and
undeclared (docs/BACKLOG.md item 72). The terminal states the code names do
still fall through to a documented default rather than a raise, so they are not
a closed set on the code side and are not checked here.
```

- [ ] **Step 8: Run the full ontology suite and the project check**

Run: `uv run pytest tests/ontology/ -v`
Expected: PASS, including `test_no_dead_terms` (satisfied because both
`CoreGateShape` and `SizeTierShape` now name `factory:witness`),
`test_generated_surfaces_are_current`, and `test_shapes`.

Run: `make check`
Expected: PASS. The `shacl` gate reads the shapes file, so a reflow is a gate
diff — if `shacl` errors with `pyshacl not on PATH` when run through
`LocalExecutor`, that is backlog item 20, not this change.

- [ ] **Step 9: Commit**

```bash
git add tests/ontology/test_vocabulary_agrees_with_code.py ontology/factory.ttl ontology/shapes/factory-shapes.ttl CONTEXT.md
git commit -m "fix(ontology): a core gate absent from the vocabulary was absent from its own guard

\`witness\` was built in SA-0057/SA-0058 and reached neither
\`ontology/factory.ttl\` nor \`CONTEXT.md\`. CLAUDE.md promises a test names the
shape and the file when a new core gate has no blocking level, and
\`test_shapes\` does exactly that — over
\`vocabulary.subjects(rdf:type, factory:CoreGate)\`. A gate missing from the
vocabulary is missing from that set, so the guard passed and the promise was
false for precisely the case it exists to catch.

Declares \`witness\` at \`blockingWhenElevated\`, the level
\`contract.witness_blocking\` already fixes (§5.4.1), and adds it to
\`SizeTierShape\` — the second core gate a tier moves, so three comments
calling \`size\` the only one are amended.

The new test reads \`saffron/gates/core/*.py\` off disk rather than the
vocabulary it is checking, and asserts the glob found something: a closed set
that measures nothing is the failure mode being closed here, not a stricter
version of it. Run against the unfixed tree it names \`['witness']\`.

docs/BACKLOG.md item 72."
```

---

### Task 2: `mutant` and `witness` enter the glossary, and only the glossary

**Files:**
- Modify: `CONTEXT.md` — append two entries at the end of §4 Verification, after the **No-progress** entry (currently ends line 289) and before the `---` separator (currently line 291)

**Interfaces:**
- Consumes: nothing from Task 1 in code; depends on Task 1 only for the claim in the **Witness** entry that `witness` is a core gate.
- Produces: no symbol. `CONTEXT.md` prose other tasks cite.

- [ ] **Step 1: Add the two entries**

`CONTEXT.md` is authoritative for meaning; the vocabulary is authoritative only
for the closed sets it encodes. Neither term gets a `factory:` triple —
`test_no_dead_terms` requires every term to be referenced by a shape or a query,
and there is no shape for either, so a `factory:Mutant` class would ship dead.
Insert after the **No-progress** entry:

```markdown
**Witness**: The test a spec's `acceptance:` entry names as the guard for its
claim. One per criterion, declared by the spec author, never chosen by the agent.
_Avoid_: "the test for it" — a witness is named in frontmatter and checked by
the `witness` gate; an ordinary test that happens to cover the claim is not one.

**Mutant**: A find-and-replace edit a criterion declares against its own subject,
which its witness must fail on (`DESIGN.md` §5.4.1). Applied by the `witness`
gate to ask whether the tests would notice the claim being broken. Withheld from
the implementer's prompt on purpose: a mutant a cell chooses is a mutant chosen
to be killed.
_Avoid_: "mutation testing" for the gate as a whole — the gate runs one declared
edit against one named witness, not a generated suite. _Avoid_ "mutant" for the
mutated tree; that is the worktree, mutated.
```

- [ ] **Step 2: Verify the generator does not own these lines**

Run: `uv run python -m ontology.render && git diff --stat CONTEXT.md`

Expected: **no change** from the render — `render_context` rewrites only the
spans it locates from the six `SETS` markers, and neither new term is one. If
the render deletes or rewrites either entry, stop: that is the
`render_context` span bug `test_render.py:121` describes, and it is a bigger
problem than this task.

- [ ] **Step 3: Run the tests that read `CONTEXT.md`**

Run: `uv run pytest tests/ontology/ tests/ontology/test_vocabulary_agrees_with_context.py -v`
Expected: PASS. `test_vocabulary_agrees_with_context` checks the six closed sets
only, so a new hand-written term is invisible to it — which is the intended
relationship between the two documents, not a gap.

Run: `make check`
Expected: PASS. Watch for the `retired-vocabulary` prek hook; the new prose uses
no retired term, but the hook matches line-by-line (backlog item 57) so a clean
run here is weaker evidence than it looks.

- [ ] **Step 4: Commit**

```bash
git add CONTEXT.md
git commit -m "docs(context): the glossary had no word for the thing a witness guards

\`DESIGN.md\` §5.4.1 introduces **mutant** in bold as a defined term and a module
is named after it, and CONTEXT.md — authoritative for what the words mean — did
not contain either it or \`witness\`. Adds both to §4.

Neither becomes a vocabulary term. \`test_no_dead_terms\` requires every
\`factory:\` term to be read by a shape or a query, and there is no shape for
either, so a \`factory:Mutant\` class would ship dead in exactly the way that
test exists to reject. \`witness\` the *gate* earns its triple because two shapes
name it; \`witness\` the *term* and \`mutant\` earn a definition and nothing more.

docs/BACKLOG.md item 72."
```

---

### Task 3: The rule that stops this recurring, and the backlog told what was decided

**Files:**
- Modify: `docs/agents/issue-tracker.md:8-18` (the `## Conventions` list)
- Modify: `docs/BACKLOG.md:3999-4067` (item 72's status and closing paragraphs)

**Interfaces:**
- Consumes: the triple from Task 1 and the entries from Task 2, both cited in the backlog status line.
- Produces: nothing consumed by later tasks. This is the last task.

- [ ] **Step 1: Add the convention**

Item 72 offers two arms: stop forbidding the vocabulary to the spec that
introduces a term, or make every such spec carry a follow-up filed at writing
time. **The first arm is structurally unavailable**, and this was measured, not
argued: `ontology/factory.ttl` is neither `protected` nor in
`integrity.gate_config`, so a cell may edit it — but the change is only complete
once `ontology.render` rewrites `CONTEXT.md`, which **is** `protected`, and
`protected_touch_refusal` runs at intake (`saffron/cli.py:441`). A spec that
declares the regeneration is refused before a cell starts; one that omits it
fails `scope` on an out-of-scope file, or lands a vocabulary the derived
surfaces disagree with and fails `test_generated_surfaces_are_current`. That
test's own docstring already says so. So the second arm it is.

Append to the `## Conventions` list in `docs/agents/issue-tracker.md`, after the
**Dependencies** bullet:

```markdown
- **A spec that introduces a term files its vocabulary follow-up when it is
  written.** `ontology/` is rightly `forbidden` to the spec implementing against
  a term — a cell inventing vocabulary while implementing against it is how a
  term comes to mean whatever the implementation needed. The defect is that
  nothing then owns the entry: `witness`, `mutant` and the four batch stop
  reasons each reached `main` with the code using a word the glossary did not
  have (`docs/BACKLOG.md` items 65, 72). The follow-up cannot be a spec — a cell
  cannot land it. `ontology/factory.ttl` is editable by a cell, but
  `CONTEXT.md` is `protected` and is generated from it, so the two halves cannot
  move together inside a cell and the task is refused at intake. File it as a
  backlog item marked **by hand**, in the same commit as the spec.
```

- [ ] **Step 2: Update item 72 in the backlog**

Add a status line directly under the `## 72.` heading, matching the form items 1
and 19 use:

```markdown
**Status:** **done**, by hand, on branch `joel/vocabulary-guard-reads-the-vocabulary`.
`factory:witness` is declared at `blockingWhenElevated` and named by
`SizeTierShape`; `mutant` and `witness` are `CONTEXT.md` §4 entries and
deliberately not vocabulary terms (`test_no_dead_terms` would reject a class no
shape reads). The guard now reads `saffron/gates/core/` off disk, and was run
against the unfixed tree, where it names `['witness']`.
```

Then replace the closing **And a decision on the pattern** paragraph with the
decision actually taken:

```markdown
**The pattern, decided.** Of the two arms, the first — stop forbidding the
vocabulary to the spec that introduces the term — is structurally unavailable,
and this is measured rather than argued. `ontology/factory.ttl` is neither
`protected` nor in `integrity.gate_config`, so a cell may edit it; but the
change is not complete until `ontology.render` rewrites `CONTEXT.md`, which is
`protected`, and `protected_touch_refusal` runs at intake
(`saffron/cli.py:441`). A spec declaring the regeneration is refused before a
cell starts; one omitting it fails `scope`, or lands a vocabulary its derived
surfaces contradict. `test_generated_surfaces_are_current`'s docstring already
stated this and nobody had read it back to this item.

So the second arm: `docs/agents/issue-tracker.md` now requires a spec that
introduces a term to file its vocabulary follow-up, marked **by hand**, in the
same commit as the spec.

**One term left undecided, on purpose.** `notes` — item 74's channel, shipped in
`SA-0063`/`SA-0064` — is in no vocabulary either. It is not a gate and
`DESIGN.md` does not bold it as a defined term the way §5.4.1 bolds **mutant**,
so declaring it here would be the vocabulary-invention the `forbidden` lists
exist to prevent. It is a candidate, not an omission; decide it when a document
defines it.
```

- [ ] **Step 3: Verify the backlog's own guards still pass**

Run: `make check`
Expected: PASS. `docs/BACKLOG.md` item numbers are cited from ten comments under
`saffron/` and are an append-only API — confirm you renumbered nothing with
`git diff docs/BACKLOG.md | grep -E '^[-+]## [0-9]+\.'`, which should show only
the `## 72.` line if it shows anything at all.

- [ ] **Step 4: Commit**

```bash
git add docs/agents/issue-tracker.md docs/BACKLOG.md
git commit -m "docs(specs): nothing owned the glossary entry for a term a spec introduced

Three chains have now ended with the code using a word CONTEXT.md does not have
— the four batch stop reasons (item 65), \`mutant\`, \`witness\`. Each spec's
\`forbidden\` list was right; the gap is that forbidding the vocabulary to the
spec that introduces a term left nobody holding the entry.

Item 72 offered two arms. The first is structurally unavailable and this is
measured, not argued: a cell may edit \`ontology/factory.ttl\`, but the change is
incomplete until \`ontology.render\` rewrites \`CONTEXT.md\`, which is
\`protected\` — so the task is refused at intake, fails \`scope\`, or lands a
vocabulary its own derived surfaces contradict. Takes the second arm: the
follow-up is filed when the spec is written, by hand, in the same commit.

Records \`notes\` as an undecided candidate rather than declaring it, since
nothing yet defines it as a term.

Closes docs/BACKLOG.md item 72."
```

---

## Self-Review

**Spec coverage** — item 72's **Done looks like** has four clauses, each with a task:

| Clause | Where |
|---|---|
| `factory:witness a factory:CoreGate` with a blocking level in `SizeTierShape` | Task 1, Steps 3 and 5 |
| that shape's `size`-is-the-only-one comment amended | Task 1, Step 5 (and two more comments found: `factory.ttl:67-75`, `CoreGateBlockingShape`) |
| a `mutant` entry in `CONTEXT.md` | Task 2, Step 1 |
| `uv run python -m ontology.render` re-run, closed-set tests green | Task 1, Steps 6 and 8 |
| "a decision on the pattern, worth more than the two entries" | Task 3 |

Two things the item did not ask for and this plan adds, both flowing from the
item's own framing that the guard is what matters: the disk-reading test
(Task 1, Step 1) and the docstring that reasoned core gates out of scope
(Task 1, Step 7). Without them the entries are fixed and gate nine repeats it.

One thing the item asked for that this plan declines: a `mutant` **vocabulary**
term. The item says "a `mutant` entry in `CONTEXT.md`'s vocabulary", which reads
either way; `test_no_dead_terms` settles it, and Task 2, Step 1 states the
reason in the commit rather than leaving it to a reader.

**Placeholder scan** — no TBDs. Every code step carries the literal text to
insert and every run step names its expected output, including both required
failures (`['witness']`, twice, from two different tests).

**Type consistency** — `_declared` is the existing helper at
`test_vocabulary_agrees_with_code.py:29` and is called, not redefined.
`_core_gate_modules` and `CORE_GATES` are defined once in Task 1, Step 1 and
referenced only there. `ONTOLOGY` is added to an existing import line rather
than a new one. `factory:witness` is spelled identically in the vocabulary
triple, both shape edits and the backlog status.

**Risk noted, not resolved:** line numbers in this plan are from `main` at
`1a167b6`. Task 1's edits shift `factory-shapes.ttl` and `CONTEXT.md`, so use
the quoted text as the anchor, never the line number, from Step 5 onward.
