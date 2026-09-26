"""The end review's two in-cell lenses over one layer, the join lens over
a whole stack, and `run_end_review`, which runs both.

A layer is one task's `stack_layers` row. `layer_fields` reads it, its
task and its run, and `end_review_prompt` fills one of the two core
prompts with the result. `review_layer` runs both lenses, in order,
through `review.run_lens`, the same fresh-session contract every
in-cell lens uses.

`review_stack` walks a batch's layers top down, within a reserve, and
records each lens through `Ledger.record_end_review`. `review_joins`
reads the same batch's whole range once, under ADR 6's rubric.
`run_end_review` runs the join first, so its cost comes out of the
reserve before any layer starts. `layer_cell` is the critic cell a
layer, or the whole stack, is read in.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path

from saffron.agents import context
from saffron.cell.worktree import DIFF_FLAGS
from saffron.events import Event, describe
from saffron.intake import Criterion, Spec
from saffron.ledger import Ledger
from saffron.phases import implement, review
from saffron.repos.mirror import _git

# Lens id, in the order a layer is read, mapped to its own prompt file.
END_LENSES = {
    "spec": "end-review-spec.md",
    "standards": "end-review-standards.md",
}

# The join lens's own ceilings, and the reserve share a stack batch
# holds for the whole end review (`SA-0157` passes each as-is).
LENS_BUDGET_USD = 2.5
LENS_MAX_TURNS = 50
RESERVE_SHARE = 0.25

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

# One batch's layers, highest position first. `review_stack`'s own walk.
_BATCH_LAYERS = """
    SELECT sl.task_key, t.task_id
      FROM stack_layers sl
      JOIN tasks t ON t.record_key = sl.task_key
     WHERE sl.batch_key = ?
     ORDER BY sl.position DESC
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


@dataclass(frozen=True)
class LayerReview:
    """One layer's end review, its own key and the lens reviews collected
    for it. Empty for a layer the reserve did not reach."""

    task_key: str
    reviews: list[review.LensReview]


def _diff(mirror: Path, head: str) -> str:
    """One layer's own commit, `head^..head`, `DIFF_FLAGS` pinned the same
    way every other diff in this repository is. Never `fields.base..head`,
    since a repushed predecessor or a bottom layer's run `base_sha` can
    each differ from the commit PACKAGE built this head on."""
    return _git(mirror, "diff", *DIFF_FLAGS, f"{head}^..{head}", strip=False)


def _review_one_layer(
    ledger: Ledger,
    task_key: str,
    specs: Mapping[str, Spec],
    *,
    mirror: Path,
    open_cell: Callable[[LayerFields], AbstractContextManager[str]],
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
    max_turns: int,
    budget_usd: float,
    agent: Callable[..., implement.AttemptResult],
    emit: Callable[[Event], None],
) -> list[review.LensReview]:
    """One layer's own two lens reviews, or a synthetic error for each.

    A raise reading the layer's fields, its spec or its diff is caught
    here, and so is one opening the cell or running its lenses. Either
    gives every lens in `END_LENSES` a `LensReview` naming the
    exception's type and message, at cost 0. The layer below it is
    still tried.
    """
    try:
        fields = layer_fields(ledger, task_key)
        spec = specs[fields.spec_id]
        diff = _diff(mirror, fields.head)
        with open_cell(fields) as container:
            return review_layer(
                container,
                fields,
                spec_body=spec.body,
                diff=diff,
                acceptance=spec.acceptance,
                touches=spec.touches,
                forbidden=spec.forbidden,
                context_md=context_md,
                claude_md=claude_md,
                prompts_dir=prompts_dir,
                max_turns=max_turns,
                budget_usd=budget_usd,
                agent=agent,
                emit=emit,
            )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        return [
            review.LensReview(lens, cost_usd=0.0, error=error) for lens in END_LENSES
        ]


def review_stack(
    ledger: Ledger,
    batch_key: str,
    reserve_usd: float,
    specs: Mapping[str, Spec],
    *,
    mirror: Path,
    open_cell: Callable[[LayerFields], AbstractContextManager[str]],
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
    max_turns: int,
    budget_usd: float,
    agent: Callable[..., implement.AttemptResult],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> list[LayerReview]:
    """One stack's layers, highest position first, inside one reserve.

    A layer starts only while `reserve_usd`, less every lens cost spent
    so far, covers `budget_usd` times `len(END_LENSES)`. The first layer
    that fails that check, and every layer below it, is recorded
    `not_reached` for each lens with no cell opened. A reached layer's
    findings are recorded unanchored, then one `end_review` fact per
    lens.
    """
    rows = ledger._db.execute(_BATCH_LAYERS, (batch_key,)).fetchall()
    layer_cost = budget_usd * len(END_LENSES)
    spent = 0.0
    results: list[LayerReview] = []
    for row in rows:
        task_key, task_id = row["task_key"], row["task_id"]
        if reserve_usd - spent >= layer_cost:
            reviews = _review_one_layer(
                ledger,
                task_key,
                specs,
                mirror=mirror,
                open_cell=open_cell,
                context_md=context_md,
                claude_md=claude_md,
                prompts_dir=prompts_dir,
                max_turns=max_turns,
                budget_usd=budget_usd,
                agent=agent,
                emit=emit,
            )
            spent += sum(r.cost_usd for r in reviews)
            findings = [f for r in reviews for f in r.findings]
            ledger.record_findings(task_id, findings)
            for r in reviews:
                ledger.record_end_review(
                    task_id,
                    lens=r.lens,
                    status="error" if r.error is not None else "reviewed",
                    cost_usd=r.cost_usd,
                    error=r.error,
                )
        else:
            reviews = []
            for lens in END_LENSES:
                ledger.record_end_review(
                    task_id, lens=lens, status="not_reached", cost_usd=0.0, error=None
                )
        results.append(LayerReview(task_key, reviews))
    return results


# One batch's layer keys, lowest position first. The join lens walks
# bottom to top, the opposite of `review_stack`'s own walk.
_BATCH_LAYER_KEYS = """
    SELECT task_key
      FROM stack_layers
     WHERE batch_key = ?
     ORDER BY position ASC
"""


def _stack_spec_text(layers: Sequence[LayerFields], specs: Mapping[str, Spec]) -> str:
    """One heading per layer, bottom first: its spec id, branch and head,
    then its own spec body, verbatim."""
    parts = []
    for fields in layers:
        heading = (
            f"### {fields.spec_id} — branch `{fields.branch}`, head `{fields.head}`"
        )
        parts.append(f"{heading}\n\n{specs[fields.spec_id].body}")
    return "\n\n".join(parts)


def _join_prompt(
    *,
    base: str,
    head: str,
    diff: str,
    stack_text: str,
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
) -> str:
    """The join lens's own file, filled with the stack's whole range."""
    template = (prompts_dir / "end-review-join.md").read_text()
    return context.build_system_prompt(
        "REVIEW",
        context_md,
        template=template,
        spec=stack_text,
        diff=diff,
        base=base,
        head=head,
        standing_instructions=context.standing_instructions(claude_md),
    )


def review_joins(
    ledger: Ledger,
    batch_key: str,
    reserve_usd: float,
    specs: Mapping[str, Spec],
    *,
    mirror: Path,
    open_cell: Callable[[LayerFields], AbstractContextManager[str]],
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
    max_turns: int,
    budget_usd: float,
    agent: Callable[..., implement.AttemptResult],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> review.LensReview | None:
    """The join lens, over one batch's whole stack (ADR 6, principle 50).

    Reads the batch's layers bottom to top. Fewer than two layers has no
    seam to read, so this returns `None` and records nothing. The lens
    starts only while `reserve_usd` covers `budget_usd`. Short of that it
    records `not_reached` under the top layer's task and returns `None`.
    A raise anywhere before the lens returns, `open_cell`'s included, is
    caught in one place and recorded as an `error` review at cost 0.
    """
    task_keys = [
        row["task_key"]
        for row in ledger._db.execute(_BATCH_LAYER_KEYS, (batch_key,)).fetchall()
    ]
    if len(task_keys) < 2:
        return None
    top_key = task_keys[-1]
    top_row = ledger._db.execute(
        "SELECT task_id FROM tasks WHERE record_key = ?", (top_key,)
    ).fetchone()
    top_task_id = top_row["task_id"]

    if reserve_usd < budget_usd:
        ledger.record_end_review(
            top_task_id, lens="join", status="not_reached", cost_usd=0.0, error=None
        )
        return None

    try:
        layers = [layer_fields(ledger, key) for key in task_keys]
        top_fields, bottom_fields = layers[-1], layers[0]
        diff = _git(
            mirror,
            "diff",
            *DIFF_FLAGS,
            f"{bottom_fields.head}^..{top_fields.head}",
            strip=False,
        )
        system_prompt = _join_prompt(
            base=f"{bottom_fields.head}^",
            head=top_fields.head,
            diff=diff,
            stack_text=_stack_spec_text(layers, specs),
            context_md=context_md,
            claude_md=claude_md,
            prompts_dir=prompts_dir,
        )
        with open_cell(top_fields) as container:
            lens_review = review.run_lens(
                container,
                lens="join",
                system_prompt=system_prompt,
                max_turns=max_turns,
                budget_usd=budget_usd,
                agent=agent,
                spec_id=top_fields.spec_id,
                emit=emit,
            )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        ledger.record_end_review(
            top_task_id, lens="join", status="error", cost_usd=0.0, error=error
        )
        return review.LensReview("join", cost_usd=0.0, error=error)

    ledger.record_findings(top_task_id, lens_review.findings)
    ledger.record_end_review(
        top_task_id,
        lens="join",
        status="error" if lens_review.error is not None else "reviewed",
        cost_usd=lens_review.cost_usd,
        error=lens_review.error,
    )
    return lens_review


@dataclass(frozen=True)
class StackReview:
    """A whole stack's end review: the join lens once, and every layer's
    own two lenses (`LayerReview`, one per layer)."""

    join: review.LensReview | None
    layers: list[LayerReview]


def run_end_review(
    ledger: Ledger,
    batch_key: str,
    reserve_usd: float,
    specs: Mapping[str, Spec],
    *,
    mirror: Path,
    open_cell: Callable[[LayerFields], AbstractContextManager[str]],
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
    max_turns: int,
    budget_usd: float,
    agent: Callable[..., implement.AttemptResult],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> StackReview:
    """One stack's whole end review: the join lens first, the layers on
    what it left (ADR 6, principles 40 and 50).

    Each layer already gets two in-cell lenses of its own. The joins get
    none, so the join lens spends first. `review_stack` then starts a
    layer only while what remains of `reserve_usd` still covers it. An
    errored join's cost counts the same as a clean one's, and a join of
    `None` leaves the reserve whole.
    """
    join = review_joins(
        ledger,
        batch_key,
        reserve_usd,
        specs,
        mirror=mirror,
        open_cell=open_cell,
        context_md=context_md,
        claude_md=claude_md,
        prompts_dir=prompts_dir,
        max_turns=max_turns,
        budget_usd=budget_usd,
        agent=agent,
        emit=emit,
    )
    spent_on_join = join.cost_usd if join is not None else 0.0
    layers = review_stack(
        ledger,
        batch_key,
        reserve_usd - spent_on_join,
        specs,
        mirror=mirror,
        open_cell=open_cell,
        context_md=context_md,
        claude_md=claude_md,
        prompts_dir=prompts_dir,
        max_turns=max_turns,
        budget_usd=budget_usd,
        agent=agent,
        emit=emit,
    )
    return StackReview(join=join, layers=layers)


@contextmanager
def layer_cell(
    fields: LayerFields,
    *,
    repo: Path,
    mirror: Path,
    gates_dir: Path,
    thread_env: Mapping[str, str],
) -> Iterator[str]:
    """A fresh critic cell, seeded at a layer's own head, for the end
    review to read (`review_stack`'s and `review_joins`'s `open_cell`).

    No task's own network is up once the end review runs. So this brings
    a whole cell up through `session.cell_up`, rather than joining one the
    way `critic_cell` does. `cell_up` and `cell_down` are reached through
    their own module, never imported by name, so a caller that replaces
    them there reaches this call too. `cell_down` always runs from a
    `finally`, whether `cell_up` raised, the body raised, or neither did.
    """
    from saffron.cell import runtime, session

    container = f"saffron-endreview-{fields.spec_id}"
    volume = f"saffron-endreview-wt-{fields.spec_id}"
    state = f"saffron-endreview-st-{fields.spec_id}"
    network = "saffron-cells"
    created: set[str] = set()

    runtime.remove_container(container)
    try:
        session.cell_up(
            repo=repo,
            mirror=mirror,
            tree_base=fields.head,
            branch=fields.branch,
            network=network,
            volume=volume,
            state=state,
            container=container,
            gates_dir=gates_dir,
            thread_env=thread_env,
            created=created,
            note=lambda step, detail: print(detail),
        )
        yield container
    finally:
        session.cell_down(
            network=network,
            volume=volume,
            state=state,
            container=container,
            created=created,
            note=lambda step, ok, detail: print(detail),
        )
