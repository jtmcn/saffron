# The first live Jev call

Command run for the models list, from the worktree root:

```
uv run --env-file "$SCRATCH/jev.env" python -c "from typesafe_sdk import TypeSafeClient; [print(m.name, m.release_date) for m in TypeSafeClient().models.list().models]"
```

`models.list()` printed two models, both aliases:

```
jev-latest 2026-09-10T18:38:01.391457+00:00
jev-preview 2026-09-10T18:39:06.057655+00:00
```

Neither `name` is a dated build. `MODEL` in `harness/jev_observe.py` stays `"jev-latest"`.

SDK version, from `uv.lock`: `typesafe-sdk==0.7.1`.

Command run to score SA-0117's cell:

```
uv run --env-file "$SCRATCH/jev.env" .claude/skills/run-saffron-spec-loop/driver.py jev SA-0117 --kind cell
```

Output:

```
SA-0117  cell round 1  4 answers  /Users/jm/.saffron/batches/v0/SA-0117
```

Exit code: 0.

## jev.ttl written

```turtle
@prefix earl: <http://www.w3.org/ns/earl#> .
@prefix jev: <urn:software-factory:jev#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

[] a earl:Assertion ;
  earl:assertedBy jev:jev ;
  earl:subject <urn:software-factory:jev:cell:SA-0117:605963dd6fd37286> ;
  earl:test jev:Q1 ;
  earl:mode earl:automatic ;
  earl:result [ a earl:TestResult ; earl:outcome earl:cantTell ;
    jev:distribution "{\"c1\": 1.0, \"c10\": 0.0, \"c11\": 0.0, \"c12\": 0.0, \"c13\": 0.0, \"c14\": 0.0, \"c2\": 0.0, \"c3\": 0.0, \"c4\": 0.0, \"c5\": 0.0, \"c6\": 0.0, \"c7\": 0.0, \"c8\": 0.0, \"c9\": 0.0, \"noMatch\": 0.0}"^^rdf:JSON ] ;
  jev:model "jev-1.13.0" ;
  jev:round 1 ;
  jev:commit "36606e407417b2baface9a7636713d4147539e02" .

[] a earl:Assertion ;
  earl:assertedBy jev:jev ;
  earl:subject <urn:software-factory:jev:cell:SA-0117:605963dd6fd37286> ;
  earl:test jev:Q2 ;
  earl:mode earl:automatic ;
  earl:result [ a earl:TestResult ; earl:outcome earl:cantTell ;
    jev:distribution "{\"0\": 0.01, \"1\": 0.01, \"2\": 0.59, \"3\": 0.39}"^^rdf:JSON ] ;
  jev:model "jev-1.13.0" ;
  jev:round 1 ;
  jev:commit "36606e407417b2baface9a7636713d4147539e02" .

[] a earl:Assertion ;
  earl:assertedBy jev:jev ;
  earl:subject <urn:software-factory:jev:cell:SA-0117:605963dd6fd37286> ;
  earl:test jev:Q3 ;
  earl:mode earl:automatic ;
  earl:result [ a earl:TestResult ; earl:outcome earl:cantTell ;
    jev:distribution "{\"false\": 0.4, \"true\": 0.6}"^^rdf:JSON ] ;
  jev:model "jev-1.13.0" ;
  jev:round 1 ;
  jev:commit "36606e407417b2baface9a7636713d4147539e02" .

[] a earl:Assertion ;
  earl:assertedBy jev:jev ;
  earl:subject <urn:software-factory:jev:cell:SA-0117:round-1> ;
  earl:test jev:Q6 ;
  earl:mode earl:automatic ;
  earl:result [ a earl:TestResult ; earl:outcome earl:cantTell ;
    jev:distribution "{\"false\": 0.4, \"true\": 0.6}"^^rdf:JSON ] ;
  jev:model "jev-1.13.0" ;
  jev:round 1 ;
  jev:commit "36606e407417b2baface9a7636713d4147539e02" .
```

## Distributions, read plain

- Q1 (which criterion the one finding maps to): `c1` gets 1.0, every other criterion and
  `noMatch` get 0.0. SA-0117 has 14 criteria in this list, not nine.
- Q2 (severity level, 0 to 3): `2` gets 0.59, `3` gets 0.39, `0` and `1` get 0.01 each.
- Q3 (a yes/no question about the finding): `true` gets 0.6, `false` gets 0.4.
- Q6 (a yes/no question about the round): `true` gets 0.6, `false` gets 0.4.

## Input tokens

`observe()` in `harness/jev_observe.py` returns only `(response.model, answers)`, so the
driver's Step 3 run did not expose `response.usage`. A second call was made outside the
driver, building the identical round from the same batch files and calling
`client.system_one` directly with `model="jev-latest"`. It read `response.usage` and wrote
no file. That call reported:

```
response.usage: input_tokens=23016 output_tokens=240
```

This number comes from a second, separate call, not from the run recorded above as `jev.ttl`.

## Where the response differed from the design's assumption

- `response.model` came back as `"jev-1.13.0"`, a dated build number, even though the call
  passed `model="jev-latest"`. `models.list()` on the same day did not list `"jev-1.13.0"` as
  a name. The design assumed `models.list()` would be where a dated name shows up. Instead,
  the dated name surfaces only in a scoring response's `model` field.

## Where the record differed from the brief's Step 3 description

- SA-0117's spec lists 14 acceptance criteria, not nine. The brief's expected count of four
  answers held regardless, because Q1 is one question no matter how many criteria it scores
  against.

## Result

DONE_WITH_CONCERNS. No dated Jev name existed in `models.list()` on 2026-09-21, so `MODEL`
stays `"jev-latest"`. The scoring call itself succeeded, matched the expected output line and
exit code, and produced a well-formed `jev.ttl`.
