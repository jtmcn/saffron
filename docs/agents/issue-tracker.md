# Issue tracker: Saffron spec files

Saffron's own work is tracked as spec files, not GitHub issues. A spec is
`.saffron/specs/SA-NNNN-<slug>.md` — the `<slug>` is a short kebab-case phrase.
GitHub issues remain in use only for research/evidence records under
`docs/evidence/`; feature work never goes through the `gh` CLI.

## Conventions

- **One spec per file**: `.saffron/specs/SA-NNNN-<slug>.md`, numbered from the
  highest existing `SA-` id + 1 (e.g. after `SA-0011`, next is `SA-0012`).
- **Frontmatter** (YAML between `---` fences). `id`, `title` and `type` are
  required. The rest default: `priority` 3; `depends_on`, `envelope`, `touches`,
  `forbidden` and `pending_symbols` empty; the ceilings `budget_usd` 12,
  `max_attempts` 4, `max_turns` 60 and `risk` `standard`. An unknown key is
  refused, not ignored.
- **`estimated_lines`** is optional and absent by default. When declared it is
  a strict positive integer, the author's size estimate. `driver.py check`
  prices it against the type's `size` ceiling and blocks at 80% of it. No
  cell gate reads it.
- **`consumes`** is optional and empty by default. Each entry is a
  repo-relative `path` or `path:name` that `depends_on[0]` produces. A spec
  that declares it needs a `depends_on`. `run_task` resolves each entry at
  the tree base before the cell starts and refuses the task on a miss.
- **`pending_symbols`** lists dead code this spec will bring into use, one
  `<path>::<name>` per entry (`saffron/events.py::GateResult`). The `dead` gate
  defers each one while the spec is open, so a parent spec can add what only its
  child calls. A method is named without its class.
- **Acceptance criteria are `acceptance:` in the frontmatter**, one entry per
  criterion: a `claim` (the prose the PR body renders) and a `witness` (a test
  node id), plus `preserves: true` or a `mutant` where the bullets below say so.
  They are load-bearing: `criteria` checks each witness at base and at head, and
  `witness` runs each mutant.

  ```yaml
  acceptance:
    - claim: >-
        A task that wrote notes opens a pull request carrying them.
      witness: tests/test_package.py::test_the_packaged_body_carries_the_implementers_notes
      mutant:
        file: saffron/phases/package.py
        find: notes=outcome.notes
        replace: notes=""
  ```

  A `## Acceptance criteria` checklist in the body still parses — every spec up to
  `SA-0031` used one — but it names no witness, so nothing host-side can check
  it, and a spec declaring both is refused at intake.
- **Body**: headings `## Context`, `## Problem`, `## Out of scope`, `## Notes for
  the agent`.
- **Dependencies**: list blocked-by spec ids in `depends_on` (e.g. `[SA-0002, SA-0005]`).
- **A new spec changes this repo's measured queue.**
  `tests/test_scheduler.py::test_saffron_queue_smoke_reproduces_this_repos_measured_queue`
  pins the exact candidates and refusals the live `.saffron/specs/` produces.
  So the commit that adds a spec updates that list and adds a "Re-measured"
  paragraph to the top of its docstring, and so does the commit that retires one
  to `done/`. Run `make check` before pushing a spec: `SA-0078` reached CI
  without it and failed there. The commit that adds a spec also lists it in its
  origin item's `specs:` — the item its `## Context` cites first.
- **A spec that introduces a term files its vocabulary follow-up when it is
  written.** `ontology/` is rightly `forbidden` to the spec implementing against
  a term — a cell inventing vocabulary while implementing against it is how a
  term comes to mean whatever the implementation needed. The defect is that
  nothing then owns the entry: `witness`, `mutant` and the four batch stop
  reasons each reached `main` with the code using a word the glossary did not
  have (backlog items 65, 72). The follow-up cannot itself be a spec —
  a cell cannot land it. `ontology/factory.ttl` is editable by a cell, but
  `CONTEXT.md` is `protected` and is generated from it, so the two halves cannot
  move together inside a cell and the task is refused at intake. File it as a new
  `docs/backlog/b-xxxxxx-slug.md` record marked `by_hand: true`, in the same commit as the spec.

- **A mutant pins text the existing code already determines; a spec that
  creates new code declares a witness and no mutant.** A `mutant` names exact
  text and applies only where `find` matches exactly once (§5.4.1), so for code
  that does not exist yet the operator cannot know the spelling the agent will
  produce. There are only two ways out and one of them is barred.

  *Dictating the literal does not work.* `SA-0063` mandated an exact heading so
  its mutants would match, and they did — the first real `witness` verdict this
  repo produced. But the body **is** prompt text: `build_system_prompt` passes
  it as the substituted `{spec}` value, so every literal a spec pins is a
  literal the implementer reads, and a test written to kill a known edit is the
  theater `witness` exists to refuse. That verdict is sound evidence the
  mechanism works and no evidence the tests are honest. `intake.py` now refuses
  it at parse: a mutant whose `find` appears in the spec's body or in its own
  claim is a `SpecError` before any money is spent. No reviewer caught
  `SA-0063` — both lenses that read the diff missed it, and it was found only by
  reading the agent's own reasoning as it worked.

  *That check is a tripwire, not a boundary*, and writing to it as though the
  channel were shut is the mistake it invites. A paraphrase evades it entirely —
  "declare a module-scope constant named CEILING, set to 60" discloses the
  spelling without containing it — and the cell can read the spec file directly
  in any case: `.saffron/**` is forbidden to *write*, not to *read*
  (backlog item 80). It catches the literal, which is the shape
  `SA-0063` took; the honest mutant is still the author's job.

  *Pinning what the code determines does work*, and is what `SA-0064` did: a
  field that exists, a parameter that exists, a predicate already written, so
  the natural spelling is close to forced and no disclosure is needed to make
  it match. The verdict then means something.

  So a spec whose change is an **edit** declares a mutant, and one whose change
  is **new** declares a witness alone and accepts that `witness` will report
  `skip`. That is a real limit on the answer item 69 was built to give
  (backlog item 82) rather than a rule of thumb — say which of the two
  a spec is when it is written, in `## Notes for the agent`, so a reviewer can
  tell an honest `skip` from a missing mutant.

  *A mutant's file needs no `touches` entry.* Intake checks only the paths a
  claim names. Listing a file the change must not edit lets `scope` pass an
  edit to it, and makes the spec overlap any other spec's open pull request
  that does edit it (`saffron/scheduler.py`'s overlap refusal). Put such a file
  in `forbidden` instead, as `SA-0079` and `SA-0097` do.

- **A spec names the wrong versions its witnesses must kill, and never asks
  the cell to run them.** Each name is one sentence in `## Notes for the
  agent`, such as "a fold that defaults a missing key to 0". They are for
  the readers who run them. The `witness` gate applies a criterion's declared
  mutant, REVIEW's criterion probes run the wrong versions REVIEW names, and
  the spec loop's Spec seat probes the rest with `driver.py probe`. A cell
  told to run twenty of them spends its turns there. `SA-0123`'s IMPLEMENT and first REPAIR each hit the
  fifteen-minute turn bound that way (backlog item b-2dea1c).

- **A claim over a set names the set, and its witness drives every member.**
  A witness driving one member passes code handling one member. The claim the
  pull request renders then says more than the code does. Where the set is
  open, the claim names what the witness drives, and the notes say what is
  left. The sets a claim quantifies over in passing count too, such as the
  forms of a call or the spellings of a path. Five instances across four
  criteria in `SA-0114` and `SA-0115` carried this defect, and three passed a
  first review (backlog item b-250dc7). The author checks each claim against
  its own witness rather than leaving it to a reader.

- **A witness must fail with the source reverted, not merely be missing at
  base.** `criteria` requires a non-`preserves` witness to be red at base, and a
  test that does not exist yet is red there by construction, so that check is
  easy to pass. `revert` is the strict one. It re-runs a subset with the diff's
  source files reverted and blocks any that still pass: **every test the diff
  adds, united with every declared witness the suite collected at head, minus
  every `preserves` witness** (`saffron/gates/core/revert.py`). Two things
  follow. A test the spec asks the cell to write is judged whether or not a
  criterion declares it, so never ask in prose for a guard that passes at base.
  And a criterion describing behaviour already true at base — "nothing is
  pushed", "the breaker does not fire" — cannot be witnessed honestly as
  written. Reword it until its
  test must observe something only the change produces, or mark it `preserves`
  and name a test that already exists. Watch the other way round too: a witness
  module that imports a name the change adds, at module scope, makes the
  reverted run a collection error, which `revert` reads as `skip`, so the
  anti-theater gate checks nothing. Found reviewing `SA-0066`–`SA-0073`,
  2026-09-11, where it had been missed in five of eight specs.

- **A `preserves` witness names a test that exists now; any other names one
  that does not.** `tests/test_queued_specs.py` holds both on every commit
  (backlog item 152). The first is resolved by collection, so the right name in
  the wrong file or class fails. The second is read at the commit that last
  changed the spec's `witness:` or `preserves:` lines, because the cell that
  implements the spec writes that test. Any `def` of the name in the file
  counts, whatever its class. Whether the witness *fails* with the source
  reverted is still yours to reason out.

- **A declared witness is a bare node id; never ask for a parametrised test.**
  `criteria` matches the id the spec names against the names the suite collected,
  by exact string — it executes nothing and never parses a name
  (`saffron/gates/core/criteria.py`). A `pytest.mark.parametrize` test collects
  as `test_name[case]`, so a bare id is in no such set and the criterion fails
  `witness-not-collected`. Naming one case instead pins the spec to a parameter
  list the cell has not written yet. Two cases in one criterion is a plain `def`
  driving both. `SA-0095`'s re-review offered "parametrise the witness or put
  both cases in it; keep its name" (#306). The cell took the first half, which
  failed `criteria` on attempt 1 and spent attempt 2 on the repair turn
  (backlog item 159).

- **For each criterion, name the plausible wrong implementation its witness
  would pass, before you declare the witness.** If you can name one, the
  witness is not yet a witness: tighten it until that implementation fails
  it. This is the spec review's check 3, turned on your own criteria rather
  than left for the review to run. Both blockers in `SA-0093`–`SA-0095` (#290)
  were this shape, and the rules above had been read and quoted into those
  specs' notes for the agent's witnesses, never applied to the author's
  (backlog item 153).

- **Every sentence that says what the code does now carries a `file:line` you
  read while writing that sentence.** Not earlier in the session, and not a
  backlog record's own words: re-read the file. This is the spec review's
  check 6 moved upstream, and it costs ordering rather than effort. It was
  the largest defect class in #290 — five false sentences about current code,
  one a blocker copied from item 140's record without re-reading
  `session.py`. No gate can hold it: `tests/test_citations.py` catches a
  dangling `§` citation, never one pointing at the wrong section.

- **Run a spec review before a spec's pull request merges.** Its agent
  definition is `.claude/agents/spec-reviewer.md`, with `base:` the head of the spec's own
  branch (the pull request's head, e.g. `origin/<branch>`), since the spec is
  not on `origin/main` yet, and `history: run it yourself`. Dispatch it from a
  checkout of that branch: live `history` reads specs from the working tree,
  and says "no spec declares" for one it cannot see. Fix its verified
  blockers in the same pull
  request. Every defect it finds there is a cell that never has to find it
  (`docs/superpowers/specs/2026-09-14-spec-reviewer-design.md`).

- **A spec edited to answer its review is held to every rule above.** The fix
  is spec text too, written by a reader who has just been thinking about the
  code rather than about `acceptance`, and it gets no second reader unless one
  is arranged — the spec loop's step 1b re-reviews an edited spec before its
  cell. Two shapes cost run 5 a cell and a repair turn (backlog item 159):

  *A test the edit asks for in prose is judged like any declared one*, by the
  rule above. So "it is not a declared criterion, because it passes at base; it
  guards the new call" — #292's own words in `SA-0093` — describes a test that
  failed the attempt: `2 of 5 new test(s) passed without their source`. #293 took both out, and the operator's review added them instead,
  which is where a test that passes at base belongs.

  *A claim widened in review names the witness that reaches the new half, in
  the same edit.* #292 widened `SA-0095`'s criterion 1 to "whenever that suite
  returns, an aborted or drifted suite included" and left the witness under it
  unchanged, so a write on the lens path alone still passed it. The re-review
  at the parent's branch found it (#306). A claim whose witness observes only
  its old half is prose.

## Driving a spec

```
uv run saffron cell .saffron/specs/SA-NNNN-<slug>.md --repo .
```

## When a skill says "publish to the issue tracker"

Create the next `SA-` spec file under `.saffron/specs/` and record the work in
`docs/backlog/` / `docs/evidence/` per the conventions there.

## When a skill says "fetch the relevant ticket"

Read the referenced `.saffron/specs/SA-NNNN-<slug>.md` (or the `SA-` id / number
the user passed, resolving to its file).

## Wayfinding operations

Used by `/wayfinder`. The **map** is a spec file; research/one-off records live
in `docs/evidence/` as markdown, each prefixed with the issue/record number. A
work item is a spec with a `depends_on` line. Triage state is read from the
spec's `priority`, `depends_on`, and whether it has been retired to
`.saffron/specs/done/`, not from a label string.
