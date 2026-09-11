---
id: SA-0064
title: the notes channel is built and nothing connects it to a pull request
type: bug
priority: 1
depends_on:
  - SA-0063
touches:
  - saffron/phases/package.py
  - tests/test_package.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - saffron/gates/**
  - saffron/report/pr_body.py
  - saffron/cell/session.py
  - saffron/agents/**
  - saffron/mutation.py
  - saffron/intake.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/replay.py
budget_usd: 8
max_attempts: 3
max_turns: 60
risk: elevated
acceptance:
  - claim: >-
      The production packaging path forwards what the implementer recorded, so
      a task that wrote notes opens a pull request carrying them. A default
      standing in for data the run already computed is worse than an absent
      feature: it is indistinguishable from a task that had nothing to say.
    witness: tests/test_package.py::test_the_packaged_body_carries_the_implementers_notes
    mutant:
      file: saffron/phases/package.py
      find: notes=outcome.notes
      replace: notes=""
  - claim: >-
      A repo-wide protected list is on its own enough to ask an implementer
      for notes, and a test says so. Both halves of that rule shipped with
      only the both-true and both-false cases covered, so the repo-wide half
      was unwitnessed and could be deleted with the suite still green.
    witness: tests/test_session.py::test_a_protected_path_alone_asks_for_notes
  - claim: >-
      A credential an implementer writes into its notes is caught by the same
      scan the rest of the body already goes through. The notes are a new way
      into a channel that leaves the boundary without ever appearing in the
      diff, which is why that scan runs after rendering rather than over the
      parts.
    witness: tests/test_package.py::test_a_credential_in_the_notes_refuses_the_package
  - claim: >-
      A task that recorded nothing packages the body it packages today.
    witness: tests/test_package.py::test_the_pr_body_reports_the_effective_tier_not_the_specs_declared_one
    preserves: true
---

## Context

`SA-0063` built the findings channel item **74** asked for and could not connect
it. Two lenses blocked on the same line independently, the implementer argued
rather than fixed, and both critics confirmed: *"that explains why the gap
wasn't closed, it doesn't close it."*

The cause was the spec, not the agent. `SA-0063` listed `saffron/phases/**` as
`forbidden` while the only production call to the renderer lives there, so the
last hop was unreachable from inside that task. This spec exists to make the
hop, and its `touches` is written from where the call site actually is.

## Problem

An implementer's notes are extracted, validated, hashed and carried on the
outcome. Nothing reads them. The renderer accepts them and renders them
correctly when handed them directly, which every unit test does — and the one
production call that writes the body a pull request is opened with does not
pass them, so the parameter falls back to its default for every real task.

The failure is silent by construction. A task that recorded a finding and a
task that had nothing to say produce byte-identical bodies, so no gate, no
lens and no reader can tell them apart. `SA-0063`'s own pull request is the
worked example: it argued a confirmed blocker about this line, and its body
carries no notes section to have argued it in.

## Out of scope

**Widening what counts as worth asking.** The eligibility rule fires on a
declared `forbidden` list or a repo-wide `protected` one. An implementer can
also be stopped by a path simply outside `touches`, which is neither — and
every spec has a `touches`, so gating on it means asking always. Whether that
is right is a budget question with a real answer and this is not the spec to
decide it in. `saffron/cell/session.py` is `forbidden` here; criterion 2 is a
test of the rule as it stands, not a change to it.

**The renderer.** `saffron/report/pr_body.py` is `forbidden` and correct. If
the body cannot carry the notes without a renderer change, that is a finding to
file — and the channel to file it in is the one this spec connects.

## Notes for the agent

**On this spec's mutants.** Some criteria carry one and you are not told which,
or what they are: `agents/context.py` hands you `witness` and `claim` and never
`mutant`. That is deliberate, and `docs/BACKLOG.md` item **80** records the one
way it leaks.

`SA-0063` was the first spec to declare mutants and it made a mistake worth not
repeating: it pinned literals the spec dictated, then restated them in prose
here, which is the same as handing them over. This spec pins nothing. What it
declares names text the *existing* code already determines, so the natural
spelling is close to forced and no disclosure is needed to make it match. Write
the obvious thing and it will be found.

This spec's first attempt declared a second mutant and never ran: exit 2 at
baseline, because that mutant named text already present at the base commit,
applied there, and the gate then ran a witness that does not exist until you
write it. That is `docs/BACKLOG.md` item **83**, and it is why criterion 2
carries no mutant — not because its claim is worth less.

**Do not paper over criterion 3.** The scan that refuses a package when a
credential reaches the body already runs. What is missing is a test that the
notes path is inside it. If you find it is not, that is the finding, and it is
worth more than a passing witness.
