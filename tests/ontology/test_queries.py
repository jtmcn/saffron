"""Every committed query runs against the fixture graph and is asserted on."""

import pyoxigraph as ox
import pytest
from ontology_paths import EXPECTED, FIXTURES, NS, QUERIES, VENDOR, VOCABULARY


def query(stem_prefix: str):
    """By name, never by position in the glob — a renamed or inserted query would
    otherwise retarget these tests silently, and most would still pass."""
    (found,) = [q for q in QUERIES if q.stem.startswith(stem_prefix)]
    return found


def _solutions(store, text: str) -> ox.QuerySolutions:
    """`Store.query` returns one of three result kinds; every query asserted on
    here is a SELECT. Narrowed at the call, so a query rewritten as an ASK
    fails here rather than at the first attribute read on a row."""
    result = store.query(text)
    assert isinstance(result, ox.QuerySolutions), type(result).__name__
    return result


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
    rows = list(_solutions(store, query("Q1").read_text()))
    assert rows, "Q1 must find the rejected task's failed criterion"
    assert any(row["assertor"] is None for row in rows)


def test_q3_names_a_declared_gate_that_never_ran(store):
    """Set containment across two populations — declared and executed. The
    §4.1 schema stores the declared side nowhere."""
    rows = list(_solutions(store, query("Q3").read_text()))
    never_ran = [r["gate"] for r in rows if r["everRan"].value == "false"]
    assert len(never_ran) == 1


def test_q4_reconstructs_a_merged_change_end_to_end(store):
    """N5 as a machine-checkable property: every artifact kind between spec and
    PR is reachable from the PR by derivation alone — asserted per PR, because a
    union across PRs lets one complete chain cover for an incomplete one."""
    chains: dict[str, set[str]] = {}
    for row in _solutions(store, query("Q4").read_text()):
        kind = str(row["kind"]).removeprefix(f"<{NS}").removesuffix(">")
        chains.setdefault(str(row["pr"]), set()).add(kind)
    assert chains, "no merged PR reconstructed"
    for pr, kinds in chains.items():
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
        }, f"{pr} is in the result with an incomplete chain: {sorted(kinds)}"


def test_q4_excludes_a_merged_pr_whose_chain_is_broken(store):
    """The fixture's second merged PR records no derivation back to its spec.
    N5 is only a property if a change that fails it is visibly absent — a query
    that returned it anyway would be reporting reachability it never checked."""
    prs = {str(r["pr"]) for r in _solutions(store, query("Q4").read_text())}
    assert "<https://saffron.dev/data/pr-t4>" not in prs
    merged = list(
        store.query(f"""
        PREFIX saffron: <{NS}>
        SELECT ?t WHERE {{ ?t saffron:endedInState saffron:MERGED }}""")
    )
    assert len(merged) == 2, "both merged tasks are in the fixture"


# ── The mutations that found the defects above, kept so they cannot come back ──


def mutated(extra: str) -> ox.Store:
    """The lifecycle graph plus a few triples. Every query below broke on one of
    these, and each broke silently — returning a plausible number, not an error."""
    store = ox.Store()
    for path in [VOCABULARY, FIXTURES / "lifecycle.ttl", *VENDOR]:
        store.bulk_load(path=str(path), format=ox.RdfFormat.TURTLE)
    store.load(extra, format=ox.RdfFormat.TURTLE, base_iri="https://saffron.dev/data/")
    return store


PREAMBLE = """
@prefix saffron: <https://saffron.dev/ns#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix earl: <http://www.w3.org/ns/earl#> .
@prefix : <https://saffron.dev/data/> .
"""


def test_q3_a_red_advisory_gate_does_not_unseat_a_sole_blocking_failure():
    """`coverage` is red on a merged task in the fixture, so advisory failures are
    the ordinary case. Counting one as a co-failure zeroes the §8 ranking."""
    store = mutated(
        PREAMBLE
        + """
        :gr-t2-1-cov a saffron:GateResult ; prov:wasGeneratedBy :suite-t2-1 ;
            earl:assertedBy saffron:coverage ; earl:subject :diff-t2-1 ;
            earl:mode earl:automatic ; earl:result [ earl:outcome earl:failed ] .
        """
    )
    rows = {
        str(r["gate"]): r["soleFailures"].value
        for r in _solutions(store, query("Q3").read_text())
    }
    assert rows["<https://saffron.dev/data/g-types>"] == "1"


def test_q3_a_gate_that_fired_in_another_run_still_never_fired_in_this_one():
    """Unscoped, "never fired" is permanently false against an accumulating
    ledger the moment a gate fires once anywhere."""
    store = mutated(
        PREAMBLE
        + """
        :run-2 a saffron:Run ; prov:used :policy-1 ; saffron:baseSha "aa11bb2" .
        :task-x a saffron:Task ; prov:wasInformedBy :run-2 ; prov:used :spec-t2 ;
            saffron:riskTier saffron:standard ; saffron:endedInState saffron:EXHAUSTED .
        :ph-x a saffron:Phase ; prov:wasInformedBy :task-x .
        :at-x a saffron:Attempt ; saffron:withinPhase :ph-x ; saffron:n 1 .
        :suite-x a saffron:GateSuite ; prov:wasInformedBy :at-x .
        :gr-x-nonet a saffron:GateResult ; prov:wasGeneratedBy :suite-x ;
            earl:assertedBy :g-nonet ; earl:subject :diff-t2-1 ;
            earl:mode earl:automatic ; earl:result [ earl:outcome earl:passed ] .
        """
    )
    never_ran = {
        (str(r["run"]), str(r["gate"]))
        for r in _solutions(store, query("Q3").read_text())
        if r["everRan"].value == "false"
    }
    assert (
        "<https://saffron.dev/data/run-1>",
        "<https://saffron.dev/data/g-nonet>",
    ) in never_ran


def test_q4_a_rejected_task_reusing_the_spec_is_not_reconstructible():
    """One spec reaching two tasks is ordinary. Tied to the spec rather than the
    task, N5's check passes an unmerged change on the merge's own evidence."""
    store = mutated(
        PREAMBLE
        + """
        :task-t1b a saffron:Task ; prov:wasInformedBy :run-1 ; prov:used :spec-t1 ;
            saffron:riskTier saffron:elevated ; saffron:endedInState saffron:REJECTED .
        :ph-t1b a saffron:Phase ; prov:wasInformedBy :task-t1b .
        :at-t1b a saffron:Attempt ; saffron:withinPhase :ph-t1b ; saffron:n 1 ;
            prov:generated :diff-t1b .
        :diff-t1b a saffron:Diff ; prov:wasDerivedFrom :plan-t1 .
        :pr-t1b a saffron:PullRequest ; prov:wasDerivedFrom :diff-t1b .
        """
    )
    prs = {str(r["pr"]) for r in _solutions(store, query("Q4").read_text())}
    assert prs == {"<https://saffron.dev/data/pr-t1>"}


def test_q5_a_merged_task_with_no_cost_estimate_still_counts_as_accepted():
    """A crashed session may report every cost field as zero (§4.1). The cost
    should read low; the denominator of cost-per-accepted-PR should not move."""
    store = mutated(
        PREAMBLE
        + """
        :spec-t5 a saffron:Spec ; saffron:specType saffron:refactor ;
            saffron:hasCriterion :ac-t5-1 .
        :ac-t5-1 a saffron:AcceptanceCriterion .
        :task-t5 a saffron:Task ; prov:wasInformedBy :run-1 ; prov:used :spec-t5 ;
            saffron:riskTier saffron:standard ; saffron:endedInState saffron:MERGED .
        :ph-t5 a saffron:Phase ; prov:wasInformedBy :task-t5 .
        :at-t5 a saffron:Attempt ; saffron:withinPhase :ph-t5 ; saffron:n 1 .
        """
    )
    rows = {
        (str(r["specType"]), str(r["riskTier"])): r["accepted"].value
        for r in _solutions(store, query("Q5").read_text())
    }
    assert (
        rows[("<https://saffron.dev/ns#refactor>", "<https://saffron.dev/ns#standard>")]
        == "1"
    )


def test_q1_a_finding_without_a_mode_is_not_reported_as_silence():
    """An unbound assertor is Q1's entire signal — that nothing automatic reached
    a criterion the operator rejected on. A missing optional leg must not fake it."""
    store = mutated(
        PREAMBLE
        + """
        :finding-t3-2 a saffron:Finding ; saffron:severity saffron:concern ;
            earl:assertedBy :lens-contract ; earl:subject :diff-t3-1 ;
            earl:test :ac-t3-1 ; earl:result [ earl:outcome earl:failed ] .
        """
    )
    rows = list(_solutions(store, query("Q1").read_text()))
    assert all(r["assertor"] is not None for r in rows)


def test_q3_a_red_size_at_standard_risk_does_not_unseat_a_sole_blocking_failure():
    """`size` is advisory at standard risk and blocking at `elevated` (§5.4, §5.6).
    A level tested as `!= advisory` counts it as a co-failure at both tiers, which
    is the same half-sentence that survived two revisions of DESIGN.md itself."""
    store = mutated(
        PREAMBLE
        + """
        :gr-t2-1-size a saffron:GateResult ; prov:wasGeneratedBy :suite-t2-1 ;
            earl:assertedBy saffron:size ; earl:subject :diff-t2-1 ;
            earl:mode earl:automatic ; earl:result [ earl:outcome earl:failed ] .
        """
    )
    rows = {
        str(r["gate"]): r["soleFailures"].value
        for r in _solutions(store, query("Q3").read_text())
    }
    assert rows["<https://saffron.dev/data/g-types>"] == "1"


def test_q3_a_red_size_at_elevated_risk_does_unseat_it():
    """The other half of the same sentence — a tier-blind fix in either direction
    is wrong, and only one of these two tests fails for each."""
    store = mutated(
        PREAMBLE
        + """
        :gr-t1-1-size-red a saffron:GateResult ; prov:wasGeneratedBy :suite-t1-1 ;
            earl:assertedBy saffron:size ; earl:subject :diff-t1-1 ;
            earl:mode earl:automatic ; earl:result [ earl:outcome earl:failed ] .
        """
    )
    rows = {
        str(r["gate"]): r["soleFailures"].value
        for r in _solutions(store, query("Q3").read_text())
    }
    assert rows["<https://saffron.dev/data/g-lint>"] == "0"


def test_q4_a_merged_pr_reaching_its_spec_by_a_shortcut_is_not_end_to_end():
    """Reaching the spec is not reconstructing the change. The per-PR assertion
    is what separates them; a union of kinds across PRs cannot."""
    store = mutated(PREAMBLE + ":diff-t4-1 prov:wasDerivedFrom :spec-t4 .")
    chains: dict[str, set[str]] = {}
    for row in _solutions(store, query("Q4").read_text()):
        chains.setdefault(str(row["pr"]), set()).add(str(row["kind"]))
    assert len(chains["<https://saffron.dev/data/pr-t4>"]) < 9
