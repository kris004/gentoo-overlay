# Copyright 2026 Kristopher Keller
# Distributed under the terms of the GNU General Public License v2

EAPI=8

CRATES="
	aho-corasick@1.1.4
	anstream@1.0.0
	anstyle-parse@1.0.0
	anstyle-query@1.1.5
	anstyle-wincon@3.0.11
	anstyle@1.0.14
	anyhow@1.0.103
	async-broadcast@0.7.2
	async-recursion@1.1.1
	async-trait@0.1.89
	atomic-waker@1.1.2
	autocfg@1.5.1
	base64@0.22.1
	bitflags@2.13.0
	bumpalo@3.20.3
	bytes@1.11.1
	cc@1.2.64
	cfg-if@1.0.4
	clap@4.6.1
	clap_builder@4.6.0
	clap_derive@4.6.1
	clap_lex@1.1.0
	colorchoice@1.0.5
	core-foundation-sys@0.8.7
	core-foundation@0.10.1
	displaydoc@0.2.6
	endi@1.1.1
	enumflags2@0.7.12
	enumflags2_derive@0.7.12
	equivalent@1.0.2
	errno@0.3.14
	event-listener-strategy@0.5.4
	event-listener@5.4.2
	fastrand@2.4.1
	find-msvc-tools@0.1.9
	foldhash@0.1.5
	foreign-types-shared@0.1.1
	foreign-types@0.3.2
	form_urlencoded@1.2.2
	fsevent-sys@4.1.0
	futures-channel@0.3.32
	futures-core@0.3.32
	futures-io@0.3.32
	futures-lite@2.6.1
	futures-macro@0.3.32
	futures-task@0.3.32
	futures-util@0.3.32
	getrandom@0.4.2
	hashbrown@0.15.5
	hashbrown@0.17.1
	heck@0.5.0
	hex@0.4.3
	http-body-util@0.1.3
	http-body@1.0.1
	http@1.4.2
	httparse@1.10.1
	hyper-tls@0.6.0
	hyper-util@0.1.20
	hyper@1.10.1
	icu_collections@2.2.0
	icu_locale_core@2.2.0
	icu_normalizer@2.2.0
	icu_normalizer_data@2.2.0
	icu_properties@2.2.0
	icu_properties_data@2.2.0
	icu_provider@2.2.0
	id-arena@2.3.0
	idna@1.1.0
	idna_adapter@1.2.2
	indexmap@2.14.0
	inotify-sys@0.1.5
	inotify@0.11.2
	ipnet@2.12.0
	is_terminal_polyfill@1.70.2
	itoa@1.0.18
	js-sys@0.3.102
	kqueue-sys@1.1.2
	kqueue@1.2.0
	lazy_static@1.5.0
	leb128fmt@0.1.0
	libc@0.2.186
	linux-raw-sys@0.12.1
	litemap@0.8.2
	log@0.4.32
	matchers@0.2.0
	memchr@2.8.2
	memoffset@0.9.1
	mio@1.2.1
	native-tls@0.2.18
	notify-types@2.1.0
	notify@8.2.0
	nu-ansi-term@0.50.3
	once_cell@1.21.4
	once_cell_polyfill@1.70.2
	openssl-macros@0.1.1
	openssl-probe@0.2.1
	openssl-sys@0.9.117
	openssl@0.10.81
	ordered-stream@0.2.0
	parking@2.2.1
	percent-encoding@2.3.2
	pin-project-lite@0.2.17
	pkg-config@0.3.33
	potential_utf@0.1.5
	prettyplease@0.2.37
	proc-macro-crate@3.5.0
	proc-macro2@1.0.106
	quote@1.0.45
	r-efi@6.0.0
	regex-automata@0.4.14
	regex-syntax@0.8.11
	reqwest@0.12.28
	rustix@1.1.4
	rustls-pki-types@1.14.1
	rustversion@1.0.22
	ryu@1.0.23
	same-file@1.0.6
	schannel@0.1.29
	security-framework-sys@2.17.0
	security-framework@3.7.0
	semver@1.0.28
	serde@1.0.228
	serde_core@1.0.228
	serde_derive@1.0.228
	serde_json@1.0.150
	serde_repr@0.1.20
	serde_spanned@0.6.9
	serde_urlencoded@0.7.1
	sharded-slab@0.1.7
	shell-words@1.1.1
	shlex@2.0.1
	signal-hook-registry@1.4.8
	slab@0.4.12
	smallvec@1.15.2
	socket2@0.6.4
	stable_deref_trait@1.2.1
	strsim@0.11.1
	syn@2.0.117
	sync_wrapper@1.0.2
	synstructure@0.13.2
	tempfile@3.27.0
	thiserror-impl@2.0.18
	thiserror@2.0.18
	thread_local@1.1.9
	tinystr@0.8.3
	tokio-macros@2.7.0
	tokio-native-tls@0.3.1
	tokio@1.52.3
	toml@0.8.23
	toml_datetime@0.6.11
	toml_datetime@1.1.1+spec-1.1.0
	toml_edit@0.22.27
	toml_edit@0.25.12+spec-1.1.0
	toml_parser@1.1.2+spec-1.1.0
	toml_write@0.1.2
	tower-http@0.6.11
	tower-layer@0.3.3
	tower-service@0.3.3
	tower@0.5.3
	tracing-attributes@0.1.31
	tracing-core@0.1.36
	tracing-log@0.2.0
	tracing-subscriber@0.3.23
	tracing@0.1.44
	try-lock@0.2.5
	uds_windows@1.2.1
	unicode-ident@1.0.24
	unicode-xid@0.2.6
	url@2.5.8
	utf8_iter@1.0.4
	utf8parse@0.2.2
	uuid@1.23.3
	valuable@0.1.1
	vcpkg@0.2.15
	walkdir@2.5.0
	want@0.3.1
	wasi@0.11.1+wasi-snapshot-preview1
	wasip2@1.0.4+wasi-0.2.12
	wasip3@0.4.0+wasi-0.3.0-rc-2026-01-06
	wasm-bindgen-futures@0.4.75
	wasm-bindgen-macro-support@0.2.125
	wasm-bindgen-macro@0.2.125
	wasm-bindgen-shared@0.2.125
	wasm-bindgen@0.2.125
	wasm-encoder@0.244.0
	wasm-metadata@0.244.0
	wasmparser@0.244.0
	web-sys@0.3.102
	winapi-util@0.1.11
	windows-link@0.2.1
	windows-sys@0.60.2
	windows-sys@0.61.2
	windows-targets@0.53.5
	windows_aarch64_gnullvm@0.53.1
	windows_aarch64_msvc@0.53.1
	windows_i686_gnu@0.53.1
	windows_i686_gnullvm@0.53.1
	windows_i686_msvc@0.53.1
	windows_x86_64_gnu@0.53.1
	windows_x86_64_gnullvm@0.53.1
	windows_x86_64_msvc@0.53.1
	winnow@0.7.15
	winnow@1.0.3
	wit-bindgen-core@0.51.0
	wit-bindgen-rust-macro@0.51.0
	wit-bindgen-rust@0.51.0
	wit-bindgen@0.51.0
	wit-bindgen@0.57.1
	wit-component@0.244.0
	wit-parser@0.244.0
	writeable@0.6.3
	yoke-derive@0.8.2
	yoke@0.8.3
	zbus@5.16.0
	zbus_macros@5.16.0
	zbus_names@4.3.2
	zerofrom-derive@0.1.7
	zerofrom@0.1.8
	zeroize@1.9.0
	zerotrie@0.2.4
	zerovec-derive@0.11.3
	zerovec@0.11.6
	zmij@1.0.21
	zvariant@5.12.0
	zvariant_derive@5.12.0
	zvariant_utils@3.4.0
"

RUST_MIN_VER="1.95.0"
inherit cargo systemd

DESCRIPTION="Event-driven daemon that runs commands when configured sources change"
HOMEPAGE="https://github.com/kris004/mailwake"
COMMIT="35531e5a74d3ecd61ca964999dfe15ba1545bf2b"
SRC_URI="
	https://github.com/kris004/mailwake/archive/${COMMIT}.tar.gz -> ${P}.tar.gz
	${CARGO_CRATE_URIS}
"
S="${WORKDIR}/${PN}-${COMMIT}"

LICENSE="|| ( Apache-2.0 MIT ) Apache-2.0 CC0-1.0 ISC MIT Unicode-3.0"
SLOT="0"
KEYWORDS="~amd64"

DEPEND="dev-libs/openssl:0="
RDEPEND="${DEPEND}"
BDEPEND="virtual/pkgconfig"

src_compile() {
	cargo_src_compile --locked --bin mailwake
}

src_test() {
	TMPDIR="/tmp" cargo_src_test --locked
}

src_install() {
	cargo_src_install --locked --path .

	sed \
		-e 's|^ExecStart=.*|ExecStart=/usr/bin/mailwake --config %h/.config/mailwake/config.toml|' \
		contrib/systemd/mailwake.service > "${T}/mailwake.service" || die
	systemd_douserunit "${T}/mailwake.service"

	dodoc README.md SECURITY.md THIRD_PARTY_LICENSES.html
	docinto docs
	dodoc docs/*.md
	docinto examples
	dodoc examples/*.toml
	docinto examples/systemd
	dodoc contrib/systemd/mailwake-hardened.service
	docinto examples/oauth
	dodoc contrib/oauth/gmail-oauth-token-oauth2l
}

pkg_postinst() {
	einfo "Copy an example configuration to ~/.config/mailwake/config.toml,"
	einfo "set its mode to 0600, and edit it before starting the user service."
	einfo "Enable the service with: systemctl --user enable --now mailwake.service"
}
