//! Anna's Archive API integration
//! 
//! Fetches torrent metadata from Anna's Archive public endpoints.

use anyhow::{Result, anyhow};
use serde::{Deserialize, Serialize};
use reqwest::Client;
use log::{info, debug, warn};

const ANNAS_ARCHIVE_API: &str = "https://annas-archive.org/dyn/torrents.json";
const ANNAS_TORRENT_URL: &str = "https://annas-archive.org/torrent";

#[derive(Debug, Deserialize, Serialize)]
pub struct AnnaTorrent {
    pub info_hash: String,
    pub name: String,
    pub size: u64,
    pub files: Vec<AnnaFile>,
    pub trackers: Vec<String>,
    #[serde(default)]
    pub source: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct AnnaFile {
    pub md5: Option<String>,
    pub sha256: Option<String>,
    pub name: String,
    pub size: u64,
    pub path: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct TorrentMetadata {
    pub torrents: Vec<AnnaTorrent>,
    pub total: usize,
}

/// Search Anna's Archive metadata for a file by MD5 hash
pub async fn search_metadata(md5: &str, limit: usize) -> Result<Vec<AnnaFile>> {
    let client = Client::new();
    
    info!("Fetching Anna's Archive torrent metadata...");
    
    let response = client
        .get(ANNAS_ARCHIVE_API)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await?;
    
    if !response.status().is_success() {
        return Err(anyhow!("API request failed: {}", response.status()));
    }
    
    let metadata: TorrentMetadata = response.json().await?;
    
    let mut results = Vec::new();
    let mut count = 0;
    
    for torrent in &metadata.torrents {
        for file in &torrent.files {
            if let Some(file_md5) = &file.md5 {
                if file_md5.to_lowercase() == md5.to_lowercase() {
                    results.push(file.clone());
                    count += 1;
                    if count >= limit {
                        break;
                    }
                }
            }
        }
        if count >= limit {
            break;
        }
    }
    
    info!("Found {} files matching MD5: {}", results.len(), md5);
    
    if results.is_empty() {
        warn!("No files found with MD5: {}", md5);
    }
    
    Ok(results)
}

/// Get information about a specific torrent
pub async fn get_torrent_info(info_hash: &str) -> Result<AnnaTorrent> {
    let client = Client::new();
    
    // Try to get torrent info from the API
    let url = format!("{}/{}", ANNAS_ARCHIVE_API.replace("/dyn/torrents.json", "/dyn/torrent"), info_hash);
    
    let response = client
        .get(&url)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await?;
    
    if response.status().is_success() {
        let torrent: AnnaTorrent = response.json().await?;
        info!("Found torrent: {} ({} files)", torrent.name, torrent.files.len());
        Ok(torrent)
    } else {
        // Try searching by info hash in the main metadata
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
}

/// Download a .torrent file from Anna's Archive
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

/// List available torrents from Anna's Archive
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