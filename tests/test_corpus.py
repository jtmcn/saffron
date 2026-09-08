from pathlib import Path

from harness import corpus

FIXTURES = Path(__file__).parent.parent / "docs" / "evidence" / "fixtures"


def test_the_corpus_is_every_fixture_directory_under_the_root():
    """A directory, not a list in code: adding a fixture is a directory, and
    the harness is not edited to admit it."""
    loaded = corpus.load_corpus(FIXTURES)
    assert [f.spec_id for f in loaded] == sorted(f.spec_id for f in loaded)
    assert "SA-0062" in {f.spec_id for f in loaded}


def test_a_directory_without_a_fixture_toml_is_not_a_fixture(tmp_path):
    """`docs/evidence/fixtures/` may hold a README or a stray export; only a
    directory declaring itself is loaded."""
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "README.md").write_text("not a fixture")
    assert corpus.load_corpus(tmp_path) == []
