<!--
The body a person writes. Saffron's own pull requests never see this file:
PACKAGE renders its body from the ledger and passes `gh pr create --body-file`,
which suppresses the template (DESIGN.md §5.7, `saffron/report/pr_body.py`).

Delete a heading you have nothing to put under it, and delete these comments as
you go. A section left empty is a claim that there was nothing to say, and a
reviewer here reads it that way.
-->

## What

<!--
The defect, not the file — the commit subject is the short form of this sentence
(`type(scope): what changed`). Say what was wrong before, then what each bullet
changes about it.

Cite `DESIGN.md` by section number (§5.4), backlog work by item number
(`docs/BACKLOG.md` item 47), specs by id (SA-0064), and prior pull requests by
number. Use `CONTEXT.md`'s vocabulary exactly, including its _Avoid_ lists.

If this is stacked, say what it sits on and what is left for the layers above.
-->

## Verification

<!--
A measured fact beats a reasoned one, and this section says which it is. Name
the command and its result, never "tests pass":

- `make check`: N passed.
- `uv run pytest -m cell`: N passed — expected when the change reaches
  `saffron/cell/`, and it needs the images CLAUDE.md names.
- `uv run ast-grep test -c .saffron/sgconfig.yml`, when a rule changed.
- `uv run python -m ontology.render` leaves the tree unchanged, when the change
  reaches `ontology/` or a generated span of `CONTEXT.md` / `DESIGN.md`.

A new test is not trusted until it has been run against the unfixed code: say
you watched it fail. For a test guarding a property that is already true, name
the mutant you broke the property with and say the test killed it.
-->

## Not covered

<!--
The residual: what a reviewer would reasonably take as verified and is not. A
stub standing in for a real cell, a path reasoned about rather than measured, a
ceiling a `ponytail:` comment names, a follow-up filed instead of fixed. Stating
it costs a line here and a review round if it is found later.
-->
