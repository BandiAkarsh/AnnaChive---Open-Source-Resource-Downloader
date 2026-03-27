//! AnnaChive Torrent Downloader - High-performance BitTorrent client
//! 
//! Downloads files from Anna's Archive torrents without requiring donation.
//! Uses metadata API to find files, then downloads via BitTorrent protocol.

use std::path::PathBuf;
use anyhow::Result;
use clap::{Parser, Subcommand};
use log::{info, error};

mod anna;
mod download;

#[derive(Parser)]
#[command(name = "annchive-torrent")]
#[command(about = "High-performance torrent downloader for AnnaChive", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Search Anna's Archive torrent metadata for a file
    Search {
        /// MD5 hash to search for
        md5: String,
        
        /// Limit results
        #[arg(short, long, default_value = "10")]
        limit: usize,
    },
    
    /// Download a file from Anna's Archive by MD5
    Download {
        /// MD5 hash of the file
        md5: String,
        
        /// Output directory
        #[arg(short, long)]
        output: PathBuf,
        
        /// Optional filename
        #[arg(short, long)]
        filename: Option<String>,
        
        /// Use Tor proxy (for restricted sources)
        #[arg(long)]
        tor: bool,
    },
    
    /// Get torrent info by info hash
    Info {
        /// Info hash to look up
        info_hash: String,
    },
    
    /// List available torrents from Anna's Archive
    List {
        /// Filter by collection (zlib, libgen, scihub)
        #[arg(short, long)]
        collection: Option<String>,
        
        /// Limit results
        #[arg(short, long, default_value = "20")]
        limit: usize,
    },
    
    /// Generate a magnet link from info hash
    Magnet {
        /// Info hash
        info_hash: String,
        
        /// Torrent name
        name: String,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logger (minimal for security)
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info"))
        .init();
    
    let cli = Cli::parse();
    
    match cli.command {
        Commands::Search { md5, limit } => {
            info!("Searching for MD5: {}", md5);
            match anna::search_metadata(&md5, limit).await {
                Ok(files) => {
                    if files.is_empty() {
                        println!("No files found with MD5: {}", md5);
                    } else {
                        for f in &files {
                            println!("  - {} ({} bytes)", f.name, f.size);
                        }
                    }
                }
                Err(e) => error!("Search failed: {}", e),
            }
        },
        
        Commands::Download { md5, output, filename, tor } => {
            info!("Downloading MD5: {} to {:?}", md5, output);
            match download::download_file(&md5, &output, filename.as_deref(), tor).await {
                Ok(path) => println!("Downloaded to: {:?}", path),
                Err(e) => error!("Download failed: {}", e),
            }
        },
        
        Commands::Info { info_hash } => {
            info!("Getting info for: {}", info_hash);
            match anna::get_torrent_info(&info_hash).await {
                Ok(t) => {
                    println!("Torrent: {}", t.name);
                    println!("  Files: {}", t.files.len());
                    println!("  Size: {}", format_size(t.size));
                }
                Err(e) => error!("Failed: {}", e),
            }
        },
        
        Commands::List { collection, limit } => {
            info!("Listing torrents");
            match anna::list_torrents(collection.as_deref(), limit).await {
                Ok(torrents) => {
                    for t in &torrents {
                        println!("  - {} ({} files, {})", 
                            t.name, 
                            t.files.len(),
                            format_size(t.size)
                        );
                    }
                }
                Err(e) => error!("Failed: {}", e),
            }
        },
        
        Commands::Magnet { info_hash, name } => {
            let magnet = download::generate_magnet(&info_hash, &name);
            println!("{}", magnet);
        },
    }
    
    Ok(())
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