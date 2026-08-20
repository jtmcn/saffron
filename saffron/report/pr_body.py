"""The PR body, rendered from the ledger (DESIGN.md §5.7).

ponytail: f-strings, not Jinja. v0's body has no findings, no rebuttals and no
disagreement section because none of those have a producer yet. Move to Jinja
when REVIEW lands and the conditionals arrive.
"""

from __future__ import annotations

from saffron.gates.baseline import NewFailure
from saffron.gates.contract import GateResult
from saffron.intake import Spec


def render_pr_body(
    spec: Spec,
    results: list[GateResult],
    new_failures: list[NewFailure],
    *,
    base_sha: str,
    head_sha: str,
    added: int,
    removed: int,
    transcript_path: str,
) -> str:
    sections = [
        f"## {spec.id} — {spec.title}",
        "",
        f"`{spec.type}` · risk `{spec.risk}` · +{added}/−{removed}",
        "",
        _criteria(spec),
        _new_failures(new_failures),
        _gate_table(results),
        _provenance(spec, base_sha, head_sha, transcript_path),
    ]
    return "\n".join(section for section in sections if section) + "\n"


def _criteria(spec: Spec) -> str:
    if not spec.acceptance_criteria:
        return ""
    lines = ["### Acceptance criteria", ""]
    lines += [f"- [ ] {criterion}" for criterion in spec.acceptance_criteria]
    lines.append("")
    return "\n".join(lines)


def _new_failures(new_failures: list[NewFailure]) -> str:
    """New failures lead, because they are the only thing here that is this
    change's problem (DESIGN.md §5.4)."""
    if not new_failures:
        return "### No new failures\n\nEvery failure at head was already present at base.\n"

    lines = ["### New failures", "", "| gate | where | code | message |", "|---|---|---|---|"]
    for gate, failure in new_failures:
        where = f"{failure.file}:{failure.line}" if failure.line else failure.file
        lines.append(f"| `{gate}` | {where} | `{failure.code}` | {failure.message} |")
    lines.append("")
    return "\n".join(lines)


def _gate_table(results: list[GateResult]) -> str:
    lines = ["### Gates", "", "| gate | status | duration | summary |", "|---|---|---|---|"]
    for result in results:
        duration = f"{result.duration_ms / 1000:.1f}s" if result.duration_ms else "—"
        lines.append(
            f"| `{result.gate}` | `{result.status}` | {duration} | {result.summary} |"
        )
    lines += ["", "`skip` means the repo declares no such gate. `error` means the gate "
              "itself broke and is charged to nobody.", ""]
    return "\n".join(lines)


def _provenance(spec: Spec, base_sha: str, head_sha: str, transcript_path: str) -> str:
    touches = ", ".join(f"`{t}`" for t in spec.touches) or "—"
    return (
        "### Provenance\n\n"
        f"- base `{base_sha}`\n"
        f"- head `{head_sha}`\n"
        f"- touches {touches}\n"
        f"- artifacts `{transcript_path}`\n"
    )
