# Issue tracker: Saffron spec files

Saffron's own work is tracked as spec files, not GitHub issues. A spec is
`.saffron/specs/SA-NNNN-<slug>.md` — the `<slug>` is a short kebab-case phrase.
GitHub issues remain in use only for research/evidence records under
`docs/evidence/`; feature work never goes through the `gh` CLI.

## Conventions

- **One spec per file**: `.saffron/specs/SA-NNNN-<slug>.md`, numbered from the
  highest existing `SA-` id + 1 (e.g. after `SA-0011`, next is `SA-0012`).
- **Frontmatter** (YAML between `---` fences, required): `id`, `title`, `type`,
  `priority`, `depends_on`, `touches`, `forbidden`, `budget_usd`, `max_attempts`,
  `risk`. Do not leave a field out — the parser gates on all of them.
- **Body**: headings `## Context`, `## Problem`, `## Acceptance criteria` (as
  `- [ ]` boxes), `## Out of scope`, `## Notes for the agent`. The acceptance
  criteria are load-bearing: each drives a gate check.
- **Dependencies**: list blocked-by spec ids in `depends_on` (e.g. `[SA-0002, SA-0005]`).
- **A spec that introduces a term files its vocabulary follow-up when it is
  written.** `ontology/` is rightly `forbidden` to the spec implementing against
  a term — a cell inventing vocabulary while implementing against it is how a
  term comes to mean whatever the implementation needed. The defect is that
  nothing then owns the entry: `witness`, `mutant` and the four batch stop
  reasons each reached `main` with the code using a word the glossary did not
  have (`docs/BACKLOG.md` items 65, 72). The follow-up cannot itself be a spec —
  a cell cannot land it. `ontology/saffron.ttl` is editable by a cell, but
  `CONTEXT.md` is `protected` and is generated from it, so the two halves cannot
  move together inside a cell and the task is refused at intake. File it as a
  backlog item marked **by hand**, in the same commit as the spec.

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

  *Pinning what the code determines does work*, and is what `SA-0064` did: a
  field that exists, a parameter that exists, a predicate already written, so
  the natural spelling is close to forced and no disclosure is needed to make
  it match. The verdict then means something.

  So a spec whose change is an **edit** declares a mutant, and one whose change
  is **new** declares a witness alone and accepts that `witness` will report
  `skip`. That is a real limit on the answer item 69 was built to give
  (`docs/BACKLOG.md` item 82) rather than a rule of thumb — say which of the two
  a spec is when it is written, in `## Notes for the agent`, so a reviewer can
  tell an honest `skip` from a missing mutant.

## Driving a spec

```
uv run saffron cell .saffron/specs/SA-NNNN-<slug>.md --repo .
```

## When a skill says "publish to the issue tracker"

Create the next `SA-` spec file under `.saffron/specs/` and record the work in
`docs/BACKLOG.md` / `docs/evidence/` per the conventions there.

## When a skill says "fetch the relevant ticket"

Read the referenced `.saffron/specs/SA-NNNN-<slug>.md` (or the `SA-` id / number
the user passed, resolving to its file).

## Wayfinding operations

Used by `/wayfinder`. The **map** is a spec file; research/one-off records live
in `docs/evidence/` as markdown, each prefixed with the issue/record number. A
work item is a spec with a `depends_on` line. Triage state is read from the
spec's `priority`, `depends_on`, and whether its acceptance criteria are ticked,
not from a label string.
