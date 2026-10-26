---
id: 11
title: "An avoided phrase is either banned or confusable"
status: accepted
date: 2026-10-24
supersedes: []
superseded_by: []
appendices: [D, F, H, R]
principles: [24, 28, 29, 30, 34, 36, 59]
---

## Context

Most `CONTEXT.md` entries end in an `_Avoid_` line that quotes the phrases
not to use for their term. Measured on 2026-10-24 at `2e1efa2b`:

- `CONTEXT.md` has 134 entries of the form `**Term**:`. Their `_Avoid_` lines
  quote 194 distinct phrases.
- 14 of those phrases are another term's headword, such as "run" under batch
  and "verdict" under suite comparison.
- Of the other 180, the `terms` gate reports 7. It reads them from a
  dictionary kept by hand in `.saffron/gates/prose.py`.
- 49 of the 180 occur in no tracked Markdown file outside `CONTEXT.md`,
  `docs/evidence/` and `docs/appendices/`. That set is wider than the gate's
  own scope, and it leaves out the Python prose the gate also reads.
- Others, such as "session", "check" and "pass", each occur over a thousand
  times in that set with correct meanings. No pattern can report them.
- 21 phrases are avoided under more than one entry. "Pass" is avoided under
  four.

So one `_Avoid_` line holds two kinds of phrase. One kind has no correct use
here, and a pattern can find it. The other is correct in another sense, and
only a reader can judge it. The gate reports few phrases because the line
does not say which kind each phrase is, and no rule says which seven it took.

The lines also vary in form. Some quote a phrase the entry then allows, as
"Regression test" is. Some continue as `_Avoid_ also` in mid-paragraph, and
some sit inside a definition. A reader of quoted text would ban phrases the
entry never meant to ban.

Two documents also disagree about how the lists reach a cell.
`docs/agents/domain.md` says injection enforces them. `saffron/agents/context.py`
strips them from every phase, and only the conventions lens keeps them
(item 162).

## Decision

**Each avoided phrase is banned or confusable.** A banned phrase has no
correct use in the `terms` gate's scope. It stays on an `_Avoid_:` line. A
confusable phrase is correct in another sense. It moves to a `_Confusable_:`
line, which quotes the phrase and names that sense in parentheses. A phrase
that is another term's headword is always confusable.

**A phrase has one kind across the file.** A banned phrase appears on exactly
one entry's `_Avoid_:` line. A confusable phrase appears under every entry
whose term it is confused with, and each names its own sense. A test holds both rules.

**An `_Avoid_:` paragraph holds only quoted banned phrases.** It starts its
own line, wraps like any paragraph, and its quotes are its whole content. The reason a
phrase is banned moves into the entry's body. Any other form of avoided phrase
moves to one of the two lines during triage.

**The `terms` gate reports every banned phrase.** It parses the `_Avoid_:`
lines of `CONTEXT.md`, and the hand-kept dictionary is deleted. Each hit names
the one entry and section that ban the phrase. The gate reports `error` when it
parses no banned phrase, or when an `_Avoid_:` line holds anything but quotes.
Either case means the list it read is not the list the file states. The gate
stays advisory, and making it blocking is a separate decision. A test in the
`tests` gate parses `CONTEXT.md` under the same grammar, so a malformed line
fails `make check` before a cell runs the gate.

Existing hits stay tolerated by §5.4's baseline subtraction, which counts
`terms` failures as it counts any gate's. No phrase waits for the tree to be
clean before the gate takes it.

**The conventions lens judges confusable phrases.** Injection strips both lines
from every phase, and the conventions lens keeps both. A `_Confusable_:` line
still quotes the word to avoid, so item 162's reason reaches it too. The strip pattern in
`context.py` names both markers, so neither line depends on the other's
paragraph break.

**`docs/agents/domain.md` is rewritten to match.** Its "Keeping the model in
sync" section names three mechanisms. The `terms` gate reports banned phrases.
The conventions lens judges confusable ones. The `retired-vocabulary` hook
refuses a term a settled naming decision retired.

## Principles

- **24** departs. Item 162 already departs the same way. Appendix D's lists were read by
  agents before they touched code. A prohibition puts the banned word in the
  prompt, so injection strips the lists, and this ADR keeps that. Each kind
  now states its own reader instead.
- **28** upholds. A parser tuned to one line form would drop the others in
  silence. The grammar is stated, and any other form is an `error`.
- **29** upholds. Seven phrases were reported and 173 were not, and no rule
  said why. The split states the rule, and the gate follows it.
- **30** departs. `domain.md`, `DESIGN.md` §5.5 and `context.py` disagree
  about who reads the lists. This change corrects `domain.md`'s false sentence
  about injection. §5.5 and the `CONTEXT.md` preamble stay stale until
  b-541e9a lands.
- **34** upholds. A parser that found no phrase would print `pass` over a tree
  full of them. The gate reports `error` on an empty list instead.
- **36** upholds. A list missing some phrases is a partial result. The gate
  refuses a line it cannot read whole rather than report from part of it.
- **59** upholds. Widening the list exempts no file, and existing hits ride
  baseline subtraction rather than a cleanup first.

## Consequences

Every `_Avoid_` line is triaged once, entry by entry, into the two kinds. The
49 phrases with no hit in the measured set go first. Backlog items carry the
rest.

The `CONTEXT.md` preamble that calls the `_Avoid_` lists "the load-bearing part"
is rewritten to describe both markers. `DESIGN.md` §5.5 says the conventions
lens reads the `_Avoid_` lists, and it is rewritten to say the lens judges
confusable phrases. The comment on `terms` in `.saffron/policy.yaml` is
rewritten too. All three files are protected, so these edits are host-side.

A `terms` failure's message carries the phrase but no hash of its sentence, as
a `prose` message does. One hit of a phrase removed and another of the same
phrase added in one file cancel in the subtraction.

An `error` aborts the attempt whether the gate is advisory or blocking
(`saffron/gates/suite.py`, `aborted_gates`). So a malformed `_Avoid_:` line
would stop every cell. The `make check` test above is what keeps it out.

The commit-time `prek` hook checks `prose` only. A new banned hit reaches the
gate's result in a cell, and no commit is refused for it.

A confusable phrase reaches only the conventions lens. A misuse in a file no
REVIEW reads, such as a backlog item, is caught by no one.

Rendered spans stay exempt from `terms`. They cover a closed set's first
sentence, and no `_Avoid_` line falls inside one.

The `retired-vocabulary` hook keeps its own pattern list. Its scope covers code
and history, which differs from the `terms` gate's.
