"""The end review's two lenses over one layer, the join lens over
a whole stack, and `run_end_review`, which runs both.

A layer is one task's `stack_layers` row. `layer_fields` reads it, its
task and its run, and `end_review_prompt` fills one of the two core
prompts with the result. `review_layer` runs both lenses, in order,
through `review.run_lens`, the same fresh-session contract every
in-cell lens uses.

`branch_heads` builds a resolver that reads a layer the way
`layer_fields` does, but at the branch's own current head. A review
commit lands after PACKAGE (`DESIGN.md` §5.7), so the current head can
sit ahead of it. `run_end_review`, `review_joins` and `review_stack`
take that resolver through a required `resolve` keyword, and never call
`layer_fields` themselves.

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
from dataclasses import dataclass, field
from pathlib import Path

from saffron.agents import context
from saffron.cell.worktree import DIFF_FLAGS
from saffron.events import Event, describe
from saffron.intake import Criterion, Spec
from saffron.ledger import Ledger
from saffron.phases import implement, review
from saffron.phases import package as package_phase
from saffron.repos.mirror import GitError, _git, _run

# Lens id, in the order a layer is read, mapped to its own prompt file.
END_LENSES = {
    "spec": "end-review-spec.md",
    "standards": "end-review-standards.md",
}

# Each end-review lens's ceilings, over the measured in-cell peak of $1.80
# and 41 turns. The reserve is this share of `--budget` (`SA-0157`).
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
    formatted for the prompt (`layer_fields` builds it).

    `diff_base` is the commit a layer's diff starts from.
    `layer_fields` sets it to the pushed head's parent and keeps `base` as
    before. `branch_heads`' resolver sets both to the base
    it chose at the branch's current head (`DESIGN.md` §5.7)."""

    spec_id: str
    branch: str
    pr_url: str
    base: str
    head: str
    known: str
    diff_base: str


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
        diff_base=f"{row['pushed_sha']}^",
    )


_PREDECESSOR_BRANCH = "SELECT branch FROM tasks WHERE record_key = ?"


def _is_ancestor(mirror: Path, ancestor: str, descendant: str) -> bool:
    """Whether `ancestor` is reachable from `descendant`, read by exit
    code rather than through `_git`, which raises on any non-zero exit.
    Exit 0 means yes, exit 1 means no, and any other exit raises."""
    done = _run(
        ["git", "-C", str(mirror), "merge-base", "--is-ancestor", ancestor, descendant]
    )
    if done.returncode == 0:
        return True
    if done.returncode == 1:
        return False
    raise GitError(
        f"git merge-base --is-ancestor {ancestor} {descendant}: {done.stderr.strip()}"
    )


def _merge_base(mirror: Path, a: str, b: str) -> str | None:
    """`git merge-base a b`'s own stdout, or `None` for its exit 1: the
    two share no ancestor at all, read as "no merge base" rather than
    raised. Any other exit is a broken mirror, and still raises."""
    done = _run(["git", "-C", str(mirror), "merge-base", a, b])
    if done.returncode == 1:
        return None
    if done.returncode != 0:
        raise GitError(f"git merge-base {a} {b}: {done.stderr.strip()}")
    return done.stdout.strip()


def _first_contained(
    mirror: Path, candidates: list[str], current_head: str
) -> str | None:
    """The first of `candidates` the current head contains, or `None`."""
    for candidate in candidates:
        if _is_ancestor(mirror, candidate, current_head):
            return candidate
    return None


def _layer_candidates(
    ledger: Ledger,
    mirror: Path,
    row,
    pushed_sha: str,
    current_head: str,
    *,
    fetch: Callable[[str], str],
    fetch_default: Callable[[], str],
) -> tuple[list[str], str | None]:
    """The ordered candidate bases for one layer, and any predecessor
    branch found gone while building them.

    With a predecessor: its current head, then its recorded head. A
    gone predecessor branch offers this layer's own pushed head's
    parent first, then the predecessor's recorded head. With none: the
    merge base of the current head and the default branch, when the
    pushed head's parent is its ancestor and the pushed head is not.
    Otherwise the candidate is the pushed head's parent.
    """
    own_parent = f"{pushed_sha}^"
    if row["predecessor_key"] is None:
        default_head = fetch_default()
        merge_base = _merge_base(mirror, current_head, default_head)
        if (
            merge_base is not None
            and _is_ancestor(mirror, own_parent, merge_base)
            and not _is_ancestor(mirror, pushed_sha, merge_base)
        ):
            return [merge_base], None
        return [own_parent], None

    if row["predecessor_head"] is None:
        raise ValueError(f"{row['branch']!r}'s predecessor was recorded with no head")
    pred_row = ledger._db.execute(
        _PREDECESSOR_BRANCH, (row["predecessor_key"],)
    ).fetchone()
    predecessor_branch = pred_row["branch"] if pred_row is not None else None
    if predecessor_branch is not None:
        try:
            return [fetch(predecessor_branch), row["predecessor_head"]], None
        except package_phase.ParentGone:
            return [own_parent, row["predecessor_head"]], predecessor_branch
    return [own_parent, row["predecessor_head"]], None


def branch_heads(mirror: Path, url: str) -> Callable[[Ledger, str], LayerFields]:
    """A resolver with `layer_fields`'s own signature, reading a layer at
    its current branch head, not the head PACKAGE pushed (`DESIGN.md` §5.7).

    Fetches each branch, and the default branch, caching each success
    once per resolver. A raise is never cached. `_layer_candidates`
    picks the candidate bases. The chosen one becomes `base` and
    `diff_base`, and the fetched head becomes `head`.
    """
    heads: dict[str, str] = {}
    default: list[tuple[str, str]] = []

    def fetch(branch: str) -> str:
        if branch not in heads:
            heads[branch] = package_phase.fetch_parent_branch(mirror, url, branch)
        return heads[branch]

    def fetch_default() -> str:
        if not default:
            default.append(package_phase.fetch_default_branch(mirror, url))
        return default[0][1]

    def resolve(ledger: Ledger, task_key: str) -> LayerFields:
        row = ledger._db.execute(_LAYER_ROW, (task_key,)).fetchone()
        if row is None:
            raise ValueError(f"{task_key!r} names no layer")
        branch = row["branch"]
        pushed_sha = row["pushed_sha"]
        if pushed_sha is None:
            raise ValueError(f"{task_key!r} names a layer with no pushed head")
        try:
            current_head = fetch(branch)
        except package_phase.ParentGone as gone:
            # ParentGone's own text would call this layer's branch a parent.
            raise ValueError(f"layer branch {branch!r} could not be fetched") from gone

        candidates, gone_predecessor_branch = _layer_candidates(
            ledger,
            mirror,
            row,
            pushed_sha,
            current_head,
            fetch=fetch,
            fetch_default=fetch_default,
        )
        base = _first_contained(mirror, candidates, current_head)
        if base is None:
            message = (
                f"{branch!r}'s head {current_head} contains none of {candidates!r}"
            )
            if gone_predecessor_branch is not None:
                message += f", predecessor branch {gone_predecessor_branch!r} is gone"
            raise ValueError(message)

        known = _known_block(ledger.findings(row["task_id"]))
        return LayerFields(
            spec_id=row["spec_id"],
            branch=branch,
            pr_url=row["pr_url"],
            base=base,
            head=current_head,
            known=known,
            diff_base=base,
        )

    return resolve


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


def _diff(mirror: Path, diff_base: str, head: str) -> str:
    """One layer's own range, `diff_base..head`, `DIFF_FLAGS` pinned the
    same way every other diff in this repository is. Never `fields.base..
    head`: a repushed predecessor or a bottom layer's run `base_sha` can
    each differ from the commit this layer's diff must start at."""
    return _git(mirror, "diff", *DIFF_FLAGS, f"{diff_base}..{head}", strip=False)


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
    resolve: Callable[[Ledger, str], LayerFields],
) -> list[review.LensReview]:
    """One layer's own two lens reviews, or a synthetic error for each.

    A raise reading the layer's fields, its spec or its diff is caught
    here, and so is one opening the cell or running its lenses. Either
    gives every lens in `END_LENSES` a `LensReview` naming the
    exception's type and message, at cost 0. The layer below it is
    still tried.
    """
    try:
        fields = resolve(ledger, task_key)
        spec = specs[fields.spec_id]
        diff = _diff(mirror, fields.diff_base, fields.head)
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
    resolve: Callable[[Ledger, str], LayerFields],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> list[LayerReview]:
    """One stack's layers, highest position first, inside one reserve.

    A layer starts only while `reserve_usd`, less every lens cost spent
    so far, covers `budget_usd` times `len(END_LENSES)`. The first layer
    that fails that check, and every layer below it, is recorded
    `not_reached` for each lens with no cell opened. A reached layer's
    findings are recorded unanchored, then one `end_review` fact per
    lens. `resolve` reads each layer's fields, never `layer_fields` directly.
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
                resolve=resolve,
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


def _stack_spec_text(layers: Sequence[LayerFields], specs: Mapping[str, Spec]) -> str:
    """One heading per layer, bottom first: its spec id, branch and head,
    then its own spec body, verbatim."""
    parts = []
    for fields in layers:
        heading = (
            f"### {fields.spec_id}, branch `{fields.branch}`, head `{fields.head}`"
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
    resolve: Callable[[Ledger, str], LayerFields],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> review.LensReview | None:
    """The join lens, over one batch's whole stack (ADR 6, principle 50).

    Reads the batch's layers bottom to top, through `resolve`, never
    `layer_fields` directly. Fewer than two layers has no seam to read, so
    this returns `None` and records nothing. The lens starts only while
    `reserve_usd` covers `budget_usd`. Short of that it records
    `not_reached` under the top layer's task and returns `None`. A raise
    from the diff, the prompt, the cell or the lens is caught in one
    place. It is recorded as an `error` review at cost 0.
    """
    rows = ledger._db.execute(_BATCH_LAYERS, (batch_key,)).fetchall()[::-1]
    if len(rows) < 2:
        return None
    task_keys = [row["task_key"] for row in rows]
    top_task_id = rows[-1]["task_id"]

    if reserve_usd < budget_usd:
        ledger.record_end_review(
            top_task_id, lens="join", status="not_reached", cost_usd=0.0, error=None
        )
        return None

    try:
        layers = [resolve(ledger, key) for key in task_keys]
        top_fields, bottom_fields = layers[-1], layers[0]
        diff = _git(
            mirror,
            "diff",
            *DIFF_FLAGS,
            f"{bottom_fields.diff_base}..{top_fields.head}",
            strip=False,
        )
        system_prompt = _join_prompt(
            base=bottom_fields.diff_base,
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
    """A whole stack's end review: the join lens once, every layer's own
    two lenses (`LayerReview`, one per layer), and `fields`, every layer
    either walk resolved, keyed by its `task_key`. A layer absent from
    `fields` had no resolution."""

    join: review.LensReview | None
    layers: list[LayerReview]
    fields: dict[str, LayerFields] = field(default_factory=dict)


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
    resolve: Callable[[Ledger, str], LayerFields],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> StackReview:
    """One stack's whole end review: the join lens first, the layers on
    what it left (ADR 6, principles 40 and 50).

    `review_stack` starts a layer only while what remains of
    `reserve_usd` still covers it. An errored join's cost counts the
    same as a clean one's, and a join of `None` leaves the reserve
    whole. `resolve` is wrapped once here, so every layer either walk
    resolves through it lands in the returned `StackReview.fields`.
    """
    fields: dict[str, LayerFields] = {}

    def _recording_resolve(ledger_arg: Ledger, task_key: str) -> LayerFields:
        resolved = resolve(ledger_arg, task_key)
        fields[task_key] = resolved
        return resolved

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
        resolve=_recording_resolve,
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
        resolve=_recording_resolve,
        emit=emit,
    )
    return StackReview(join=join, layers=layers, fields=fields)


@contextmanager
def layer_cell(
    fields: LayerFields,
    *,
    repo: Path,
    mirror: Path,
    gates_dir: Path,
    thread_env: Mapping[str, str],
    spec_session: bool = False,
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
    from saffron.cell import proxy, runtime, session

    container = f"saffron-endreview-{fields.spec_id}"
    volume = f"saffron-endreview-wt-{fields.spec_id}"
    state = f"saffron-endreview-st-{fields.spec_id}"
    network = f"saffron-cells-endreview-{fields.spec_id.lower()}"
    proxy_name = proxy.proxy_name(f"endreview-{fields.spec_id}")
    created: set[str] = set()

    runtime.remove_container(container)
    try:
        # A spec session's Bash runs a prior layer's code, so only its
        # cell gets the wrapper's capabilities and the self-check.
        if spec_session:
            session.cell_up(
                repo=repo,
                mirror=mirror,
                tree_base=fields.head,
                branch=fields.branch,
                network=network,
                critic_network=None,
                proxy_name=proxy_name,
                volume=volume,
                state=state,
                container=container,
                gates_dir=gates_dir,
                thread_env=thread_env,
                created=created,
                note=lambda step, detail: print(detail),
                cap_add=implement.UNPRIVILEGED_BASH_CAPS,
            )
            session.assert_bash_is_unprivileged(container)
        else:
            session.cell_up(
                repo=repo,
                mirror=mirror,
                tree_base=fields.head,
                branch=fields.branch,
                network=network,
                critic_network=None,
                proxy_name=proxy_name,
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
            critic_network=None,
            proxy_name=proxy_name,
            volume=volume,
            state=state,
            container=container,
            created=created,
            note=lambda step, ok, detail: print(detail),
        )
