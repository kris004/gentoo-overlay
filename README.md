# kris004 Gentoo overlay

Gentoo ebuilds for versioned releases of selected public projects maintained at
[github.com/kris004](https://github.com/kris004).

This repository contains build recipes, not prebuilt binaries. Packages are
built locally by Portage from immutable upstream release sources.

## Packages

| Package | Upstream release | Keyword |
| --- | --- | --- |
| `mail-client/notm` | `v0.1.0` | `~amd64` |
| `net-mail/mailwake` | `v0.1.0-beta.2` | `~amd64` |

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

## Repository policy

- Packages track immutable versioned releases; live ebuilds are exceptional.
- Packages begin with testing keywords such as `~amd64`.
- Manifests are generated with Portage tooling and are never hand-edited.
- Repository QA uses `pkgcheck scan` locally and in GitHub Actions.
- The overlay inherits eclasses, categories, and licenses from `::gentoo`.

## License

Ebuilds and repository support files are distributed under GPL-2.0-only unless
a file states otherwise. Packaged projects retain their own upstream licenses.
