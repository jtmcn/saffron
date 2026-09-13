"""The PR body, rendered from the ledger (DESIGN.md §5.7).

ponytail: f-strings, not Jinja. Not "until the conditionals arrive" — they have
arrived and f-strings still handle them. The dependency is what settles it:
`uv.lock` is in `.saffron/policy.yaml`'s `protected` list, so adding jinja2 is
structurally blocked. Revisit only if a template needs inheritance.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Sequence

from saffron.gates.baseline import NewFailure
from saffron.gates.contract import GateResult, split_lines
from saffron.intake import Spec
from saffron.phases.rebut import RebutResult, first_answers
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

# The spec's own statement of the defect, so `## What` answers the question its
# heading asks instead of restating the title. Shaped like `intake`'s
# `_CRITERIA_SECTION`, and deliberately not a parsed `Spec` field: the heading is
# a rendering concern, and a spec that omits it renders exactly as before.
_PROBLEM_SECTION = re.compile(
    r"^##\s*Problem\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE
)
_PROBLEM_LIMIT = 2000

# GitHub rejects a pull request body over 65,536 characters. Left uncapped,
# `gh pr create` fails *after* the push and the run exits 2 with no `pr_url`
# and no queue line — the state `_finish` exists to avoid. A margin, because
# the limit is on what GitHub receives, not on what we counted.
_BODY_LIMIT = 64_000
_TRUNCATED = (
    "\n… truncated to fit GitHub's body limit; the full diff is on the branch.\n"
)
_UNCHECKED = (
    "> **Not mechanically checked.** No `criteria` gate result stands behind these "
    "boxes: an unticked one means nobody looked, not that the criterion failed. A "
    "spec declares witnesses with an `acceptance:` block."
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
    reviews: Sequence[LensReview] = (),
    rebut_result: RebutResult | None = None,
    attempts: int = 1,
    spent_usd: float = 0.0,
    test_paths: Sequence[str] = (),
    diff: str = "",
    verified_on: str = "base",
    effective_risk: str | None = None,
    advisory_gates: Sequence[str] = (),
    notes: str = "",
) -> str:
    """`effective_risk` is what the header reports — `elevated` when the spec
    says so *or* the diff crossed a `policy.elevate_on` path — never bare
    `spec.risk`, which only ever knows the first of those two (§5.6). Left
    unset it falls back to `spec.risk`, so a caller that has not computed the
    effective tier yet still gets the behaviour it always had.

    `advisory_gates` names every gate result in `results` this attempt did not
    hold blocking — `size` at `standard`, a declared `blocking: false` gate at
    any tier — so its row can say so: a `fail` here is not a contradiction of
    a green pull request, and unmarked it would read like one (§5.6).

    `notes` is the implementer's own extraction-turn text, if any (SA-0063,
    `docs/BACKLOG.md` items 71/75) — untrusted cell-authored prose, rendered
    last and clipped like every other such string here. Empty for every task
    that produced none, which is every task before this channel existed."""
    risk = effective_risk if effective_risk is not None else spec.risk
    # The three `##` headings are the spine `.github/pull_request_template.md`
    # asks a person for, in that order, and a test holds the two lists equal. The
    # bodies cannot be one file — this one is rendered from the ledger and its
    # section *order* is load-bearing twice over (see `_notes` and `_test_diff`
    # below), where the template's is guidance someone edits freely — so the
    # shape is coupled by that test and nothing else.
    sections = [
        _what(
            spec,
            risk=risk,
            added=added,
            removed=removed,
            attempts=attempts,
            spent_usd=spent_usd,
        ),
        _criteria(spec, results),
        _verification(verified_on),
        _new_failures(new_failures),
        _disagreements(reviews, rebut_result),
        None,  # _test_diff, sized last: it is the only unbounded section.
        _gate_table(results, advisory_gates),
        _findings(reviews),
        _provenance(spec, base_sha, head_sha, transcript_path),
        _not_covered(spec, results, reviews, advisory_gates=advisory_gates),
        # Last, deliberately: every status, checklist and table above is fully
        # rendered before this ever starts, so cell-authored prose here cannot
        # be mistaken for having moved any of them (SA-0044's reasoning, held
        # unchanged). Falsy when there is nothing to report, so a task with no
        # notes renders a body byte-identical to one from before this existed.
        # It sits under `## Not covered` because that is what it is: the
        # implementer's account of something it saw and was not asked to fix.
        _notes(notes),
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


def _what(
    spec: Spec,
    *,
    risk: str,
    added: int,
    removed: int,
    attempts: int,
    spent_usd: float,
) -> str:
    """The spec, the tier, and what the change cost — under the heading the
    template asks a person for."""
    lines = [
        "## What",
        "",
        f"**{spec.id} — {spec.title}**",
        "",
        f"`{spec.type}` · risk `{risk}` · +{added}/−{removed} · "
        f"{attempts} attempt{'' if attempts == 1 else 's'} · ${spent_usd:.2f}",
        "",
    ]
    if problem := _problem(spec.body):
        lines += [problem, ""]
    return "\n".join(lines)


def _problem(body: str) -> str:
    """The spec's `## Problem` section, verbatim, or nothing.

    Operator-authored and out of a cell's reach by construction: the host parses
    the spec at `base_sha` before the cell exists, and every render reads that
    object rather than the worktree. Neutralized regardless, which `spec.title`
    is not — a title is a phrase and this is prose long enough to carry a
    `Fixes #12` written about the work, which would close an issue on merge that
    nobody meant to close. Saffron's own work is not tracked as issues at all
    (`docs/agents/issue-tracker.md`), so there is no reading of that keyword in a
    spec worth honouring.
    """
    section = _PROBLEM_SECTION.search(body)
    if section is None:
        return ""
    text = section.group(1).strip()
    if not text:
        return ""
    if len(text) > _PROBLEM_LIMIT:
        text = (
            text[:_PROBLEM_LIMIT].rstrip()
            + "\n\n… clipped at the problem ceiling; the spec is the record."
        )
    return neutralize(text)


def _criteria(spec: Spec, results: Sequence[GateResult]) -> str:
    """The checklist, and which kind of unticked each box is.

    Every box was unticked always, for every criterion, with nothing host-side
    that could ever tick one — a checklist that reads as evidence and is not
    (§5.4's `tool` defect, one layer up). A box ticks only from a `criteria`
    gate result; `skip` means nobody looked and must not render as a failure.
    """
    # Last, not first: `_suite` appends the host-constructed result after every
    # declared gate, so a repo declaring its own gate named `criteria` cannot
    # shadow it.
    result = next((r for r in reversed(list(results)) if r.gate == "criteria"), None)
    if spec.acceptance and result is not None and result.status in ("pass", "fail"):
        unmet = {f.file: f for f in result.failures}
        lines = ["### Acceptance criteria", ""]
        for criterion in spec.acceptance:
            failure = unmet.get(criterion.witness)
            box = "- [ ]" if failure else "- [x]"
            why = f": `{failure.code}`" if failure else ""
            lines.append(f"{box} {criterion.claim} — `{criterion.witness}`{why}")
        lines.append("")
        return "\n".join(lines)

    claims = [c.claim for c in spec.acceptance] or spec.acceptance_criteria
    if not claims:
        return ""
    return "\n".join(
        ["### Acceptance criteria", "", _UNCHECKED, ""]
        + [f"- [ ] {claim}" for claim in claims]
        + [""]
    )


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


def _disagreements(
    reviews: Sequence[LensReview], rebut_result: RebutResult | None
) -> str:
    """§6: disagreements first. Two columns — the implementer's rebuttal and
    the critic's verdict. Never `adjudication`: that is the operator's, and it
    happens in GitHub against the pull request this phase is creating."""
    anchored = anchored_blockers(reviews)
    if not anchored:
        return ""
    rebuttals = {}
    verdicts = {}
    if rebut_result is not None:
        rebuttals = first_answers(rebut_result.rebuttal)
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


def _findings(reviews: Sequence[LensReview]) -> str:
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


def _test_diff(
    diff: str, test_paths: Sequence[str], *, budget: int = _BODY_LIMIT
) -> str:
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
    # `split_lines`, not `splitlines()`: the loop recomputes the stanza
    # boundary from any line starting a header, and one raw separator byte in a
    # `+` line shattered it into a fragment that could be one — ending the
    # section early and hiding the deletions below it from the human reader.
    for line in split_lines(diff):
        line += "\n"
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
    """What the sections below were measured on. The sentence is unchanged; it
    had no heading of its own until the spine gave it one."""
    if verified_on == "base":
        return (
            "## Verification\n\n"
            "Gates ran at `base_sha`, and were not re-run: the base had not "
            "moved, so the packaged tree is byte-identical to the one they saw.\n"
        )
    return (
        "## Verification\n\n"
        "Gates were re-run on the **packaged commit**, because the base moved "
        "after this task started.\n"
    )


def _gate_table(results: list[GateResult], advisory_gates: Sequence[str] = ()) -> str:
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
        # In the summary column, not between `gate` and `status`: those two
        # cells are what a reader — and `test_the_gate_table_holds_every_
        # result_with_its_status_in_backticks` — matches on verbatim, and an
        # advisory `fail` still belongs beside its own gate and status.
        summary = result.summary
        # `fail` only: the marker exists to explain a red row on a green pull
        # request, and `size` is advisory on every standard-tier attempt — so
        # keying on the gate alone tags its `pass` rows too.
        if result.gate in advisory_gates and result.status == "fail":
            summary = f"(advisory) {summary}" if summary else "(advisory)"
        lines.append(
            f"| `{_cell(result.gate)}` | `{result.status}` | {duration} "
            f"| {_cell(summary)} |"
        )
    lines += [
        "",
        "`skip` means the repo declares no such gate. `error` means the gate "
        "itself broke and is charged to nobody.",
        "",
    ]
    return "\n".join(lines)


def _not_covered(
    spec: Spec,
    results: Sequence[GateResult],
    reviews: Sequence[LensReview],
    *,
    advisory_gates: Sequence[str] = (),
) -> str:
    """What this body does not stand behind, collected.

    Every line is derivable from a section above — a `skip` row, an `(advisory)`
    mark, the checklist's blockquote, an `anchored: no` cell — and each is one
    cell of a wide table a reviewer is scanning for something else. §5.7 states
    its own residual that way (the credential shapes the refusal does not know),
    for the same reason: a reader who has to assemble it never does.

    One thing that belongs here and is deliberately absent: gates that ran at
    `base_sha` and were not re-run. §5.7 makes that case *provably* redundant —
    the packaged tree is byte-identical to the tree they saw — so listing it as
    a gap would be false, and `_verification` already says which case this is.
    """
    lines = []
    if skipped := [r.gate for r in results if r.status == "skip"]:
        lines.append(
            "- Did not run: "
            + ", ".join(f"`{_cell(gate)}`" for gate in skipped)
            + " — the repo declares no such gate."
        )
    # PACKAGE aborts on an errored gate, so a packaged body does not carry one.
    # It is here because this is a renderer and the caller decides what it is
    # handed: a body that shows an `error` row and then omits it from the list of
    # what went unjudged is the narrower lie of the two.
    if broken := [r.gate for r in results if r.status == "error"]:
        lines.append(
            "- Broke rather than judged: "
            + ", ".join(f"`{_cell(gate)}`" for gate in broken)
            + " — an `error` is charged to nobody, and checks nothing either."
        )
    # `fail` only, exactly as the gate table's marker: an advisory gate that
    # passed is not a gap, and keying on the gate alone would list it as one.
    if advisory := [
        r.gate for r in results if r.status == "fail" and r.gate in advisory_gates
    ]:
        lines.append(
            "- Failed without blocking: "
            + ", ".join(f"`{_cell(gate)}`" for gate in advisory)
            + " — advisory at this risk tier, so the pull request is green anyway."
        )
    claims = [c.claim for c in spec.acceptance] or spec.acceptance_criteria
    criteria = next((r for r in reversed(list(results)) if r.gate == "criteria"), None)
    if claims and (criteria is None or criteria.status not in ("pass", "fail")):
        lines.append(
            f"- The {len(claims)} acceptance "
            f"criteri{'on is' if len(claims) == 1 else 'a are'} not mechanically "
            "checked: no `criteria` gate result stands behind the checklist."
        )
    # Anchoring is what `anchored_blockers` and `anchored_concerns` both filter
    # on, so an unanchored finding is absent from REBUT *and* from the concern
    # count the morning queue sorts on (§6). Nothing else in the body says so.
    # Keyed on the review's lens, not the finding's own `lens` field, because
    # `_findings` builds the table carrying the `anchored: no` cells that way and
    # this line exists to be cross-referenced against it.
    if unanchored := [
        (r.lens, f) for r in reviews for f in r.findings if not f.anchored
    ]:
        lenses = sorted({lens for lens, _ in unanchored})
        lines.append(
            f"- {len(unanchored)} finding"
            f"{'' if len(unanchored) == 1 else 's'} could not be anchored to the "
            "diff ("
            + ", ".join(f"`{_cell(lens)}`" for lens in lenses)
            + "), so neither the implementer nor the concern count ever saw "
            + ("it." if len(unanchored) == 1 else "them.")
        )
    if not lines:
        lines.append(
            "- No gate reported `skip`, no failure was advisory, and every "
            "finding anchored to the diff."
        )
    return "\n".join(["## Not covered", "", *lines, ""])


_NOTES_LIMIT = 4000


def _notes(notes: str) -> str:
    """The implementer's own account of something it saw but was not asked to
    fix — a different speaker at a different trust level from §5.5's critics,
    whose findings are anchored to the diff and adjudicated. This carries
    neither: no anchor, no severity, no adjudication, and the heading exists
    to say so at a glance.

    Cell-authored text reaching GitHub, so it is neutralized exactly like
    every other such string in this renderer, and clipped to a declared
    ceiling — an agent that can write prose into a pull request body can
    write a screenful of it, or an `@name`, or a `Fixes #12`."""
    text = notes.strip()
    if not text:
        return ""
    safe = neutralize(text)
    clipped = ""
    if len(safe) > _NOTES_LIMIT:
        safe = safe[:_NOTES_LIMIT]
        clipped = "\n\n… clipped at the notes ceiling; the rest was not kept.\n"
    return (
        "### Notes from the implementer\n\n"
        "> The implementer's own account, unadjudicated: nobody has reviewed "
        "this, it carries no severity, and it is not a finding.\n\n"
        f"{safe}\n"
        f"{clipped}"
    )


def _provenance(spec: Spec, base_sha: str, head_sha: str, transcript_path: str) -> str:
    touches = ", ".join(f"`{t}`" for t in spec.touches) or "—"
    return (
        "### Provenance\n\n"
        f"- base `{base_sha}`\n"
        f"- head `{head_sha}`\n"
        f"- touches {touches}\n"
        f"- artifacts `{transcript_path}`\n"
    )
