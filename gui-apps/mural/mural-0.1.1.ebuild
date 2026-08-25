# Copyright 2026 Kristopher Keller
# Distributed under the terms of the GNU General Public License v2

EAPI=8

CRATES="
	adler2@2.0.1
	autocfg@1.5.0
	bitflags@2.11.1
	bumpalo@3.20.2
	bytemuck@1.25.0
	bytemuck_derive@1.10.2
	byteorder-lite@0.1.0
	calloop-wayland-source@0.4.1
	calloop@0.14.4
	cc@1.2.62
	cfg-if@1.0.4
	concurrent-queue@2.5.0
	crc32fast@1.5.0
	crossbeam-utils@0.8.21
	cursor-icon@1.2.0
	dlib@0.5.3
	downcast-rs@1.2.1
	errno@0.3.14
	fdeflate@0.3.7
	find-msvc-tools@0.1.9
	flate2@1.1.9
	futures-core@0.3.32
	futures-task@0.3.32
	futures-util@0.3.32
	glow@0.17.0
	hermit-abi@0.5.2
	image-webp@0.2.4
	image@0.25.10
	js-sys@0.3.98
	khronos-egl@6.0.0
	libc@0.2.186
	libloading@0.8.9
	linux-raw-sys@0.12.1
	log@0.4.29
	memchr@2.8.0
	memmap2@0.9.11
	miniz_oxide@0.8.9
	moxcms@0.8.1
	num-traits@0.2.19
	once_cell@1.21.4
	pin-project-lite@0.2.17
	pkg-config@0.3.33
	png@0.18.1
	polling@3.11.0
	proc-macro2@1.0.106
	pxfm@0.1.29
	quick-error@2.0.1
	quick-xml@0.41.0
	quote@1.0.45
	rustix@1.1.4
	rustversion@1.0.22
	scoped-tls@1.0.1
	shlex@1.3.0
	simd-adler32@0.3.9
	slab@0.4.12
	slotmap@1.1.1
	smallvec@1.15.1
	smithay-client-toolkit@0.20.0
	syn@2.0.117
	thiserror-impl@2.0.18
	thiserror@2.0.18
	tracing-core@0.1.36
	tracing@0.1.44
	unicode-ident@1.0.24
	version_check@0.9.5
	wasm-bindgen-macro-support@0.2.121
	wasm-bindgen-macro@0.2.121
	wasm-bindgen-shared@0.2.121
	wasm-bindgen@0.2.121
	wayland-backend@0.3.15
	wayland-client@0.31.14
	wayland-csd-frame@0.3.0
	wayland-cursor@0.31.14
	wayland-egl@0.32.11
	wayland-protocols-experimental@20250721.0.1
	wayland-protocols-misc@0.3.12
	wayland-protocols-wlr@0.3.12
	wayland-protocols@0.32.12
	wayland-scanner@0.31.11
	wayland-sys@0.31.11
	web-sys@0.3.98
	windows-link@0.2.1
	windows-sys@0.61.2
	xcursor@0.3.10
	xkbcommon@0.8.0
	xkeysym@0.2.1
	zune-core@0.5.1
	zune-jpeg@0.5.15
"

RUST_MIN_VER="1.95.0"
inherit cargo systemd

DESCRIPTION="GPU-accelerated scriptable Wayland wallpaper daemon"
HOMEPAGE="https://github.com/kris004/mural"
COMMIT="6c90e890e27ea642716ecf58559cff98aa807619"
SRC_URI="
	https://github.com/kris004/mural/archive/${COMMIT}.tar.gz -> ${P}.tar.gz
	${CARGO_CRATE_URIS}
"
S="${WORKDIR}/${PN}-${COMMIT}"

LICENSE="
	|| ( Apache-2.0 MIT )
	0BSD Apache-2.0 Apache-2.0-with-LLVM-exceptions
	BSD ISC MIT Unicode-3.0 Unlicense ZLIB
"
SLOT="0"
KEYWORDS="~amd64"
IUSE="vips"

DEPEND="
	dev-libs/wayland
	media-libs/libglvnd
	x11-libs/libxkbcommon
"
RDEPEND="
	${DEPEND}
	vips? ( media-libs/vips )
"
BDEPEND="virtual/pkgconfig"

src_compile() {
	cargo_src_compile --locked --workspace
}

src_test() {
	cargo_src_test --locked --workspace --all-targets
}

src_install() {
	emake \
		CARGO=true \
		CARGO_FLAGS=--frozen \
		CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-target}" \
		DESTDIR="${D}" \
		PREFIX="${EPREFIX}/usr" \
		BINDIR="${EPREFIX}/usr/bin" \
		MANDIR="${EPREFIX}/usr/share/man" \
		DOCDIR="${EPREFIX}/usr/share/doc/${PF}" \
		SYSTEMD_USER_DIR="$(systemd_get_userunitdir)" \
		install
}

pkg_postinst() {
	einfo "Copy the example config into ~/.config/mural/config.toml before use."
	einfo "Enable the daemon with: systemctl --user enable --now murald.service"
	if ! use vips; then
		einfo "Enable USE=vips to install vipsthumbnail for faster image preparation."
	fi
}
