"""Per-phase vocabulary injection (DESIGN.md §5.3).

`CONTEXT.md` lives in Saffron, not in any target repo, so an agent inside a
cell cannot follow a reference to it — it is injected. Only the sections the
phase needs: injecting all of it into every prompt of every attempt is real
money for terms the agent has no use for, and a long glossary crowds out the
instructions that actually change behaviour.
"""

from __future__ import annotations

import re

# CONTEXT.md's own table, in code. REPAIR and REBUT are deliberately absent:
# both resume a session that already carries the implementer's sections, and
# re-injecting pays for the same terms twice.
SECTIONS_BY_PHASE: dict[str, tuple[int, ...]] = {
    "DIAGNOSE": (1, 2, 3, 10),
    "IMPLEMENT": (1, 2, 3, 4, 10),
    "REVIEW": (1, 2, 3, 4, 5, 10),
}

# Optional number group: a heading with no `N. ` is still a boundary (e.g.
# CONTEXT.md's trailing "## Settled naming decisions"), just never selected.
_HEADING = re.compile(r"^## (?:(\d+)\. )?", re.MULTILINE)


def sections_for(
    phase: str, context_md: str, sections: tuple[int, ...] | None = None
) -> str:
    """The numbered sections this phase receives, in document order."""
    wanted = set(sections if sections is not None else SECTIONS_BY_PHASE[phase])
    matches = list(_HEADING.finditer(context_md))
    chunks = []
    for index, match in enumerate(matches):
        number = match.group(1)
        if number is None or int(number) not in wanted:
            continue
        end = (
            matches[index + 1].start() if index + 1 < len(matches) else len(context_md)
        )
        chunks.append(context_md[match.start() : end].rstrip())
    return "\n\n".join(chunks)


def build_system_prompt(
    phase: str, context_md: str, template: str, **values: str
) -> str:
    """Assemble a prompt from a versioned template plus substituted values.

    `str.format` over the template's non-spec parts, never a templating
    engine: the spec body is a *substituted value*, and a spec that happens
    to contain `{{`, backticks, or command syntax must pass through
    untouched. Specs are markdown written by a human about code, so it will
    happen (§5.3).

    A template with no `{spec}` is a bug in a versioned prompt file, not a
    valid prompt with no task — it raises rather than silently dropping the
    spec. A template with `{spec}` more than once gets the same literal spec
    text at every occurrence.
    """
    if "{spec}" not in template:
        raise ValueError(f"prompt template for {phase!r} has no {{spec}} placeholder")
    vocabulary = sections_for(phase, context_md)
    other_values = {k: v for k, v in values.items() if k != "spec"}
    parts = [
        part.format(vocabulary=vocabulary, **other_values)
        for part in template.split("{spec}")
    ]
    return values.get("spec", "").join(parts)
