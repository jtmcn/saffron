"""The morning queue's stack section, one batch and one layer at a time (ADR 7).

`saffron/report/index.py` never imports this module. The queue page is the
older surface, and this one only adds to it.
"""

from __future__ import annotations

import html
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from saffron.end_review import END_LENSES
from saffron.gates.contract import GateResult
from saffron.intake import Spec
from saffron.ledger import Ledger
from saffron.report.index import (
    PLACEHOLDER,
    _atomic_write,
    _existing_queue_rows,
    _link,
    _locked,
    counted_header,
    render_index,
    trailing_accept_rate,
)


@dataclass(frozen=True)
class StackLayer:
    """One `stack_layers` row, with its task's own facts folded in."""

    position: int
    spec_id: str
    title: str | None
    state: str
    spent_usd: float
    budget_usd: float | None
    peak_turns: int | None
    max_turns: int | None
    pr_url: str | None
    size: str | None
    generation: int
    predecessor: str | None
    predecessor_head: str | None
    end_review: str


@dataclass(frozen=True)
class StackView:
    """One batch, as the queue page shows it."""

    batch_id: int
    order: list[tuple[str, str, int | None]]
    spent_usd: float
    budget_usd: float | None
    outcomes: dict[str, int]
    layers: list[StackLayer]


def stack_view(
    ledger: Ledger, batch_id: int, specs: dict[str, Spec]
) -> StackView | None:
    """Build one batch's stack view, or `None` for a batch with no layer.

    A layer is matched to its task by `task_key`, never by spec id.
    """
    layer_rows = ledger.stack_layers(batch_id)
    if not layer_rows:
        return None

    position_by_key = {row["task_key"]: row["position"] for row in layer_rows}
    spec_id_by_key = {row["task_key"]: row["spec_id"] for row in layer_rows}
    review_by_key = _end_review_lenses(ledger.end_reviews(batch_id))

    layers = [
        _build_layer(ledger, row, specs, spec_id_by_key, review_by_key)
        for row in layer_rows
    ]

    order = [
        (task["spec_id"], task["state"], position_by_key.get(task["record_key"]))
        for task in ledger.batch_tasks(batch_id)
    ]
    outcomes: dict[str, int] = {}
    for _, state, _position in order:
        outcomes[state] = outcomes.get(state, 0) + 1

    return StackView(
        batch_id=batch_id,
        order=order,
        spent_usd=ledger.batch_spend(batch_id),
        budget_usd=ledger.batch_budget(batch_id),
        outcomes=outcomes,
        layers=layers,
    )


def _build_layer(
    ledger: Ledger,
    row: sqlite3.Row,
    specs: dict[str, Spec],
    spec_id_by_key: dict[str, str],
    review_by_key: dict[str, dict[str, str]],
) -> StackLayer:
    spec = specs.get(row["spec_id"])
    task_id = row["task_id"]
    peak_turns = _peak_turns(ledger.attempts(task_id))
    predecessor_key = row["predecessor_key"]
    predecessor = (
        spec_id_by_key.get(predecessor_key) if predecessor_key is not None else None
    )
    return StackLayer(
        position=row["position"],
        spec_id=row["spec_id"],
        title=spec.title if spec is not None else None,
        state=row["state"],
        spent_usd=ledger.task_spend(task_id),
        budget_usd=row["budget_usd"],
        peak_turns=peak_turns,
        max_turns=spec.max_turns if spec is not None else None,
        pr_url=row["pr_url"],
        size=_last_size_summary(ledger.task_results(task_id)),
        generation=row["generation"],
        predecessor=predecessor,
        predecessor_head=row["predecessor_head"],
        end_review=_end_review_status(review_by_key.get(row["task_key"], {})),
    )


def _peak_turns(attempts: list[sqlite3.Row]) -> int | None:
    turns = [a["num_turns"] for a in attempts if a["num_turns"] is not None]
    return max(turns) if turns else None


def _last_size_summary(results: list[GateResult]) -> str | None:
    summary = None
    for result in results:
        if result.gate == "size":
            summary = result.summary
    return summary


def _end_review_lenses(rows: list[sqlite3.Row]) -> dict[str, dict[str, str]]:
    by_key: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["lens"] not in END_LENSES:
            continue
        by_key.setdefault(row["task_key"], {})[row["lens"]] = row["status"]
    return by_key


def _end_review_status(lenses: dict[str, str]) -> str:
    if any(lenses.get(lens) == "error" for lens in END_LENSES):
        return "error"
    if all(lenses.get(lens) == "reviewed" for lens in END_LENSES):
        return "reviewed"
    return "not_reached"


def render_stack(view: StackView) -> str:
    """One `<section>` for the batch, then one for each layer in order."""
    budget = _money(view.budget_usd)
    order_items = "\n".join(f"<li>{_order_entry(entry)}</li>" for entry in view.order)
    outcome_items = "\n".join(
        f"<li><code>{html.escape(state)}</code> {count}</li>"
        for state, count in view.outcomes.items()
    )
    batch_section = f"""<section>
<h2>batch {view.batch_id}</h2>
<p>${view.spent_usd:.2f} of {budget}</p>
<ul>
{order_items}
</ul>
<ul>
{outcome_items}
</ul>
</section>"""
    layer_sections = "\n".join(_layer_section(layer) for layer in view.layers)
    return f"{batch_section}\n{layer_sections}\n"


def _order_entry(entry: tuple[str, str, int | None]) -> str:
    spec_id, state, position = entry
    layer = f"layer {position}" if position is not None else "no layer"
    return f"{spec_id} <code>{html.escape(state)}</code> {layer}"


def _layer_section(layer: StackLayer) -> str:
    title = html.escape(layer.title) if layer.title is not None else PLACEHOLDER
    budget = _money(layer.budget_usd)
    turns = (
        f"{layer.peak_turns if layer.peak_turns is not None else PLACEHOLDER} of "
        f"{layer.max_turns if layer.max_turns is not None else PLACEHOLDER} turns"
    )
    size = html.escape(layer.size) if layer.size is not None else PLACEHOLDER
    pr_html = _link(layer.pr_url) if layer.pr_url else PLACEHOLDER
    predecessor = _predecessor_text(layer.predecessor, layer.predecessor_head)
    return f"""<section>
<h2>{layer.spec_id}</h2>
<p><code>{html.escape(layer.state)}</code> layer {layer.position}</p>
<p>{title}</p>
<p>${layer.spent_usd:.2f} of {budget}</p>
<p>{turns}</p>
<p>generation {layer.generation}</p>
<p>{predecessor}</p>
<p>{pr_html}</p>
<p>{size}</p>
<p>end review <code>{layer.end_review}</code></p>
</section>"""


def _money(amount: float | None) -> str:
    return f"${amount:.2f}" if amount is not None else PLACEHOLDER


def _predecessor_text(predecessor: str | None, head: str | None) -> str:
    if predecessor is None:
        return f"on {PLACEHOLDER}"
    return f"on {predecessor} at {head if head is not None else PLACEHOLDER}"


def write_stack_view(
    out_dir: Path, ledger: Ledger, specs: dict[str, Spec]
) -> Path | None:
    """Render the newest batch's stack view into `index.html`, 0 included.

    Writes nothing, and leaves `queue.json` untouched, when the newest
    batch has no `stack_layers` row.
    """
    view = stack_view(ledger, ledger.latest_batch_id(), specs)
    if view is None:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    with _locked(out_dir):
        rows = _existing_queue_rows(out_dir / "queue.json")
        header = counted_header(rows) | {
            "trailing accept rate": trailing_accept_rate(ledger)
        }
        index_html = render_index(rows, header=header, stack=render_stack(view))
        index = out_dir / "index.html"
        _atomic_write(index, index_html)
    return index
