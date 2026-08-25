# AGENTS.md for the kris004 Gentoo overlay

Purpose:
- This is a public Gentoo ebuild repository for versioned releases of selected
  public projects maintained by kris004.
- Treat every file, commit, branch, tag, and reachable-history object as public.

Public-source rules:
- Never commit secrets, personal data, private network details, private issue
  links, environment identifiers, or unnecessary absolute home-directory paths.
- Keep documentation, examples, metadata, and defaults portable for unfamiliar
  external users.
- Preserve upstream licenses, notices, and attribution.
- Preserve unrelated dirty work and stage exact paths.
- Human-initiated visibility changes, pushes, publication, and releases require
  explicit authorization. The committed `.github/workflows/autobump.yml` is a
  durable exception authorized to push only generated release-update commits
  after all configured gates pass.

Ebuild policy:
- Prefer immutable versioned source archives and local source builds. Do not use
  live ebuilds or prebuilt upstream binaries unless the package has a documented
  reason and the user approves that tradeoff.
- Match each ebuild EAPI to all inherited eclasses. Do not bump EAPI merely
  because a newer EAPI exists; the current Rust and systemd eclasses require
  EAPI 8.
- Use standard Gentoo categories where possible and inherit from `::gentoo`.
- Start newly tested packages with testing keywords such as `~amd64`; do not
  claim stable keywords without the corresponding testing process.
- Generate Manifests with `pkgdev manifest`; never edit them by hand.
- Include accurate `metadata.xml`, licenses, dependencies, USE descriptions,
  install paths, service behavior, and upstream remote IDs.
- Do not alter the workstation's separate `/etc/portage/localrepo` or its
  auto-update providers as part of overlay maintenance.

Automated-release policy:
- A published upstream GitHub Release is the normal trigger for a new ebuild.
  Ordinary version releases must not require a manual overlay bump.
- Keep each package's release channel, minimum version, exact required checks,
  and optional `blocked_tags` in `metadata/autobump/packages.toml`.
- The updater may derive only version, commit, Rust minimum, and crates.io crate
  locks from upstream. Packaging logic remains in reviewed local templates.
- Reject draft or unsupported releases, unreachable tag commits, missing or
  failed required checks, tag/source version mismatches, Git dependencies,
  unsafe archives, template collisions, Manifest failures, and configured
  blocking `pkgcheck` findings before committing.
- Automated commits may contain only the affected package directory and its
  state file. Never remove older ebuilds or change packaging templates
  automatically.
- Keep the write token out of upstream discovery, Manifest, and QA subprocess
  environments. Dependency tooling and GitHub Actions must remain version-pinned;
  Python CI requirements must remain hash-locked.
- On failure, retain the previously published ebuild and report one reusable
  package-specific issue. To roll back a bad generated release, block its exact
  tag first, then revert the generated commit.

Workflow:
1. Inspect Git status and package/release state before editing.
2. Make the smallest source-grounded change.
3. Run updater unit tests and language-specific linting for automation changes.
4. Run `pkgdev manifest` for affected packages and `pkgcheck scan` for QA.
5. When practical, test fetch, compile, install staging, and package behavior in
   isolation before considering a live merge.
6. Stage exact completed paths and commit scoped units. Leave unrelated work
   untouched.
7. Report impact, validation, remaining release blockers, and rollback steps.
