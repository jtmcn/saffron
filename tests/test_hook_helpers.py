import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK_TESTS = (
    "test_dead_gate.py",
    "test_prose_gate.py",
    "test_terms_hook.py",
    "test_retired_vocabulary_hook.py",
)
SHARED = {"_hook_config", "_git_in", "_tracked"}


def test_the_hook_tests_share_one_helper_module_and_no_stale_revert_reason():
    """b-a99c76: three hook tests restated the same helpers and one stale reason."""
    for name in HOOK_TESTS:
        tree = ast.parse((HERE / name).read_text())
        own = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        if name != "test_retired_vocabulary_hook.py":
            assert not own & SHARED, (name, own & SHARED)
        docstring = ast.get_docstring(tree) or ""
        assert "script deleted" not in docstring, name
