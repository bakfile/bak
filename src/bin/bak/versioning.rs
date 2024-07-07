const CRATE_VERSION: &str = clap::crate_version!();

#[allow(nonstandard_style)]
pub fn BAK_VERSION() -> semver::Version { 
    /* This function provides the version of the bak *crate*, which is also the version of the bak *executable* (bak-bin).
     * For the separately-maintained libbakfile version, use LIBBAK_VERSION()
     */
    semver::Version::parse(CRATE_VERSION).unwrap()
}
