---
id: b-2bc0d5
title: Cell images and the build cache are never reclaimed, so every worktree a cell ran from leaves its image behind
status: open
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§4.5, §5.1]
related: []
---

## Problem

Measured on the dev laptop on 2026-10-11, when free disk fell to 16 GB.

`container system df` showed 34 images at 43.52 GB, 42 GB of it reclaimable.
It also showed one container at 84.45 GB. That container was the runtime's
`buildkit` builder, running since 2026-09-23. Removing both freed the disk to
269 GB.

Two leaks fill it, and nothing in `saffron/` reclaims either.

- **One image per directory.** `cell_tag` (`saffron/repos/image.py:24`) tags
  each image `saffron/cell:<directory name>`. A cell run from a worktree builds
  under that worktree's name. The host held 27 such tags over 8 distinct
  digests, and most named worktrees long gone.
- **The build cache.** Every `saffron cell` and `saffron batch` rebuilds the
  base and the repo image (`build_cell_image`). The builder keeps every layer
  it ever built, and Saffron never stops it or prunes it.

A cell's teardown removes its container, networks and volumes
(`saffron/cell/session.py`). `saffron gc` (§4.5) covers volumes and
worktrees. Neither touches an image or the builder. The preflight headroom
check detects the full disk but reclaims nothing, which §4.5 itself names as
the failure it exists to prevent.

## Done looks like

- A cell image is tagged by repo, or the tag a cell built is removed once no
  live task uses it. Twenty worktrees of one repo then hold one image.
- The build cache is bounded. A batch start prunes it, or caps it, through
  the cell runtime's own command spelled in `runtimes/`.
- A test builds two cells from two worktree names and asserts the image count
  afterwards.

## Record

- 2026-10-11: filed after a hand cleanup (`container builder delete --force`,
  `container image prune -a`) reclaimed about 128 GB of runtime storage.
