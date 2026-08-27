# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those
roles to where they surface in this repo's work tracker (spec files), since a
spec on disk carries no GitHub label strings.

| Skill role             | Surfaces in a spec as                                       | Meaning                                          |
| ---------------------- | ----------------------------------------------------------- | ------------------------------------------------ |
| `needs-triage`         | spec without review; a fresh `.saffron/specs/*.md`          | Evaluator needs to assess this spec              |
| `needs-info`           | acceptance criteria under-specified                         | Waiting on additional detail before driving       |
| `ready-for-agent`      | `priority`, `depends_on` clear + criteria tickable          | Fully specified, ready for an AFK agent (`saffron cell`) |
| `ready-for-human`      | `risk: elevated` / blocked on `depends_on`                  | Requires human implementation                     |
| `wontfix`              | acceptance criteria marked N/A / spec closed in `docs/BACKLOG.md` | Will not be actioned                             |

Driving role maps onto a concrete action:

- **`needs-triage`** → skim the spec's frontmatter + acceptance criteria.
- **`ready-for-agent`** → `uv run saffron cell .saffron/specs/<spec>.md --repo .`.
- **`ready-for-human`** → route the spec to a person, don't drive it unattended.

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the
corresponding surfacing from this table rather than creating a GitHub label.
