---
id: b-7aefb8
title: "`factory:claim` carries two `rdfs:domain` triples, so a reasoner reads every finding as a principle"
status: open
tier: 3
filed: 2026-10-24
specs: [SA-0319]
prs: []
commits: []
cites: [§4.6]
related: []
---

## Problem

`ontology/factory.ttl` declares `factory:claim` twice. One declaration gives
`rdfs:domain factory:Finding`, and the design-record block gives
`rdfs:domain factory:Principle`. RDFS intersects two domains, so anything with
a claim is inferred to be both a finding and a principle.

Nothing runs a reasoner today, and SHACL is what runs. The `owl:disjointWith`
axioms are stated for external reasoners, and this property breaks the graph
for exactly those readers.

## Done looks like

Two properties, one per domain, and every shape and query that names
`factory:claim` names the right one. A test fails when one property carries two
domains.

## Record

- 2026-10-24: filed from a review of the controlled vocabulary against SKOS
  practice.
