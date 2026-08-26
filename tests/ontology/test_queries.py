"""Every committed query runs against the fixture graph and is asserted on."""

import pyoxigraph as ox
import pytest
from ontology_paths import EXPECTED, NS, QUERIES


def run(store, query_path):
    """CSV rows, newline-normalized — the serializer emits CRLF per RFC 4180 and
    a committed fixture read back through universal newlines would never match."""
    result = store.query(query_path.read_text())
    return result.serialize(format=ox.QueryResultsFormat.CSV).decode().splitlines()


@pytest.mark.parametrize("query", QUERIES, ids=lambda p: p.stem)
def test_query_returns_the_committed_result(store, query):
    actual = run(store, query)
    expected = (EXPECTED / f"{query.stem}.csv").read_text().splitlines()
    assert actual == expected


@pytest.mark.parametrize("query", QUERIES, ids=lambda p: p.stem)
def test_query_is_not_empty(store, query):
    """A query that returns nothing has not been shown to answer anything."""
    assert len(run(store, query)) > 1


@pytest.mark.parametrize("query", QUERIES, ids=lambda p: p.stem)
def test_query_states_its_sql_equivalent(query):
    """Each .rq opens with the SQL-equivalence challenge. A query that skips it
    has not been argued for, only written."""
    header = "\n".join(
        line for line in query.read_text().splitlines() if line.startswith("#")
    )
    assert "SQL equivalent:" in header
    assert "preferable" in header or "no reasonable" in header


def test_q1_finds_a_criterion_nothing_automatic_asserted_on(store):
    """The bucket-triage question (§8): the operator rejected on a criterion and
    no gate or lens had reached it. An unbound assertor is the whole signal."""
    rows = list(store.query((QUERIES[0]).read_text()))
    assert rows, "Q1 must find the rejected task's failed criterion"
    assert any(row[2] is None for row in rows)


def test_q3_names_a_declared_gate_that_never_ran(store):
    """Set containment across two populations — declared and executed. The
    §4.1 schema stores the declared side nowhere."""
    rows = list(store.query((QUERIES[2]).read_text()))
    never_ran = [r[0] for r in rows if str(r[1].value) == "false"]
    assert len(never_ran) == 1


def test_q4_reconstructs_a_merged_change_end_to_end(store):
    """N5 as a machine-checkable property: every artifact kind between spec and
    PR is reachable from the PR by derivation alone."""
    rows = list(store.query((QUERIES[3]).read_text()))
    kinds = {str(r[2]).removeprefix(f"<{NS}").removesuffix(">") for r in rows}
    assert kinds == {
        "Spec",
        "ScopeProposal",
        "TouchesSet",
        "Plan",
        "Diff",
        "GateSuite",
        "Finding",
        "Rebuttal",
        "PullRequest",
    }


def test_q4_excludes_a_merged_pr_whose_chain_is_broken(store):
    """The fixture's second merged PR records no derivation back to its spec.
    N5 is only a property if a change that fails it is visibly absent — a query
    that returned it anyway would be reporting reachability it never checked."""
    prs = {str(r[0]) for r in store.query((QUERIES[3]).read_text())}
    assert "<https://saffron.dev/data/pr-t4>" not in prs
    merged = list(
        store.query(f"""
        PREFIX saffron: <{NS}>
        SELECT ?t WHERE {{ ?t saffron:endedInState saffron:MERGED }}""")
    )
    assert len(merged) == 2, "both merged tasks are in the fixture"
