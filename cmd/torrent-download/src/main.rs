/*
 * AnnaChive Torrent Downloader - Rust CLI
 * 
 * This is a high-performance tool for downloading files from Anna's Archive
 * using BitTorrent protocol. It's written in Rust because Rust is fast and
 * handles low-level operations well.
 * 
 * What can this do:
 * - Search Anna's Archive for files by their MD5 hash
 * - Download files using BitTorrent (no donation needed!)
 * - Get information about torrents
 * - List all available torrents
 * - Generate magnet links (for sharing torrents)
 * 
 * Why Rust?
 * - Faster than Python for heavy downloads
 * - Memory safe (no buffer overflows)
 * - Good libraries for networking
 */

use std::path::PathBuf;  // For handling file paths
use anyhow::Result;  // For error handling
use clap::{Parser, Subcommand};  // For CLI arguments
use log::{info, error};  // For logging messages

mod anna;  // Anna's Archive API functions
mod download;  // Download logic

/*
 * This is the main command-line interface definition.
 * It uses "derive" macros - a way to automatically generate code.
 * 
 * Think of it like a form where you fill in what you want to do.
 */
#[derive(Parser)]
#[command(name = "annchive-torrent")]
#[command(about = "High-performance torrent downloader for AnnaChive", long_about = None)]
struct Cli {
    // The "command" field holds which subcommand the user wants
    // Like "search" or "download" or "list"
    #[command(subcommand)]
    command: Commands,
}

/*
 * Here's where we define all the possible commands.
 * Each variant is a different thing the user can ask for.
 * 
 * Examples of use:
 *   annchive-torrent search abc123def456
 *   annchive-torrent download abc123def456 --output ./Downloads/
 *   annchive-torrent list --collection zlib
 */
#[derive(Subcommand)]
enum Commands {
    /// Search Anna's Archive torrent metadata for a file
    Search {
        /// MD5 hash to search for
        /// 
        /// An MD5 is like a fingerprint for files - every file has a unique one.
        /// You can find MD5 hashes in Anna's Archive search results.
        md5: String,
        
        /// Limit results
        /// How many results to show at most (default: 10)
        #[arg(short, long, default_value = "10")]
        limit: usize,
    },
    
    /// Download a file from Anna's Archive by MD5
    Download {
        /// MD5 hash of the file you want
        md5: String,
        
        /// Output directory - where to save the file
        /// Default is current directory
        #[arg(short, long)]
        output: PathBuf,
        
        /// Optional custom filename
        /// If you don't specify, it uses the original filename
        #[arg(short, long)]
        filename: Option<String>,
        
        /// Use Tor proxy for this download
        /// Turn this on if you're downloading something blocked in your country
        #[arg(long)]
        tor: bool,
    },
    
    /// Get information about a specific torrent
    Info {
        /// The unique ID (info hash) of the torrent
        /// This is a special code that identifies the torrent
        info_hash: String,
    },
    
    /// List available torrents from Anna's Archive
    List {
        /// Filter by collection name
        /// Examples: zlib (Z-Library), libgen (Library Genesis), scihub
        #[arg(short, long)]
        collection: Option<String>,
        
        /// How many torrents to show (default: 20)
        #[arg(short, long, default_value = "20")]
        limit: usize,
    },
    
    /// Generate a magnet link from info hash
    /// 
    /// A magnet link is a special URL that BitTorrent clients can use
    /// to start downloading without needing a .torrent file.
    /// It's shorter and easier to share than torrent files.
    Magnet {
        /// The torrent's info hash (its unique ID)
        info_hash: String,
        
        /// The name of the torrent (for display)
        name: String,
    },
}

/*
 * This is the main function - where the program starts.
 * 
 * It's marked "async" because we want it to wait for network calls
 * without freezing the computer.
 * 
 * What happens here:
 * 1. Parse command-line arguments
 * 2. Set up logging
 * 3. Execute the requested command
 * 4. Handle any errors gracefully
 */
#[tokio::main]  // This macro lets us use async/await
async fn main() -> Result<()> {
    // Initialize logger (minimal for security - no logging!)
    // We use env_logger which reads RUST_LOG environment variable
    // But by default, we keep it quiet for privacy
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info"))
        .init();
    
    // Parse the command-line arguments
    let cli = Cli::parse();
    
    // Figure out what the user wants to do
    match cli.command {
        // SEARCH: Find a file by its MD5 hash
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
        
        // DOWNLOAD: Get a file from Anna's Archive
        Commands::Download { md5, output, filename, tor } => {
            info!("Downloading MD5: {} to {:?}", md5, output);
            match download::download_file(&md5, &output, filename.as_deref(), tor).await {
                Ok(path) => println!("Downloaded to: {:?}", path),
                Err(e) => error!("Download failed: {}", e),
            }
        },
        
        // INFO: Get details about a specific torrent
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
        
        // LIST: Show all available torrents
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
        
        // MAGNET: Create a shareable magnet link
        Commands::Magnet { info_hash, name } => {
            let magnet = download::generate_magnet(&info_hash, &name);
            println!("{}", magnet);
        },
    }
    
    Ok(())
}

/*
 * Helper function to make file sizes readable
 * 
 * Instead of showing "1234567890 bytes", shows "1.23 GB"
 * 
 * How it works:
 * - Check if size is >= GB, MB, or KB
 * - Convert and format with 2 decimal places
 * - Add the unit name
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
