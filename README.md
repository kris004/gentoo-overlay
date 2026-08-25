# kris004 Gentoo overlay

Gentoo ebuilds for versioned releases of selected public projects maintained at
[github.com/kris004](https://github.com/kris004).

This repository contains build recipes, not prebuilt binaries. Portage builds
packages locally from source archives pinned to immutable release commits.

## Packages

| Package | Update channel | Keyword |
| --- | --- | --- |
| `mail-client/notm` | Stable GitHub releases | `~amd64` |
| `net-mail/mailwake` | GitHub releases, including prereleases | `~amd64` |
| `gui-apps/mural` | Stable releases starting with `v0.1.0` | `~amd64` |
| `sys-auth/pam-u2f-touch-popup` | Stable releases starting with `v0.1.1` | `~amd64` |

A package directory appears when its first eligible release is published.

## Install

Install `app-eselect/eselect-repository`, then add and synchronize the overlay:

```sh
eselect repository add kris004 git https://github.com/kris004/gentoo-overlay.git
emaint sync -r kris004
```

Review an ebuild before installing it. Third-party ebuild repositories have the
same ability to execute package build and installation logic as other Portage
repositories.

Install a package with its repository qualified explicitly:

```sh
emerge --ask category/package::kris004
```

## Automatic release updates

Publishing an eligible upstream GitHub Release is the normal ebuild-release
operation. No manual version bump in this repository is required.

An hourly GitHub Actions job polls the registered projects. For each new
release, it:

1. accepts only the configured stable or prerelease channel and semantic tag;
2. resolves the tag to its exact commit and verifies that commit is reachable
   from the upstream default branch;
3. requires the package's named upstream CI checks to have succeeded;
4. verifies Cargo package versions, Rust requirements, and locked crates where
   applicable, while rejecting Git dependencies and non-crates.io registries;
5. renders an ebuild pinned to the release commit, runs `pkgdev manifest`, and
   rejects `pkgcheck` errors, warnings, style findings, and selected maintenance
   findings such as stale Python compatibility; and
6. pushes one scoped bot commit for that package.

A failed gate leaves the published overlay unchanged and opens or updates a
package-specific issue with a link to the failed run. The updater uses the
repository's short-lived `GITHUB_TOKEN` only for overlay issues and pushes;
public upstream discovery is read-only and unauthenticated. Source
repositories do not need a cross-repository token or release secret.

The registry and ebuild templates live under `metadata/autobump/`. Ordinary
source and version releases are automatic. A real change to a project's system
dependencies, install paths, service files, or other packaging contract still
requires the corresponding reviewed template change rather than guessing from
source code.

To suppress a bad release, add its exact tag to that package's `blocked_tags`
array in `metadata/autobump/packages.toml` before reverting the generated
package commit. The next run skips the blocked tag instead of recreating the ebuild.

## Repository policy

- Packages track immutable versioned release commits; live ebuilds are
  exceptional.
- Packages begin with testing keywords such as `~amd64`.
- Manifests are generated with Portage tooling and are never hand-edited.
- Repository QA uses `pkgcheck scan` locally and in GitHub Actions.
- The overlay inherits eclasses, categories, and licenses from `::gentoo`.

## License

Ebuilds and repository support files are distributed under GPL-2.0-only unless
a file states otherwise. Packaged projects retain their own upstream licenses.
