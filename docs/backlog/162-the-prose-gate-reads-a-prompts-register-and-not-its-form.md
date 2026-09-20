---
id: 162
title: The prose gate reads a prompt's register and not its instruction form
status: open
tier: 3
filed: 2026-09-17
by_hand: false
specs: []
prs: [317]
commits: []
cites: [§5.3, §5.4]
related: [161]
---

## Problem

PR #313 put `saffron/agents/prompts/` in the `prose` gate's scope. The gate
reads register: sentence length, em-dash, semicolon, filler, hedge, contraction
and perfect tense. Not one of those rules bears on whether an instruction works.

The guidance on writing for an agent names a different axis, and one arm of it
is measured. A trailing prohibition list attached to a shaping failure produced
more of the unwanted content than a positive recipe did. It also did worse than
no guidance at all (`superpowers/writing-skills`, "Match the Form to the
Failure"). Four critic prompts and one extraction turn carried such a list from
PR #310 until this stack replaced it with a recipe.

The gate reads none of that. It also reads past where the strongest instructions
sit. `_prepare` blanks frontmatter, fenced blocks, HTML comments, headings,
table rows, code spans and URLs. A prompt written in the shape that guidance
recommends puts its contract in a table or a fence. A gate-clean prompt is not
therefore a well-formed one.

## Done looks like

A prompt's instruction form is held by something other than review. The narrow
arm is a rule under `.saffron/rules/` that fails a trailing prohibition list in
`saffron/agents/prompts/`. It ships with the mutant that proves it fires, as
every rule there does. The wider arm is a recorded decision that form stays a
review matter, written where a reader of principle 59 finds it. The gate's own
exemptions put the instructions that matter most beyond its reach.

## Record

**Filed 2026-09-17** while rewriting five prompts from a prohibition list into a
recipe. That is the fourth pull request of the stack that opened the gate on
them.
