from __future__ import annotations

import pytest

from saffron.intake import Mutant
from saffron.mutation import MutationError, MutationResult, apply_mutant, restore_mutant


def test_applying_a_mutant_returns_what_it_displaced(tmp_path):
    target = tmp_path / "a.py"
    target.write_text("def total():\n    return max(x, 0)\n")
    mutant = Mutant(file="a.py", find="max(x, 0)", replace="x")

    result = apply_mutant(tmp_path, mutant)

    assert result.ok
    assert result.displaced == b"max(x, 0)"
    assert target.read_text() == "def total():\n    return x\n"

    restore_mutant(tmp_path, mutant, result)
    assert target.read_text() == "def total():\n    return max(x, 0)\n"


def test_a_deletion_mutant_with_an_empty_replace_also_restores(tmp_path):
    """`Mutant.replace` defaults to `""` — a guard or clamp removed outright,
    arguably the most ordinary mutant to write. Restoring must not depend on
    finding `replace` in the file: an empty string "matches" every position,
    so a restore that searched for it the way it searches for a non-empty
    `replace` would never find exactly one place to reinsert `displaced`."""
    target = tmp_path / "a.py"
    target.write_text("def total():\n    return max(x, 0)\n")
    mutant = Mutant(file="a.py", find="max(x, 0)", replace="")

    result = apply_mutant(tmp_path, mutant)

    assert result.ok
    assert result.displaced == b"max(x, 0)"
    assert target.read_text() == "def total():\n    return \n"

    restore_mutant(tmp_path, mutant, result)
    assert target.read_text() == "def total():\n    return max(x, 0)\n"


def test_restoring_when_replace_recurs_elsewhere_in_the_file(tmp_path):
    """A non-empty `replace` that happens to already exist elsewhere in the
    file must not make restoring ambiguous — the applier records *where* it
    edited, so restoring never has to search the file for `replace` at all."""
    target = tmp_path / "a.py"
    target.write_text("x = 1\ndef total():\n    return max(x, 0)\n")
    mutant = Mutant(file="a.py", find="max(x, 0)", replace="x")

    result = apply_mutant(tmp_path, mutant)
    assert result.ok
    assert target.read_text() == "x = 1\ndef total():\n    return x\n"

    restore_mutant(tmp_path, mutant, result)
    assert target.read_text() == "x = 1\ndef total():\n    return max(x, 0)\n"


def test_a_find_that_matches_twice_does_not_apply(tmp_path):
    target = tmp_path / "a.py"
    target.write_text("max(x, 0)\nmax(x, 0)\n")
    mutant = Mutant(file="a.py", find="max(x, 0)", replace="x")

    result = apply_mutant(tmp_path, mutant)

    assert not result.ok
    assert result.displaced is None
    assert "a.py" in result.reason
    # Left untouched — a mutant that does not apply must not edit the first
    # occurrence silently.
    assert target.read_text() == "max(x, 0)\nmax(x, 0)\n"


def test_a_find_that_matches_nothing_does_not_apply(tmp_path):
    target = tmp_path / "a.py"
    original = "def total():\n    return x\n"
    target.write_text(original)
    mutant = Mutant(file="a.py", find="max(x, 0)", replace="x")

    result = apply_mutant(tmp_path, mutant)

    assert not result.ok
    assert result.displaced is None
    # Must read as "this mutant did not apply", never as "the witness
    # survived" — which means naming the file and the text, not just failing.
    assert "a.py" in result.reason
    assert "max(x, 0)" in result.reason
    assert target.read_text() == original


def test_apply_then_restore_is_byte_identical(tmp_path):
    target = tmp_path / "a.py"
    # CRLF line endings and no trailing newline: exactly what text-mode I/O
    # would silently normalize away.
    original = b"def total():\r\n    return max(x, 0)\r\n    # no trailing nl"
    target.write_bytes(original)
    mutant = Mutant(file="a.py", find="max(x, 0)", replace="x")

    result = apply_mutant(tmp_path, mutant)
    assert result.ok
    assert target.read_bytes() != original

    restore_mutant(tmp_path, mutant, result)
    assert target.read_bytes() == original


def test_a_mutant_cannot_escape_the_tree_it_is_applied_to(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "a.py").write_text("max(x, 0)\n")
    outside = tmp_path / "outside.txt"
    outside.write_text("max(x, 0)\n")

    mutant = Mutant(file="../outside.txt", find="max(x, 0)", replace="x")
    result = apply_mutant(tree, mutant)

    assert not result.ok
    assert result.displaced is None
    # Never touched, whatever the reason says.
    assert outside.read_text() == "max(x, 0)\n"

    absolute = Mutant(file=str(outside), find="max(x, 0)", replace="x")
    result = apply_mutant(tree, absolute)
    assert not result.ok
    assert outside.read_text() == "max(x, 0)\n"


def test_restoring_across_the_tree_boundary_also_refuses(tmp_path):
    """The same guard on the way back — `restore_mutant` never writes outside
    the tree it was given either, even if a caller mistakenly hands it one
    that would."""
    tree = tmp_path / "tree"
    tree.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x\n")

    mutant = Mutant(file="../outside.txt", find="max(x, 0)", replace="x")
    fake_result = MutationResult(ok=True, displaced=b"max(x, 0)", offset=0)
    with pytest.raises(MutationError):
        restore_mutant(tree, mutant, fake_result)
    assert outside.read_text() == "x\n"
