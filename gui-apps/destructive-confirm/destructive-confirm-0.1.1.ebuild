# Copyright 2026 Kristopher Keller
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{11..15} )
inherit python-any-r1 toolchain-funcs

DESCRIPTION="Native GTK confirmation dialog with compile-time fire animation presets"
HOMEPAGE="https://github.com/kris004/destructive-confirm"
COMMIT="d033a6ffa349d72d8a95e0bae1a2ee79d9a8a597"
SRC_URI="https://github.com/kris004/destructive-confirm/archive/${COMMIT}.tar.gz -> ${P}.tar.gz"
S="${WORKDIR}/${PN}-${COMMIT}"

LICENSE="GPL-3+"
SLOT="0"
KEYWORDS="~amd64"
IUSE="animation-fire-ring animation-real-fire animation-svg +animation-tall-ring test"
REQUIRED_USE="?? ( animation-fire-ring animation-real-fire animation-svg animation-tall-ring )"
RESTRICT="!test? ( test )"

RDEPEND="
	>=gui-libs/gtk-4.14:4=
	>=gui-libs/libadwaita-1.5:1=
"
DEPEND="${RDEPEND}"
BDEPEND="
	dev-libs/glib:2
	virtual/pkgconfig
	test? (
		$(python_gen_any_dep 'dev-python/pillow[${PYTHON_USEDEP}]')
		dev-vcs/git
		sys-apps/coreutils
		sys-devel/binutils
	)
"

python_check_deps() {
	python_has_version "dev-python/pillow[${PYTHON_USEDEP}]"
}

pkg_setup() {
	if use test; then
		python-any-r1_pkg_setup
	fi
}

src_prepare() {
	default
	[[ $(< VERSION) == "${PV}" ]] || die "Source VERSION does not match package version"
}

src_configure() {
	local preset=ANIMATION_NONE
	use animation-fire-ring && preset=ANIMATION_FIRE_RING
	use animation-real-fire && preset=ANIMATION_REAL_FIRE
	use animation-svg && preset=ANIMATION_SVG_FLAMES
	use animation-tall-ring && preset=ANIMATION_TALL_RING
	printf '#define CONFIRM_ANIMATION %s\n' "${preset}" > config.h || die
}

src_compile() {
	tc-export CC PKG_CONFIG
	emake
}

src_test() {
	tc-export CC PKG_CONFIG
	export DC_TEST_TMPDIR="${T}"
	emake PYTHON="${EPYTHON}" check check-presets check-release
	"${EPYTHON}" -B -m unittest discover -s art -v || die "Artwork tests failed"
}

src_install() {
	emake DESTDIR="${D}" PREFIX="${EPREFIX}/usr" \
		DOCDIR="${EPREFIX}/usr/share/doc/${PF}" install
	dodoc CONTRIBUTING.md SECURITY.md
}
