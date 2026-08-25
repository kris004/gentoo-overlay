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
- Do not change visibility, push, publish, or create a release without explicit
  authorization.

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

Workflow:
1. Inspect Git status and package/release state before editing.
2. Make the smallest source-grounded change.
3. Run `pkgdev manifest` for affected packages and `pkgcheck scan` for QA.
4. When practical, test fetch, compile, install staging, and package behavior in
   isolation before considering a live merge.
5. Stage exact completed paths and commit scoped units. Leave unrelated work
   untouched.
6. Report impact, validation, remaining release blockers, and rollback steps.
