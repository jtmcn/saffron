# The refusal predicate, built twice — Phase B's primary record

Run 2026-09-04, for `DESIGN.md` Appendix O's spike. The verdict and the four
answers live in `docs/superpowers/plans/2026-09-02-ontology-authoritative.md`;
this file is the material they were measured on, so a later reader can check
rather than trust.

**The artifacts are here rather than in `tests/ontology/fixtures/`, where the
plan's B1 asked for them, because they cannot live there.** The `shacl` gate is
blocking and validates every tracked `.ttl` against `ontology/shapes/`, and these
fixtures fail it by design: six tasks have no `endedInState` and no `riskTier`,
and eight `TouchesSet` nodes have no `ratifiedBy`. That is not a defect in the
fixtures — it is Q3's finding in its sharpest form. B1 as written is unsatisfiable.

## What the first write-up got wrong

The first version of this spike asserted that glob matching is **not expressible**
in SHACL, and rested Q2 and half of Q4 on a false refusal that followed from it.
Review falsified it. `scope._to_regex`'s translation table can be rebuilt with
SPARQL 1.1 `REPLACE` at validation time, from the pattern literal already in the
graph — no emitter, nothing pre-translated. The corrected shape agrees with
`scope.matches` on all 18 adversarial pairs below and returns the correct verdict
on all four R5 fixtures.

The objection that survives is different and is stated in Q3/Q4: the translation
table ends up **reimplemented in SPARQL**, where nothing tests it and no gate
compares it against `scope.py`.

## The shape arm as first built — the naive R5

Its R5 approximated a glob by stripping a trailing `**` and taking a prefix. That
is what produced the false refusal on `**/size.py`. Kept here because the
correction is the finding.

```turtle
@prefix sh:      <http://www.w3.org/ns/shacl#> .
@prefix saffron: <https://saffron.dev/ns#> .
@prefix sp:      <https://saffron.dev/spike#> .

# The refusal predicate of DESIGN.md §4.2 gate 0 and §4.2.1, as SHACL.
# Written from the prose. saffron/scheduler.py was not read before this file.
# A violation means REFUSE.

sp:R1 a sh:NodeShape ;
    sh:targetClass saffron:Task ;
    sh:sparql [ a sh:SPARQLConstraint ;
        sh:message "R1: an open PR from another task already targets this spec" ;
        sh:prefixes sp: ;
        sh:select """
            SELECT $this WHERE {
              $this <https://saffron.dev/spike#inState> ?s ;
                    <https://saffron.dev/spike#forSpec> ?spec .
              ?pr <https://saffron.dev/spike#targets> ?spec ;
                  <https://saffron.dev/spike#isOpen> true ;
                  <https://saffron.dev/spike#openedByTask> ?other .
              FILTER (?other != $this)
            }
        """ ] .

sp:R3 a sh:NodeShape ;
    sh:targetClass saffron:Task ;
    sh:sparql [ a sh:SPARQLConstraint ;
        sh:message "R3: the spec_sha moved under this task" ;
        sh:select """
            SELECT $this WHERE {
              $this <https://saffron.dev/spike#inState> ?s ;
                    <https://saffron.dev/spike#atSpecSha> ?was ;
                    <https://saffron.dev/spike#forSpec> ?spec .
              ?spec <https://saffron.dev/spike#currentSpecSha> ?now .
              FILTER (?was != ?now)
            }
        """ ] .

sp:R6 a sh:NodeShape ;
    sh:targetClass saffron:Task ;
    sh:sparql [ a sh:SPARQLConstraint ;
        sh:message "R6: a depends_on parent will not merge as it stands" ;
        sh:select """
            SELECT $this WHERE {
              $this <https://saffron.dev/spike#inState> ?s ;
                    <https://saffron.dev/spike#forSpec> ?spec .
              ?spec <https://saffron.dev/spike#dependsOn> ?parent .
              ?ptask <https://saffron.dev/spike#forSpec> ?parent ;
                     <https://saffron.dev/ns#endedInState> ?pstate .
              FILTER (?pstate NOT IN (
                <https://saffron.dev/ns#MERGED>,
                <https://saffron.dev/ns#READY_FOR_REVIEW>,
                <https://saffron.dev/ns#APPROVED>
              ))
            }
        """ ] .

# R5 — a criterion naming a path no `touches` pattern matches.
# §4.2.1: "It matches globs, not strings." SHACL has no glob operator, so this
# is the closest expressible approximation: treat a trailing `**` as a prefix.
sp:R5 a sh:NodeShape ;
    sh:targetClass saffron:Task ;
    sh:sparql [ a sh:SPARQLConstraint ;
        sh:message "R5: an acceptance criterion names a path no touches pattern reaches" ;
        sh:select """
            SELECT $this WHERE {
              $this <https://saffron.dev/spike#inState> ?s ;
                    <https://saffron.dev/spike#forSpec> ?spec .
              ?spec <https://saffron.dev/ns#hasCriterion> ?crit .
              ?crit <https://saffron.dev/spike#namesPath> ?path .
              # Skipped when touches is empty: the documented shape for a bug
              # awaiting DIAGNOSE. NOT EXISTS is vacuously true on an empty set,
              # so the unguarded form refuses the whole bug class.
              FILTER EXISTS {
                ?spec <https://saffron.dev/spike#declaresTouches> ?any .
                ?any <https://saffron.dev/spike#pattern> ?anyp .
              }
              FILTER NOT EXISTS {
                ?spec <https://saffron.dev/spike#declaresTouches> ?tw .
                ?tw <https://saffron.dev/spike#pattern> ?pat .
                FILTER (STRSTARTS(?path, REPLACE(?pat, "\\\\*\\\\*$", "")))
              }
            }
        """ ] .
```

## The corrected R5

```turtle
@prefix sh:      <http://www.w3.org/ns/shacl#> .
@prefix saffron: <https://saffron.dev/ns#> .
@prefix sp:      <https://saffron.dev/spike#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .

sp:decls a owl:Ontology ;
    sh:declare [ sh:prefix "sp" ; sh:namespace "https://saffron.dev/spike#" ] ;
    sh:declare [ sh:prefix "saffron" ; sh:namespace "https://saffron.dev/ns#" ] .

# R5, corrected: `scope._to_regex`'s translation table rebuilt in SPARQL at
# validation time. Nothing is pre-translated in the graph and no emitter runs.
sp:R5corrected a sh:NodeShape ;
    sh:targetClass saffron:Task ;
    sh:sparql [ a sh:SPARQLConstraint ;
        sh:message "R5: an acceptance criterion names a path no touches pattern reaches" ;
        sh:prefixes sp:decls ;
        sh:select """
            SELECT $this WHERE {
              $this sp:inState ?s ; sp:forSpec ?spec .
              ?spec saffron:hasCriterion ?crit .
              ?crit sp:namesPath ?path .
              FILTER EXISTS { ?spec sp:declaresTouches ?any . ?any sp:pattern ?anyp . }
              FILTER NOT EXISTS {
                ?spec sp:declaresTouches ?tw .
                ?tw sp:pattern ?pat .
                FILTER(REGEX(?path, CONCAT("^",
  REPLACE(REPLACE(REPLACE(REPLACE(
    REPLACE(REPLACE(REPLACE(REPLACE(
      REPLACE(?pat, "([.+^$(){}\\\\[\\\\]|\\\\\\\\])", "\\\\\\\\$1"),
    "\\\\*\\\\*/", "«A»"), "\\\\*\\\\*", "«B»"), "\\\\*", "«C»"), "\\\\?", "«D»"),
  "«A»", "(?:[^/]+/)*"), "«B»", ".*"), "«C»", "[^/]*"), "«D»", "[^/]"),
"$")))
              }
            }
        """ ] .
```

### Agreement with `scope.matches`, 18 pairs

| pattern | path | `scope.matches` | SPARQL |
|---|---|---|---|
| `**/size.py` | `saffron/gates/core/size.py` | True | True |
| `**/size.py` | `size.py` | True | True |
| `saffron/gates/**` | `saffron/cli.py` | False | False |
| `saffron/gates/core/**` | `saffron/gates/core/size.py` | True | True |
| `saffron/**/c.py` | `saffron/a/b/c.py` | True | True |
| `saffron/**/c.py` | `saffron/c.py` | True | True |
| `tests/test_*.py` | `tests/sub/test_a.py` | False | False |
| `tests/test_*.py` | `tests/test_a.py` | True | True |
| `*.py` | `a/x.py` | False | False |
| `*.py` | `x.py` | True | True |
| `a.b.py` | `axb.py` | False | False |
| `a?c.py` | `abc.py` | True | True |
| `a?c.py` | `a/c.py` | False | False |
| `**` | `any/deep/path.py` | True | True |
| `docs/[a]/x.py` | `docs/[a]/x.py` | True | True |
| `c++/x.py` | `c++/x.py` | True | True |
| `saffron/**` | `saffron/` | True | True |
| `CONTEXT.md` | `CONTEXT.md` | True | True |

18/18 agree.

## The fixtures

Twelve tasks, ten of them in flight (`sp:t6p` and `sp:t7p` carry
`saffron:endedInState` and are the parents a dependency refusal reads).

```turtle
@prefix saffron: <https://saffron.dev/ns#> .
@prefix sp:      <https://saffron.dev/spike#> .

# Hand-authored in-flight tasks, one per refusal §4.2.1 states, plus the two
# cases the prose says must NOT refuse. Authored from the prose.

sp:policy a saffron:Policy ; sp:protectedPath "CONTEXT.md" , "DESIGN.md" .
sp:repo sp:preflightPassed true ; sp:retiredByPath "saffron/replay.py" .

# R1 — an open PR from ANOTHER task already targets this spec.  REFUSE
sp:s1 a saffron:Spec ; sp:currentSpecSha "s1a" ; sp:declaresTouches sp:tw1 .
sp:tw1 a saffron:TouchesSet ; sp:pattern "saffron/a/**" .
sp:t1 a saffron:Task ; sp:forSpec sp:s1 ; sp:atSpecSha "s1a" ; sp:inState sp:QUEUED .
sp:t0 a saffron:Task ; sp:forSpec sp:s1 ; sp:atSpecSha "s1a" ; sp:inState sp:REVIEWING .
sp:pr1 a saffron:PullRequest ; sp:targets sp:s1 ; sp:openedByTask sp:t0 ; sp:isOpen true .

# R1' — the re-queue case: the ONLY open PR is this task's own.  ADMIT
sp:s9 a saffron:Spec ; sp:currentSpecSha "s9a" ; sp:declaresTouches sp:tw9 .
sp:tw9 a saffron:TouchesSet ; sp:pattern "saffron/i/**" .
sp:t9 a saffron:Task ; sp:forSpec sp:s9 ; sp:atSpecSha "s9a" ; sp:inState sp:QUEUED .
sp:pr9 a saffron:PullRequest ; sp:targets sp:s9 ; sp:openedByTask sp:t9 ; sp:isOpen true .

# R3 — the spec_sha moved under the task.  REFUSE
sp:s3 a saffron:Spec ; sp:currentSpecSha "bbb" ; sp:declaresTouches sp:tw3 .
sp:tw3 a saffron:TouchesSet ; sp:pattern "saffron/c/**" .
sp:t3 a saffron:Task ; sp:forSpec sp:s3 ; sp:atSpecSha "aaa" ; sp:inState sp:QUEUED .

# R6a — parent is EXHAUSTED: will not merge as it stands.  REFUSE
sp:s6p a saffron:Spec ; sp:currentSpecSha "p" .
sp:t6p a saffron:Task ; sp:forSpec sp:s6p ; sp:atSpecSha "p" ;
       saffron:endedInState saffron:EXHAUSTED .
sp:s6 a saffron:Spec ; sp:currentSpecSha "s6a" ; sp:dependsOn sp:s6p ; sp:declaresTouches sp:tw6 .
sp:tw6 a saffron:TouchesSet ; sp:pattern "saffron/f/**" .
sp:t6 a saffron:Task ; sp:forSpec sp:s6 ; sp:atSpecSha "s6a" ; sp:inState sp:QUEUED .

# R6b — parent at READY_FOR_REVIEW admits its dependent (stacked).  ADMIT
sp:s7p a saffron:Spec ; sp:currentSpecSha "q" .
sp:t7p a saffron:Task ; sp:forSpec sp:s7p ; sp:atSpecSha "q" ;
       saffron:endedInState saffron:READY_FOR_REVIEW .
sp:s7 a saffron:Spec ; sp:currentSpecSha "s7a" ; sp:dependsOn sp:s7p ; sp:declaresTouches sp:tw7 .
sp:tw7 a saffron:TouchesSet ; sp:pattern "saffron/g/**" .
sp:t7 a saffron:Task ; sp:forSpec sp:s7 ; sp:atSpecSha "s7a" ; sp:inState sp:QUEUED .

# R5a — a criterion naming a path NO touches pattern reaches.  REFUSE
sp:s5 a saffron:Spec ; sp:currentSpecSha "s5a" ; sp:declaresTouches sp:tw5 ; saffron:hasCriterion sp:c5 .
sp:tw5 a saffron:TouchesSet ; sp:pattern "saffron/gates/**" .
sp:c5 a saffron:AcceptanceCriterion ; sp:namesPath "saffron/cli.py" .
sp:t5 a saffron:Task ; sp:forSpec sp:s5 ; sp:atSpecSha "s5a" ; sp:inState sp:QUEUED .

# R5b — the false-refusal trap §4.2.1 names: the glob DOES match.  ADMIT
sp:s8 a saffron:Spec ; sp:currentSpecSha "s8a" ; sp:declaresTouches sp:tw8 ; saffron:hasCriterion sp:c8 .
sp:tw8 a saffron:TouchesSet ; sp:pattern "saffron/gates/core/**" .
sp:c8 a saffron:AcceptanceCriterion ; sp:namesPath "saffron/gates/core/size.py" .
sp:t8 a saffron:Task ; sp:forSpec sp:s8 ; sp:atSpecSha "s8a" ; sp:inState sp:QUEUED .

# R5c — a bug awaiting DIAGNOSE: touches is empty, so R5 is skipped.  ADMIT
sp:s10 a saffron:Spec ; sp:currentSpecSha "s10a" ; saffron:specType saffron:bug ;
       saffron:hasCriterion sp:c10 .
sp:c10 a saffron:AcceptanceCriterion ; sp:namesPath "saffron/anything.py" .
sp:t10 a saffron:Task ; sp:forSpec sp:s10 ; sp:atSpecSha "s10a" ; sp:inState sp:QUEUED .

# R5d — a leading-** glob. Real glob matching says this MATCHES, so the spec is
# satisfiable and must be ADMITted. §4.2.1: "a false refusal at gate 0 costs a
# whole spec overnight with no cell started and nothing to notice until morning."
sp:s11 a saffron:Spec ; sp:currentSpecSha "s11a" ; sp:declaresTouches sp:tw11 ; saffron:hasCriterion sp:c11 .
sp:tw11 a saffron:TouchesSet ; sp:pattern "**/size.py" .
sp:c11 a saffron:AcceptanceCriterion ; sp:namesPath "saffron/gates/core/size.py" .
sp:t11 a saffron:Task ; sp:forSpec sp:s11 ; sp:atSpecSha "s11a" ; sp:inState sp:QUEUED .
```

### Scored

| task | case | expected | naive arm | corrected R5 |
|---|---|---|---|---|
| `sp:t1` | open PR from another task | REFUSE | REFUSE | — |
| `sp:t9` | only open PR is this task's own | ADMIT | ADMIT | — |
| `sp:t3` | `spec_sha` moved | REFUSE | REFUSE | — |
| `sp:t6` | parent `EXHAUSTED` | REFUSE | REFUSE | — |
| `sp:t7` | parent `READY_FOR_REVIEW` | ADMIT | ADMIT | — |
| `sp:t5` | criterion outside `touches` | REFUSE | REFUSE | REFUSE |
| `sp:t8` | criterion inside a `**` glob | ADMIT | ADMIT | ADMIT |
| `sp:t10` | bug, `touches` empty | ADMIT | ADMIT (after a guard was added) | ADMIT |
| `sp:t11` | leading-`**` glob | ADMIT | **REFUSE — wrong** | ADMIT |

## The vocabulary the predicate needs

27 terms here plus `MERGE_TRAIN` = 28, against the vocabulary's 92 (`rdflib`
subject count in the `saffron:` namespace, less the `owl:Ontology` node).

Nine of the 28 are the in-flight state class and its eight individuals; a
modelling that read "has not ended" as the *absence* of `endedInState` would cut
the count to about 20. The number is doing rhetorical work in Q3, so its
sensitivity to that choice is stated here rather than left for a reader to find.

```turtle
@prefix saffron: <https://saffron.dev/ns#> .
@prefix sp:      <https://saffron.dev/spike#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .

# Spike vocabulary: the terms §4.2.1's refusal predicate needs and
# ontology/saffron.ttl does not declare. Written from the prose of §4.2 gate 0
# and §4.2.1, before reading saffron/scheduler.py. Counted for question 3.

## In-flight states. The vocabulary declares none: every state it has is an
## EndState, and TaskShape requires endedInState minCount 1. A task the
## scheduler reasons about has not ended.
sp:InFlightState a owl:Class .
sp:DRAFT a sp:InFlightState . sp:QUEUED a sp:InFlightState .
sp:DIAGNOSING a sp:InFlightState . sp:IMPLEMENTING a sp:InFlightState .
sp:GATING a sp:InFlightState . sp:REPAIRING a sp:InFlightState .
sp:REVIEWING a sp:InFlightState . sp:REBUTTING a sp:InFlightState .

## Identity and versioning of the thing being scheduled.
sp:forSpec        a owl:ObjectProperty ; rdfs:domain saffron:Task ; rdfs:range saffron:Spec .
sp:atSpecSha      a owl:DatatypeProperty ; rdfs:domain saffron:Task ; rdfs:range xsd:string .
sp:currentSpecSha a owl:DatatypeProperty ; rdfs:domain saffron:Spec ; rdfs:range xsd:string .
sp:inState        a owl:ObjectProperty ; rdfs:domain saffron:Task .

## Declared blast radius, as patterns rather than paths.
sp:declaresTouches a owl:ObjectProperty ; rdfs:domain saffron:Spec ; rdfs:range saffron:TouchesSet .
sp:pattern         a owl:DatatypeProperty ; rdfs:domain saffron:TouchesSet ; rdfs:range xsd:string ;
    rdfs:comment "A glob, not a path. §4.2.1: touches is glob-matched everywhere it is enforced." .

## Dependencies.
sp:dependsOn a owl:ObjectProperty ; rdfs:domain saffron:Spec ; rdfs:range saffron:Spec .

## Pull requests, which gate 0 reads and the run record does not relate.
sp:targets      a owl:ObjectProperty ; rdfs:domain saffron:PullRequest ; rdfs:range saffron:Spec .
sp:openedByTask a owl:ObjectProperty ; rdfs:domain saffron:PullRequest ; rdfs:range saffron:Task .
sp:isOpen       a owl:DatatypeProperty ; rdfs:domain saffron:PullRequest ; rdfs:range xsd:boolean .
sp:changedFile  a owl:DatatypeProperty ; rdfs:domain saffron:PullRequest ; rdfs:range xsd:string .

## Criteria, protected paths, retirement markers, preflight.
sp:namesPath      a owl:DatatypeProperty ; rdfs:domain saffron:AcceptanceCriterion ; rdfs:range xsd:string .
sp:protectedPath  a owl:DatatypeProperty ; rdfs:domain saffron:Policy ; rdfs:range xsd:string .
sp:retiredByPath  a owl:DatatypeProperty ; rdfs:range xsd:string .
sp:preflightPassed a owl:DatatypeProperty ; rdfs:range xsd:boolean .
sp:malformed      a owl:DatatypeProperty ; rdfs:domain saffron:Spec ; rdfs:range xsd:boolean .
sp:retiredToDone  a owl:DatatypeProperty ; rdfs:domain saffron:Spec ; rdfs:range xsd:boolean .
sp:declaresId     a owl:DatatypeProperty ; rdfs:domain saffron:Spec ; rdfs:range xsd:boolean .
```

## Which refusals were shaped

Four of the eight: R1 (open PR from another task), R3 (malformed / `spec_sha`
moved), R5 (criterion path vs `touches`), R6 (`depends_on` parent state). Not
shaped: R2 (`touches` vs an open PR's changed files), R4 (preflight), R7
(`touches` vs protected paths), R8 (`saffron:retired-by` marker vs `touches`).

R4 is a boolean and was skipped as trivial. R2, R7 and R8 are glob refusals and
were skipped on the false premise above — with the corrected translation they are
expressible too, so **no conclusion here rests on their absence.**

Two shapes are also incomplete against the prose, and both gaps cut *against* the
shape arm: R6 omits `MERGE_TRAIN` and the `done/`-retirement admission and never
refuses "no task at the parent's current `spec_sha`"; R3 covers only the moved
`spec_sha` and `sp:malformed` is declared and read by nothing. No fixture probes
where the shape arm under-refuses, so Q2's "nothing the shapes catch and the
Python misses" is asserted over fixtures that do not test that direction.

## Provenance, per shape

All four were written from `DESIGN.md` §4.2 gate 0 and §4.2.1's prose, with
`saffron/scheduler.py` unread; the scheduler was opened only to score the arms.
The evidence that the discipline held is in what the shapes do *not* contain:
R6's admit set omits `MERGE_TRAIN` (which `DEPENDENCY_WAITING_STATES` has), R5
approximated the glob rather than using `scope._to_regex`'s four-token table, and
neither the `forbidden` carve-out nor the `_path_tokens` glob-character skip
appears anywhere.
