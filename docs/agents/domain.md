# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the glossary. Saffron is single-context; there is no `CONTEXT-MAP.md` and there will not be one.
- **`DESIGN.md`** — authoritative for what the system does (§1–9), an index over `docs/adr/`, and two indexes over `docs/appendices/`, the revision appendices that carry the design record, one record each (`CONTEXT.md` §11). Read the §-numbered section covering the area you're about to work in, and the revision appendix that last touched it. The numbered principles run in one global sequence across those appendices and are cited as "principle 34".
- **`docs/evidence/`** — the primary records, one dated document per live run or spike. When `DESIGN.md` says a revision *found* something, this is where it found it.

**`docs/adr/` holds Saffron's ADRs, one decision per file, cited as "ADR 1".** A revision appendix records what a revision found, and an ADR records where one decision stands now (`CONTEXT.md` §11, ADR 1). Prior art's decision records keep their dashed form, `ADR-NNNN`, and appear where Appendix D cites them.

## File structure

```
/
├── CONTEXT.md                  ← the glossary; its §11 names the decision-record genres
├── DESIGN.md                   ← §-numbered design + the appendix, principle and ADR indexes
├── docs/appendices/            ← revision appendices, one record each; the letter is the id
├── docs/adr/                   ← ADRs, one decision per file; the number is the id
├── ontology/
│   ├── factory.ttl             ← authoritative for CONTEXT.md's six closed sets
│   └── RATIONALE.md            ← a spike verdict, not an ADR
├── docs/evidence/              ← dated primary records, one per run or spike
└── saffron/
```

`CONTEXT.md`'s closed sets — `Terminal state`, `Batch stop reason`, `Severity`, `Risk tier`, `Gate role`, `Core gates` — are **generated**: their backticked spans render from `ontology/factory.ttl` (`ontology/render.py:SETS`). Edit the vocabulary and run `uv run python -m ontology.render`; editing those spans in `CONTEXT.md` gets reverted, and a test fails first. Every other definition in the file is hand-written and edited in place.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag conflicts with the design record

If your output contradicts a principle, a revision appendix, or a `DESIGN.md` section, surface it explicitly rather than silently overriding:

> _Contradicts principle 34 (a green result and an absent result are the same bytes), but worth reopening because…_

A principle is never renumbered and an appendix is never rewritten — a revision that overturns one says so in its own appendix.

## Keeping the model in sync

`prek`'s `retired-vocabulary` hook enforces the only thing a grep can decide: a term
a settled naming decision killed outright, where no context rescues it. It runs on
every commit, which matters because `.saffron/policy.yaml` protects `CONTEXT.md` and
`DESIGN.md` — no cell can edit them, so the two authoritative documents drift only
from host-side edits, which no gate ever sees.

Three kinds of drift stay outside it, and pretending otherwise is the trap:

- Most `_Avoid_` entries are ordinary English elsewhere — `check`, `issue`, `note`,
  `fix`. They are enforced the only way they can be: `DESIGN.md` §5.3 injects
  `CONTEXT.md` per phase.
- A stale *list* has no string to match. §4.6's `prov:Activity` types were written at
  rev 3 and never gained `batch` when the ledger did.
- A definition the schema contradicts is correct English in correct vocabulary.
  `Gate result` read "against one attempt", which excluded every baseline result.

So a domain pass re-reads `CONTEXT.md` §4 and §5 against `DESIGN.md` §4.1's schema and
§4.6's type assignments. All three of the above were found that way, which is
principle 25 — a vocabulary is a test suite for a design.
