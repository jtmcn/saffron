"""The `prose` gate (docs/superpowers/specs/2026-09-16-prose-ratchet-design.md).

The script is loaded inside each test, never at module scope: the `revert`
gate re-runs a new witness with the script deleted.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GATES = REPO / ".saffron" / "gates"
SCRIPT = GATES / "prose.py"
LONG_A = "alpha " * 30 + "end."
LONG_B = "beta " * 30 + "end."


def _prose():
    spec = importlib.util.spec_from_file_location("saffron_prose_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered first: `Hit` is a dataclass under postponed annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _codes(text: str, path: str = "README.md", root: Path = REPO) -> list[str]:
    return [f.code for f in _prose().check(text, path, "prose", root=root)]


HITS = [
    ("sentence-length", "word " * 26 + "end."),
    ("hedge", "The gate should pass."),
    ("hedge", "The gate may pass."),
    ("hedge", "The gate might pass."),
    ("em-dash", "The cell stops — then it restarts."),
    ("em-dash", "The cell stops -- then it restarts."),
    ("em-dash", "The cell stops - then it restarts."),
    ("semicolon", "The cell stops; it restarts."),
    ("filler", "The gate actually passes."),
    ("filler", "The gate passes, in fact."),
    ("perfect-tense", "The gate has been declared."),
    ("perfect-tense", "The gate has passed."),
    ("contraction", "The gate doesn't pass."),
    ("contraction", "The cell stops, and it's done."),
    ("contraction", "That's the gate."),
    ("contraction", "Here's the gate."),
]


@pytest.mark.parametrize("code,text", HITS)
def test_each_rule_fires_on_its_own_hit(code, text):
    assert _codes(text) == [code]


MISSES = [
    ("sentence-length", "word " * 24 + "end."),
    ("sentence-length", "# " + "word " * 30),
    ("sentence-length", "```\n" + "word " * 30 + "\n```\n"),
    ("hedge", 'The rule flags "should" in prose.'),
    ("hedge", "The gate calls `should_pass` first."),
    ("hedge", "The design changed in May 2026."),
    ("em-dash", "Rows 3–5 hold the ranges."),
    ("em-dash", "- The first item.\n- The second item."),
    ("filler", "The suite has exactly one baseline."),
    ("filler", "The choice was made deliberately."),
    ("perfect-tense", "The gate had a result."),
    ("contraction", "The gate's result is green."),
    ("trailing-condition", "The gate fails when the cell stops."),
]


@pytest.mark.parametrize("code,text", MISSES)
def test_each_rule_holds_its_measured_false_positive(code, text):
    assert code not in _codes(text)


def test_a_trailing_condition_is_read_only_in_a_spec_instruction():
    item = "- Run the gate when the cell stops.\n"
    assert _codes(item, ".saffron/specs/SA-0001-x.md") == ["trailing-condition"]
    assert "trailing-condition" not in _codes(item, "docs/backlog/1-x.md")
    assert (
        _codes("- If the cell stops, run the gate.\n", ".saffron/specs/SA-0001-x.md")
        == []
    )


def test_a_quoted_condition_is_a_mention_in_a_spec_instruction():
    item = '- Say "stop when done" to the agent.\n'
    assert "trailing-condition" not in _codes(item, ".saffron/specs/SA-0001-x.md")


def test_a_quote_wrapped_onto_the_next_line_is_still_a_mention():
    assert _codes('The rule flags "a word that\nshould go" in prose.') == []
    # One break only: a stray quote cannot hide a paragraph.
    assert _codes('A stray " quote.\nThe gate\nshould pass. "End.') == ["hedge"]


def test_a_numbered_item_is_read_as_its_own_list_item():
    assert _codes(
        "1. Run the gate when the cell stops.\n", ".saffron/specs/SA-0001-x.md"
    ) == ["trailing-condition"]
    assert _codes(
        "  2. Run the gate when the cell stops.\n", ".saffron/specs/SA-0001-x.md"
    ) == ["trailing-condition"]


def test_a_numbered_reference_still_splits_the_sentence():
    # Merged, this would be 29 words (over the limit); split, neither half is.
    text = "word " * 6 + "rev 21. " + "word " * 20 + "end."
    assert "sentence-length" not in _codes(text)


def test_a_mid_sentence_ordinal_is_not_read_as_a_list_item():
    text = "The count is 3. 4. Stop the gate when it fails."
    assert "trailing-condition" not in _codes(text, ".saffron/specs/SA-0001-x.md")


def test_a_list_item_is_its_own_sentence():
    items = "".join(f"- {'word ' * 15}end\n" for _ in range(3))
    assert "sentence-length" not in _codes(items)


def test_a_hit_names_its_source_line():
    text = "```\ncode\n```\n\nIntro.\n\nThe gate should pass.\n"
    (hit,) = _prose().check(text, "README.md", "prose", root=REPO)
    assert (hit.line, hit.code) == (7, "hedge")


def test_a_defined_term_is_never_filler(tmp_path):
    (tmp_path / "ontology").mkdir()
    shutil.copy(REPO / "ontology" / "spans.py", tmp_path / "ontology" / "spans.py")
    assert _codes("It actually works.", root=tmp_path) == ["filler"]
    (tmp_path / "CONTEXT.md").write_text("**Actually**: a defined term.\n")
    assert _codes("It actually works.", root=tmp_path) == []


def test_a_closed_set_member_is_never_filler(tmp_path):
    (tmp_path / "ontology").mkdir()
    shutil.copy(REPO / "ontology" / "spans.py", tmp_path / "ontology" / "spans.py")
    (tmp_path / "CONTEXT.md").write_text("**Risk tier**: `standard` or `quietly`.\n")
    assert _codes("It quietly works.", root=tmp_path) == []


def test_the_real_vocabulary_protects_elevated(monkeypatch):
    prose = _prose()
    assert {"elevated", "standard"} <= prose.protected_words(REPO)
    monkeypatch.setattr(prose, "FILLER", (*prose.FILLER, "elevated"))
    assert prose.check("An elevated task.", "README.md", "prose", root=REPO) == []


def test_a_rendered_principle_is_counted_once():
    claim = "word " * 30
    design = (
        "## Principles — an index\n\n"
        "| # | The claim | From |\n|---|---|---|\n"
        f"| 1 | {claim} | A |\n\n"
        "## Appendix A\n\n"
        f"1. **{claim}.** Body.\n"
    )
    assert _codes(design, "DESIGN.md").count("sentence-length") == 1
    assert _codes(design, "README.md").count("sentence-length") == 2


def test_a_rendered_closed_set_is_not_counted():
    members = ", ".join(f"`m{i}`" for i in range(30))
    context = f"**Risk tier**: {members}.\n"
    assert _codes(context, "CONTEXT.md") == []
    assert _codes(context, "README.md") == ["sentence-length"]


def test_every_rule_code_has_a_message():
    prose = _prose()
    codes = {code for code, _ in HITS} | {"trailing-condition", "rendered-span"}
    assert set(prose.MESSAGES) == codes
    assert all(word in prose.MESSAGES["filler"] for word in prose.FILLER[:3])


def test_a_duplicated_closed_set_definition_is_a_hit():
    context = "**Severity**: `a` or `b`.\n\n**Severity**: `c`.\n"
    assert _codes(context, "CONTEXT.md") == ["rendered-span"]


def test_a_principle_index_without_its_header_is_a_hit():
    design = "## Principles — an index\n\nNo table here.\n"
    assert _codes(design, "DESIGN.md") == ["rendered-span"]


def _run_gate(name: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(GATES / name)], cwd=cwd, capture_output=True, text=True, timeout=120
    )


def _init(repo: Path, files: dict[str, str]) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)


def test_prose_names_its_tool_and_reports_on_this_repo():
    from saffron.gates.contract import parse_gate_json

    done = _run_gate("prose", REPO)
    assert done.returncode == 0, done.stderr
    result = parse_gate_json(done.stdout, expected_gate="prose")
    assert result.status in ("pass", "fail"), result.summary
    assert result.tool and result.tool.startswith("saffron-prose ")
    messages = _prose().MESSAGES
    assert all(f.message == messages[f.code] for f in result.failures)


def test_prose_reports_the_version_the_script_printed():
    from saffron.gates.contract import parse_gate_json

    printed = subprocess.run(
        [sys.executable, str(SCRIPT), "--version"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    result = parse_gate_json(_run_gate("prose", REPO).stdout, expected_gate="prose")
    assert result.tool == printed


def test_prose_passes_a_clean_tree_and_fails_a_long_sentence(tmp_path):
    from saffron.gates.contract import parse_gate_json

    _init(tmp_path, {"README.md": "The gate passes.\n", "notes.txt": LONG_A})
    clean = parse_gate_json(_run_gate("prose", tmp_path).stdout, expected_gate="prose")
    assert (clean.status, clean.failures) == ("pass", [])

    (tmp_path / "README.md").write_text(LONG_A + "\n")
    red = parse_gate_json(_run_gate("prose", tmp_path).stdout, expected_gate="prose")
    assert red.status == "fail"
    assert [(f.file, f.line, f.code) for f in red.failures] == [
        ("README.md", 1, "sentence-length")
    ]


def test_a_message_is_constant_per_rule(tmp_path):
    from saffron.gates.contract import parse_gate_json

    _init(tmp_path, {"README.md": "The gate should pass.\n\nThe cell might stop.\n"})
    result = parse_gate_json(_run_gate("prose", tmp_path).stdout, expected_gate="prose")
    assert [f.line for f in result.failures] == [1, 3]
    assert len({f.message for f in result.failures}) == 1


def test_a_mangled_closed_set_fails_rather_than_errors(tmp_path):
    from saffron.gates.contract import parse_gate_json

    context = "**Severity**: `a` or `b`.\n\n**Severity**: `c`.\n"
    _init(tmp_path, {"CONTEXT.md": context})
    (tmp_path / "ontology").mkdir()
    shutil.copy(REPO / "ontology" / "spans.py", tmp_path / "ontology" / "spans.py")
    result = parse_gate_json(_run_gate("prose", tmp_path).stdout, expected_gate="prose")
    assert result.status == "fail", result.summary
    assert [(f.file, f.code) for f in result.failures] == [
        ("CONTEXT.md", "rendered-span")
    ]


def test_prose_errors_rather_than_passes_when_nothing_is_in_scope(tmp_path):
    from saffron.gates.contract import parse_gate_json

    _init(tmp_path, {"notes.txt": "nothing to read\n"})
    result = parse_gate_json(_run_gate("prose", tmp_path).stdout, expected_gate="prose")
    assert result.status == "error"
    assert "in scope" in result.summary


def test_a_rewritten_hit_is_not_new_and_an_added_one_is():
    """The per-file limit is baseline subtraction over `(file, code, message)`."""
    from saffron.gates.baseline import subtract_baseline
    from saffron.gates.contract import Failure, GateResult

    prose = _prose()

    def result(text: str) -> GateResult:
        failures = [
            Failure(
                file="README.md",
                line=f.line,
                code=f.code,
                message=prose.MESSAGES[f.code],
            )
            for f in prose.check(text, "README.md", "prose", root=REPO)
        ]
        return GateResult(gate="prose", status="fail", tool="t", failures=failures)

    base = [result(LONG_A + "\n")]
    assert subtract_baseline([result("Intro.\n\n" + LONG_B + "\n")], base) == []
    added = subtract_baseline([result(LONG_A + "\n\n" + LONG_B + "\n")], base)
    assert [(n.gate, n.failure.code) for n in added] == [("prose", "sentence-length")]


def test_scope_reaches_every_place_it_names():
    prose = _prose()
    listed = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    for name in prose.ROOT_FILES:
        assert name in listed and prose.in_scope(name), name
    for directory in prose.INCLUDED_DIRS:
        assert any(p.startswith(directory) and prose.in_scope(p) for p in listed), (
            directory
        )


def test_scope_leaves_the_records_alone():
    prose = _prose()
    assert prose.EXCLUDED_DIRS == (".saffron/specs/done/",)
    for record in (
        ".saffron/specs/done/SA-0001-x.md",
        "docs/evidence/2026-01-01-x.md",
        "docs/superpowers/specs/x.md",
        "docs/backlog/notes.txt",
    ):
        assert not prose.in_scope(record), record
    assert prose.in_scope(".claude/skills/a/b/SKILL.md")
