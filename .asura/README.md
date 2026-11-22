# ASURA's branch of Void's package recipes

This repository is a fork of void-linux/void-packages.

- `master` is always identical to Void's master. Never commit to it.
- `asura` is `master` plus the recipes ASURA maintains: the Hyprland stack
  (listed in `.asura/stack`) and the rebuilds their library changes need.
  All ASURA work and every pull request targets `asura`.

Workflows (on `asura`):

- `asura-sync`: daily, fast-forwards `master` from Void and rebases `asura`
  onto it. If the rebase conflicts it pushes nothing and fails, so the
  conflict is fixed by hand.
- `asura-bump`: daily, checks each package in `.asura/stack` for a newer
  upstream release, and opens one pull request into `asura` with the new
  versions and checksums. It never merges.
- Void's own `Check build` workflow lints and builds every package a pull
  request changes.

ASURA's main repository (mohitjoer/ASURA-OS) builds the stack from `asura`,
tests it against ASURA's desktop, and publishes it in ASURA's signed package
repository.

When a library's soname changes, add its new line to `common/shlibs` and bump
`revision=` of every package built against it (xbps-src names them).
