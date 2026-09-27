Record your review's findings now. The value is an object with one key,
`findings`. Its value is an array with one entry per finding you raised, in
the order you raised them. Each entry holds `severity` (`blocker`, `concern`
or `note`), `claim`, `criterion`, `file`, `line` and `fixes`. `criterion` is
the criterion number a finding concerns, or null for a finding about the
whole spec. `file` and `line` are null for a finding that names no place.

Your review's own tags are `scope`, `build` and `witness`. Copy each
finding's `fixes` exactly as your review gave it, and decide no tag from
the prose. `fixes` is null where your review named no tag.

Answer now in the required structured format.
Do not change files.
Do not run commands.
