"""Per-phase vocabulary injection (DESIGN.md §5.3).

`CONTEXT.md` lives in Saffron, not in any target repo, so an agent inside a
cell cannot follow a reference to it — it is injected. Only the sections the
phase needs: injecting all of it into every prompt of every attempt is real
money for terms the agent has no use for, and a long glossary crowds out the
instructions that actually change behaviour.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from saffron.intake import Criterion

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


def constraints_block(
    touches: list[str], forbidden: list[str], protected: list[str]
) -> str:
    """The path rules the host judges a plan and a diff against, as prompt text.

    `touches` and `forbidden` come from the spec's frontmatter and `protected`
    from `policy.yaml`, so none of the three reaches the prompt through the spec
    body — and `validate_plan` rejects against all three with no model call.

    Returned as a *substituted value*, like the spec body: the caller hands it to
    `build_system_prompt`, which passes it to `.format` as an argument and never
    as a format string (§5.3).
    """
    sections = [
        ("`touches` — the only paths you may change:", touches),
        ("`forbidden` — deny paths declared by this spec:", forbidden),
        ("Protected paths — the repo's global deny paths:", protected),
    ]
    # An empty list is omitted rather than shown as a heading with nothing under
    # it: a heading over nothing reads as withheld and invites an invented list.
    return "\n\n".join(
        lead + "\n\n" + "\n".join(f"- `{path}`" for path in paths)
        for lead, paths in sections
        if paths
    )


def witnesses_block(acceptance: Sequence[Criterion]) -> str:
    """The witnesses `criteria` checks, as prompt text.

    Verbatim, because they are exact strings the implementer has to name its
    tests. Returned as a substituted value, like `constraints_block` — the
    caller hands it to `build_system_prompt`, which passes it to `.format` as an
    argument and never as a format string (§5.3). Empty for a spec declaring
    none: a heading over nothing invites an invented list.
    """
    if not acceptance:
        return ""
    lines = [
        "## The witnesses you are judged against",
        "",
        "Each criterion names a test node id the host checks after you finish, "
        "by reading what the suite collected and what it failed — at the base "
        "commit and at head. Name your tests exactly these strings.",
        "",
        "A witness marked `preserves` must already pass at the base commit and "
        "still pass. Every other witness must **not** pass at the base commit "
        "and must pass when you are done: a test that was already green proves "
        "nothing about this change.",
        "",
    ]
    lines += [
        f"- `{c.witness}`{' *(preserves)*' if c.preserves else ''} — {c.claim}"
        for c in acceptance
    ]
    return "\n".join(lines)


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
