"""Where the ontology lives, for the tests that read it."""

from pathlib import Path

ONTOLOGY = Path(__file__).resolve().parents[2] / "ontology"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
NS = "https://saffron.dev/ns#"

VOCABULARY = ONTOLOGY / "saffron.ttl"
SHAPES = sorted((ONTOLOGY / "shapes").glob("*.ttl"))
QUERIES = sorted((ONTOLOGY / "queries").glob("*.rq"))
VENDOR = sorted((ONTOLOGY / "vendor").glob("*.ttl"))
EXPECTED = ONTOLOGY / "queries" / "expected"
NEGATIVE = sorted((FIXTURES / "negative").glob("*.ttl"))
