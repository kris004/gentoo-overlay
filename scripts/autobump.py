#!/usr/bin/env python3
"""Generate versioned Gentoo ebuilds from verified GitHub releases."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import tomllib


class AutobumpError(RuntimeError):
    """A release cannot be converted into a trusted ebuild update."""


SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9][0-9]*)\."
    r"(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)"
    r"(?:-(?P<stage>alpha|beta|rc)(?:[.-]?(?P<stage_num>0|[1-9][0-9]*))?)?$"
)
PLACEHOLDER_RE = re.compile(r"@[A-Z][A-Z0-9_]*@")
SUCCESS = "success"
CRATE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
CRATE_VERSION_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,127}")
CRATES_IO_SOURCES = {
    "registry+https://github.com/rust-lang/crates.io-index",
    "registry+sparse+https://index.crates.io/",
}


@dataclasses.dataclass(frozen=True, order=False)
class SemVer:
    major: int
    minor: int
    patch: int
    stage: str | None = None
    stage_num: int | None = None
    upstream: str = dataclasses.field(default="", compare=False)

    @classmethod
    def parse(cls, value: str) -> SemVer:
        match = SEMVER_RE.fullmatch(value)
        if match is None:
            raise AutobumpError(
                f"unsupported release version {value!r}; expected vMAJOR.MINOR.PATCH "
                "with an optional alpha, beta, or rc suffix"
            )
        stage_num = match.group("stage_num")
        upstream = value.removeprefix("v")
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            stage=match.group("stage"),
            stage_num=int(stage_num) if stage_num is not None else None,
            upstream=upstream,
        )

    @property
    def gentoo(self) -> str:
        value = f"{self.major}.{self.minor}.{self.patch}"
        if self.stage is not None:
            value += f"_{self.stage}"
            if self.stage_num is not None:
                value += str(self.stage_num)
        return value

    @property
    def sort_key(self) -> tuple[int, int, int, int, int]:
        stage_order = {"alpha": 0, "beta": 1, "rc": 2, None: 3}
        return (
            self.major,
            self.minor,
            self.patch,
            stage_order[self.stage],
            self.stage_num if self.stage_num is not None else -1,
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self.sort_key < other.sort_key

    def __le__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self.sort_key <= other.sort_key


@dataclasses.dataclass(frozen=True)
class PackageConfig:
    atom: str
    repository: str
    template: Path
    kind: str
    include_prereleases: bool
    required_checks: tuple[str, ...]
    minimum_version: SemVer
    blocked_tags: frozenset[str] = frozenset()
    metadata_template: Path | None = None
    rust_min_version: str | None = None

    @property
    def category(self) -> str:
        return self.atom.split("/", 1)[0]

    @property
    def package(self) -> str:
        return self.atom.split("/", 1)[1]

    @property
    def package_dir(self) -> Path:
        return Path(self.category) / self.package

    @property
    def state_path(self) -> Path:
        return Path("metadata/autobump/state") / f"{self.category}__{self.package}.json"


@dataclasses.dataclass(frozen=True)
class Release:
    release_id: int
    tag: str
    published_at: str
    prerelease: bool
    version: SemVer

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Release:
        if data.get("draft"):
            raise AutobumpError("draft releases are not eligible")
        tag = str(data["tag_name"])
        published_at = data.get("published_at")
        if not isinstance(published_at, str):
            raise AutobumpError(f"release {tag!r} has no publication timestamp")
        try:
            dt.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AutobumpError(
                f"release {tag!r} has an invalid publication timestamp"
            ) from exc
        version = SemVer.parse(tag)
        prerelease = bool(data.get("prerelease"))
        if prerelease != (version.stage is not None):
            raise AutobumpError(f"release {tag!r} has inconsistent prerelease metadata")
        return cls(
            release_id=int(data["id"]),
            tag=tag,
            published_at=published_at,
            prerelease=prerelease,
            version=version,
        )


@dataclasses.dataclass(frozen=True)
class PackageState:
    release_id: int
    tag: str
    published_at: str
    commit: str
    gentoo_version: str

    @classmethod
    def load(cls, path: Path) -> PackageState | None:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != 1:
            raise AutobumpError(f"unsupported state schema in {path}")
        state = cls(
            release_id=int(data["release_id"]),
            tag=str(data["tag"]),
            published_at=str(data["published_at"]),
            commit=str(data["commit"]),
            gentoo_version=str(data["gentoo_version"]),
        )
        if re.fullmatch(r"[0-9a-f]{40}", state.commit) is None:
            raise AutobumpError(f"invalid commit in {path}")
        parsed = SemVer.parse(state.tag)
        if parsed.gentoo != state.gentoo_version:
            raise AutobumpError(f"inconsistent tag and Gentoo version in {path}")
        return state

    @classmethod
    def from_release(cls, release: Release, commit: str) -> PackageState:
        return cls(
            release_id=release.release_id,
            tag=release.tag,
            published_at=release.published_at,
            commit=commit,
            gentoo_version=release.version.gentoo,
        )

    def to_json(self) -> str:
        data = {
            "schema": 1,
            "release_id": self.release_id,
            "tag": self.tag,
            "published_at": self.published_at,
            "commit": self.commit,
            "gentoo_version": self.gentoo_version,
        }
        return json.dumps(data, indent=2, sort_keys=True) + "\n"


class GitHubClient:
    def __init__(
        self, token: str | None = None, api_base: str = "https://api.github.com"
    ):
        self.token = token
        self.api_base = api_base.rstrip("/")

    def _headers(self, *, api: bool = True) -> dict[str, str]:
        headers = {"User-Agent": "kris004-gentoo-overlay-autobump/1"}
        if api:
            headers.update(
                {
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
            )
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get_json(self, path: str) -> Any:
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        request = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:1000]
            raise AutobumpError(
                f"GitHub API request failed ({exc.code}) for {url}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AutobumpError(
                f"GitHub API request failed for {url}: {exc.reason}"
            ) from exc

    def releases(self, repository: str) -> list[dict[str, Any]]:
        releases: list[dict[str, Any]] = []
        for page in range(1, 101):
            batch = self._get_json(
                f"/repos/{repository}/releases?per_page=100&page={page}"
            )
            if not isinstance(batch, list):
                raise AutobumpError(f"invalid releases response for {repository}")
            releases.extend(batch)
            if len(batch) < 100:
                return releases
        raise AutobumpError(f"more than 10,000 releases found for {repository}")

    def resolve_tag(self, repository: str, tag: str) -> str:
        encoded = urllib.parse.quote(tag, safe="")
        ref = self._get_json(f"/repos/{repository}/git/ref/tags/{encoded}")
        obj = ref.get("object", {})
        for _ in range(8):
            obj_type = obj.get("type")
            sha = obj.get("sha")
            if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
                raise AutobumpError(f"invalid Git tag object for {repository}@{tag}")
            if obj_type == "commit":
                return sha
            if obj_type != "tag":
                raise AutobumpError(
                    f"unsupported Git object type {obj_type!r} for {repository}@{tag}"
                )
            obj = self._get_json(f"/repos/{repository}/git/tags/{sha}").get(
                "object", {}
            )
        raise AutobumpError(f"excessive annotated-tag depth for {repository}@{tag}")

    def verify_default_branch_reachability(self, repository: str, commit: str) -> None:
        repo = self._get_json(f"/repos/{repository}")
        default_branch = repo.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch:
            raise AutobumpError(f"missing default branch for {repository}")
        comparison = self._get_json(
            f"/repos/{repository}/compare/{commit}..."
            f"{urllib.parse.quote(default_branch, safe='')}"
        )
        if comparison.get("status") not in {"ahead", "identical"}:
            raise AutobumpError(
                f"release commit {commit} is not reachable from {repository}'s "
                f"default branch {default_branch}"
            )

    def verify_checks(
        self, repository: str, commit: str, required_checks: Iterable[str]
    ) -> None:
        runs: list[dict[str, Any]] = []
        for page in range(1, 101):
            response = self._get_json(
                f"/repos/{repository}/commits/{commit}/check-runs"
                f"?per_page=100&filter=latest&page={page}"
            )
            batch = response.get("check_runs", [])
            if not isinstance(batch, list):
                raise AutobumpError(
                    f"invalid check-runs response for {repository}@{commit}"
                )
            runs.extend(batch)
            if len(batch) < 100:
                break
        else:
            raise AutobumpError(
                f"more than 10,000 check runs found for {repository}@{commit}"
            )
        by_name: dict[str, list[dict[str, Any]]] = {}
        for run in runs:
            by_name.setdefault(str(run.get("name")), []).append(run)
        failed: list[str] = []
        for name in required_checks:
            matching = by_name.get(name, [])
            if not matching or not all(
                run.get("status") == "completed" and run.get("conclusion") == SUCCESS
                for run in matching
            ):
                conclusions = sorted(
                    {
                        str(run.get("conclusion") or run.get("status"))
                        for run in matching
                    }
                )
                failed.append(
                    f"{name} ({', '.join(conclusions) if conclusions else 'missing'})"
                )
        if failed:
            raise AutobumpError(
                f"required checks are not successful for {repository}@{commit}: "
                + "; ".join(failed)
            )

    def download_archive(self, repository: str, commit: str, target: Path) -> None:
        url = f"https://github.com/{repository}/archive/{commit}.tar.gz"
        request = urllib.request.Request(url, headers=self._headers(api=False))
        try:
            with (
                urllib.request.urlopen(request, timeout=120) as response,
                target.open("wb") as out,
            ):
                shutil.copyfileobj(response, out)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            raise AutobumpError(f"failed to download {url}: {exc}") from exc


@dataclasses.dataclass(frozen=True)
class RenderedRelease:
    release: Release
    commit: str
    path: Path
    content: str


def _repo_path(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise AutobumpError(f"path escapes repository: {value}") from exc
    return path


def load_config(root: Path, config_path: Path) -> list[PackageConfig]:
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise AutobumpError(f"unsupported config schema in {config_path}")
    rows = data.get("package")
    if not isinstance(rows, list) or not rows:
        raise AutobumpError(f"no packages configured in {config_path}")
    packages: list[PackageConfig] = []
    seen: set[str] = set()
    for row in rows:
        atom = str(row["atom"])
        if not re.fullmatch(r"[a-z0-9+_.-]+/[a-z0-9+_-]+", atom):
            raise AutobumpError(f"invalid package atom {atom!r}")
        if atom in seen:
            raise AutobumpError(f"duplicate package atom {atom}")
        seen.add(atom)
        repository = str(row["repository"])
        if not re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,38})/[A-Za-z0-9_.-]+", repository
        ):
            raise AutobumpError(f"invalid GitHub repository {repository!r} for {atom}")
        kind = str(row["kind"])
        if kind not in {"cargo", "generic"}:
            raise AutobumpError(f"unsupported package kind {kind!r} for {atom}")
        checks = tuple(str(x) for x in row.get("required_checks", []))
        if not checks:
            raise AutobumpError(f"{atom} must define at least one required check")
        if len(set(checks)) != len(checks):
            raise AutobumpError(f"{atom} defines duplicate required checks")
        template = _repo_path(root, str(row["template"]))
        metadata_value = row.get("metadata_template")
        metadata = _repo_path(root, str(metadata_value)) if metadata_value else None
        package = PackageConfig(
            atom=atom,
            repository=repository,
            template=template,
            kind=kind,
            include_prereleases=bool(row.get("include_prereleases", False)),
            required_checks=checks,
            minimum_version=SemVer.parse(str(row["minimum_version"])),
            blocked_tags=frozenset(str(x) for x in row.get("blocked_tags", [])),
            metadata_template=metadata,
            rust_min_version=(
                str(row["rust_min_version"]) if row.get("rust_min_version") else None
            ),
        )
        if not package.template.is_file():
            raise AutobumpError(f"missing template for {atom}: {package.template}")
        if (
            package.metadata_template is not None
            and not package.metadata_template.is_file()
        ):
            raise AutobumpError(
                f"missing metadata template for {atom}: {package.metadata_template}"
            )
        packages.append(package)
    return packages


def _safe_extract(archive: Path, destination: Path) -> Path:
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        roots: set[str] = set()
        destination_resolved = destination.resolve()
        for member in members:
            parts = Path(member.name).parts
            if not parts:
                continue
            roots.add(parts[0])
            if member.isdev() or member.issym() or member.islnk():
                raise AutobumpError(f"unsafe archive entry: {member.name}")
            target = (destination / member.name).resolve()
            try:
                target.relative_to(destination_resolved)
            except ValueError as exc:
                raise AutobumpError(
                    f"archive path escapes extraction root: {member.name}"
                ) from exc
        if len(roots) != 1:
            raise AutobumpError(
                f"release archive must contain one top-level directory, got {roots}"
            )
        tar.extractall(destination, filter="data")
    root = destination / next(iter(roots))
    if not root.is_dir():
        raise AutobumpError("release archive top-level entry is not a directory")
    return root


def _cargo_package_values(
    source: Path, rust_min_fallback: str | None = None
) -> tuple[str, str]:
    manifest_path = source / "Cargo.toml"
    if not manifest_path.is_file():
        raise AutobumpError("Cargo release is missing Cargo.toml")
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    package = manifest.get("package", {})
    workspace = manifest.get("workspace", {})
    if not isinstance(package, dict) or not isinstance(workspace, dict):
        raise AutobumpError("Cargo.toml has invalid package or workspace metadata")
    workspace_package = workspace.get("package", {})
    if not isinstance(workspace_package, dict):
        raise AutobumpError("Cargo.toml has invalid workspace package metadata")
    package_version = package.get("version")
    version = (
        package_version
        if isinstance(package_version, str)
        else workspace_package.get("version")
    )
    package_rust_version = package.get("rust-version")
    rust_version = (
        package_rust_version
        if isinstance(package_rust_version, str)
        else workspace_package.get("rust-version")
    )
    if not isinstance(rust_version, str):
        rust_version = rust_min_fallback
    if not isinstance(version, str):
        raise AutobumpError(
            "Cargo.toml does not declare a root or workspace package version"
        )
    if not isinstance(rust_version, str):
        raise AutobumpError("Cargo.toml does not declare rust-version")
    rust_parts = rust_version.split(".")
    if len(rust_parts) == 2:
        rust_version += ".0"
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", rust_version):
        raise AutobumpError(f"unsupported rust-version {rust_version!r}")
    return version, rust_version


def _cargo_crates(source: Path) -> str:
    lock_path = source / "Cargo.lock"
    if not lock_path.is_file():
        raise AutobumpError("Cargo release is missing Cargo.lock")
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    crates: list[str] = []
    seen: set[str] = set()
    packages = lock.get("package", [])
    if not isinstance(packages, list):
        raise AutobumpError("Cargo.lock has invalid package metadata")
    for package in packages:
        if not isinstance(package, dict):
            raise AutobumpError("Cargo.lock has an invalid package entry")
        source_value = package.get("source")
        if source_value is None:
            continue
        if str(source_value).startswith("git+"):
            raise AutobumpError(
                f"Git dependency is not supported: {package.get('name')} {package.get('version')}"
            )
        if str(source_value) not in CRATES_IO_SOURCES:
            raise AutobumpError(
                f"unsupported Cargo source for {package.get('name')}: {source_value}"
            )
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or CRATE_NAME_RE.fullmatch(name) is None:
            raise AutobumpError(f"unsupported Cargo package name: {name!r}")
        if not isinstance(version, str) or CRATE_VERSION_RE.fullmatch(version) is None:
            raise AutobumpError(f"unsupported Cargo version for {name}: {version!r}")
        crate = f"{name}@{version}"
        if crate not in seen:
            seen.add(crate)
            crates.append(crate)
    if not crates:
        raise AutobumpError("Cargo.lock contains no registry crates")
    crates.sort()
    body = "\n".join(f"\t{crate}" for crate in crates)
    return f'CRATES="\n{body}\n"'


def render_template(
    package: PackageConfig, source: Path, release: Release, commit: str
) -> str:
    text = package.template.read_text(encoding="utf-8")
    if text.count("@COMMIT@") != 1:
        raise AutobumpError(f"{package.template} must contain exactly one @COMMIT@")
    replacements = {"@COMMIT@": commit}
    if package.kind == "cargo":
        cargo_version, rust_version = _cargo_package_values(
            source, package.rust_min_version
        )
        if cargo_version != release.version.upstream:
            raise AutobumpError(
                f"tag {release.tag} does not match Cargo version {cargo_version}"
            )
        replacements["@RUST_MIN_VER@"] = rust_version
        replacements["@CRATES@"] = _cargo_crates(source)
    for marker, value in replacements.items():
        count = text.count(marker)
        if count != 1:
            raise AutobumpError(
                f"{package.template} must contain exactly one {marker}, found {count}"
            )
        text = text.replace(marker, value)
    remaining = sorted(set(PLACEHOLDER_RE.findall(text)))
    if remaining:
        raise AutobumpError(
            f"unexpanded placeholders in {package.template}: {', '.join(remaining)}"
        )
    return text.rstrip() + "\n"


def eligible_releases(
    package: PackageConfig,
    api_releases: Iterable[dict[str, Any]],
    state: PackageState | None,
) -> list[Release]:
    current = SemVer.parse(state.tag) if state is not None else None
    releases: list[Release] = []
    for data in api_releases:
        if data.get("draft"):
            continue
        if str(data.get("tag_name")) in package.blocked_tags:
            continue
        if data.get("prerelease") and not package.include_prereleases:
            continue
        release = Release.from_api(data)
        if release.version < package.minimum_version:
            continue
        if current is not None and release.version <= current:
            continue
        releases.append(release)
    releases.sort(key=lambda item: item.version.sort_key)
    return releases


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def update_package(
    *,
    root: Path,
    package: PackageConfig,
    client: GitHubClient,
    write: bool,
) -> dict[str, Any]:
    state_path = root / package.state_path
    state = PackageState.load(state_path)
    if state is not None:
        current_ebuild = (
            root
            / package.package_dir
            / f"{package.package}-{state.gentoo_version}.ebuild"
        )
        if not current_ebuild.is_file():
            raise AutobumpError(
                f"state points to missing current ebuild {current_ebuild.relative_to(root)}"
            )
        expected_commit = f'COMMIT="{state.commit}"'
        if current_ebuild.read_text(encoding="utf-8").count(expected_commit) != 1:
            raise AutobumpError(
                f"state commit does not match {current_ebuild.relative_to(root)}"
            )
    releases = eligible_releases(package, client.releases(package.repository), state)
    if not releases:
        return {
            "status": "current" if state is not None else "waiting",
            "atom": package.atom,
            "package_dir": str(package.package_dir),
            "state_path": str(package.state_path),
            "updates": [],
            "paths": [],
        }

    rendered: list[RenderedRelease] = []
    rendered_paths: set[Path] = set()
    with tempfile.TemporaryDirectory(prefix="gentoo-autobump-") as temp_value:
        temp = Path(temp_value)
        for release in releases:
            commit = client.resolve_tag(package.repository, release.tag)
            client.verify_default_branch_reachability(package.repository, commit)
            client.verify_checks(package.repository, commit, package.required_checks)
            archive = temp / f"{release.release_id}.tar.gz"
            extraction = temp / str(release.release_id)
            extraction.mkdir()
            client.download_archive(package.repository, commit, archive)
            source = _safe_extract(archive, extraction)
            content = render_template(package, source, release, commit)
            relative_path = (
                package.package_dir
                / f"{package.package}-{release.version.gentoo}.ebuild"
            )
            if relative_path in rendered_paths:
                raise AutobumpError(
                    f"multiple releases map to Gentoo ebuild {relative_path}"
                )
            rendered_paths.add(relative_path)
            target = root / relative_path
            if target.exists() and target.read_text(encoding="utf-8") != content:
                raise AutobumpError(
                    f"refusing to overwrite differing existing ebuild {relative_path}"
                )
            rendered.append(
                RenderedRelease(
                    release=release,
                    commit=commit,
                    path=relative_path,
                    content=content,
                )
            )

    paths: list[Path] = []
    if write:
        for item in rendered:
            target = root / item.path
            if not target.exists():
                _atomic_write(target, item.content)
            paths.append(item.path)
        metadata_path = package.package_dir / "metadata.xml"
        metadata_target = root / metadata_path
        if not metadata_target.exists():
            if package.metadata_template is None:
                raise AutobumpError(
                    f"{package.atom} has no metadata.xml and no metadata template"
                )
            _atomic_write(
                metadata_target,
                package.metadata_template.read_text(encoding="utf-8").rstrip() + "\n",
            )
            paths.append(metadata_path)
        final = rendered[-1]
        _atomic_write(
            state_path,
            PackageState.from_release(final.release, final.commit).to_json(),
        )
        paths.append(package.state_path)
    else:
        paths = [item.path for item in rendered] + [package.state_path]

    return {
        "status": "updated" if write else "available",
        "atom": package.atom,
        "package_dir": str(package.package_dir),
        "state_path": str(package.state_path),
        "updates": [
            {
                "release_id": item.release.release_id,
                "tag": item.release.tag,
                "published_at": item.release.published_at,
                "commit": item.commit,
                "gentoo_version": item.release.version.gentoo,
                "path": str(item.path),
            }
            for item in rendered
        ],
        "paths": [str(path) for path in paths],
    }


def _write_result(path: Path | None, result: Any) -> None:
    content = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if path is None:
        sys.stdout.write(content)
    else:
        _atomic_write(path, content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("metadata/autobump/packages.toml"),
        help="package registry relative to the repository root",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list configured package atoms")
    list_parser.add_argument("--json", action="store_true", help="emit a JSON array")

    update_parser = subparsers.add_parser(
        "update", help="discover and generate updates"
    )
    update_parser.add_argument(
        "--package", required=True, help="exact category/package atom"
    )
    update_parser.add_argument(
        "--dry-run", action="store_true", help="validate without writing"
    )
    update_parser.add_argument(
        "--result", type=Path, help="write structured result JSON"
    )
    update_parser.add_argument(
        "--api-base",
        default="https://api.github.com",
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    config_path = args.config if args.config.is_absolute() else root / args.config
    try:
        packages = load_config(root, config_path)
        if args.command == "list":
            atoms = [package.atom for package in packages]
            if args.json:
                print(json.dumps(atoms))
            else:
                print("\n".join(atoms))
            return 0

        by_atom = {package.atom: package for package in packages}
        try:
            package = by_atom[args.package]
        except KeyError as exc:
            raise AutobumpError(f"unknown package {args.package!r}") from exc
        client = GitHubClient(
            token=os.environ.get("AUTOBUMP_GITHUB_TOKEN"),
            api_base=args.api_base,
        )
        result = update_package(
            root=root,
            package=package,
            client=client,
            write=not args.dry_run,
        )
        _write_result(args.result, result)
        return 0
    except (
        AutobumpError,
        OSError,
        ValueError,
        KeyError,
        tomllib.TOMLDecodeError,
    ) as exc:
        print(f"autobump: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
