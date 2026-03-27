/*
 * Download Module - Handles downloading files from Anna's Archive
 * 
 * This module contains the logic for actually downloading files
 * using BitTorrent protocol through aria2c.
 * 
 * Why use BitTorrent?
 * - Anna's Archive provides files via torrents (no donation needed!)
 * - Direct downloads often require paid access
 * - BitTorrent is decentralized and reliable
 * 
 * How the download works:
 * 1. Search for the file in Anna's Archive metadata
 * 2. Find which torrent contains the file
 * 3. Download the .torrent file OR use a magnet link
 * 4. Use aria2c to download the actual file
 */

use anyhow::{Result, anyhow};  // For error handling
use std::path::PathBuf;  // For file paths
use log::{info, error, warn};  // For logging
use tokio::process::Command;  // For running external programs

mod anna;  // Import Anna's Archive API functions

/*
 * Configuration for downloads
 * 
 * These are the settings we can customize for each download.
 * They have sensible defaults but can be changed if needed.
 */
#[derive(Debug, Clone)]
pub struct DownloadConfig {
    pub output_dir: PathBuf,  // Where to save downloaded files
    pub use_tor: bool,  // Route through Tor network?
    pub max_connections: u32,  // Max simultaneous connections
    pub timeout_secs: u64,  // How long to wait before giving up
}

/*
 * Default settings
 * 
 * These are used if you don't specify custom settings.
 * - Current directory as output
 * - No Tor (direct connection)
 * - 10 connections (good balance)
 * - 5 minute timeout
 */
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

/*
 * Main download function
 * 
 * This is the main entry point for downloading a file.
 * It coordinates the whole process:
 * 1. Search for the file
 * 2. Find the right torrent
 * 3. Download using aria2c
 * 
 * Arguments:
 *   md5 - The MD5 hash of the file you want
 *   output_dir - Where to save it
 *   filename - Optional custom filename
 *   use_tor - Whether to use Tor network
 * 
 * Returns:
 *   The path where the file was saved
 */
pub async fn download_file(
    md5: &str,
    output_dir: &PathBuf,
    filename: Option<&str>,
    use_tor: bool,
) -> Result<PathBuf> {
    // Step 1: Find the file in Anna's Archive
    info!("Searching for MD5: {}", md5);
    
    // Ask Anna's Archive API to find files with this MD5
    let files = anna::search_metadata(md5, 1).await?;
    
    // If nothing found, give up
    if files.is_empty() {
        return Err(anyhow!("File not found in Anna's Archive: {}", md5));
    }
    
    // Get the first match
    let file = &files[0];
    
    // Figure out what to name the file
    let name = filename.unwrap_or(&file.name).to_string();
    let output_path = output_dir.join(&name);
    
    info!("Found file: {} ({} bytes)", file.name, file.size);
    
    // Step 2: Find which torrent has this file
    // We need to search through all torrents to find the right one
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
    
    // Still nothing? Give up
    let torrent = target_torrent.ok_or_else(|| anyhow!("Could not find torrent for file"))?;
    
    info!("Found in torrent: {}", torrent.name);
    
    // Step 3: Actually download it using aria2c
    download_via_aria2(&torrent.info_hash, &torrent.name, output_dir, filename, use_tor).await?;
    
    // Return where we saved it
    let final_path = if let Some(name) = filename {
        output_dir.join(name)
    } else {
        output_dir.join(&file.name)
    };
    
    // Check if it actually got downloaded
    if final_path.exists() {
        info!("Download complete: {:?}", final_path);
        Ok(final_path)
    } else {
        Err(anyhow!("Download completed but file not found at expected path"))
    }
}

/*
 * Download using aria2c
 * 
 * aria2c is a command-line BitTorrent client.
 * We use it because:
 * - It works well on all platforms
 * - It's fast and supports parallel downloads
 * - It handles magnets well
 * 
 * Arguments:
 *   info_hash - The torrent's unique ID
 *   name - The name for display
 *   output_dir - Where to save
 *   filename - Optional custom filename
 *   use_tor - Whether to route through Tor
 */
async fn download_via_aria2(
    info_hash: &str,
    name: &str,
    output_dir: &PathBuf,
    filename: Option<&str>,
    use_tor: bool,
) -> Result<()> {
    // Step 1: Create a "magnet link"
    // A magnet link is like a compact URL that tells BitTorrent
    // what to download without needing a .torrent file
    let magnet = format!(
        "magnet:?xt=urn:btih:{}&dn={}",
        info_hash,
        urlencoding::encode(name)
    );
    
    info!("Using magnet: {}", &magnet[..80]);
    
    // Step 2: Build the aria2c command
    // This is the command we'll run
    let mut cmd = Command::new("aria2c");
    
    // Add the magnet link
    cmd.arg(&magnet)
        // Where to save files
        .arg("--dir")
        .arg(output_dir)
        // Stop seeding after download (we just want the file)
        .arg("--seed-time=0")
        // Use multiple connections for speed
        .arg("--max-connection-per-server=5")
        .arg("--split=10")
        // If interrupted, resume where we left off
        .arg("--continue")
        // If it fails, try a few more times
        .arg("--max-tries=3")
        .arg("--retry-wait=5");
    
    // Add filename if specified
    if let Some(fname) = filename {
        cmd.arg("--out").arg(fname);
    }
    
    // Add Tor proxy if requested
    // Tor listens on port 9050 by default
    if use_tor {
        cmd.arg("--all-proxy=socks5://127.0.0.1:9050");
    }
    
    // Step 3: Run the command and wait for it to finish
    let status = cmd.spawn()?.wait().await?;
    
    // Check if it worked
    if !status.success() {
        warn!("aria2c exited with status: {}", status);
    }
    
    Ok(())
}

/*
 * Generate a magnet link from info hash
 * 
 * This creates a shareable magnet URL.
 * You can give this to someone and they can start downloading.
 * 
 * Arguments:
 *   info_hash - The torrent's unique ID
 *   name - The torrent's name
 * 
 * Returns:
 *   A magnet link string
 */
pub fn generate_magnet(info_hash: &str, name: &str) -> String {
    format!(
        "magnet:?xt=urn:btih:{}&dn={}",
        info_hash,
        urlencoding::encode(name)
    )
}
