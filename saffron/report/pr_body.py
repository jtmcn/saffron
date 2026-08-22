"""The PR body, rendered from the ledger (DESIGN.md §5.7).

ponytail: f-strings, not Jinja. Not "until the conditionals arrive" — they have
arrived and f-strings still handle them. The dependency is what settles it:
`uv.lock` is in `.saffron/policy.yaml`'s `protected` list, so adding jinja2 is
structurally blocked. Revisit only if a template needs inheritance.
"""

from __future__ import annotations

import fnmatch
import re

from saffron.gates.baseline import NewFailure
from saffron.gates.contract import GateResult
from saffron.intake import Spec
from saffron.phases.rebut import RebutResult
from saffron.phases.review import LensReview, anchored_blockers

# ponytail: covers #N, GH-N, and owner/repo#N — not the full issue-URL form
# (`https://github.com/o/r/issues/12`), which GitHub also closes on. The
# upgrade path is matching that URL shape, not more keyword lookaheads.
_CLOSES = re.compile(
    r"\b(clos(e|es|ed)|fix(es|ed)?|resolv(e|es|ed))\b"
    r"(?=\s*:?\s*(?:[\w.-]+/[\w.-]+)?(?:#|GH-)\d)",
    re.IGNORECASE,
)
_MENTION = re.compile(r"(?<![\w/])@(?=\w)")

# GitHub rejects a pull request body over 65,536 characters. Left uncapped,
# `gh pr create` fails *after* the push and the run exits 2 with no `pr_url`
# and no queue line — the state `_finish` exists to avoid. A margin, because
# the limit is on what GitHub receives, not on what we counted.
_BODY_LIMIT = 64_000
_TRUNCATED = (
    "\n… truncated to fit GitHub's body limit; the full diff is on the branch.\n"
)


def neutralize(text: str) -> str:
    """Defang model-authored text before it reaches GitHub.

    GitHub closes an issue named by `Fixes #12` in a commit body *and* in a pull
    request body, and `@name` notifies a real account. This is the one place a
    cell's output causes an effect outside the boundary without executing (§2).
    Lives here, with the other renderer, because both consumers are renderers.
    """
    return _MENTION.sub(
        "@​", _CLOSES.sub(lambda m: m.group(0)[:1] + "​" + m.group(0)[1:], text)
    )


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
        f"`{spec.type}` · risk `{spec.risk}` · +{added}/−{removed} · "
        f"{attempts} attempt{'' if attempts == 1 else 's'} · ${spent_usd:.2f}",
        "",
        _criteria(spec),
        _new_failures(new_failures),
        _disagreements(reviews, rebut_result),
        None,  # _test_diff, sized last: it is the only unbounded section.
        _verification(verified_on),
        _gate_table(results),
        _findings(reviews),
        _provenance(spec, base_sha, head_sha, transcript_path),
    ]
    slot = sections.index(None)
    spent = sum(len(section) + 1 for section in sections if section)
    sections[slot] = _test_diff(diff, test_paths, budget=_BODY_LIMIT - spent)
    body = "\n".join(section for section in sections if section) + "\n"
    # Last resort: the tables are unbounded too — a lens with a hundred
    # findings outruns the limit on its own. A trimmed body still opens the
    # pull request, and every artifact it names is on disk regardless.
    return body if len(body) <= _BODY_LIMIT else body[:_BODY_LIMIT]


def _cell(value: object) -> str:
    """One table cell, and the body's single choke point for model-authored
    text. A gate message routinely carries a pipe (a shell echo, a ruff rule,
    an assertion diff), and an unescaped one splits the row; a finding's claim
    routinely quotes `@pytest.mark.skip`, which notifies a real GitHub org.

    `spec.title` is human-authored and never routed here. `_test_diff`'s fenced
    block is not either: GitHub parses neither mention nor closing keyword
    inside a code fence, and `_fence` sizes that block's fence to outrun the
    longest backtick run inside it, so no line of the diff can close it early.
    """
    return neutralize(str(value).replace("|", "\\|").replace("\n", " "))


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
    anchored = anchored_blockers(reviews)
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


def _fence(text: str) -> str:
    """A fence longer than the longest backtick run it has to contain.

    Four was not enough. A diff *context* line carries one leading space, and
    CommonMark closes a fence indented up to three — so an unchanged line of
    four backticks in a test file closed the block, and everything after it
    left the fence and stopped being inert: `@org` and `Fixes #N` in the rest
    of the diff would be live on GitHub.
    """
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(4, longest + 1)


def _test_diff(diff: str, test_paths: list[str], *, budget: int = _BODY_LIMIT) -> str:
    """§7's second countermeasure. `test_paths` is the repo's declaration
    (`policy.integrity.test_paths`); core supplies the question, never the
    answer (§2.1).

    `budget` is what is left of `_BODY_LIMIT` after every other section: this
    is the one section that grows with the change, and a body GitHub refuses
    costs the whole pull request rather than the part that did not fit.
    """
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
    head = (
        "### Test files changed\n\n"
        "Shown separately because a green gate says nothing about a deleted "
        "test (§7).\n\n"
    )
    body, note = "".join(sections), ""
    # The fence is measured before the room it has to fit in, and on the whole
    # diff: it is cell-authored and unbounded — a context line of 5,000
    # backticks costs 10,000 of the budget — and a fixed reserve let the
    # section overshoot, which the last-resort clamp then paid for out of the
    # *end* of the body, cutting the gate table and the findings. Truncating
    # can only shorten a backtick run, so this is a safe upper bound.
    # 6: `diff\n` and the closing fence's own newline.
    fence = _fence(body)
    room = budget - len(head) - len(_TRUNCATED) - 2 * len(fence) - 6
    if room < 200:
        return ""
    if len(body) > room:
        # Cut at a line boundary: the closing fence has to start a line.
        body, note = body[:room].rsplit("\n", 1)[0] + "\n", _TRUNCATED
    return f"{head}{fence}diff\n{body}{fence}\n{note}"


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
