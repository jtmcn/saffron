# Structured output in the pinned Agent SDK, measured

Backlog item b-4e0868 asked three questions before any spec. This record
answers them from two runs on the host, 2026-09-23. Total SDK estimate $1.30.

## Setup

- `claude-agent-sdk==0.2.142` in a scratch venv, the version
  `images/cell-base.python.Dockerfile` pins. Python 3.12.
- The schemas are `model_json_schema()` from Saffron's own models: `Plan`,
  `ScopeProposal`, `_Rebuttals`, `_Verdicts`, and a report wrapping
  `_Reported` or `_ReportedWithProbe`. The union is
  `TypeAdapter(Union[Plan, ScopeProposal]).json_schema()`.
- Each turn ran in a scratch directory holding one buggy `calc.py`.
  `allowed_tools=["Read"]`, `setting_sources=[]`.
- The token came from the operator's own shell, scoped to the command.

This ran on the host, not in a cell. The SDK and its bundled CLI are the same
wheel a cell installs. The network path and the container are not measured.

## Results

| Turn | Schema | Outcome |
|---|---|---|
| work | none | `success`, 3 turns, $0.14 |
| resumed | `Plan` | `success`, `structured_output` valid, $0.14 |
| resumed | `_Rebuttals` | `success`, `structured_output` valid, $0.14 |
| fresh | `Plan` or `ScopeProposal` | `ResultError`: API 400 |
| fresh | `_Verdicts` | `success`, `structured_output` valid, $0.16 |
| fresh | lens report | `success`, `structured_output` valid, $0.16 |
| fresh | adequacy report | `success`, `structured_output` valid, $0.21 |
| fresh | unsatisfiable | `success`, `structured_output` null, $0.19 |

**Q1, a resumed session.** The schema holds on a resumed session, and the
context carries. The resumed rebuttal cited `calc.py` line 2, which only the
first turn read. Both resumed turns kept the first turn's `session_id`.

**Q2, the schemas Pydantic generates.** Every object schema was accepted as
generated. That covers `Literal` fields, `additionalProperties: false`, and
`Mutant` nested under `$defs`. The union was refused before the model ran:

```
ResultError: Claude Code returned an error result: API Error: 400
tools.8.custom.input_schema.type: Field required (exit code: 1)
```

The union's top level is `anyOf` with no `type`. A tool input schema needs
`"type": "object"` at its root. The error is raised out of `query()`, not
returned on a `ResultMessage`.

**Q3, a schema no value satisfies.** The turn ends as a success:

```
subtype: success   is_error: false   stop_reason: end_turn
structured_output: null   tool_uses: StructuredOutput x4
```

The CLI rejected three candidate values and the model gave up in prose. The
`subtype` does not report the failure. Only the null `structured_output` does.

## Run 2: the production option shape

The first run used default options. Production turns set `tools` and
`allowed_tools` to one list, `permission_mode="dontAsk"`, `setting_sources=[]`,
`max_turns` and `max_budget_usd`, as `saffron.phases.implement.agent_options`
builds them. `tools` withholds every tool it does not list, and `StructuredOutput`
is a tool. So the second run repeated the turns under that shape. SDK estimate
$0.16.

| Turn | Tools | Schema | Outcome |
|---|---|---|---|
| fresh | `REVIEW_TOOLS` | `_Verdicts` | valid, no denials, `num_turns` 3 |
| work | `IMPLEMENT_TOOLS` | none | `success`, `num_turns` 2 |
| resumed | `IMPLEMENT_TOOLS` | `_Rebuttals` | valid, no denials, `num_turns` 2 |
| fresh | `REVIEW_TOOLS` plus `StructuredOutput` | `_Verdicts` | valid, no denials |
| fresh, `max_turns=1` | `REVIEW_TOOLS` | `_Verdicts` | valid, `num_turns` 2 |

`StructuredOutput` survives `tools` and `dontAsk` without being named in
either list. Naming it changes nothing observed. A turn under `max_turns=1`
still delivered its answer, and reported two turns. One run does not show
whether a ceiling ever cuts the tool call.

## Other observations

- The CLI implements `output_format` as a tool named `StructuredOutput`. A
  turn that answers through it ends with `stop_reason: tool_use`.
- `ResultMessage.result` carries the same JSON as text when the tool succeeds.
- A schema carries every model's docstring as `description`, so the model
  reads them. Nothing here measured whether that changes an answer.
- Fresh turns still read files before answering. The schema constrains the
  answer's shape, not what the turn does first.

## The script

Run from the scratch directory, beside a `schemas/` directory of the JSON
above. Recorded here and not under `scripts/`, because
`.saffron/rules/agent-sdk-import-is-runner-only.yml` forbids the import
anywhere in the tree but `images/agent_runner.py`.

```python
import asyncio, json, pathlib, time
from claude_agent_sdk import ClaudeAgentOptions, query

HERE = pathlib.Path(__file__).parent
SCHEMAS = {p.stem: json.loads(p.read_text()) for p in (HERE / "schemas").glob("*.json")}
WORK = HERE / "work"
WORK.mkdir(exist_ok=True)
(WORK / "calc.py").write_text(
    "def add(a, b):\n    return a - b  # bug: should be a + b\n\n"
    "def test_add():\n    assert add(2, 2) == 4\n"
)
EXTRACT = ("Emit your answer in the required structured format. "
           "Do not change files. Do not run commands.")

def base_options(**extra):
    return ClaudeAgentOptions(cwd=str(WORK), allowed_tools=["Read"],
                              disallowed_tools=["Bash", "Edit", "Write"],
                              setting_sources=[], **extra)

async def turn(prompt, options):
    out = {}
    async for message in query(prompt=prompt, options=options):
        if type(message).__name__ == "ResultMessage":
            out.update(subtype=message.subtype, is_error=message.is_error,
                       session_id=message.session_id, cost=message.total_cost_usd,
                       stop_reason=message.stop_reason,
                       structured_output=message.structured_output)
    return out

def fmt(name):
    return {"type": "json_schema", "schema": SCHEMAS[name]}

async def main():
    work = await turn("Read calc.py and explain the bug in two sentences.", base_options())
    sid = work["session_id"]
    await turn("Write a plan to fix the bug you found. " + EXTRACT,
               base_options(resume=sid, output_format=fmt("plan")))
    await turn("A reviewer filed finding 1: 'add subtracts instead of adding'. "
               "Answer it as a rebuttal. " + EXTRACT,
               base_options(resume=sid, output_format=fmt("rebuttals")))
    for name in ("plan_or_scope", "verdicts", "lens", "adequacy"):
        await turn(f"Read calc.py. Produce a {name} about it. " + EXTRACT,
                   base_options(output_format=fmt(name)))
    impossible = {"type": "object", "additionalProperties": False, "required": ["x"],
                  "properties": {"x": {"type": "integer", "minimum": 5, "maximum": 3}}}
    await turn("Answer with any x. " + EXTRACT,
               base_options(output_format={"type": "json_schema", "schema": impossible}))

asyncio.run(main())
```

The run's own copy also logged message kinds, tool names and timings. It
printed each result as it arrived and caught each turn's exception.

## Addendum, 2026-09-25: beside a file system prompt

`SA-0140` made the runner hand the SDK its system prompt as
`{"type": "file", "path": ...}`. The runs above sent strings. Before
`SA-0141`'s cell, the delegate ran the same SDK pin on the host with a file
system prompt and the production option shape: `tools`, `allowed_tools`,
`permission_mode="dontAsk"`, `setting_sources=[]`, `max_turns=20` and
`max_budget_usd=2.0`. The schemas were `_Rebuttals` and `_Verdicts` from
`saffron/phases/rebut.py` at `55dba385`.

The prompt file told the model to start every `argument` and `reason` with
the word PAPRIKA. That proves the file was read.

| Turn | Schema | Outcome |
|---|---|---|
| work | none | `success`, $0.05 |
| resumed | `_Rebuttals` | `success`, valid, `argument` starts PAPRIKA, $0.07 |
| fresh, `Read`/`Glob`/`Grep` | `_Verdicts` | `success`, valid, `reason` starts PAPRIKA, $0.04 |

The schema and the file prompt both hold on the same turn. Total $0.15.

## Addendum, 2026-09-25: a whole spec as one string

Before `SA-0160` and `SA-0176` moved the spec writer onto `output_format`,
the delegate measured the one case the runs above left open: a large string
value. The SDK pin was 0.2.142 on the host, with the option shape above and
`Bash` among the tools but not allowed. The work turn read a real spec and
was told to prefix its `title:` value with `SPIKE `. The resumed turn carried
`output_format` for an object with one string field, `spec`, and was asked
for the whole revised file, frontmatter first.

| Spec | Chars | Returned | Extract turn | Extract cost | Total cost |
|---|---|---|---|---|---|
| `SA-0167` | 40,153 | identical to the expected text | 130 s | $0.40 | $0.57 |
| `SA-0162` | 45,945 | identical to the expected text | 150 s | $0.41 | $0.55 |

Both values matched the expected text exactly, with no strip needed. The
extraction turn is slow because it writes the whole file as output tokens.
One run each, so a rate of failure is not measured. Not measured in a cell,
and not with a turn ceiling low enough to cut the tool call.
