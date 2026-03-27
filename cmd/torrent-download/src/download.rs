//! Download module - handles torrent file downloads
//!
//! Uses BitTorrent protocol to download files from Anna's Archive.
//! Falls back to magnet links if .torrent file unavailable.

use anyhow::{Result, anyhow};
use std::path::PathBuf;
use log::{info, error, warn};
use tokio::process::Command;

mod anna;

/// Configuration for downloads
#[derive(Debug, Clone)]
pub struct DownloadConfig {
    pub output_dir: PathBuf,
    pub use_tor: bool,
    pub max_connections: u32,
    pub timeout_secs: u64,
}

impl Default for DownloadConfig {
    fn default() -> Self {
        Self {
            output_dir: PathBuf::from("."),
            use_tor: false,
            max_connections: 10,
            timeout_secs: 300,
        }
    }
}

/// Download a file from Anna's Archive by MD5 hash
pub async fn download_file(
    md5: &str,
    output_dir: &PathBuf,
    filename: Option<&str>,
    use_tor: bool,
) -> Result<PathBuf> {
    // Step 1: Find the file in Anna's Archive metadata
    info!("Searching for MD5: {}", md5);
    
    let files = anna::search_metadata(md5, 1).await?;
    
    if files.is_empty() {
        return Err(anyhow!("File not found in Anna's Archive: {}", md5));
    }
    
    let file = &files[0];
    let name = filename.unwrap_or(&file.name).to_string();
    let output_path = output_dir.join(&name);
    
    info!("Found file: {} ({} bytes)", file.name, file.size);
    
    // Step 2: Try to get the info hash for this file
    // We need to find which torrent contains this file
    let torrents = anna::list_torrents(None, 100).await?;
    
    let mut target_torrent = None;
    for torrent in &torrents {
        for f in &torrent.files {
            if let Some(file_md5) = &f.md5 {
                if file_md5.to_lowercase() == md5.to_lowercase() {
                    target_torrent = Some(torrent.clone());
                    break;
                }
            }
        }
        if target_torrent.is_some() {
            break;
        }
    }
    
    let torrent = target_torrent.ok_or_else(|| anyhow!("Could not find torrent for file"))?;
    
    info!("Found in torrent: {}", torrent.name);
    
    // Step 3: Download using aria2c (fallback to magnet)
    // First try direct torrent download, then magnet
    download_via_aria2(&torrent.info_hash, &torrent.name, output_dir, filename, use_tor).await?;
    
    // Return the path to downloaded file
    let final_path = if let Some(name) = filename {
        output_dir.join(name)
    } else {
        output_dir.join(&file.name)
    };
    
    if final_path.exists() {
        info!("Download complete: {:?}", final_path);
        Ok(final_path)
    } else {
        Err(anyhow!("Download completed but file not found at expected path"))
    }
}

/// Download using aria2c with magnet link
async fn download_via_aria2(
    info_hash: &str,
    name: &str,
    output_dir: &PathBuf,
    filename: Option<&str>,
    use_tor: bool,
) -> Result<()> {
    // Generate magnet link
    let magnet = format!(
        "magnet:?xt=urn:btih:{}&dn={}",
        info_hash,
        urlencoding::encode(name)
    );
    
    info!("Using magnet: {}", &magnet[..80]);
    
    // Build aria2c command
    let mut cmd = Command::new("aria2c");
    cmd.arg(&magnet)
        .arg("--dir")
        .arg(output_dir)
        .arg("--seed-time=0")
        .arg("--max-connection-per-server=5")
        .arg("--split=10")
        .arg("--continue")
        .arg("--max-tries=3")
        .arg("--retry-wait=5");
    
    if let Some(fname) = filename {
        cmd.arg("--out").arg(fname);
    }
    
    if use_tor {
        // Route through Tor SOCKS5 proxy
        cmd.arg("--all-proxy=socks5://127.0.0.1:9050");
    }
    
    // Run the download
    let status = cmd.spawn()?.wait().await?;
    
    if !status.success() {
        warn!("aria2c exited with status: {}", status);
    }
    
    Ok(())
}

/// Generate magnet link from info hash
pub fn generate_magnet(info_hash: &str, name: &str) -> String {
    format!(
        "magnet:?xt=urn:btih:{}&dn={}",
        info_hash,
        urlencoding::encode(name)
    )
}

// Add urlencoding to Cargo.toml dependencies