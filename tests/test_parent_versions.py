import json
from pathlib import Path

from saffron.intake import RETIRED_DIRNAME

DIFF = """\
diff --git a/tests/test_a.py b/tests/test_a.py
index 1111111..2222222 100644
--- a/tests/test_a.py
+++ b/tests/test_a.py
@@ -1,1 +1,1 @@
-old a
+new a
diff --git a/src/a.py b/src/a.py
index 3333333..4444444 100644
--- a/src/a.py
+++ b/src/a.py
@@ -1,1 +1,1 @@
-old src
+new src
diff --git a/tests/test_c.py b/tests/test_c.py
index 5555555..6666666 100644
--- a/tests/test_c.py
+++ b/tests/test_c.py
@@ -1,1 +1,1 @@
-old c
+new c
"""


def _spec_text(spec_id: str, criteria: list[dict]) -> str:
    """Frontmatter-only spec text: id, title, type and an acceptance list."""
    lines = [f"id: {spec_id}", f"title: {spec_id} title", "type: bug", "acceptance:"]
    for criterion in criteria:
        lines.append(f"  - claim: {criterion['claim']}")
        lines.append(f"    witness: {criterion['witness']}")
        if criterion.get("wrong_versions"):
            lines.append("    wrong_versions:")
            for version in criterion["wrong_versions"]:
                lines.append(f"      - {version}")
    return "---\n" + "\n".join(lines) + "\n---\n"


def _write(path: Path, text: str) -> None:
    path.write_text(text)


def _killed(version: str, file: str, find: str, replace: str = "r") -> dict:
    return {
        "version": version,
        "edit": {"file": file, "find": find, "replace": replace},
        "reason": "the witness failed",
        "outcome": "killed",
        "summary": "s",
    }


def test_a_childs_diff_pairs_each_killed_version_of_each_parent_whose_witness_it_edits(
    tmp_path,
):
    from saffron.parent_versions import names_file, parent_version_pairs

    assert names_file("tests/test_a.py::test_x", "tests/test_a.py")
    assert names_file("tests/test_a.py test_x", "tests/test_a.py")
    assert names_file("tests/test_a.py", "tests/test_a.py")

    assert not names_file("tests/test_a.pyi", "tests/test_a.py")
    assert not names_file("tests/test_a.py2", "tests/test_a.py")
    assert not names_file("tests/test_a.py_x", "tests/test_a.py")
    assert not names_file("tests/test_a.py.bak", "tests/test_a.py")
    assert not names_file("tests/test_a.py-old", "tests/test_a.py")
    assert not names_file("tests/test_a.py/sub", "tests/test_a.py")
    assert not names_file("tests/test_b.py", "tests/test_a.py")
    assert not names_file("sub/tests/test_a.py", "tests/test_a.py")
    # The path is a substring of the witness, but not its prefix.
    assert not names_file("xy:ab", "ab")
    assert not names_file("tests/test_a.pyé", "tests/test_a.py")

    specs_dir = tmp_path / "specs"
    retired_dir = specs_dir / RETIRED_DIRNAME
    retired_dir.mkdir(parents=True)
    out_dir = tmp_path / "out"

    _write(retired_dir / "README.md", "not a spec\n")
    _write(specs_dir / "broken.md", "not a spec\n")

    sp1_criteria = [
        {"claim": "c1", "witness": "tests/test_a.py", "wrong_versions": ["v1"]},
        {"claim": "c2", "witness": "tests/test_a.pyi", "wrong_versions": ["v2"]},
        {"claim": "c3", "witness": "tests/test_b.py", "wrong_versions": ["v3"]},
        {"claim": "c4", "witness": "tests/test_c.py", "wrong_versions": ["v4"]},
    ]
    _write(retired_dir / "SP-1.md", _spec_text("SP-1", sp1_criteria))
    _write(
        retired_dir / "SP-2.md",
        _spec_text(
            "SP-2",
            [{"claim": "c5", "witness": "tests/test_c.py", "wrong_versions": ["v5"]}],
        ),
    )
    _write(
        retired_dir / "SP-4.md",
        _spec_text(
            "SP-4",
            [{"claim": "c6", "witness": "tests/test_a.py", "wrong_versions": ["v6"]}],
        ),
    )
    _write(
        specs_dir / "SP-3.md",
        _spec_text(
            "SP-3",
            [
                {"claim": "c7", "witness": "tests/test_a.py", "wrong_versions": ["v7"]},
                {"claim": "c7b", "witness": "tests/test_c.py"},
            ],
        ),
    )
    _write(
        specs_dir / "SP-5.md",
        _spec_text(
            "SP-5",
            [{"claim": "c8", "witness": "tests/test_a.py", "wrong_versions": ["v8"]}],
        ),
    )

    (out_dir / "SP-1").mkdir(parents=True)
    sp1_record = [
        {
            "witness": "tests/test_a.py",
            "claim": "c1",
            "versions": [
                _killed("k1", "a.py", "f1"),
                {
                    "version": "surv",
                    "edit": {"file": "a.py", "find": "f2", "replace": "r"},
                    "reason": "",
                    "outcome": "survived",
                    "summary": "s",
                },
                {
                    "version": "unpr",
                    "edit": {"file": "a.py", "find": "f3", "replace": "r"},
                    "reason": "",
                    "outcome": "unproven",
                    "summary": "s",
                },
                {
                    "version": "err",
                    "edit": {"file": "a.py", "find": "f4", "replace": "r"},
                    "reason": "",
                    "outcome": "error",
                    "summary": "s",
                },
                _killed("k2", "a.py", "f5"),
            ],
        },
        {
            "witness": "tests/test_a.pyi",
            "claim": "c2",
            "versions": [_killed("k_pyi", "a.pyi", "f6")],
        },
        {
            "witness": "tests/test_b.py",
            "claim": "c3",
            "versions": [_killed("k_b", "b.py", "f7")],
        },
        {
            "witness": "tests/test_c.py",
            "claim": "c4",
            "versions": [_killed("k_c", "c.py", "f8")],
        },
        {
            "witness": "tests/test_a.py::test_old",
            "claim": "cold",
            "versions": [_killed("k_old", "a.py", "f9")],
        },
    ]
    (out_dir / "SP-1" / "wrong-versions.json").write_text(json.dumps(sp1_record))

    (out_dir / "SP-2").mkdir(parents=True)
    (out_dir / "SP-2" / "wrong-versions.json").write_text(
        json.dumps(
            [
                {
                    "witness": "tests/test_c.py",
                    "claim": "c5",
                    "versions": [_killed("k_sp2", "c.py", "f10")],
                }
            ]
        )
    )

    (out_dir / "SP-3").mkdir(parents=True)
    (out_dir / "SP-3" / "wrong-versions.json").write_text(
        json.dumps(
            [
                {
                    "witness": "tests/test_a.py",
                    "claim": "c7",
                    "versions": [_killed("k_sp3", "a.py", "f11")],
                },
                {
                    "witness": "tests/test_c.py",
                    "claim": "c7b",
                    "versions": [_killed("k_sp3b", "a.py", "f11b")],
                },
            ]
        )
    )

    pairs, unreadable = parent_version_pairs(
        depends_on=["SP-3", "SP-1", "SP-7", "SP-2"],
        specs_dir=specs_dir,
        out_dir=out_dir,
        diff=DIFF,
    )

    assert unreadable == []
    assert len(pairs) == 5

    criterion, entry = pairs[0]
    assert criterion.claim == "c7"
    assert criterion.witness == "tests/test_a.py"
    assert entry == {
        "parent": "SP-3",
        "witness": "tests/test_a.py",
        "version": "k_sp3",
        "edit": {"file": "a.py", "find": "f11", "replace": "r"},
        "reason": "",
    }

    criterion, entry = pairs[1]
    assert criterion.claim == "c1"
    assert entry["version"] == "k1"
    criterion, entry = pairs[2]
    assert criterion.claim == "c1"
    assert entry["version"] == "k2"
    criterion, entry = pairs[3]
    assert criterion.claim == "c4"
    assert entry["version"] == "k_c"

    criterion, entry = pairs[4]
    assert criterion.claim == "c5"
    assert entry == {
        "parent": "SP-2",
        "witness": "tests/test_c.py",
        "version": "k_sp2",
        "edit": {"file": "c.py", "find": "f10", "replace": "r"},
        "reason": "",
    }

    only_queued_dir = tmp_path / "specs_only_queued"
    only_queued_dir.mkdir()
    _write(
        only_queued_dir / "SP-3.md",
        _spec_text(
            "SP-3",
            [{"claim": "c7", "witness": "tests/test_a.py", "wrong_versions": ["v7"]}],
        ),
    )
    pairs2, unreadable2 = parent_version_pairs(
        depends_on=["SP-3", "SP-1", "SP-7", "SP-2"],
        specs_dir=only_queued_dir,
        out_dir=out_dir,
        diff=DIFF,
    )
    assert unreadable2 == []
    assert len(pairs2) == 1
    criterion, entry = pairs2[0]
    assert criterion.claim == "c7"
    assert entry["version"] == "k_sp3"

    # A diff `integrity` refuses names no changed path.
    assert parent_version_pairs(
        depends_on=["SP-3"],
        specs_dir=only_queued_dir,
        out_dir=out_dir,
        diff="diff --git a/x b/y z\n",
    ) == ([], [])


def test_a_parent_whose_record_cannot_be_read_is_named_and_pairs_nothing(tmp_path):
    from saffron.parent_versions import parent_version_pairs

    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def write_spec(
        spec_id: str, witness: str, wrong_versions: list[str] | None
    ) -> None:
        criterion = {"claim": f"claim for {spec_id}", "witness": witness}
        if wrong_versions:
            criterion["wrong_versions"] = wrong_versions
        _write(specs_dir / f"{spec_id}.md", _spec_text(spec_id, [criterion]))

    write_spec("SP-5", "tests/test_a.py", ["v5"])
    write_spec("SP-6", "tests/test_a.py", ["v6"])
    write_spec("SP-7", "tests/test_a.py", ["v7"])
    write_spec("SP-8", "tests/test_a.py", ["v8"])
    write_spec("SP-9", "tests/test_a.py", ["v9"])
    write_spec("SP-13", "tests/test_a.py", ["v13a", "v13b"])
    write_spec("SP-10", "unrelated/path.py", ["v10"])
    write_spec("SP-11", "tests/test_a.py", None)
    write_spec("SP-12", "unrelated/path2.py", ["v12"])
    write_spec("SP-99", "tests/test_a.py", ["v99"])

    # SP-5: no record directory at all.

    (out_dir / "SP-6").mkdir()
    (out_dir / "SP-6" / "wrong-versions.json").write_text("not json")

    (out_dir / "SP-7").mkdir()
    (out_dir / "SP-7" / "wrong-versions.json").write_text(json.dumps({"not": "a list"}))

    (out_dir / "SP-8").mkdir()
    (out_dir / "SP-8" / "wrong-versions.json").write_text(
        json.dumps([{"witness": "tests/test_a.py", "claim": "c8"}])
    )

    (out_dir / "SP-9").mkdir()
    (out_dir / "SP-9" / "wrong-versions.json").write_text(
        json.dumps(
            [
                {
                    "witness": "tests/test_a.py",
                    "claim": "c9",
                    "versions": [
                        {
                            "version": "v9",
                            "edit": None,
                            "reason": "",
                            "outcome": "killed",
                            "summary": "s",
                        }
                    ],
                }
            ]
        )
    )

    (out_dir / "SP-13").mkdir()
    (out_dir / "SP-13" / "wrong-versions.json").write_text(
        json.dumps(
            [
                {
                    "witness": "tests/test_a.py",
                    "claim": "c13",
                    "versions": [
                        _killed("v13a", "x.py", "foo"),
                        {
                            "version": "v13b",
                            "edit": {"file": "x.py", "replace": "bar"},
                            "reason": "",
                            "outcome": "killed",
                            "summary": "s",
                        },
                    ],
                }
            ]
        )
    )

    (out_dir / "SP-12").mkdir()
    (out_dir / "SP-12" / "wrong-versions.json").write_text("not json either")

    (out_dir / "SP-99").mkdir()
    (out_dir / "SP-99" / "wrong-versions.json").write_text(
        json.dumps(
            [
                {
                    "witness": "tests/test_a.py",
                    "claim": "c99",
                    "versions": [
                        _killed("v99", "x.py", "foo99"),
                        {
                            "version": "v99b",
                            "edit": None,
                            "reason": "",
                            "outcome": "unproven",
                            "summary": "s",
                        },
                    ],
                },
                {"witness": "other-witness-1", "claim": "cO1"},
                {
                    "witness": "other-witness-2",
                    "claim": "cO2",
                    "versions": [
                        {
                            "version": "vO2",
                            "edit": None,
                            "reason": "",
                            "outcome": "killed",
                            "summary": "s",
                        }
                    ],
                },
            ]
        )
    )

    depends_on = [
        "SP-9",
        "SP-5",
        "SP-6",
        "SP-7",
        "SP-8",
        "SP-13",
        "SP-10",
        "SP-11",
        "SP-12",
        "SP-99",
    ]
    pairs, unreadable = parent_version_pairs(
        depends_on=depends_on,
        specs_dir=specs_dir,
        out_dir=out_dir,
        diff=DIFF,
    )

    assert unreadable == ["SP-9", "SP-5", "SP-6", "SP-7", "SP-8", "SP-13"]
    assert len(pairs) == 1
    criterion, entry = pairs[0]
    assert criterion.claim == "claim for SP-99"
    assert entry == {
        "parent": "SP-99",
        "witness": "tests/test_a.py",
        "version": "v99",
        "edit": {"file": "x.py", "find": "foo99", "replace": "r"},
        "reason": "",
    }
