"""The end review's two lenses, over one stack-batch layer.

`SA-0153` wires the order and the reserve. This module builds what a
layer needs. A layer is one task's `stack_layers` row. `layer_fields`
reads it, its task and its run, and `end_review_prompt` fills one of the
two core prompts with the result. `review_layer` runs both lenses, in
order, through `review.run_lens`, the same fresh-session contract every
in-cell lens uses.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from saffron.agents import context
from saffron.events import Event, describe
from saffron.intake import Criterion
from saffron.ledger import Ledger
from saffron.phases import implement, review

# Lens id, in the order a layer is read, mapped to its own prompt file.
END_LENSES = {
    "spec": "end-review-spec.md",
    "standards": "end-review-standards.md",
}

_WHITESPACE = re.compile(r"\s+")


def _flatten(text: str) -> str:
    """Every run of whitespace folded to one space. A newline in a claim
    or a rebuttal cannot then break a `known` line in two."""
    return _WHITESPACE.sub(" ", text.strip())


@dataclass(frozen=True)
class LayerFields:
    """What one layer's two end-review prompts are filled from. `known` is one
    line per in-cell finding the layer's own task carries, already
    formatted for the prompt (`layer_fields` builds it)."""

    spec_id: str
    branch: str
    pr_url: str
    base: str
    head: str
    known: str


def _known_line(row) -> str:
    claim = _flatten(row["claim"])
    line = f"- {row['severity']} ({row['lens']}) {row['file']}:{row['line']}: {claim}"
    if row["verdict"]:
        rebuttal = _flatten(row["rebuttal"] or "")
        line += f" [{row['verdict']}: {rebuttal}]"
    return line


def _known_block(rows: Sequence) -> str:
    lines = [_known_line(row) for row in rows if row["lens"] in review.LENSES]
    return "\n".join(lines)


_LAYER_ROW = """
    SELECT sl.predecessor_key, sl.predecessor_head,
           t.task_id, t.spec_id, t.branch, t.pr_url, t.pushed_sha, t.run_id
      FROM stack_layers sl
      JOIN tasks t ON t.record_key = sl.task_key
     WHERE sl.task_key = ?
"""


def layer_fields(ledger: Ledger, task_key: str) -> LayerFields:
    """One layer's fields, from its own `stack_layers` row, task and run.

    `base` is the predecessor's head as the row recorded it, never a
    fresh read of its current `pushed_sha`. A later push to the
    predecessor cannot move a layer already recorded on it. A layer with
    no predecessor takes its own run's `base_sha`. Raises `ValueError`
    for an unknown key, a layer with no pushed head, or one whose named
    predecessor has none.
    """
    row = ledger._db.execute(_LAYER_ROW, (task_key,)).fetchone()
    if row is None:
        raise ValueError(f"{task_key!r} names no layer")
    if row["pushed_sha"] is None:
        raise ValueError(f"{task_key!r} names a layer with no pushed head")
    if row["predecessor_key"] is None:
        base_row = ledger._db.execute(
            "SELECT base_sha FROM runs WHERE run_id = ?", (row["run_id"],)
        ).fetchone()
        base = base_row["base_sha"]
    elif row["predecessor_head"] is None:
        raise ValueError(f"{task_key!r}'s predecessor was recorded with no head")
    else:
        base = row["predecessor_head"]
    known = _known_block(ledger.findings(row["task_id"]))
    return LayerFields(
        spec_id=row["spec_id"],
        branch=row["branch"],
        pr_url=row["pr_url"],
        base=base,
        head=row["pushed_sha"],
        known=known,
    )


def _criteria_lines(acceptance: Sequence[Criterion]) -> str:
    """One line per criterion, holding its claim and its witness node id.

    Not `context.criteria_section`. That drops the witness id and the
    `preserves` flag. The Spec lens needs both, the way `criteria` and
    `witness` do.
    """
    lines = []
    for criterion in acceptance:
        tag = " (preserves)" if criterion.preserves else ""
        lines.append(f"- {criterion.claim} — witness `{criterion.witness}`{tag}")
    return "\n".join(lines)


def end_review_prompt(
    lens: str,
    fields: LayerFields,
    *,
    spec_body: str,
    diff: str,
    acceptance: Sequence[Criterion],
    touches: list[str],
    forbidden: list[str],
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
) -> str:
    """That lens's own file, filled with one layer's fields.

    `{criteria}` and `{constraints}` reach every template. A template
    that names neither drops both, since `str.format` ignores an
    argument its string never references.
    """
    template = (prompts_dir / END_LENSES[lens]).read_text()
    return context.build_system_prompt(
        "REVIEW",
        context_md,
        template=template,
        spec=spec_body,
        diff=diff,
        spec_id=fields.spec_id,
        branch=fields.branch,
        pr=fields.pr_url,
        base=fields.base,
        head=fields.head,
        known=fields.known,
        standing_instructions=context.standing_instructions(claude_md),
        criteria=_criteria_lines(acceptance),
        constraints=context.constraints_block(touches, forbidden, []),
    )


def review_layer(
    container: str,
    fields: LayerFields,
    *,
    spec_body: str,
    diff: str,
    acceptance: Sequence[Criterion],
    touches: list[str],
    forbidden: list[str],
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
    max_turns: int,
    budget_usd: float,
    agent: Callable[..., implement.AttemptResult],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> list[review.LensReview]:
    """One layer, read by the Spec lens and then the Standards lens.

    Each lens is its own fresh session. Each runs whether or not the one
    before it failed, so a Spec-lens crash cannot silence the Standards
    lens too.
    """
    reviews = []
    for lens in END_LENSES:
        system_prompt = end_review_prompt(
            lens,
            fields,
            spec_body=spec_body,
            diff=diff,
            acceptance=acceptance,
            touches=touches,
            forbidden=forbidden,
            context_md=context_md,
            claude_md=claude_md,
            prompts_dir=prompts_dir,
        )
        reviews.append(
            review.run_lens(
                container,
                lens=lens,
                system_prompt=system_prompt,
                max_turns=max_turns,
                budget_usd=budget_usd,
                agent=agent,
                spec_id=fields.spec_id,
                emit=emit,
            )
        )
    return reviews
