# Copyright 2026 Kristopher Keller
# Distributed under the terms of the GNU General Public License v2

EAPI=8

CRATES="
	aho-corasick@1.1.4
	ammonia@4.1.2
	android_system_properties@0.1.5
	anstream@1.0.0
	anstyle-parse@1.0.0
	anstyle-query@1.1.5
	anstyle-wincon@3.0.11
	anstyle@1.0.14
	anyhow@1.0.102
	async-trait@0.1.89
	autocfg@1.5.1
	base64@0.22.1
	bindgen@0.72.1
	bitflags@2.13.0
	bumpalo@3.20.3
	bytes@1.12.0
	cairo-rs@0.22.0
	cairo-sys-rs@0.22.0
	cc@1.2.64
	cexpr@0.6.0
	cfg-expr@0.20.8
	cfg-if@1.0.4
	charset@0.1.5
	chrono@0.4.45
	clang-sys@1.8.1
	clap@4.6.1
	clap_builder@4.6.0
	clap_derive@4.6.1
	clap_lex@1.1.0
	colorchoice@1.0.5
	core-foundation-sys@0.8.7
	cssparser-macros@0.6.1
	cssparser@0.35.0
	data-encoding@2.11.0
	displaydoc@0.2.6
	dtoa-short@0.3.5
	dtoa@1.0.11
	either@1.16.0
	email_address@0.2.9
	encoding_rs@0.8.35
	equivalent@1.0.2
	errno@0.3.14
	fastrand@2.4.1
	field-offset@0.3.6
	find-msvc-tools@0.1.9
	form_urlencoded@1.2.2
	futf@0.1.5
	futures-channel@0.3.32
	futures-core@0.3.32
	futures-executor@0.3.32
	futures-io@0.3.32
	futures-macro@0.3.32
	futures-task@0.3.32
	futures-util@0.3.32
	gdk-pixbuf-sys@0.22.0
	gdk-pixbuf@0.22.0
	gdk4-sys@0.11.2
	gdk4@0.11.2
	getrandom@0.4.3
	gio-sys@0.22.0
	gio@0.22.6
	glib-macros@0.22.6
	glib-sys@0.22.6
	glib@0.22.7
	glob@0.3.3
	gobject-sys@0.22.6
	graphene-rs@0.22.0
	graphene-sys@0.22.0
	gsk4-sys@0.11.1
	gsk4@0.11.1
	gtk4-macros@0.11.0
	gtk4-sys@0.11.3
	gtk4@0.11.3
	hashbrown@0.17.1
	heck@0.5.0
	html2text@0.16.5
	html5ever@0.35.0
	html5ever@0.36.1
	iana-time-zone-haiku@0.1.2
	iana-time-zone@0.1.65
	icu_collections@2.2.0
	icu_locale_core@2.2.0
	icu_normalizer@2.2.0
	icu_normalizer_data@2.2.0
	icu_properties@2.2.0
	icu_properties_data@2.2.0
	icu_provider@2.2.0
	idna@1.1.0
	idna_adapter@1.2.2
	indexmap@2.14.0
	is_terminal_polyfill@1.70.2
	itertools@0.13.0
	itoa@1.0.18
	javascriptcore6-sys@0.6.0
	javascriptcore6@0.6.0
	js-sys@0.3.102
	lazy_static@1.5.0
	libc@0.2.186
	libloading@0.8.9
	linux-raw-sys@0.12.1
	litemap@0.8.2
	lock_api@0.4.14
	log@0.4.32
	mac@0.1.1
	mailparse@0.16.1
	maplit@1.0.2
	markup5ever@0.35.0
	markup5ever@0.36.1
	match_token@0.35.0
	matchers@0.2.0
	memchr@2.8.2
	memoffset@0.9.1
	minimal-lexical@0.2.1
	mio@1.2.1
	new_debug_unreachable@1.0.6
	nom@7.1.3
	nu-ansi-term@0.50.3
	num-traits@0.2.19
	once_cell@1.21.4
	once_cell_polyfill@1.70.2
	pango-sys@0.22.0
	pango@0.22.6
	parking_lot@0.12.5
	parking_lot_core@0.9.12
	percent-encoding@2.3.2
	phf@0.11.3
	phf@0.13.1
	phf_codegen@0.11.3
	phf_codegen@0.13.1
	phf_generator@0.11.3
	phf_generator@0.13.1
	phf_macros@0.11.3
	phf_shared@0.11.3
	phf_shared@0.13.1
	pin-project-lite@0.2.17
	pkg-config@0.3.33
	potential_utf@0.1.5
	precomputed-hash@0.1.1
	prettyplease@0.2.37
	proc-macro-crate@3.5.0
	proc-macro2@1.0.106
	quote@1.0.45
	quoted_printable@0.5.2
	r-efi@6.0.0
	rand@0.8.6
	rand_core@0.6.4
	redox_syscall@0.5.18
	regex-automata@0.4.14
	regex-syntax@0.8.11
	regex@1.12.4
	rustc-hash@2.1.2
	rustc_version@0.4.1
	rustix@1.1.4
	rustversion@1.0.22
	scopeguard@1.2.0
	semver@1.0.28
	serde@1.0.228
	serde_core@1.0.228
	serde_derive@1.0.228
	serde_json@1.0.150
	serde_spanned@0.6.9
	serde_spanned@1.1.1
	sharded-slab@0.1.7
	shell-words@1.1.1
	shlex@1.3.0
	shlex@2.0.1
	signal-hook-registry@1.4.8
	siphasher@1.0.3
	slab@0.4.12
	smallvec@1.15.2
	soup3-sys@0.9.0
	soup3@0.9.0
	sourceview5-sys@0.11.0
	sourceview5@0.11.0
	stable_deref_trait@1.2.1
	string_cache@0.8.9
	string_cache@0.9.0
	string_cache_codegen@0.5.4
	string_cache_codegen@0.6.1
	strsim@0.11.1
	syn@2.0.118
	synstructure@0.13.2
	system-deps@7.0.8
	target-lexicon@0.13.5
	tempfile@3.27.0
	tendril@0.4.3
	thiserror-impl@2.0.18
	thiserror@2.0.18
	thread_local@1.1.9
	tinystr@0.8.3
	tokio-macros@2.7.0
	tokio@1.52.3
	toml@0.8.23
	toml@1.1.2+spec-1.1.0
	toml_datetime@0.6.11
	toml_datetime@1.1.1+spec-1.1.0
	toml_edit@0.22.27
	toml_edit@0.25.12+spec-1.1.0
	toml_parser@1.1.2+spec-1.1.0
	toml_write@0.1.2
	toml_writer@1.1.1+spec-1.1.0
	tracing-attributes@0.1.31
	tracing-core@0.1.36
	tracing-log@0.2.0
	tracing-subscriber@0.3.23
	tracing@0.1.44
	unicode-ident@1.0.24
	unicode-width@0.2.2
	url@2.5.8
	utf-8@0.7.6
	utf8_iter@1.0.4
	utf8parse@0.2.2
	uuid@1.23.3
	valuable@0.1.1
	version-compare@0.2.1
	wasi@0.11.1+wasi-snapshot-preview1
	wasm-bindgen-macro-support@0.2.125
	wasm-bindgen-macro@0.2.125
	wasm-bindgen-shared@0.2.125
	wasm-bindgen@0.2.125
	web_atoms@0.1.3
	web_atoms@0.2.6
	webkit6-sys@0.6.0
	webkit6@0.6.1
	windows-core@0.62.2
	windows-implement@0.60.2
	windows-interface@0.59.3
	windows-link@0.2.1
	windows-result@0.4.1
	windows-strings@0.5.1
	windows-sys@0.61.2
	winnow@0.7.15
	winnow@1.0.3
	writeable@0.6.3
	yoke-derive@0.8.2
	yoke@0.8.3
	zerofrom-derive@0.1.7
	zerofrom@0.1.8
	zerotrie@0.2.4
	zerovec-derive@0.11.3
	zerovec@0.11.6
	zmij@1.0.21
"

RUST_MIN_VER="1.92.0"
LLVM_COMPAT=( {17..22} )
inherit cargo llvm-r2 xdg

DESCRIPTION="Fast, keyboard-first desktop mail client backed by notmuch"
HOMEPAGE="https://github.com/kris004/notm"
COMMIT="dc56fdf2837f9d4f2546b0295e8defbd7552f636"
SRC_URI="
	https://github.com/kris004/notm/archive/${COMMIT}.tar.gz -> ${P}.tar.gz
	${CARGO_CRATE_URIS}
"
S="${WORKDIR}/${PN}-${COMMIT}"

LICENSE="
	GPL-3+ CC0-1.0
	0BSD Apache-2.0 Apache-2.0-with-LLVM-exceptions
	BSD ISC MIT MPL-2.0 Unicode-3.0 Unlicense
"
SLOT="0"
KEYWORDS="~amd64"
IUSE="test"
RESTRICT="!test? ( test )"

DEPEND="
	>=dev-libs/glib-2.56:2
	>=gui-libs/gtk-4.12:4
	>=gui-libs/gtksourceview-5.4:5
	>=media-libs/graphene-1.10
	>=net-libs/libsoup-3.0:3.0
	>=net-libs/webkit-gtk-2.40:6=
	>=net-mail/notmuch-0.38:0=
	>=x11-libs/cairo-1.14
	>=x11-libs/gdk-pixbuf-2.36.8:2
	>=x11-libs/pango-1.40
"
RDEPEND="${DEPEND}"
BDEPEND="
	virtual/pkgconfig
	$(llvm_gen_dep '
		llvm-core/clang:${LLVM_SLOT}=
		llvm-core/llvm:${LLVM_SLOT}=
	')
	test? (
		dev-libs/appstream
		dev-util/desktop-file-utils
	)
"

pkg_setup() {
	llvm-r2_pkg_setup
	rust_pkg_setup
}

src_compile() {
	cargo_src_compile --locked -p notm-app
}

src_test() {
	# The desktop_ui_smoke target starts a nested headless Sway compositor.
	# Portage's LD_PRELOAD sandbox prevents it from creating a Wayland socket;
	# upstream CI exercises that suite outside the Portage sandbox.
	local test_targets=(
		attachment_contract
		compose_send_contract
		config_validation
		fixture_database
		forward_attachment
		live_readonly_smoke
		live_self_send
		mime_rendering
		print_config
		probe_send
		reply_contract
		search_threads
		tag_ops
	)
	cargo_src_test --locked --workspace --all-features --lib --bins

	local target
	for target in "${test_targets[@]}"; do
		cargo_src_test --locked --workspace --all-features --test "${target}"
	done

	cargo_env cargo run --release --locked -p notm-app -- fixture-smoke
	emake check-packaging
}

src_install() {
	emake \
		PREFIX="${EPREFIX}/usr" \
		DESTDIR="${D}" \
		CARGO=true \
		BINARY="$(cargo_target_dir)/notm" \
		install

	dodoc CHANGELOG.md README.md
}
