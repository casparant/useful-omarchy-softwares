# Repository instructions

This repository maintains Arch packaging recipes and Omarchy integration. Read README.md and the relevant package README before changing a recipe.

- Keep each pkgbase self-contained in pkgbuilds/<pkgbase>. Match the directory and pkgbase names.
- Keep catalog.json current. Distinguish a recipe's declared architectures, verified downloads/staging, Linux builds, and real runtime testing.
- Pin upstream versions and HTTPS URLs, and provide SHA256 for every source including local files. Do not add latest URLs or SKIP for ordinary release archives.
- Never run upstream installation scripts in PKGBUILD. package() only stages files under pkgdir; do not log in, start services, edit user configuration or enable autostart.
- Keep vendor binaries unchanged unless a reviewed compatibility patch is required. Do not commit downloads or generated packages. The 0BSD repository license covers our own code, not third-party applications.
- Existing maintained AUR packages are collaboration targets. Do not create duplicate AUR submissions. Keep .omarchy metadata out of AUR exports.
- New candidates use sync=false until real Linux validation and licensing for any intended binary distribution are resolved. Do not upload vendor binaries as CI artifacts or Releases by default.
- After edits run tools/check-package and python3 -m unittest discover -s tests -v. On Arch also run tools/check-package --require-makepkg and the Linux build/lifecycle checks in docs/testing.md.
- Bump pkgrel for packaging changes to published packages; reset it for a new pkgver. Never silently introduce an epoch.
- Documentation is primarily Chinese. Link primary upstream sources and record dates for release/architecture claims.
