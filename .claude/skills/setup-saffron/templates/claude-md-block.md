## Saffron

Saffron runs tasks here from specs in `.saffron/specs/`. Each gate in `.saffron/gates/` wraps one command. Run the same commands before you commit:

- `format`: `FILL`
- `lint`: `FILL`
- `types`: `FILL`
- `tests`: `FILL`

Commit your work before the gates run. An uncommitted change fails `committed`, because the patch a reviewer reads holds only commits.
A test skip or an ignore comment fails `integrity`. Fix the code the gate names instead.
