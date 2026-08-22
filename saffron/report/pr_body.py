"""The PR body, rendered from the ledger (DESIGN.md §5.7).

ponytail: f-strings, not Jinja. Not "until the conditionals arrive" — they have
arrived and f-strings still handle them. The dependency is what settles it:
`uv.lock` is in `.saffron/policy.yaml`'s `protected` list, so adding jinja2 is
structurally blocked. Revisit only if a template needs inheritance.
"""

from __future__ import annotations

from saffron.gates.baseline import NewFailure
from saffron.gates.contract import GateResult
from saffron.intake import Spec
from saffron.phases.rebut import RebutResult
from saffron.phases.review import LensReview


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
    reviews: list[LensReview] = (),
    rebut_result: RebutResult | None = None,
    attempts: int = 1,
    spent_usd: float = 0.0,
    test_paths: list[str] = (),
    diff: str = "",
    verified_on: str = "base",
) -> str:
    sections = [
        f"## {spec.id} — {spec.title}",
        "",
        f"`{spec.type}` · risk `{spec.risk}` · +{added}/−{removed}",
        "",
        _criteria(spec),
        _new_failures(new_failures),
        _disagreements(reviews, rebut_result),
        _test_diff(diff, test_paths),
        _verification(verified_on),
        _gate_table(results),
        _findings(reviews),
        _provenance(spec, base_sha, head_sha, transcript_path),
    ]
    return "\n".join(section for section in sections if section) + "\n"


def _cell(value: object) -> str:
    """One table cell. A gate message routinely carries a pipe (a shell echo, a
    ruff rule, an assertion diff), and an unescaped one splits the row."""
    return str(value).replace("|", "\\|").replace("\n", " ")


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

    lines = [
        "### New failures",
        "",
        "| gate | where | code | message |",
        "|---|---|---|---|",
    ]
    for gate, failure in new_failures:
        where = (
            f"{failure.file}:{failure.line}"
            if failure.line is not None
            else failure.file
        )
        lines.append(
            f"| `{_cell(gate)}` | {_cell(where)} | `{_cell(failure.code)}` "
            f"| {_cell(failure.message)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _disagreements(reviews: list[LensReview], rebut_result: RebutResult | None) -> str:
    """§6: disagreements first. Two columns — the implementer's rebuttal and
    the critic's verdict. Never `adjudication`: that is the operator's, and it
    happens in GitHub against the pull request this phase is creating."""
    anchored = [
        f for r in reviews for f in r.findings if f.anchored and f.severity == "blocker"
    ]
    if not anchored:
        return ""
    rebuttals = {}
    verdicts = {}
    if rebut_result is not None:
        rebuttals = {r.finding: r for r in rebut_result.rebuttal.rebuttals}
        verdicts = {
            v.finding: v for lens in rebut_result.verdicts for v in lens.verdicts
        }
    lines = [
        "### Disagreements",
        "",
        "| # | lens | where | claim | implementer | critic |",
        "|---|---|---|---|---|---|",
    ]
    for number, finding in enumerate(anchored, start=1):
        rebuttal = rebuttals.get(number)
        verdict = verdicts.get(number)
        lines.append(
            f"| {number} | `{_cell(finding.lens)}` "
            f"| {_cell(finding.file)}:{finding.line} "
            f"| {_cell(finding.claim)} "
            f"| {_cell(rebuttal.action + ': ' + rebuttal.argument) if rebuttal else '—'} "
            f"| {_cell(verdict.verdict + ': ' + verdict.reason) if verdict else '—'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _findings(reviews: list[LensReview]) -> str:
    rows = [(r.lens, f) for r in reviews for f in r.findings]
    if not rows:
        return ""
    lines = [
        "### Findings",
        "",
        "| lens | severity | where | claim | anchored |",
        "|---|---|---|---|---|",
    ]
    for lens, finding in rows:
        lines.append(
            f"| `{_cell(lens)}` | `{finding.severity}` "
            f"| {_cell(finding.file)}:{finding.line} | {_cell(finding.claim)} "
            f"| {'yes' if finding.anchored else 'no'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _test_diff(diff: str, test_paths: list[str]) -> str:
    """§7's second countermeasure. `test_paths` is the repo's declaration
    (`policy.integrity.test_paths`); core supplies the question, never the
    answer (§2.1)."""
    import fnmatch

    if not diff or not test_paths:
        return ""
    sections, current, keep = [], [], False
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if keep and current:
                sections.append("".join(current))
            path = line.split(" b/", 1)[-1].strip()
            keep = any(fnmatch.fnmatch(path, p) for p in test_paths)
            current = [line]
        else:
            current.append(line)
    if keep and current:
        sections.append("".join(current))
    if not sections:
        return ""
    return (
        "### Test files changed\n\n"
        "Shown separately because a green gate says nothing about a deleted "
        "test (§7).\n\n```diff\n" + "".join(sections) + "```\n"
    )


def _verification(verified_on: str) -> str:
    if verified_on == "base":
        return (
            "Gates ran at `base_sha`, and were not re-run: the base had not "
            "moved, so the packaged tree is byte-identical to the one they saw."
        )
    return (
        "Gates were re-run on the **packaged commit**, because the base moved "
        "after this task started."
    )


def _gate_table(results: list[GateResult]) -> str:
    lines = [
        "### Gates",
        "",
        "| gate | status | duration | summary |",
        "|---|---|---|---|",
    ]
    for result in results:
        # `is not None`: a measured 0 is a measurement, and "—" means the
        # opposite — that nothing was measured.
        duration = (
            f"{result.duration_ms / 1000:.1f}s"
            if result.duration_ms is not None
            else "—"
        )
        lines.append(
            f"| `{_cell(result.gate)}` | `{result.status}` | {duration} "
            f"| {_cell(result.summary)} |"
        )
    lines += [
        "",
        "`skip` means the repo declares no such gate. `error` means the gate "
        "itself broke and is charged to nobody.",
        "",
    ]
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
