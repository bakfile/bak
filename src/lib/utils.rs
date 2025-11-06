use std::process::Command;
use std::path::PathBuf;

use anyhow::Result;

pub fn sha256_files(file1: PathBuf, file2: PathBuf) -> Result<bool> {
    fn hash(file: PathBuf) -> Result<Vec<u8>> {

        #[cfg(target_family = "unix")]
        static SHA256: &str = "shasum -a 256 %f";
    
        // The Get-FileHash commandlet seems to default to sha256, but let's be certain
        #[cfg(target_family = "windows")]
        static SHA256: &str = "powershell -command (Get-FileHash -Path %f -Algorithm SHA256).Hash";

        let file_path: &str = file.to_str().unwrap();

        let command_str = SHA256.replace("%f", file_path);
        let command_split: Vec<&str> = command_str.split(' ').collect();
        let mut command = Command::new(command_split[0]);
        command.args(&command_split[1..]);
        return Ok(command.output()?.stdout) 
    }
    
    let hash1 = hash(file1)?;
    let hash2 = hash(file2)?;
    #[cfg(target_family = "unix")]
    let out = hash1[0] == hash2[0];
    #[cfg(target_family = "windows")]
    let out = hash1.iter().eq(&hash2);
    return Ok(out)
}