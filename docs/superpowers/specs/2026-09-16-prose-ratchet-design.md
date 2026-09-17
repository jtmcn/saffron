# Prose that cannot get longer

2026-09-16. Designed with the operator after a reading of
[AminBlg/SimpleEnglish](https://github.com/AminBlg/SimpleEnglish) (MIT), an
agent skill that adapts ASD-STE100 Simplified Technical English.

**Status:** designed, not built.

## Why

Saffron's prose is often longer than its content. `CONTEXT.md`, `CLAUDE.md`,
`DESIGN.md` and the specs hold 8,940 sentences. 1,712 of them are over 25
words, and 357 are over 40. The specs are instructions to a cell, and
`CONTEXT.md` sections are injected into cell prompts (§5.3). Length there costs
tokens and invites a wrong reading.

Vocabulary has the same gap. `CONTEXT.md` has 75 `_Avoid_` lines, and one
retired term is enforced. The `retired-vocabulary` hook blocks `gate run`. The
rest reach an agent only when the `spec-reviewer` reads them.

SimpleEnglish supplies the method: a regex pass over Markdown that reports each
hit to the model at edit time. Installing it is wrong for Saffron, for three
measured reasons:

- Its filler list flags Saffron's own terms. Of its hits in scope, `elevated`
  has 66, `harness` 52 and `load-bearing` 28. Its word table maps "elevate" to
  "increase", and `elevated` is a risk tier.
- Its hooks fire on every Markdown edit in every repo. `CONTEXT.md` gets 234
  hits, and a recent spec gets 55. The model would rewrite house style it was
  never asked to touch.
- Its synonym sets are fixed to generic English. They cannot hold a Saffron
  term.

So this design adopts the method and writes Saffron's own rules.

## Measurements

All counts are from commit `1d6a608`, with SimpleEnglish's `ste_lint.py` and
scratch scripts. Code spans and fenced code are stripped first.

| Rule (SimpleEnglish's name) | `CONTEXT.md` + `CLAUDE.md` | `DESIGN.md` | specs | backlog |
|---|---:|---:|---:|---:|
| words | 7,891 | 48,446 | 91,243 | 75,951 |
| sentence over 25 words | 52 | 626 | 1,034 | 985 |
| banned modal | 21 | 162 | 325 | 281 |
| semicolon | 59 | 307 | 327 | 295 |
| em-dash | 131 | 598 | 735 | 971 |
| trailing condition | 24 | 83 | 156 | 96 |
| perfect tense | 4 | 44 | 61 | 72 |
| contraction | 3 | 66 | 8 | 6 |

Three measurements shaped the rules:

- The modals split by use. "would" (282) and "could" (95) mostly carry
  counterfactuals, which the design needs. "should" (63) and "may" (67) are
  more often hedges.
- Saffron's padding is its own. "robust", "seamless" and "crucial" appear zero
  times in scope. "actually" appears 53 times, "precisely" 22, "merely" 14,
  "genuinely" 11 and "quietly" 11.
- The `_Avoid_` lists do not parse into a usable rule. 57 terms carry 171
  quoted phrases. Matching them anywhere gives 2,472 hits, led by "tier" (316),
  "check" (157) and "rule" (147). Matching only where the file also names the
  term still gives 1,297. The lists are written for a reader, and their
  qualifiers ("when you mean…") are not machine-readable.

## Decisions

| Question | Decision |
|---|---|
| Install or rebuild | Rebuild. Reuse SimpleEnglish's code-stripping and sentence splitting, credited. |
| Existing prose | Counts cannot rise, per file and per rule. Nothing is rewritten up front. |
| Rules | Sentence length, hedges, em-dashes and semicolons, a Saffron filler list, perfect tense, trailing condition in spec instructions, contractions. |
| Sentence limit | 25 words everywhere. Separating instructions from description needs a classifier. |
| Scope | Living documents and queued specs. Records stay as written. |
| Vocabulary | A curated, advisory list, held to `CONTEXT.md` by a test. |
| Synonym rotation | Folded into the vocabulary rule. |

## Components

One module, `.saffron/gates/prose.py`, standard library only, in three layers:

1. **Parse.** Strip fenced code, code spans, URLs and table separator rows. Keep
   every original line number. Split into sentences, with each list item as
   its own sentence.
2. **Rules.** Each rule is a function from the parsed text to a list of
   `(line, code, excerpt)`.
3. **Emit.** The same hits print in three shapes, one per caller.

The scope is one constant in `prose.py`, and every caller imports it:

- In: `CONTEXT.md`, `CLAUDE.md`, `DESIGN.md`, `README.md`, `docs/backlog/*.md`,
  `.saffron/specs/*.md`, `.claude/agents/**/*.md`, `.claude/skills/**/*.md`.
- Out: `docs/evidence/`, `.saffron/specs/done/`, `docs/superpowers/`.
- Out: the spans `ontology.render` writes (see "The ontology").

### Two gates

Both are repo-defined gates, declared in `.saffron/policy.yaml`. Each has a
two-line `sh` wrapper, like `structure`.

| Gate | Level | Rules |
|---|---|---|
| `prose` | blocking | the style rules |
| `terms` | advisory | `avoided-term` |

A `prose` failure carries one fixed `message` per rule code. It says what the
rule counts and what to change, and it warns that the line shown can be an
older instance. No excerpt is recorded. The message cannot carry one without
leaving identity, and `repair_prompt` never shows `summary`. `identity` is then
`(gate, file, code, message)`. Baseline
subtraction counts identities (§5.4), so it removes one pre-existing failure
per file and rule. That is the per-file limit, with no change to `saffron/`.

`tool` is the output of running `prose.py --version`, which prints a hash of
the rule set. A changed rule reads as a different tool. The
`gate-tool-must-be-executed` rule already covers `.saffron/gates/*.py`.

### Three callers

1. **The gate suite in a cell,** through the two wrappers.
2. **A prek hook, `hooks/prose_limit.py`.** For each staged file in scope, it
   runs the `prose` rules on the staged version and on the `HEAD` version. It
   fails when any rule's count rose. A file absent at `HEAD` compares against
   zero. Renames follow `git diff --cached -M`. It runs `prose` only.
3. **A PostToolUse hook** in the project `.claude/settings.json`, on Write and
   Edit. It reports new hits for the edited file and exits so that the
   model sees them. It never blocks.

No committed baseline file exists. Parallel pull requests and `gh stack`
layers therefore cannot conflict on one.

## The `prose` rules

| Code | Hit | Exempt |
|---|---|---|
| `sentence-length` | over 25 words, a code span counting as one | headings, for every rule |
| `hedge` | "should", "may", "might" | text in double quotes, for every word rule |
| `em-dash` | `—`, spaced `--`, spaced hyphen between words | en-dash between digits |
| `semicolon` | `;` in prose | |
| `filler` | "actually", "genuinely", "precisely", "merely", "simply", "just", "very", "really", "obviously", "clearly", "essentially", "basically", "quietly", "in fact", "note that" | any protected word (below) |
| `perfect-tense` | "has been", "have been", "had been", and "has" or "have" + -ed | |
| `trailing-condition` | "if" or "when" mid-sentence | everything except list items in spec files |
| `contraction` | "don't", "it's", and the rest | |

"exactly" (129), "itself" (99) and "deliberately" (59) stay off the filler
list. They usually carry meaning, and "deliberately" marks a choice that reads
like a bug.

**Protected words.** At load, `filler` drops every word that is:

- a term defined in bold in `CONTEXT.md`, or
- a member of a closed set in `CONTEXT.md`, read with `render.MEMBER_TOKEN`.

The second source is what covers `elevated`. It is a backticked member, not a
bold definition, and the bare "an elevated task" is the form that reaches the
rules.

**No suppression comment.** Pre-existing text is already tolerated, and new
text can be rewritten. This follows `policy.yaml`'s refusal of suppressions.

## The `terms` gate

`AVOIDED` in `prose.py` maps a phrase to the Saffron term to use:

```python
AVOIDED = {
    "sandbox": ("cell", "§1"),
    "self-heal": ("repair", "§4"),
    "soft fail": ("advisory", "§4"),
    # ...
}
```

- **Entry bar.** A phrase enters only when every current hit in scope is a
  misuse, read by hand. First candidates: "sandbox", "self-heal", "auto-fix",
  "soft fail", "ticket", "work item", "the denylist".
- **`CONTEXT.md` stays authoritative.** A test asserts that each entry is quoted
  on the `_Avoid_` line of the term it maps to. The list can narrow
  `CONTEXT.md`. It cannot extend or contradict it.
- **One rule, `avoided-term`.** The message names the replacement: `sandbox:
  say "cell" (CONTEXT.md §1)`. This is SimpleEnglish's synonym-rotation rule with
  Saffron's own sets, so no second rule exists.
- **"Docker" is not an entry.** It fails the entry bar: some hits in scope
  name the product itself (`DESIGN.md`'s `--cpu` note, a backlog record's
  "Docker socket"), so no exemption list can clear them.
- **Relation to `retired-vocabulary`.** That hook is unchanged. A retired term
  blocks, and an avoided term is advisory. Promotion moves a phrase from
  `AVOIDED` to `RETIRED_TERMS`.

## The ontology

Nothing is added to `factory.ttl`.

- `test_no_dead_terms` requires a reader for every `factory:` term, and a style
  list describes no run. `AVOIDED` and the filler list stay in `prose.py`.
- `prose` and `terms` are repo-defined gates. `factory.ttl` names none, because
  their names are not vocabulary (`CONTEXT.md` §4). `CoreGateBlockingShape` and
  `TaskShape` are unchanged.
- Their results are EARL assertions already, as gate results.

The ontology supplies the protected closed-set words. It reaches `prose.py`
through `CONTEXT.md`, which `ontology.render` writes, so the gate imports no
graph library.

**Rendered spans are exempt.** `ontology.render` rewrites the closed-set spans
in `CONTEXT.md` and the principle index in `DESIGN.md`. The index renders
from the appendices, so its rows repeat text already counted there. `prose.py`
takes those spans from `ontology.render` and `ontology.design_record`, not
from a copy. Long rendered text is fixed at its source: the appendix or
`factory.ttl`.

**Words.** The `terms` gate is advisory, never a "warning" (`CONTEXT.md` §4).
The no-growth comparison in the prek hook gets no new term. The gate side is
baseline subtraction, and nothing in a cell or the run record names the hook.

## Testing

A test is trusted after it fails against the unfixed code or a mutant.

- **Each rule:** one text that hits and one that does not. The misses are the
  measured false positives: "exactly one", a bare "elevated", "fails when the
  cell stops" outside a spec, a quoted avoided word.
- **Protected words:** a fixture adds a defined term and a closed-set member to
  the filler list, and the loaded list drops both.
- **Scope:** each include pattern matches a tracked file, and the exclude list
  is asserted exactly.
- **The prek hook, in a temporary repository:** an added long sentence fails. A
  hit rewritten into another hit passes. A new file with one hit fails. A
  rename keeps its count.
- **The gates:** both emit a valid `GateResult` with an executed `tool`.
  Baseline subtraction over `prose` failures cancels per file and rule.
- **`CONTEXT.md` agreement:** removing an entry's quote from a fixture copy of
  `CONTEXT.md` fails the test.
- **Rendered spans:** a long principle added to an appendix counts once.

## Rollout

Three pull requests, stacked with `gh stack`:

1. `prose.py`, the `prose` gate, the prek hook, and their tests. No prose
   changes.
2. The `terms` gate, `AVOIDED` with each entry read by hand, and the agreement
   test.
3. The PostToolUse hook. Then one line in `CLAUDE.md` Commands, and both gates
   where `DESIGN.md` lists this repo's gates.

## Not in this design

- Rewriting existing prose. Each document is a separate backlog record, in the
  order `docs/backlog/PRIORITY.md` gives.
- A principle for "a style rule limits growth, and never baselines a file". The
  operator added it at rollout step 3, as principle 59 in `DESIGN.md`
  Appendix R.
- Prompts embedded in Python strings under `saffron/agents/`. The parser reads
  Markdown only.
