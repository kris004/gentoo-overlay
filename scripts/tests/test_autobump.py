from __future__ import annotations

import base64
import dataclasses
import io
import tarfile
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.autobump import (
    AutobumpError,
    GitHubClient,
    PackageConfig,
    PackageState,
    Release,
    SemVer,
    _cargo_crates,
    _openpgp_signature_fingerprint,
    _safe_extract,
    eligible_releases,
    load_config,
    render_template,
)

FINGERPRINT = "BE592562E6131A53F4BADE4A046928E9A919BAF9"
OTHER_FINGERPRINT = "0123456789ABCDEF0123456789ABCDEF01234567"
COMMIT = "a" * 40
TAG_SHA = "b" * 40
TAG = "v1.2.3"


def openpgp_signature(
    fingerprint: str = FINGERPRINT,
    *,
    issuer_is_hashed: bool = True,
    issuer_key_id: str | None = None,
) -> str:
    issuer_fingerprint = bytes([22, 33, 4]) + bytes.fromhex(fingerprint)
    key_id = issuer_key_id or fingerprint[-16:]
    issuer_key = bytes([9, 16]) + bytes.fromhex(key_id)
    hashed = issuer_fingerprint if issuer_is_hashed else b""
    unhashed = issuer_key if issuer_is_hashed else issuer_fingerprint + issuer_key
    body = (
        bytes([4, 0, 1, 8])
        + len(hashed).to_bytes(2)
        + hashed
        + len(unhashed).to_bytes(2)
        + unhashed
        + b"\x00\x00"
    )
    packet = bytes([0xC2, len(body)]) + body
    encoded = base64.b64encode(packet).decode("ascii")
    return "\n".join(
        [
            "-----BEGIN PGP SIGNATURE-----",
            "",
            *textwrap.wrap(encoded, 64),
            "-----END PGP SIGNATURE-----",
        ]
    )


def tag_responses(
    *,
    ref_type: str = "tag",
    target_type: str = "commit",
    verified: bool = True,
    reason: str = "valid",
    signature: str | None = None,
    payload_commit: str = COMMIT,
) -> dict[str, object]:
    ref_sha = TAG_SHA if ref_type == "tag" else COMMIT
    return {
        f"/repos/owner/project/git/ref/tags/{TAG}": {
            "ref": f"refs/tags/{TAG}",
            "object": {"type": ref_type, "sha": ref_sha},
        },
        f"/repos/owner/project/git/tags/{TAG_SHA}": {
            "sha": TAG_SHA,
            "tag": TAG,
            "object": {"type": target_type, "sha": COMMIT},
            "verification": {
                "verified": verified,
                "reason": reason,
                "payload": (
                    f"object {payload_commit}\ntype commit\ntag {TAG}\n"
                    "tagger Test <test@example.invalid> 1 +0000\n\nrelease"
                ),
                "signature": signature or openpgp_signature(),
            },
        },
    }


class FakeGitHubClient(GitHubClient):
    def __init__(self, responses: dict[str, object]):
        super().__init__()
        self.responses = responses

    def _get_json(self, path: str) -> object:
        return self.responses[path]


class SemVerTests(unittest.TestCase):
    def test_gentoo_conversion_and_order(self) -> None:
        values = [
            ("v1.2.3-alpha.1", "1.2.3_alpha1"),
            ("v1.2.3-beta.2", "1.2.3_beta2"),
            ("v1.2.3-rc.3", "1.2.3_rc3"),
            ("v1.2.3", "1.2.3"),
        ]
        parsed = [SemVer.parse(value) for value, _ in values]
        self.assertEqual(
            [item.gentoo for item in parsed], [expected for _, expected in values]
        )
        self.assertEqual(parsed, sorted(parsed))

    def test_rejects_unsupported_versions(self) -> None:
        for value in ("1.2", "release-1.2.3", "v1.2.3-pre.1", "v1.2.3+build"):
            with self.subTest(value=value), self.assertRaises(AutobumpError):
                SemVer.parse(value)

    def test_release_prerelease_flag_must_match_tag(self) -> None:
        data = {
            "id": 1,
            "tag_name": "v1.2.3-beta.1",
            "published_at": "2026-01-01T00:00:00Z",
            "prerelease": False,
            "draft": False,
            "immutable": True,
        }
        with self.assertRaisesRegex(AutobumpError, "prerelease metadata"):
            Release.from_api(data)

    def test_mutable_release_is_rejected(self) -> None:
        data = {
            "id": 1,
            "tag_name": "v1.2.3",
            "published_at": "2026-01-01T00:00:00Z",
            "prerelease": False,
            "draft": False,
            "immutable": False,
        }
        with self.assertRaisesRegex(AutobumpError, "not immutable"):
            Release.from_api(data)


class OpenPGPTagTests(unittest.TestCase):
    def test_hashed_issuer_fingerprint_is_extracted(self) -> None:
        self.assertEqual(
            _openpgp_signature_fingerprint(openpgp_signature()), FINGERPRINT
        )

    def test_unhashed_issuer_fingerprint_cannot_spoof_trust(self) -> None:
        with self.assertRaisesRegex(AutobumpError, "hashed OpenPGP issuer"):
            _openpgp_signature_fingerprint(openpgp_signature(issuer_is_hashed=False))

    def test_issuer_key_id_must_match_hashed_fingerprint(self) -> None:
        signature = openpgp_signature(issuer_key_id=OTHER_FINGERPRINT[-16:])
        with self.assertRaisesRegex(AutobumpError, "issuer key ID does not match"):
            _openpgp_signature_fingerprint(signature)

    def test_verified_direct_signed_tag_is_resolved(self) -> None:
        client = FakeGitHubClient(tag_responses())
        self.assertEqual(
            client.resolve_tag("owner/project", TAG, {FINGERPRINT}), COMMIT
        )

    def test_lightweight_tag_is_rejected(self) -> None:
        client = FakeGitHubClient(tag_responses(ref_type="commit"))
        with self.assertRaisesRegex(AutobumpError, "lightweight tag"):
            client.resolve_tag("owner/project", TAG, {FINGERPRINT})

    def test_indirect_annotated_tag_is_rejected(self) -> None:
        client = FakeGitHubClient(tag_responses(target_type="tag"))
        with self.assertRaisesRegex(AutobumpError, "directly target a commit"):
            client.resolve_tag("owner/project", TAG, {FINGERPRINT})

    def test_github_verification_must_be_valid(self) -> None:
        client = FakeGitHubClient(tag_responses(verified=False, reason="unknown_key"))
        with self.assertRaisesRegex(AutobumpError, "not valid"):
            client.resolve_tag("owner/project", TAG, {FINGERPRINT})

    def test_signer_must_match_package_allowlist(self) -> None:
        client = FakeGitHubClient(tag_responses())
        with self.assertRaisesRegex(AutobumpError, "untrusted OpenPGP signer"):
            client.resolve_tag("owner/project", TAG, {OTHER_FINGERPRINT})

    def test_signed_payload_must_match_tag_target(self) -> None:
        client = FakeGitHubClient(tag_responses(payload_commit="c" * 40))
        with self.assertRaisesRegex(AutobumpError, "does not bind"):
            client.resolve_tag("owner/project", TAG, {FINGERPRINT})


class ConfigTests(unittest.TestCase):
    def test_config_requires_full_uppercase_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root / "template").write_text("@COMMIT@\n", encoding="utf-8")
            config = root / "packages.toml"
            config.write_text(
                textwrap.dedent(
                    f"""
                    schema = 2
                    [[package]]
                    atom = "app-misc/test"
                    repository = "owner/project"
                    trusted_openpgp_fingerprints = ["{FINGERPRINT}"]
                    template = "template"
                    kind = "generic"
                    include_prereleases = false
                    minimum_version = "1.0.0"
                    required_checks = ["CI"]
                    """
                ),
                encoding="utf-8",
            )
            package = load_config(root, config)[0]
            self.assertEqual(package.trusted_openpgp_fingerprints, {FINGERPRINT})

            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    FINGERPRINT, FINGERPRINT.lower()
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AutobumpError, "invalid trusted"):
                load_config(root, config)


class CargoTests(unittest.TestCase):
    def test_registry_crates_are_rendered_and_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root / "Cargo.lock").write_text(
                textwrap.dedent(
                    """
                    version = 4

                    [[package]]
                    name = "app"
                    version = "1.0.0"

                    [[package]]
                    name = "alpha"
                    version = "1.2.3"
                    source = "registry+https://github.com/rust-lang/crates.io-index"

                    [[package]]
                    name = "alpha"
                    version = "1.2.3"
                    source = "registry+https://github.com/rust-lang/crates.io-index"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(_cargo_crates(root), 'CRATES="\n\talpha@1.2.3\n"')

    def test_lockfile_values_cannot_inject_ebuild_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root / "Cargo.lock").write_text(
                textwrap.dedent(
                    """
                    version = 4
                    [[package]]
                    name = "bad$(touch_tmp)"
                    version = "1.0.0"
                    source = "registry+https://github.com/rust-lang/crates.io-index"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AutobumpError, "package name"):
                _cargo_crates(root)

    def test_git_crates_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root / "Cargo.lock").write_text(
                textwrap.dedent(
                    """
                    version = 4
                    [[package]]
                    name = "unsafe-git"
                    version = "1.0.0"
                    source = "git+https://example.test/repo#deadbeef"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AutobumpError, "Git dependency"):
                _cargo_crates(root)

    def test_cargo_template_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            source = root / "source"
            source.mkdir()
            (source / "Cargo.toml").write_text(
                textwrap.dedent(
                    """
                    [workspace]
                    members = []

                    [workspace.package]
                    version = "2.3.4-beta.5"
                    rust-version = "1.95"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            (source / "Cargo.lock").write_text(
                textwrap.dedent(
                    """
                    version = 4
                    [[package]]
                    name = "crate-a"
                    version = "1.0.0"
                    source = "registry+https://github.com/rust-lang/crates.io-index"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            template = root / "test.ebuild.in"
            template.write_text(
                '@CRATES@\nRUST_MIN_VER="@RUST_MIN_VER@"\nCOMMIT="@COMMIT@"\n',
                encoding="utf-8",
            )
            package = PackageConfig(
                atom="app-misc/test",
                repository="owner/test",
                template=template,
                kind="cargo",
                include_prereleases=True,
                required_checks=("CI",),
                minimum_version=SemVer.parse("0.0.0"),
            )
            release = Release(
                release_id=1,
                tag="v2.3.4-beta.5",
                published_at="2026-01-01T00:00:00Z",
                prerelease=True,
                version=SemVer.parse("v2.3.4-beta.5"),
            )
            result = render_template(package, source, release, "a" * 40)
            self.assertIn("crate-a@1.0.0", result)
            self.assertIn('RUST_MIN_VER="1.95.0"', result)
            self.assertIn(f'COMMIT="{"a" * 40}"', result)

    def test_workspace_version_and_configured_rust_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root / "Cargo.toml").write_text(
                textwrap.dedent(
                    """
                    [workspace]
                    members = ["app"]

                    [workspace.package]
                    version = "1.2.3"

                    [package]
                    name = "test"
                    version.workspace = true
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            (root / "Cargo.lock").write_text(
                textwrap.dedent(
                    """
                    version = 4
                    [[package]]
                    name = "crate-a"
                    version = "1.0.0"
                    source = "registry+https://github.com/rust-lang/crates.io-index"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            template = root / "template"
            template.write_text(
                "@CRATES@\n@RUST_MIN_VER@\n@COMMIT@\n", encoding="utf-8"
            )
            package = PackageConfig(
                atom="app-misc/test",
                repository="owner/test",
                template=template,
                kind="cargo",
                include_prereleases=False,
                required_checks=("CI",),
                minimum_version=SemVer.parse("0.0.0"),
                rust_min_version="1.92.0",
            )
            release = Release(
                1,
                "v1.2.3",
                "2026-01-01T00:00:00Z",
                False,
                SemVer.parse("v1.2.3"),
            )
            result = render_template(package, root, release, "a" * 40)
            self.assertIn("1.92.0", result)

    def test_tag_and_cargo_version_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root / "Cargo.toml").write_text(
                '[package]\nname="test"\nversion="1.0.0"\nrust-version="1.95"\n',
                encoding="utf-8",
            )
            (root / "Cargo.lock").write_text(
                'version=4\n[[package]]\nname="a"\nversion="1.0.0"\nsource="registry+x"\n',
                encoding="utf-8",
            )
            template = root / "template"
            template.write_text(
                "@CRATES@\n@RUST_MIN_VER@\n@COMMIT@\n", encoding="utf-8"
            )
            package = PackageConfig(
                atom="app-misc/test",
                repository="owner/test",
                template=template,
                kind="cargo",
                include_prereleases=False,
                required_checks=("CI",),
                minimum_version=SemVer.parse("0.0.0"),
            )
            release = Release(
                1, "v1.0.1", "2026-01-01T00:00:00Z", False, SemVer.parse("v1.0.1")
            )
            with self.assertRaisesRegex(AutobumpError, "does not match Cargo version"):
                render_template(package, root, release, "a" * 40)


class ReleaseSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.package = PackageConfig(
            atom="app-misc/test",
            repository="owner/test",
            template=Path("unused"),
            kind="generic",
            include_prereleases=False,
            required_checks=("CI",),
            minimum_version=SemVer.parse("1.0.0"),
        )

    @staticmethod
    def release(
        release_id: int, tag: str, prerelease: bool = False
    ) -> dict[str, object]:
        return {
            "id": release_id,
            "tag_name": tag,
            "published_at": f"2026-01-{release_id:02d}T00:00:00Z",
            "prerelease": prerelease,
            "draft": False,
            "immutable": True,
        }

    def test_only_newer_supported_releases_are_selected(self) -> None:
        state = PackageState(1, "v1.0.0", "2026-01-01T00:00:00Z", "a" * 40, "1.0.0")
        selected = eligible_releases(
            self.package,
            [
                self.release(1, "v1.0.0"),
                self.release(3, "v1.1.0"),
                self.release(2, "v1.0.1"),
                self.release(4, "v2.0.0-beta.1", prerelease=True),
            ],
            state,
        )
        self.assertEqual([item.tag for item in selected], ["v1.0.1", "v1.1.0"])

    def test_blocked_release_is_skipped(self) -> None:
        package = dataclasses.replace(self.package, blocked_tags=frozenset({"v1.0.1"}))
        selected = eligible_releases(
            package,
            [self.release(2, "v1.0.1"), self.release(3, "v1.1.0")],
            None,
        )
        self.assertEqual([item.tag for item in selected], ["v1.1.0"])

    def test_seeded_mutable_release_is_grandfathered(self) -> None:
        state = PackageState(1, "v1.0.0", "2026-01-01T00:00:00Z", "a" * 40, "1.0.0")
        existing = self.release(1, "v1.0.0")
        existing["immutable"] = False
        self.assertEqual(eligible_releases(self.package, [existing], state), [])

    def test_new_mutable_release_fails_closed(self) -> None:
        candidate = self.release(2, "v1.0.1")
        candidate["immutable"] = False
        with self.assertRaisesRegex(AutobumpError, "not immutable"):
            eligible_releases(self.package, [candidate], None)


class ArchiveTests(unittest.TestCase):
    def test_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            archive = root / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo("../escape")
                payload = b"bad"
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
            destination = root / "out"
            destination.mkdir()
            with self.assertRaisesRegex(AutobumpError, "escapes"):
                _safe_extract(archive, destination)


if __name__ == "__main__":
    unittest.main()
