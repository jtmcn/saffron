"""PACKAGE — a green cell becomes a branch, a draft PR and a queue line (§5.7).

Host-side, no model, and no cell except the gate-only one part 3 of the spec
describes. It runs after the cell is torn down: the host should not be talking
to the real remote while an untrusted container is alive.

No named remote is ever added to the mirror, and no long-lived ref is created.
`mirror.ensure_mirror` fetches `+refs/*:refs/*` with `--prune`, so any ref left
behind that the local repo does not have is deleted on the next run — including
a branch this module just created.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from saffron.cell.worktree import DIFF_FLAGS
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import GateResult, split_lines
from saffron.phases.review import anchored_concerns
from saffron.report import index as index_report
from saffron.report import pr_body
from saffron.report.pr_body import neutralize
from saffron.repos import mirror as mirror_ops

_SLUG = re.compile(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$")

APPLY_OK = "ok"
APPLY_CONFLICT = "conflict"

# Measured on git 2.50.1 (Apple Git-155). Both of these appear on stderr while
# git exits 0, which is why neither the exit code nor the output alone decides.
_NO_BLOB = "lacks the necessary blob"
_NO_FULL_INDEX = "without full index line"

# ponytail: a refusal, not the `secrets` gate (§5.4) — that is v1's to build.
# The ceiling is named in DESIGN.md §5.7: every credential shape not listed here
# still reaches the remote, and the upgrade path is the gate, not more regexes.
_CREDENTIAL_SHAPES = (
    ("an Anthropic API key", re.compile(r"sk-ant-api\d{2}-[A-Za-z0-9_\-]{16,}")),
    ("an Anthropic OAuth token", re.compile(r"sk-ant-oat\d{2}-[A-Za-z0-9_\-]{8,}")),
    ("a GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}")),
    ("an AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)


class PackageError(RuntimeError):
    """Infrastructure. Raised, caught by `cli.main`, exits 2 (§3.3)."""


class LeaseRejected(PackageError):
    """The branch moved underneath us — the task's problem, not the toolchain's."""


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Every git call here inspects `returncode` *and* `stderr` — see
    `apply_patch`, where a zero exit does not mean what it looks like."""
    try:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise PackageError(f"git {' '.join(args)}: {exc}") from exc


def real_remote(repo: Path) -> str:
    """The URL a pull request is opened against — never the mirror's source."""
    done = _run(repo, "remote", "get-url", "origin")
    if done.returncode != 0 or not done.stdout.strip():
        raise PackageError(
            f"{repo} has no 'origin' remote, so there is nowhere to open a pull request"
        )
    return done.stdout.strip()


def github_slug(url: str) -> str:
    """`owner/repo`, from either URL shape git writes."""
    if not (found := _SLUG.search(url)):
        raise PackageError(f"cannot read owner/repo out of {url!r}")
    return f"{found.group(1)}/{found.group(2)}"


def default_branch(url: str, *, cwd: Path) -> str:
    """What the remote says HEAD points at. Not hardcoded `main`."""
    done = _run(cwd, "ls-remote", "--symref", url, "HEAD")
    if done.returncode != 0:
        raise PackageError(f"cannot reach {url}: {done.stderr.strip()[:200]}")
    for line in done.stdout.splitlines():
        if line.startswith("ref: "):
            return line.removeprefix("ref: ").split("\t")[0].removeprefix("refs/heads/")
    raise PackageError(f"{url} reported no symbolic HEAD")


def fetch_default_branch(mirror: Path, url: str) -> tuple[str, str]:
    """The remote's default branch and its head, fetched into the mirror.

    Both ends of §5.7 read this now, closing the asymmetry backlog item 11
    named: the invoking checkout's HEAD at task start vs. the remote at
    package time.
    """
    default = default_branch(url, cwd=mirror)
    fetched = _run(mirror, "fetch", url, f"refs/heads/{default}")
    if fetched.returncode != 0:
        raise PackageError(f"cannot fetch {default} from {url}: {fetched.stderr[:200]}")
    head = _run(mirror, "rev-parse", "FETCH_HEAD").stdout.strip()
    if not head:
        raise PackageError(f"{url} reported no head for {default}")
    return default, head


def assert_base_objects(mirror: Path, base_sha: str) -> None:
    """Refuse to apply against a mirror missing the patch's preimage.

    Without this, `--3way` degrades to a context match and reports success —
    see `apply_patch`. Checked up front so the failure names its cause.
    """
    done = _run(mirror, "cat-file", "-e", f"{base_sha}^{{tree}}")
    if done.returncode != 0:
        raise PackageError(
            f"mirror {mirror} lacks the objects for base {base_sha[:12]}, so a "
            "three-way merge cannot be performed"
        )


def apply_patch(worktree: Path, patch: Path) -> str:
    """Apply the cell's squashed patch. §5.7's rebase, one commit long.

    Two measured hazards, and the exit code alone catches neither:

    - A **conflicting** apply exits 1 *and writes the file*, with `<<<<<<<`
      markers and a staged `U` entry. Non-zero is APPLY_CONFLICT and the
      worktree must be discarded unread — never committed.
    - A **degraded** apply exits **0**: with the preimage blob absent and the
      hunk's context matching, git falls back to direct application and
      succeeds. That is `error`, not `pass` — the toolchain, charged to nobody.
    """
    if not patch.is_file():
        raise PackageError(f"no patch at {patch}: there is nothing to package")
    done = _run(worktree, "apply", "--3way", "--index", str(patch))
    stderr = done.stderr
    if _NO_FULL_INDEX in stderr:
        raise PackageError(
            "the patch carries a binary change with no full index line, so it "
            "was never appliable — not a conflict"
        )
    if _NO_BLOB in stderr:
        raise PackageError(
            "git fell back to direct application: the preimage blob is absent, "
            "so no three-way merge happened and a clean exit would mean only "
            "that the context matched"
        )
    return APPLY_OK if done.returncode == 0 else APPLY_CONFLICT


def _added_lines(patch_text: str) -> list[tuple[str, str]]:
    """(path, added line) for every `+` line. A credential removed by the patch
    is already in history and is not this push's doing.

    `+++` is a file header only *outside* a hunk. Inside one it is the added
    line `++...` — which a patch quoted in a test fixture produces for every
    line it carries, and which C-style `++x` produces on its own. Recognising
    it by prefix alone dropped those from the scan, and read an added `++ b/x`
    as a header that re-pointed `path` for every later hit. `diff --git` needs
    no such care: a context line is space-prefixed, so a bare one at column 0
    is always a real stanza header.
    """
    path, out, in_hunk = "?", [], False
    # split_lines, not splitlines(): one \x0c inside an added line shatters it,
    # and the fragment carrying the secret is dropped from the scan.
    for line in split_lines(patch_text):
        if line.startswith("@@"):
            in_hunk = True
        elif line.startswith("diff --git "):
            in_hunk = False
        if not in_hunk and line.startswith("+++ "):
            if line.startswith("+++ b/"):
                path = line.removeprefix("+++ b/")
            continue
        if line.startswith("+"):
            out.append((path, line[1:]))
    return out


def find_credentials(patch_text: str, *, token: str | None) -> list[str]:
    """Describe every credential the patch would push. Never returns the value."""
    return _scan(_added_lines(patch_text), token)


def find_credentials_in_text(text: str, *, token: str | None, where: str) -> list[str]:
    """The same scan over prose. A claim, a rebuttal argument and a verdict
    reason are cell-authored too, and the body carries them to the remote."""
    return _scan([(where, line) for line in split_lines(text)], token)


def _scan(lines: list[tuple[str, str]], token: str | None) -> list[str]:
    """The literal token is checked first and separately: it is the one secret we
    know is in the cell, so a miss there is not a heuristic failure.
    """
    found = []
    for path, line in lines:
        # length guard: a short/empty token would substring-match unrelated lines.
        if token and len(token) > 8 and token in line:
            found.append(f"{path}: the cell's own CLAUDE_CODE_OAUTH_TOKEN")
            continue
        for what, pattern in _CREDENTIAL_SHAPES:
            if pattern.search(line):
                found.append(f"{path}: {what}")
                break
    return found


def commit_squash(
    worktree: Path,
    *,
    spec_id: str,
    title: str,
    base_sha: str,
    cell_head: str | None,
    attempts: int,
    spent_usd: float,
    agent_subjects: list[str],
) -> str:
    """One commit. Not the repo's `type(scope):` convention — that describes a
    commit a person wrote about a defect they understood, and this one is
    generated; a subject mimicking it would claim a judgement nothing made.

    `cell_head` names an object that no longer exists anywhere: the cell's
    commits died with the volume. It is recorded because it is the only name
    the transcript and the batch tree share.
    """
    lines = [
        f"saffron {spec_id}: {neutralize(title)}",
        "",
        f"base {base_sha[:12]}",
        f"cell head {cell_head[:12] if cell_head else '(unknown)'} "
        "(unreachable: the cell's commits died with its volume)",
        f"{attempts} attempts, ${spent_usd:.2f}",
    ]
    if agent_subjects:
        lines += ["", "The agent's own commits, squashed into this one:"]
        lines += [f"  * {neutralize(s)}" for s in agent_subjects]
    # On the command, not `git config`: a --mirror clone inherits no identity,
    # and nothing is left behind in a worktree that is about to be removed.
    done = _run(
        worktree,
        "-c",
        "user.email=saffron@localhost",
        "-c",
        "user.name=Saffron",
        "commit",
        "-q",
        "-m",
        "\n".join(lines),
    )
    if done.returncode != 0:
        raise PackageError(f"commit failed: {done.stderr.strip()[:200]}")
    return _run(worktree, "rev-parse", "HEAD").stdout.strip()


def remote_sha(url: str, branch: str, *, cwd: Path) -> str:
    """What the remote has for this branch right now — "" if it has nothing.

    Read rather than assumed: this is the lease, and a guessed lease protects
    nothing.
    """
    done = _run(cwd, "ls-remote", url, f"refs/heads/{branch}")
    if done.returncode != 0:
        raise PackageError(f"cannot reach {url}: {done.stderr.strip()[:200]}")
    return done.stdout.split("\t")[0].strip() if done.stdout.strip() else ""


def push_with_lease(worktree: Path, *, url: str, branch: str, expect: str) -> None:
    """Push, pinned to what the remote said. An empty `expect` means the branch
    is not there — measured: git treats that as "expect it to be absent" and
    rejects with `stale info` if it appeared."""
    done = _run(
        worktree,
        "push",
        f"--force-with-lease=refs/heads/{branch}:{expect}",
        url,
        f"HEAD:refs/heads/{branch}",
    )
    if done.returncode != 0:
        stderr = done.stderr.strip()[:300]
        # "stale info" is git's own wording for a force-with-lease rejection,
        # for both a stale non-empty expect and an empty one that pushed too
        # late. Force always wins once the lease passes, so no other rejection
        # shape reaches here as a lease failure.
        if "stale info" in stderr:
            raise LeaseRejected(f"the branch moved underneath us: {stderr}")
        raise PackageError(f"push failed: {stderr}")


GhRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def run_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def open_draft_pr(
    *,
    slug: str,
    branch: str,
    base: str,
    title: str,
    body_path: Path,
    gh: GhRunner = run_gh,
) -> str:
    """Open the pull request as a draft, or report the one already there.

    Called *after* the push, deliberately: a missing or unauthenticated `gh`
    then leaves a branch you can open by hand, where the other order loses the
    work to a CLI.
    """
    create = [
        "gh",
        "pr",
        "create",
        "--repo",
        slug,
        "--draft",
        "--base",
        base,
        "--head",
        branch,
        # Not optional: without it and without --fill, gh prompts, and a prompt
        # in an unattended batch is a hang.
        "--title",
        title,
        "--body-file",
        str(body_path),
    ]
    try:
        done = gh(create)
    except OSError as exc:
        raise PackageError(
            f"gh is unavailable ({exc}); branch {branch} is already pushed, so "
            "the pull request can be opened by hand"
        ) from exc
    if done.returncode == 0:
        if printed := done.stdout.strip().splitlines():
            return printed[-1]
        raise PackageError(
            f"gh created the pull request for {branch} but printed no URL; the "
            "branch is already pushed, so the pull request can be found by hand"
        )

    view = gh(
        ["gh", "pr", "view", branch, "--repo", slug, "--json", "url", "--jq", ".url"]
    )
    if view.returncode == 0 and view.stdout.strip():
        return view.stdout.strip()
    raise PackageError(
        f"gh could not open or find a pull request for {branch} "
        f"(it is already pushed): {done.stderr.strip()[:200]}"
    )


def needs_reverification(fetch_head: str, base_sha: str) -> bool:
    """Re-run only when the base moved (§5.7).

    Equal shas mean the packaged tree is the tree the suite already ran on, so
    a re-run is provably redundant rather than merely expensive.
    """
    return fetch_head != base_sha


def reverify(
    *,
    mirror: Path,
    packaged_sha: str,
    new_base_sha: str,
    policy,
    gates_dir: Path,
    image: str,
    watch,
) -> tuple[list[NewFailure], list[GateResult]]:
    """Run the suite on the packaged commit, in a cell. Returns the new
    failures *and* the head results, because the body's gate table has to show
    the run its own sentence claims: `_verification` says "re-run on the
    packaged commit", and rendering `outcome.gates` there would print durations
    and summaries from the cell's run at `base_sha`.

    **Never host-side.** Exec'ing a gate on the host is the control plane
    executing model-authored code — the one thing §2 says it never does. Both
    runs read their gates from `gates_dir`, exported from `new_base_sha`: the
    two suites subtracted below come from one set of executables, and the
    patch's own `.saffron/gates/*` are never run.

    Twice, because the base moved: the old baseline describes a tree that no
    longer exists, and comparing against it would charge this task with the
    default branch's own drift. So a fresh baseline at `new_base_sha`, the head
    suite at `packaged_sha`, and the usual subtraction (§4.4 steps 2-3).
    """
    from saffron.cell import runtime, worktree
    from saffron.cell.session import aborted_gates
    from saffron.gates import runner
    from saffron.gates.baseline import subtract_baseline

    results = {}
    for label, sha in (("baseline", new_base_sha), ("head", packaged_sha)):
        # packaged_sha, not the loop's `sha`: new_base_sha is today's default-branch
        # head, identical for every concurrent task (DESIGN.md N4) — keying on it
        # would let two tasks collide and tear down each other's live cell.
        volume = f"saffron-pkg-{label}-{packaged_sha[:12]}"
        container = f"saffron-pkg-{label}-{packaged_sha[:12]}"
        network = f"{container}-net"
        try:
            # `create_network` hardcodes --internal (runtime.py:146) and
            # returns None, so the name is ours to hold. Passed explicitly to
            # `prepare_worktree` because a cell created without a network joins
            # the runtime's default one with full egress, and every control the
            # caller ran then applies to some other container (Appendix I).
            runtime.create_network(network)
            runtime.create_volume(volume)
            worktree.prepare_worktree(
                mirror=mirror,
                volume=volume,
                base_sha=sha,
                branch=f"pkg-{label}",
                image=image,
                container=container,
                # The repo's declared gate env, and nothing else: no agent, no
                # credential and no route out — this cell only runs gates.
                network=network,
                env=dict(policy.thread_env),
                gates_dir=gates_dir,
            )
            watch(f"re-verify: {label} suite at {sha[:12]}")
            # Gate paths are cell-side (`/gates/.saffron/gates/...`); `cwd` is
            # a host path that `CellExecutor` ignores. Same shape as the
            # session's suite — matched deliberately, so the two cannot drift
            # in how they name a gate.
            results[label] = runner.run_suite(
                policy.gate_executables(Path(worktree.GATES_MOUNT)),
                cwd=mirror,
                executor=runner.CellExecutor(container),
            )
            # error != fail (§5.4): a gate that broke must abort the package,
            # not net to an empty diff against an equally-broken baseline.
            if broken := aborted_gates(results[label]):
                raise PackageError(
                    f"{label} suite at {sha[:12]}: {', '.join(broken)} errored "
                    "rather than ran — infrastructure, not a task defect"
                )
        finally:
            runtime.remove_container(container)
            runtime.remove_volume(volume)
            runtime.remove_volume(f"{volume}-state")
            runtime.remove_network(network)

    return subtract_baseline(results["head"], results["baseline"]), results["head"]


@dataclass
class PackageResult:
    state: str
    pr_url: str = ""
    pushed_sha: str = ""
    branch: str = ""
    note: str = ""
    added: int = 0
    removed: int = 0


def package(
    outcome,
    *,
    spec,
    repo: Path,
    mirror: Path,
    policy,
    image: str,
    ledger,
    out_dir: Path,
    token: str | None,
    gh: GhRunner = run_gh,
    watch=print,
) -> PackageResult:
    """§5.7, host-side, after the cell is gone.

    Every `PackageError` this raises is infrastructure and reaches `cli.main`,
    which exits 2 without a queue line. Only the task's own failures —
    a conflict, a leaked credential, new failures after the rebase, a branch
    that moved — become `MERGE_FAILED`.
    """
    branch = f"saffron/{spec.id}"
    patch = outcome.task_dir / "patch.diff"
    # Before the sidecar is read: an empty diff writes neither file, and
    # `patch.json` missing surfaces as a traceback rather than this sentence.
    if not patch.is_file():
        raise PackageError(f"no patch at {patch}: there is nothing to package")
    base_sha = json.loads((outcome.task_dir / "patch.json").read_text())["base_sha"]
    url = real_remote(repo)
    slug = github_slug(url)
    # Before the fetch, not after: the fetch writes the object store this
    # reads, and would otherwise supply the very objects it is checking for.
    assert_base_objects(mirror, base_sha)
    default, fetch_head = fetch_default_branch(mirror, url)

    scratch = out_dir / "package" / spec.id
    worktree_path = mirror_ops.add_worktree(mirror, fetch_head, scratch)
    try:
        # -B, not -b: -b fails when the ref exists, which is the second-package
        # path exactly. Checked like every other git call here: an existing
        # `refs/heads/saffron` blocks the `saffron/SA-xxxx` path, and an
        # unchecked failure commits onto a detached HEAD that no `refs/heads/*`
        # reaches — which `reverify`'s fetch then cannot check out.
        checked = _run(worktree_path, "checkout", "-B", branch)
        if checked.returncode != 0:
            raise PackageError(
                f"cannot create {branch}: {checked.stderr.strip()[:200]}"
            )

        if apply_patch(worktree_path, patch) == APPLY_CONFLICT:
            watch(f"PACKAGE: {branch} conflicts with {default}")
            return _finish(
                ledger,
                outcome,
                out_dir,
                spec,
                repo.name,
                PackageResult(
                    state="MERGE_FAILED",
                    branch=branch,
                    note=f"conflicts with {default}",
                ),
            )

        def _refuse(leaked: list[str], where: str, **counts) -> PackageResult:
            """One refusal for both channels a cell has to the remote."""
            watch(f"PACKAGE: refusing to push — {'; '.join(leaked)}")
            return _finish(
                ledger,
                outcome,
                out_dir,
                spec,
                repo.name,
                PackageResult(
                    state="MERGE_FAILED",
                    branch=branch,
                    note=f"credential in {where}: {'; '.join(leaked)}",
                    **counts,
                ),
            )

        if leaked := find_credentials(patch.read_text(), token=token):
            return _refuse(leaked, "the patch")

        # The third channel out: `commit_squash` renders the agent's own
        # subjects into the commit body, where a push survives in the reflog.
        if leaked := find_credentials_in_text(
            "\n".join(outcome.agent_subjects), token=token, where="agent commit subject"
        ):
            return _refuse(leaked, "the commit subjects")

        pushed = commit_squash(
            worktree_path,
            spec_id=spec.id,
            title=spec.title,
            base_sha=base_sha,
            cell_head=outcome.cell_head_sha,
            attempts=outcome.attempts,
            spent_usd=outcome.spent_usd,
            agent_subjects=outcome.agent_subjects,
        )

        # Against the fetched default-branch head, because that is the diff a
        # reviewer sees on the pull request.
        added, removed = mirror_ops.diff_stat(mirror, fetch_head, pushed)

        verified_on, gates = "base", outcome.gates
        if needs_reverification(fetch_head, base_sha):
            # A gate that errored raises out of `reverify`: infrastructure, and
            # never this task's MERGE_FAILED.
            # A sibling of `scratch`, not a child: `scratch` is a git worktree
            # the `finally` hands to `remove_worktree`, and the export must not
            # have the worktree's lifetime.
            gates_dir = mirror_ops.export_gates(
                mirror, fetch_head, out_dir / "package" / f"{spec.id}-gates"
            )
            new, gates = reverify(
                mirror=mirror,
                packaged_sha=pushed,
                new_base_sha=fetch_head,
                policy=policy,
                gates_dir=gates_dir,
                image=image,
                watch=watch,
            )
            verified_on = "packaged"
            if new:
                watch(f"PACKAGE: {len(new)} new failures against {default}")
                return _finish(
                    ledger,
                    outcome,
                    out_dir,
                    spec,
                    repo.name,
                    PackageResult(
                        state="MERGE_FAILED",
                        branch=branch,
                        # Not `pushed`: this returns before the push, and a
                        # `pushed_sha` no remote has is a claim, not a record.
                        note=f"{len(new)} new failures after rebase "
                        f"({pushed[:12]} in the mirror)",
                        added=added,
                        removed=removed,
                    ),
                )

        # DIFF_FLAGS, not a bare diff: `diff.noprefix` in the operator's global
        # gitconfig makes every ` b/` path parse as garbage in `_test_diff`.
        diff = _run(worktree_path, "diff", *DIFF_FLAGS, f"{fetch_head}..HEAD").stdout
        body_path = outcome.task_dir / "pr_body.md"
        body = pr_body.render_pr_body(
            spec,
            gates,
            outcome.new_failures,
            base_sha=base_sha,
            head_sha=pushed,
            added=added,
            removed=removed,
            transcript_path=str(outcome.task_dir),
            reviews=outcome.reviews,
            rebut_result=outcome.rebut_result,
            attempts=outcome.attempts,
            spent_usd=outcome.spent_usd,
            test_paths=policy.integrity.test_paths,
            diff=diff,
            verified_on=verified_on,
        )
        body_path.write_text(body)
        # The body is the second cell-authored channel out: a claim or a
        # rebuttal argument reaches the remote without ever being in the diff.
        if leaked := find_credentials_in_text(body, token=token, where="pr_body.md"):
            return _refuse(leaked, "the body", added=added, removed=removed)

        try:
            push_with_lease(
                worktree_path,
                url=url,
                branch=branch,
                expect=remote_sha(url, branch, cwd=mirror),
            )
        except LeaseRejected as moved:
            # Only this: a plain PackageError here is an auth or transport
            # failure, and recording MERGE_FAILED would send the operator to
            # read a diff that was never the cause (§5.4, error != fail).
            watch(f"PACKAGE: {moved}")
            return _finish(
                ledger,
                outcome,
                out_dir,
                spec,
                repo.name,
                PackageResult(
                    state="MERGE_FAILED",
                    branch=branch,
                    note=f"{branch} moved underneath us",
                    added=added,
                    removed=removed,
                ),
            )

        pr_url = open_draft_pr(
            slug=slug,
            branch=branch,
            base=default,
            title=f"{spec.id} — {neutralize(spec.title)}",
            body_path=body_path,
            gh=gh,
        )
        watch(f"PACKAGE: {pr_url}")
        return _finish(
            ledger,
            outcome,
            out_dir,
            spec,
            repo.name,
            PackageResult(
                state="READY_FOR_REVIEW",
                pr_url=pr_url,
                pushed_sha=pushed,
                branch=branch,
                added=added,
                removed=removed,
            ),
        )
    finally:
        # The worktree otherwise leaks on every raise path, including the
        # missing-`gh` case this module deliberately creates.
        try:
            mirror_ops.remove_worktree(mirror, scratch)
        except mirror_ops.GitError as stuck:
            # Never let cleanup replace the outcome: it would turn a recorded
            # MERGE_FAILED into an exit 2. `add_worktree` self-heals anyway.
            watch(f"PACKAGE: could not remove {scratch}: {stuck}")


def _finish(ledger, outcome, out_dir: Path, spec, repo_name: str, result):
    """Persist and append. A PACKAGE that *raises* reaches neither, and that is
    deliberate: an index line whose link points at a pull request that was
    never opened is worse than no line."""
    ledger.set_task_package(
        outcome.task_id,
        result.state,
        result.branch,
        result.pushed_sha,
        result.pr_url,
    )
    index_report.append_queue_line(
        out_dir,
        index_report.QueueLine(
            repo=repo_name,
            spec_id=spec.id,
            state=result.state,
            attempts=outcome.attempts,
            cost_usd_est=outcome.spent_usd,
            concerns=anchored_concerns(outcome.reviews),
            added=result.added,
            removed=result.removed,
            link=result.pr_url,
            note=result.note,
            risk=spec.risk,
        ),
    )
    return result
