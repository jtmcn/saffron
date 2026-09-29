## Saffron

Saffron runs tasks here from specs in `.saffron/specs/`. Each gate in `.saffron/gates/` wraps one command. Run the same commands before you commit:

- `format`: `FILL`
- `lint`: `FILL`
- `types`: `FILL`
- `tests`: `FILL`
- FILL: the domain gate, and what the agent does to keep it green.
- FILL: each advisory gate, marked advisory, with any floor CI still enforces.

Commit your work before the gates run. An uncommitted change fails `committed`, because the patch a reviewer reads holds only commits.
A test skip or an ignore comment fails `integrity`. Fix the code the gate names instead.
