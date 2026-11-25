# ASURA's branch of Void's package recipes

This repository is a fork of void-linux/void-packages.

- `master` is always identical to Void's master. Never commit to it.
- `Toren` is Void's master merged with the recipes ASURA maintains: the Hyprland stack
  (listed in `.asura/stack`) and the rebuilds their library changes need.
  All ASURA work and every pull request targets `Toren`.

Workflows (on `Toren`):

- `asura-sync`: daily, fast-forwards `master` from Void and merges it into
  `Toren` (the same as GitHub's "Sync fork" button, so either can be used).
  History is never rewritten. If the merge conflicts it pushes nothing and
  fails, so the conflict is fixed by hand. After each sync, it checks for library
  soname bumps in Void that affect the stack and opens a rebuild PR.
- `asura-bump`: daily, checks each package in `.asura/stack` for a newer
  upstream release, and opens one pull request into `Toren` with the new
  versions and checksums. It never merges.
- Void's own `Check build` workflow lints and builds every package a pull
  request changes.

Toren Linux's main repository (mohitjoer/Toren-Linux) builds the stack from
`Toren`, tests it against Toren's desktop, and publishes it in Toren's signed
package repository.

When a library's soname changes, add its new line to `common/shlibs` and bump
`revision=` of every package built against it (xbps-src names them).

## Setup (once, by an owner)

- The default branch of this fork is `Toren`: GitHub runs scheduled workflows
  only from the default branch.
- Secret `ASURA_BOT_TOKEN`: a fine-grained token for this repository with
  Contents, Pull requests and Workflows set to read and write. The sync needs
  it to push when a merge from Void changes Void's workflow files, and the
  bump needs it so its pull requests start Check build.
- Void's own workflows that only make sense in Void's repository (Stale
  Cleanup, Build buildroot containers) run their jobs only there: in this
  fork they show as skipped. Nothing to disable by hand.
