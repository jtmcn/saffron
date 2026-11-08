"""`saffron mutant <spec id> --from <file> --repo <path>` (backlog item 80,
`SA-0339`). Every name `SA-0338` or this spec adds is imported inside each
test body, since neither `saffron.mutants.write_mutants` nor the `mutant`
command exists at the tree base.
"""

from __future__ import annotations

import os
import subprocess

_SOURCE_A = "def add(x, y):\n    return x + y\n\n\ndef mul(x, y):\n    return x * y\n"
_SOURCE_B = "def neg(x):\n    return -x\n"


def _isolate_git(tmp_path, monkeypatch):
    """A fresh `HOME` and `XDG_CONFIG_HOME` under `tmp_path`, and
    `GIT_CONFIG_NOSYSTEM=1`, so no `config --global` reaches the real one."""
    git_home = tmp_path / "git-home"
    git_home.mkdir()
    monkeypatch.setenv("HOME", str(git_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(git_home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _bare(tmp_path, name="origin.git"):
    repo = tmp_path / name
    subprocess.run(
        ["git", "init", "-q", "--bare", str(repo)], check=True, capture_output=True
    )
    return repo


def _source_repo(tmp_path, name, origin):
    """A working repo with `a.py` and `b.py` committed, `origin` set to
    `origin`, and `.saffron/specs/` ready for uncommitted spec files."""
    repo = tmp_path / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "t@t"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "T"],
        check=True,
        capture_output=True,
    )
    (repo / "a.py").write_text(_SOURCE_A)
    (repo / "b.py").write_text(_SOURCE_B)
    (repo / ".saffron" / "specs").mkdir(parents=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", "a.py", "b.py"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "source"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "remote", "add", "origin", str(origin)],
        check=True,
        capture_output=True,
    )
    return repo


def _write_spec(
    repo,
    spec_id,
    *,
    under_done=False,
    slug="slug",
    claim="add returns the sum of its two arguments",
    witness="tests/test_a.py::test_add",
    second_criterion="",
    body="body\n",
):
    text = (
        f'---\nid: {spec_id}\ntitle: "t"\ntype: feature\n'
        f"acceptance:\n  - claim: {claim}\n    witness: {witness}\n"
        f"{second_criterion}---\n\n{body}"
    )
    directory = repo / ".saffron" / "specs"
    if under_done:
        directory = directory / "done"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{spec_id}-{slug}.md"
    path.write_text(text)
    return path


def _write_mutants_file(
    path,
    spec_id,
    *,
    witness="tests/test_a.py::test_add",
    file="a.py",
    find="x + y",
    replace="x - y",
    leading_comment=True,
):
    lines = []
    if leading_comment:
        lines.append(f"# mutants for {spec_id}\n")
    lines.append(f"{witness}:\n  file: {file}\n  find: {find}\n  replace: {replace}\n")
    path.write_text("".join(lines))
    return path


def _rev_parse(repo, ref="refs/saffron/mutants"):
    completed = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "-q", ref],
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def _run_mutant(home, repo, spec_id, from_file):
    from saffron import cli

    return cli.main(
        [
            "--home",
            str(home),
            "mutant",
            spec_id,
            "--from",
            str(from_file),
            "--repo",
            str(repo),
        ]
    )


def test_a_mutants_file_is_committed_onto_the_ref_and_pushed_to_origin(
    tmp_path, monkeypatch, capsys
):
    """Criterion 1: a clean write lands bytes, pushes, and keeps a second
    spec's file on a rewrite of the first."""
    from saffron.mutants import read_mutants

    _isolate_git(tmp_path, monkeypatch)
    home = tmp_path / "home"
    origin = _bare(tmp_path)
    repo = _source_repo(tmp_path, "repo", origin)

    _write_spec(repo, "TE-1")
    mutants_file = tmp_path / "TE-1-mutants.yaml"
    _write_mutants_file(mutants_file, "TE-1")

    code = _run_mutant(home, repo, "TE-1", mutants_file)
    printed = capsys.readouterr().out.strip()
    assert code == 0, printed
    first = printed
    assert _rev_parse(origin) == first

    # Byte-identical, unstripped: the file starts with a comment, so a
    # parsed-and-dumped round trip would not match.
    tree_blob = subprocess.run(
        ["git", "-C", str(origin), "show", f"{first}:TE-1.yaml"],
        capture_output=True,
    ).stdout
    assert tree_blob == mutants_file.read_bytes()

    from saffron.intake import Mutant

    assert read_mutants(origin, first, "TE-1") == {
        "tests/test_a.py::test_add": Mutant(file="a.py", find="x + y", replace="x - y")
    }

    _write_spec(
        repo,
        "TE-2",
        claim="neg returns the negation of its argument",
        witness="tests/test_b.py::test_neg",
    )
    second_file = tmp_path / "TE-2-mutants.yaml"
    _write_mutants_file(
        second_file,
        "TE-2",
        witness="tests/test_b.py::test_neg",
        file="b.py",
        find="-x",
        replace="x",
    )
    code = _run_mutant(home, repo, "TE-2", second_file)
    second = capsys.readouterr().out.strip()
    assert code == 0
    assert _rev_parse(origin) == second
    parent = subprocess.run(
        ["git", "-C", str(origin), "log", "-1", "--format=%P", second],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert parent == first
    names = subprocess.run(
        ["git", "-C", str(origin), "ls-tree", second],
        capture_output=True,
        text=True,
    ).stdout
    assert "TE-1.yaml" in names and "TE-2.yaml" in names

    # A second write for the first spec replaces its file alone.
    rewrite_file = tmp_path / "TE-1-mutants-2.yaml"
    _write_mutants_file(rewrite_file, "TE-1", replace="x - y - 1")
    code = _run_mutant(home, repo, "TE-1", rewrite_file)
    third = capsys.readouterr().out.strip()
    assert code == 0
    tree_blob = subprocess.run(
        ["git", "-C", str(origin), "show", f"{third}:TE-1.yaml"],
        capture_output=True,
    ).stdout
    assert tree_blob == rewrite_file.read_bytes()
    names = subprocess.run(
        ["git", "-C", str(origin), "ls-tree", third],
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert len(names) == 2


def test_a_write_builds_on_what_origin_holds_whatever_the_local_copy(
    tmp_path, monkeypatch, capsys
):
    """Criterion 2: four local states, origin always wins."""
    _isolate_git(tmp_path, monkeypatch)
    home = tmp_path / "home"
    origin = _bare(tmp_path)
    repo_a = _source_repo(tmp_path, "repo-a", origin)
    repo_b = _source_repo(tmp_path, "repo-b", origin)

    # (a) no local copy at all: repo_b has never fetched the ref.
    _write_spec(repo_a, "TE-10")
    mutants_a = tmp_path / "TE-10.yaml"
    _write_mutants_file(mutants_a, "TE-10")
    assert _run_mutant(home, repo_a, "TE-10", mutants_a) == 0
    c1 = capsys.readouterr().out.strip()

    _write_spec(repo_b, "TE-11")
    mutants_b = tmp_path / "TE-11.yaml"
    _write_mutants_file(mutants_b, "TE-11")
    assert _rev_parse(repo_b) is None
    assert _run_mutant(home, repo_b, "TE-11", mutants_b) == 0
    c_b1 = capsys.readouterr().out.strip()
    parent = subprocess.run(
        ["git", "-C", str(origin), "log", "-1", "--format=%P", c_b1],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert parent == c1

    # (b) local copy one commit behind: repo_a writes again, building on
    # origin's newer tip (c_b1) rather than its own stale local ref (c1).
    _write_spec(repo_a, "TE-12")
    mutants_a2 = tmp_path / "TE-12.yaml"
    _write_mutants_file(mutants_a2, "TE-12")
    assert _rev_parse(repo_a) == c1
    assert _run_mutant(home, repo_a, "TE-12", mutants_a2) == 0
    c2 = capsys.readouterr().out.strip()
    parent = subprocess.run(
        ["git", "-C", str(origin), "log", "-1", "--format=%P", c2],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert parent == c_b1

    # (c) a local ref origin's own history does not contain, pointed at a
    # hand-built root commit. The leading `+` still overwrites it.
    decoy_blob = (
        subprocess.run(
            ["git", "-C", str(repo_b), "hash-object", "-w", "--stdin"],
            input=b"decoy: 1\n",
            capture_output=True,
        )
        .stdout.decode()
        .strip()
    )
    decoy_tree = subprocess.run(
        ["git", "-C", str(repo_b), "mktree"],
        input=f"100644 blob {decoy_blob}\tdecoy.yaml\n",
        capture_output=True,
        text=True,
    ).stdout.strip()
    decoy_commit = subprocess.run(
        [
            "git",
            "-C",
            str(repo_b),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=T",
            "commit-tree",
            decoy_tree,
            "-m",
            "decoy",
        ],
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(repo_b), "update-ref", "refs/saffron/mutants", decoy_commit],
        check=True,
        capture_output=True,
    )
    _write_spec(repo_b, "TE-13")
    mutants_b2 = tmp_path / "TE-13.yaml"
    _write_mutants_file(mutants_b2, "TE-13")
    assert _run_mutant(home, repo_b, "TE-13", mutants_b2) == 0
    c3 = capsys.readouterr().out.strip()
    parent = subprocess.run(
        ["git", "-C", str(origin), "log", "-1", "--format=%P", c3],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert parent == c2
    names = subprocess.run(
        ["git", "-C", str(origin), "ls-tree", c3],
        capture_output=True,
        text=True,
    ).stdout
    assert "decoy.yaml" not in names

    # (d) a brand new empty bare origin, so the fetch's `--prune` deletes
    # repo_a's still-present local ref before the write proceeds.
    origin2 = _bare(tmp_path, name="origin2.git")
    subprocess.run(
        ["git", "-C", str(repo_a), "remote", "set-url", "origin", str(origin2)],
        check=True,
        capture_output=True,
    )
    assert _rev_parse(repo_a) is not None
    _write_spec(repo_a, "TE-14")
    mutants_a3 = tmp_path / "TE-14.yaml"
    _write_mutants_file(mutants_a3, "TE-14")
    assert _run_mutant(home, repo_a, "TE-14", mutants_a3) == 0
    c4 = capsys.readouterr().out.strip()
    parent = subprocess.run(
        ["git", "-C", str(origin2), "log", "-1", "--format=%P", c4],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert parent == ""
    names = subprocess.run(
        ["git", "-C", str(origin2), "ls-tree", c4],
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert len(names) == 1


def test_a_file_run_task_would_refuse_is_refused_before_any_write(
    tmp_path, monkeypatch, capsys
):
    """Criterion 3: every refusal from step 1 exits 1, prints a cause, and
    leaves neither ref touched."""
    _isolate_git(tmp_path, monkeypatch)
    home = tmp_path / "home"
    origin = _bare(tmp_path)
    repo = _source_repo(tmp_path, "repo", origin)

    def assert_refused(code):
        assert code == 1
        out = capsys.readouterr().out.strip()
        assert out
        assert _rev_parse(repo) is None
        assert _rev_parse(origin) is None

    # No spec file at all.
    missing = tmp_path / "missing.yaml"
    _write_mutants_file(missing, "TE-20")
    assert_refused(_run_mutant(home, repo, "TE-20", missing))

    # A spec file that exists only under done/.
    _write_spec(repo, "TE-21", under_done=True)
    assert_refused(_run_mutant(home, repo, "TE-21", missing))

    # Two matching spec files.
    _write_spec(repo, "TE-22")
    _write_spec(repo, "TE-22", slug="other")
    assert_refused(_run_mutant(home, repo, "TE-22", missing))

    # The spec file does not parse.
    bad_frontmatter = repo / ".saffron" / "specs" / "TE-23-slug.md"
    bad_frontmatter.write_text("---\nid: [\n---\n\nbody\n")
    assert_refused(_run_mutant(home, repo, "TE-23", missing))

    # The spec file declares another id. Its criterion matches the
    # mutants file exactly, so only the id check can refuse this one.
    other_id = repo / ".saffron" / "specs" / "TE-24-slug.md"
    other_id.write_text(
        "---\nid: TE-999\ntitle: t\ntype: feature\n"
        "acceptance:\n  - claim: add returns the sum of its two arguments\n"
        "    witness: tests/test_a.py::test_add\n---\n\nbody\n"
    )
    other_id_file = tmp_path / "other-id.yaml"
    _write_mutants_file(other_id_file, "TE-24")
    assert_refused(_run_mutant(home, repo, "TE-24", other_id_file))

    # The --from file is missing.
    _write_spec(repo, "TE-25")
    assert_refused(_run_mutant(home, repo, "TE-25", tmp_path / "nope.yaml"))

    # The file is not YAML.
    not_yaml = tmp_path / "not-yaml.yaml"
    not_yaml.write_text("key: [\n")
    assert_refused(_run_mutant(home, repo, "TE-25", not_yaml))

    # The file is a list.
    a_list = tmp_path / "a-list.yaml"
    a_list.write_text("- a\n- b\n")
    assert_refused(_run_mutant(home, repo, "TE-25", a_list))

    # A mutant without find.
    no_find = tmp_path / "no-find.yaml"
    no_find.write_text("tests/test_a.py::test_add:\n  file: a.py\n")
    assert_refused(_run_mutant(home, repo, "TE-25", no_find))

    # A key `Mutant` lacks. `find` occurs exactly once at HEAD, so only
    # the unknown key can refuse this one, never the occurrence count.
    extra_key = tmp_path / "extra-key.yaml"
    extra_key.write_text(
        "tests/test_a.py::test_add:\n  file: a.py\n  find: x + y\n  extra: 1\n"
    )
    assert_refused(_run_mutant(home, repo, "TE-25", extra_key))

    # A find occurring zero times at HEAD.
    zero_times = tmp_path / "zero-times.yaml"
    _write_mutants_file(zero_times, "TE-25", find="not_in_the_file_at_all")
    assert_refused(_run_mutant(home, repo, "TE-25", zero_times))

    # A find occurring twice at HEAD.
    twice = tmp_path / "twice.yaml"
    _write_mutants_file(twice, "TE-25", find="def ")
    assert_refused(_run_mutant(home, repo, "TE-25", twice))

    # A find present only in the working tree, absent at HEAD.
    (repo / "a.py").write_text(_SOURCE_A + "\n# only_in_the_working_tree\n")
    only_working_tree = tmp_path / "only-working-tree.yaml"
    _write_mutants_file(only_working_tree, "TE-25", find="only_in_the_working_tree")
    assert_refused(_run_mutant(home, repo, "TE-25", only_working_tree))
    (repo / "a.py").write_text(_SOURCE_A)

    # A find in a file absent at HEAD.
    absent_file = tmp_path / "absent-file.yaml"
    _write_mutants_file(absent_file, "TE-25", file="nope.py", find="x")
    assert_refused(_run_mutant(home, repo, "TE-25", absent_file))

    # A key naming a witness no criterion declares.
    _write_spec(repo, "TE-26")
    stray_witness = tmp_path / "stray-witness.yaml"
    _write_mutants_file(stray_witness, "TE-26", witness="tests/test_a.py::no_such_test")
    assert_refused(_run_mutant(home, repo, "TE-26", stray_witness))

    # A witness two criteria declare.
    _write_spec(
        repo,
        "TE-27",
        second_criterion=(
            "  - claim: add returns the sum of its two arguments again\n"
            "    witness: tests/test_a.py::test_add\n"
        ),
    )
    dup_witness = tmp_path / "dup-witness.yaml"
    _write_mutants_file(dup_witness, "TE-27")
    assert_refused(_run_mutant(home, repo, "TE-27", dup_witness))

    # A criterion declaring subject: with no mutant.
    bare_subject = repo / ".saffron" / "specs" / "TE-28-slug.md"
    bare_subject.write_text(
        "---\nid: TE-28\ntitle: t\ntype: feature\n"
        "acceptance:\n  - claim: c\n    witness: tests/test_a.py::test_add\n"
        "    subject: a.py\n---\n\nbody\n"
    )
    no_mutant_for_it = tmp_path / "no-mutant-for-it.yaml"
    no_mutant_for_it.write_text("{}\n")
    assert_refused(_run_mutant(home, repo, "TE-28", no_mutant_for_it))

    # A find occurring once at HEAD and in the spec's own body.
    disclosed_body = repo / ".saffron" / "specs" / "TE-29-slug.md"
    disclosed_body.write_text(
        "---\nid: TE-29\ntitle: t\ntype: feature\n"
        "acceptance:\n  - claim: c\n    witness: tests/test_a.py::test_add\n"
        "---\n\nthe literal x + y is here\n"
    )
    disclosed_body_file = tmp_path / "disclosed-body.yaml"
    _write_mutants_file(disclosed_body_file, "TE-29")
    assert_refused(_run_mutant(home, repo, "TE-29", disclosed_body_file))

    # A find occurring once at HEAD and in its own criterion's claim.
    disclosed_claim = repo / ".saffron" / "specs" / "TE-30-slug.md"
    disclosed_claim.write_text(
        "---\nid: TE-30\ntitle: t\ntype: feature\n"
        "acceptance:\n  - claim: the code still returns x + y\n"
        "    witness: tests/test_a.py::test_add\n---\n\nbody\n"
    )
    disclosed_claim_file = tmp_path / "disclosed-claim.yaml"
    _write_mutants_file(disclosed_claim_file, "TE-30")
    assert_refused(_run_mutant(home, repo, "TE-30", disclosed_claim_file))

    # A find occurring once at HEAD and in another criterion's claim.
    disclosed_sibling = repo / ".saffron" / "specs" / "TE-31-slug.md"
    disclosed_sibling.write_text(
        "---\nid: TE-31\ntitle: t\ntype: feature\n"
        "acceptance:\n  - claim: c\n    witness: tests/test_a.py::test_add\n"
        "  - claim: elsewhere the code still returns x + y\n"
        "    witness: tests/test_a.py::test_other\n---\n\nbody\n"
    )
    disclosed_sibling_file = tmp_path / "disclosed-sibling.yaml"
    _write_mutants_file(disclosed_sibling_file, "TE-31")
    assert_refused(_run_mutant(home, repo, "TE-31", disclosed_sibling_file))

    # A find occurring once at HEAD and in another criterion's wrong_versions.
    disclosed_wrong = repo / ".saffron" / "specs" / "TE-32-slug.md"
    disclosed_wrong.write_text(
        "---\nid: TE-32\ntitle: t\ntype: feature\n"
        "acceptance:\n  - claim: c\n    witness: tests/test_a.py::test_add\n"
        "  - claim: c2\n    witness: tests/test_a.py::test_other\n"
        "    wrong_versions:\n      - a version that keeps returning x + y\n"
        "---\n\nbody\n"
    )
    disclosed_wrong_file = tmp_path / "disclosed-wrong.yaml"
    _write_mutants_file(disclosed_wrong_file, "TE-32")
    assert_refused(_run_mutant(home, repo, "TE-32", disclosed_wrong_file))

    # A criterion still declaring `mutant:` inline. The `--from` file names
    # no witness at all, so only the inline mutant itself can refuse this.
    inline_mutant = repo / ".saffron" / "specs" / "TE-34-slug.md"
    inline_mutant.write_text(
        "---\nid: TE-34\ntitle: t\ntype: feature\n"
        "acceptance:\n  - claim: c\n    witness: tests/test_a.py::test_add\n"
        "    mutant:\n      file: a.py\n      find: x + y\n      replace: z\n"
        "---\n\nbody\n"
    )
    no_witnesses_file = tmp_path / "no-witnesses.yaml"
    no_witnesses_file.write_text("{}\n")
    assert_refused(_run_mutant(home, repo, "TE-34", no_witnesses_file))


def test_a_write_that_loses_a_race_is_refused_and_leaves_the_winner(
    tmp_path, monkeypatch, capsys
):
    """Criterion 4: a `subprocess.run` wrapper mutates the ref it is about
    to act on, immediately before the real call, firing once."""
    _isolate_git(tmp_path, monkeypatch)
    home = tmp_path / "home"
    origin = _bare(tmp_path)
    repo = _source_repo(tmp_path, "repo", origin)
    real_run = subprocess.run
    source_head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()

    def once(match, before):
        fired = False

        def wrapper(args, *a, **kw):
            nonlocal fired
            if not fired and match(args):
                fired = True
                before()
            return real_run(args, *a, **kw)

        return wrapper

    def is_write_update_ref(args):
        return str(repo) in args and "update-ref" in args and "-d" not in args

    def is_push(args):
        return str(repo) in args and "push" in args

    # (a) the ref is created where none was, before the first write.
    _write_spec(repo, "TE-40")
    mutants_file = tmp_path / "TE-40.yaml"
    _write_mutants_file(mutants_file, "TE-40")
    monkeypatch.setattr(
        subprocess,
        "run",
        once(
            is_write_update_ref,
            lambda: real_run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "update-ref",
                    "refs/saffron/mutants",
                    source_head,
                ],
                check=True,
                capture_output=True,
            ),
        ),
    )
    assert _run_mutant(home, repo, "TE-40", mutants_file) == 1
    capsys.readouterr()
    assert _rev_parse(repo) == source_head
    assert _rev_parse(origin) is None
    monkeypatch.setattr(subprocess, "run", real_run)

    # Clean the created ref, then do one real successful write to give
    # both (b) and (c) a known old commit to race against.
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", "-d", "refs/saffron/mutants"],
        check=True,
        capture_output=True,
    )
    _write_spec(repo, "TE-41")
    first_file = tmp_path / "TE-41.yaml"
    _write_mutants_file(first_file, "TE-41")
    assert _run_mutant(home, repo, "TE-41", first_file) == 0
    old_commit = capsys.readouterr().out.strip()

    # (b) the ref is moved before the second write's update-ref.
    _write_spec(repo, "TE-42")
    second_file = tmp_path / "TE-42.yaml"
    _write_mutants_file(second_file, "TE-42")
    monkeypatch.setattr(
        subprocess,
        "run",
        once(
            is_write_update_ref,
            lambda: real_run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "update-ref",
                    "refs/saffron/mutants",
                    source_head,
                ],
                check=True,
                capture_output=True,
            ),
        ),
    )
    assert _run_mutant(home, repo, "TE-42", second_file) == 1
    capsys.readouterr()
    assert _rev_parse(repo) == source_head
    assert _rev_parse(origin) == old_commit
    monkeypatch.setattr(subprocess, "run", real_run)

    # (c) the ref is deleted before the third write's update-ref. Restore
    # the known old commit first.
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", "refs/saffron/mutants", old_commit],
        check=True,
        capture_output=True,
    )
    _write_spec(repo, "TE-43")
    third_file = tmp_path / "TE-43.yaml"
    _write_mutants_file(third_file, "TE-43")
    monkeypatch.setattr(
        subprocess,
        "run",
        once(
            is_write_update_ref,
            lambda: real_run(
                ["git", "-C", str(repo), "update-ref", "-d", "refs/saffron/mutants"],
                check=True,
                capture_output=True,
            ),
        ),
    )
    assert _run_mutant(home, repo, "TE-43", third_file) == 1
    capsys.readouterr()
    assert _rev_parse(repo) is None
    assert _rev_parse(origin) == old_commit
    monkeypatch.setattr(subprocess, "run", real_run)

    # (d) origin's ref races ahead before the push, so it is refused as a
    # non-fast-forward and the local ref returns to what it held.
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", "refs/saffron/mutants", old_commit],
        check=True,
        capture_output=True,
    )

    def race_origin_ahead():
        # Parented on `old_commit` in origin's own object store, not the
        # commit the write has not pushed yet. A sibling still works.
        blob = (
            real_run(
                ["git", "-C", str(origin), "hash-object", "-w", "--stdin"],
                input=b"decoy: 1\n",
                capture_output=True,
            )
            .stdout.decode()
            .strip()
        )
        tree = real_run(
            ["git", "-C", str(origin), "mktree"],
            input=f"100644 blob {blob}\tdecoy.yaml\n",
            capture_output=True,
            text=True,
        ).stdout.strip()
        child = real_run(
            [
                "git",
                "-C",
                str(origin),
                "-c",
                "user.email=t@t",
                "-c",
                "user.name=T",
                "commit-tree",
                tree,
                "-m",
                "a sibling of the pushed commit",
                "-p",
                old_commit,
            ],
            capture_output=True,
            text=True,
        ).stdout.strip()
        real_run(
            ["git", "-C", str(origin), "update-ref", "refs/saffron/mutants", child],
            check=True,
            capture_output=True,
        )

    _write_spec(repo, "TE-44")
    fourth_file = tmp_path / "TE-44.yaml"
    _write_mutants_file(fourth_file, "TE-44")
    monkeypatch.setattr(subprocess, "run", once(is_push, race_origin_ahead))
    assert _run_mutant(home, repo, "TE-44", fourth_file) == 1
    capsys.readouterr()
    assert _rev_parse(repo) == old_commit
    origin_tip = _rev_parse(origin)
    assert origin_tip != old_commit
    parent = subprocess.run(
        ["git", "-C", str(origin), "log", "-1", "--format=%P", origin_tip],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert parent == old_commit
    monkeypatch.setattr(subprocess, "run", real_run)


def test_a_broken_origin_or_ref_exits_2(tmp_path, monkeypatch, capsys):
    """Criterion 5: a git failure that is no race exits 2, and leaves
    neither ref existing."""
    _isolate_git(tmp_path, monkeypatch)
    home = tmp_path / "home"
    origin = _bare(tmp_path)
    repo = _source_repo(tmp_path, "repo", origin)
    real_run = subprocess.run

    def assert_broken(code):
        assert code == 2
        out = capsys.readouterr().out.strip()
        assert out
        assert _rev_parse(repo) is None
        assert _rev_parse(origin) is None

    # (1) origin's URL names no repository.
    subprocess.run(
        ["git", "-C", str(repo), "remote", "set-url", "origin", str(tmp_path / "nope")],
        check=True,
        capture_output=True,
    )
    _write_spec(repo, "TE-50")
    f1 = tmp_path / "TE-50.yaml"
    _write_mutants_file(f1, "TE-50")
    assert_broken(_run_mutant(home, repo, "TE-50", f1))

    # (2) the repository has no origin remote at all.
    subprocess.run(
        ["git", "-C", str(repo), "remote", "remove", "origin"],
        check=True,
        capture_output=True,
    )
    _write_spec(repo, "TE-51")
    f2 = tmp_path / "TE-51.yaml"
    _write_mutants_file(f2, "TE-51")
    assert_broken(_run_mutant(home, repo, "TE-51", f2))

    subprocess.run(
        ["git", "-C", str(repo), "remote", "add", "origin", str(origin)],
        check=True,
        capture_output=True,
    )

    # (3) the local ref's lock file is held when update-ref runs.
    saffron_refs = repo / ".git" / "refs" / "saffron"
    saffron_refs.mkdir(parents=True)
    lock = saffron_refs / "mutants.lock"
    lock.write_text("locked\n")
    _write_spec(repo, "TE-52")
    f3 = tmp_path / "TE-52.yaml"
    _write_mutants_file(f3, "TE-52")
    assert_broken(_run_mutant(home, repo, "TE-52", f3))
    lock.unlink()

    # (4) origin is reachable for the fetch and unreachable for the push.
    def is_push(args):
        return str(repo) in args and "push" in args

    def point_origin_at_missing_path():
        real_run(
            [
                "git",
                "-C",
                str(repo),
                "remote",
                "set-url",
                "origin",
                str(tmp_path / "gone"),
            ],
            check=True,
            capture_output=True,
        )

    def once_on_push(match, before):
        fired = False

        def wrapper(args, *a, **kw):
            nonlocal fired
            if not fired and match(args):
                fired = True
                before()
            return real_run(args, *a, **kw)

        return wrapper

    _write_spec(repo, "TE-53")
    f4 = tmp_path / "TE-53.yaml"
    _write_mutants_file(f4, "TE-53")
    monkeypatch.setattr(
        subprocess, "run", once_on_push(is_push, point_origin_at_missing_path)
    )
    assert_broken(_run_mutant(home, repo, "TE-53", f4))
    monkeypatch.setattr(subprocess, "run", real_run)


def test_every_git_call_runs_with_no_terminal_prompt(tmp_path, monkeypatch, capsys):
    """Criterion 6: every git process the command starts carries
    `GIT_TERMINAL_PROMPT=0`, including the `HEAD` read, the fetch, the
    `update-ref` and the push."""
    monkeypatch.delenv("GIT_TERMINAL_PROMPT", raising=False)
    _isolate_git(tmp_path, monkeypatch)
    home = tmp_path / "home"
    origin = _bare(tmp_path)
    repo = _source_repo(tmp_path, "repo", origin)
    real_run = subprocess.run
    calls = []

    def recording(args, *a, **kw):
        env = kw.get("env")
        calls.append((list(args), dict(env) if env is not None else dict(os.environ)))
        return real_run(args, *a, **kw)

    _write_spec(repo, "TE-60")
    mutants_file = tmp_path / "TE-60.yaml"
    _write_mutants_file(mutants_file, "TE-60")

    monkeypatch.setattr(subprocess, "run", recording)
    assert _run_mutant(home, repo, "TE-60", mutants_file) == 0
    monkeypatch.setattr(subprocess, "run", real_run)

    def matching(predicate):
        return [(args, env) for args, env in calls if predicate(args)]

    head_reads = matching(lambda a: any(e.startswith("HEAD:") for e in a))
    fetches = matching(lambda a: "fetch" in a)
    updates = matching(lambda a: "update-ref" in a)
    pushes = matching(lambda a: "push" in a)
    assert head_reads and fetches and updates and pushes
    for group in (head_reads, fetches, updates, pushes):
        for _, env in group:
            assert env.get("GIT_TERMINAL_PROMPT") == "0"
