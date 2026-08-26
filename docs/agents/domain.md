# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists: it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`docs/adr/`**: read ADRs that touch the area you're about to work in. In multi-context repos, also check `src/<context>/docs/adr/` for context-scoped decisions.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

Single-context repo (most repos):

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

Multi-context repo (presence of `CONTEXT-MAP.md` at the root):

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← system-wide decisions
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← context-specific decisions
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_

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
