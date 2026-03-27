/*
 * Anna's Archive API Integration - Rust Version
 * 
 * This module handles talking to Anna's Archive's website.
 * It fetches their public torrent metadata so we can find files.
 * 
 * What Anna's Archive provides:
 * - A public JSON API with all their torrent information
 * - No login required for searching!
 * - Contains files from Z-Library, LibGen, Sci-Hub, etc.
 * 
 * Why use their API?
 * - It's free and public
 * - No authentication needed for metadata
 * - Returns JSON (easy to work with)
 * - Updated regularly
 */

use anyhow::{Result, anyhow};  // For error handling
use serde::{Deserialize, Serialize};  // For converting data
use reqwest::Client;  // For making HTTP requests
use log::{info, debug, warn};  // For logging messages

// The main API endpoint for Anna's Archive (JSON with all torrents)
const ANNAS_ARCHIVE_API: &str = "https://annas-archive.org/dyn/torrents.json";

// Where to download .torrent files (individual torrent downloads)
const ANNAS_TORRENT_URL: &str = "https://annas-archive.org/torrent";

/*
 * This represents a torrent file in Anna's Archive
 * 
 * Think of it like a catalog entry for a book.
 * Each torrent contains multiple files.
 */
#[derive(Debug, Deserialize, Serialize)]
pub struct AnnaTorrent {
    pub info_hash: String,  // Unique ID for this torrent
    pub name: String,  // Name like "Z-Library Books Collection"
    pub size: u64,  // Total size in bytes
    pub files: Vec<AnnaFile>,  // All files in this torrent
    pub trackers: Vec<String>,  // Where to find peers
    #[serde(default)]
    pub source: String,  // Where it came from (zlib, libgen, etc.)
}

/*
 * This represents a single file inside a torrent
 */
#[derive(Debug, Deserialize, Serialize)]
pub struct AnnaFile {
    pub md5: Option<String>,  // File's unique fingerprint (MD5)
    pub sha256: Option<String>,  // Another fingerprint (SHA256)
    pub name: String,  // Filename like "book.pdf"
    pub size: u64,  // File size in bytes
    pub path: Option<String>,  // Path inside the torrent
}

/*
 * This is the main API response structure
 */
#[derive(Debug, Deserialize, Serialize)]
pub struct TorrentMetadata {
    pub torrents: Vec<AnnaTorrent>,  // All available torrents
    pub total: usize,  // How many torrents
}

/*
 * Search for a file by its MD5 hash
 * 
 * Main function: give MD5 hash, get matching files
 */
pub async fn search_metadata(md5: &str, limit: usize) -> Result<Vec<AnnaFile>> {
    let client = Client::new();
    
    info!("Fetching Anna's Archive torrent metadata...");
    
    // Get the full list of torrents from their public API
    let response = client
        .get(ANNAS_ARCHIVE_API)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await?;
    
    if !response.status().is_success() {
        return Err(anyhow!("API request failed: {}", response.status()));
    }
    
    let metadata: TorrentMetadata = response.json().await?;
    
    // Search through all torrents and files
    let mut results = Vec::new();
    let mut count = 0;
    
    for torrent in &metadata.torrents {
        for file in &torrent.files {
            if let Some(file_md5) = &file.md5 {
                if file_md5.to_lowercase() == md5.to_lowercase() {
                    results.push(file.clone());
                    count += 1;
                    if count >= limit { break; }
                }
            }
        }
        if count >= limit { break; }
    }
    
    info!("Found {} files matching MD5: {}", results.len(), md5);
    
    if results.is_empty() {
        warn!("No files found with MD5: {}", md5);
    }
    
    Ok(results)
}

/*
 * Get information about a specific torrent
 */
pub async fn get_torrent_info(info_hash: &str) -> Result<AnnaTorrent> {
    let client = Client::new();
    
    let url = format!(
        "{}/{}", 
        ANNAS_ARCHIVE_API.replace("/dyn/torrents.json", "/dyn/torrent"), 
        info_hash
    );
    
    let response = client
        .get(&url)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await?;
    
    if response.status().is_success() {
        let torrent: AnnaTorrent = response.json().await?;
        info!("Found torrent: {} ({} files)", torrent.name, torrent.files.len());
        return Ok(torrent);
    }
    
    // Fallback: search through all torrents
    let metadata: TorrentMetadata = client
        .get(ANNAS_ARCHIVE_API)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await?
        .json()
        .await?;
    
    for torrent in metadata.torrents {
        if torrent.info_hash.to_lowercase() == info_hash.to_lowercase() {
            return Ok(torrent);
        }
    }
    
    Err(anyhow!("Torrent not found: {}", info_hash))
}

/*
 * Download the actual .torrent file
 */
pub async fn download_torrent_file(info_hash: &str) -> Result<Vec<u8>> {
    let client = Client::new();
    
    let url = format!("{}/{}", ANNAS_TORRENT_URL, info_hash);
    
    info!("Downloading torrent file: {}", info_hash);
    
    let response = client
        .get(&url)
        .timeout(std::time::Duration::from_secs(60))
        .send()
        .await?;
    
    if !response.status().is_success() {
        return Err(anyhow!("Failed to download torrent: {}", response.status()));
    }
    
    let bytes = response.bytes().await?.to_vec();
    info!("Downloaded {} bytes", bytes.len());
    
    Ok(bytes)
}

/*
 * List all available torrents
 */
pub async fn list_torrents(collection: Option<&str>, limit: usize) -> Result<Vec<AnnaTorrent>> {
    let client = Client::new();
    
    info!("Fetching torrent list...");
    
    let response = client
        .get(ANNAS_ARCHIVE_API)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await?;
    
    let metadata: TorrentMetadata = response.json().await?;
    
    let filtered: Vec<AnnaTorrent> = metadata.torrents
        .into_iter()
        .filter(|t| {
            if let Some(col) = collection {
                t.name.to_lowercase().contains(&col.to_lowercase())
            } else {
                true
            }
        })
        .take(limit)
        .collect();
    
    info!("Found {} torrents", filtered.len());
    
    for torrent in &filtered {
        println!("  - {} ({} files, {})", 
            torrent.name, 
            torrent.files.len(),
            format_size(torrent.size)
        );
    }
    
    Ok(filtered)
}

/*
 * Helper function to format file sizes nicely
 * Converts bytes to KB/MB/GB
 */
fn format_size(bytes: u64) -> String {
    const KB: u64 = 1024;
    const MB: u64 = KB * 1024;
    const GB: u64 = MB * 1024;
    
    if bytes >= GB {
        format!("{:.2} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.2} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.2} KB", bytes as f64 / KB as f64)
    } else {
        format!("{} B", bytes)
    }
}
