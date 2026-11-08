"""`saffron.mutants`: reading a criterion's mutant from `refs/saffron/mutants`
(backlog item 80). Every name this module adds is imported inside each test
body, since `saffron.mutants` does not exist at the tree base.
"""

from __future__ import annotations

import subprocess

import pytest


def _bare(tmp_path):
    repo = tmp_path / "m.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", str(repo)], check=True, capture_output=True
    )
    return repo


def _commit(repo, files: dict[str, str], message: str) -> str:
    """A root commit over `files`, built with `hash-object`, `mktree` and
    `commit-tree`, so two calls never share history."""
    entries = []
    for path, content in files.items():
        blob = subprocess.run(
            ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
            input=content,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        entries.append(f"100644 blob {blob}\t{path}\n")
    tree = subprocess.run(
        ["git", "-C", str(repo), "mktree"],
        input="".join(entries),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=T",
            "commit-tree",
            tree,
            "-m",
            message,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_mutants_are_read_from_the_ref_by_spec_id_and_witness(tmp_path):
    """`ref_commit`, `read_mutants` and `parse_mutants` over a bare mirror
    with no fetch involved, since criterion 1 already covers the fetch."""
    from saffron.intake import Mutant
    from saffron.mutants import parse_mutants, read_mutants, ref_commit

    repo = _bare(tmp_path)
    assert ref_commit(repo) is None
    assert read_mutants(repo, None, "SA-1") == {}

    first = _commit(
        repo,
        {
            "SA-1.yaml": (
                "tests/test_a.py::test_one:\n"
                "  file: a.py\n"
                "  find: x\n"
                "  replace: y\n"
                "tests/test_a.py::test_two:\n"
                "  file: b.py\n"
                "  find: z\n"
            ),
            "SA-2.yaml": "{}\n",
        },
        "first mutants commit",
    )
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", "refs/saffron/mutants", first],
        check=True,
        capture_output=True,
    )
    assert ref_commit(repo) == first
    text = subprocess.run(
        ["git", "-C", str(repo), "show", f"{first}:SA-1.yaml"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert read_mutants(repo, first, "SA-1") == parse_mutants(text, "SA-1.yaml")
    assert read_mutants(repo, first, "SA-1") == {
        "tests/test_a.py::test_one": Mutant(file="a.py", find="x", replace="y"),
        "tests/test_a.py::test_two": Mutant(file="b.py", find="z"),
    }
    assert read_mutants(repo, first, "SA-2") == {}
    # A tree that holds no file at all for this spec id, not an empty one.
    assert read_mutants(repo, first, "SA-999") == {}

    second = _commit(
        repo,
        {
            "SA-1.yaml": "tests/test_a.py::test_one:\n  file: a.py\n  find: w\n",
            "SA-1.yml": "tests/test_a.py::test_one:\n  file: a.py\n  find: decoy\n",
        },
        "second, unrelated mutants commit",
    )
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", "refs/saffron/mutants", second],
        check=True,
        capture_output=True,
    )
    assert ref_commit(repo) == second
    assert read_mutants(repo, second, "SA-1") == {
        "tests/test_a.py::test_one": Mutant(file="a.py", find="w"),
    }
    # The commit a task pinned earlier still reads as it did, whatever the
    # ref points at now.
    assert read_mutants(repo, first, "SA-1") == {
        "tests/test_a.py::test_one": Mutant(file="a.py", find="x", replace="y"),
        "tests/test_a.py::test_two": Mutant(file="b.py", find="z"),
    }


def test_each_criterion_takes_its_own_witnesses_mutant_from_the_ref():
    from saffron.intake import Mutant, parse_spec
    from saffron.mutants import attach_mutants

    spec = parse_spec(
        "---\nid: TE-1\ntitle: t\ntype: feature\n"
        "acceptance:\n"
        "  - claim: c1\n    witness: w1\n"
        "  - claim: c2\n    witness: w2\n"
        "  - claim: c3\n    witness: w3\n"
        "---\n\nbody\n"
    )
    mutant2 = Mutant(file="b.py", find="beta_edit")
    mutant1 = Mutant(file="a.py", find="alpha_edit")
    # Written in the reverse of the criteria's order, w3 absent entirely.
    found = {"w2": mutant2, "w1": mutant1}

    attached = attach_mutants(spec, found)
    attached_w1, attached_w2, attached_w3 = attached.acceptance
    assert attached_w1.mutant == mutant1
    assert attached_w2.mutant == mutant2
    assert attached_w3.mutant is None

    # The handed spec is a copy's source, never mutated itself.
    assert all(criterion.mutant is None for criterion in spec.acceptance)


def test_a_mutants_file_that_cannot_apply_to_its_spec_is_refused():
    """The six parse failures, and the three ways a parsed file still
    cannot pair with its spec. Then the disclosure check `attach_mutants`
    re-runs once a mutant is in place."""
    from saffron.intake import DisclosedMutantError, Mutant, SpecError, parse_spec
    from saffron.mutants import MutantsError, attach_mutants, parse_mutants

    bad_files = [
        "key: [\n",
        "- a\n- b\n",
        "w1: not_a_mapping\n",
        "w1:\n  find: x\n",
        "w1:\n  file: a.py\n  find: ''\n",
        "w1:\n  file: a.py\n  find: x\n  extra: 1\n",
    ]
    for text in bad_files:
        with pytest.raises(SpecError) as excinfo:
            parse_mutants(text, "SA-1.yaml")
        assert isinstance(excinfo.value, SpecError)

    def spec_with(fields: str):
        return parse_spec(
            f"---\nid: TE-1\ntitle: t\ntype: feature\nacceptance:\n{fields}---\n\nbody\n"
        )

    stray = spec_with("  - claim: c\n    witness: w1\n  - claim: c\n    witness: w2\n")
    with pytest.raises(MutantsError):
        attach_mutants(stray, {"unknown": Mutant(file="a.py", find="x")})

    shared = spec_with(
        "  - claim: c\n    witness: dup\n  - claim: c\n    witness: dup\n"
    )
    with pytest.raises(MutantsError):
        attach_mutants(shared, {})

    subject_only = spec_with("  - claim: c\n    witness: w1\n    subject: a/b.py\n")
    with pytest.raises(MutantsError):
        attach_mutants(subject_only, {})

    body_disclosed = parse_spec(
        "---\nid: TE-1\ntitle: t\ntype: feature\n"
        "acceptance:\n  - claim: c\n    witness: w1\n"
        "---\n\nthe literal max(total, 0) is here\n"
    )
    with pytest.raises(DisclosedMutantError):
        attach_mutants(
            body_disclosed, {"w1": Mutant(file="a.py", find="max(total, 0)")}
        )

    claim_disclosed = spec_with(
        "  - claim: the constant stays at CEILING_X\n    witness: w1\n"
        "  - claim: nothing else changes\n    witness: w2\n"
    )
    with pytest.raises(DisclosedMutantError):
        attach_mutants(claim_disclosed, {"w2": Mutant(file="a.py", find="CEILING_X")})

    wrong_version_disclosed = spec_with(
        "  - claim: c\n    witness: w1\n"
        "    wrong_versions:\n      - a version that keeps RATE_Y fixed\n"
    )
    with pytest.raises(DisclosedMutantError):
        attach_mutants(
            wrong_version_disclosed, {"w1": Mutant(file="a.py", find="RATE_Y")}
        )
