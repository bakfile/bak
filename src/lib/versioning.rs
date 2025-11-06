#[allow(nonstandard_style)]
pub const DB_SCHEMA_VERSION: u32 = 1;

const CRATE_VERSION: &str = clap::crate_version!();

#[allow(nonstandard_style)]
pub fn LIBBAKFILE_VERSION() -> semver::Version { 
    /* This function provides the version of the bakfile *library*. To get the crate version, which is also the version
     * of the bak *executable*, use BAK_VERSION()
     */
    semver::Version::parse(CRATE_VERSION).unwrap()
}