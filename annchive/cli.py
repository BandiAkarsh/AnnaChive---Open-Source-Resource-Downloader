"""Main CLI entry point for annchive."""
import asyncio
import os
import sys
from pathlib import Path

import click

from .config import get_config, get_encryption_key
from .storage.database import get_database, LibraryItem
from .sources.arxiv import ArxivSource
from .utils.logger import setup_logging, get_logger
from .constants import DEFAULT_LIST_LIMIT, TITLE_TRUNCATE_LENGTH, DEFAULT_SEARCH_LIMIT, MD5_LENGTH
from .sources.annas_archive import AnnaSource
from .storage.downloader import DownloadManager

logger = get_logger("cli")


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def main(ctx, debug):
    """AnnaChive - Local CLI for open-access resources with Tor anonymity."""
    setup_logging(enable_handler=debug)
    ctx.ensure_object(dict)
    ctx.obj["config"] = get_config()
    ctx.obj["debug"] = debug


# ============== CONFIG COMMANDS ==============

@main.group()
def config():
    """Manage configuration settings."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    cfg = get_config()
    click.echo("Current Configuration:")
    for key, value in cfg.to_dict().items():
        click.echo(f"  {key}: {value}")
    
    click.echo("\nNote: encryption_key must be set via ANNCHIVE_ENCRYPTION_KEY environment variable")
    click.echo("Available config keys: library_path, db_path, encryption_enabled, tor_enabled,")
    click.echo("  tor_port, tor_control_port, tor_auto_fallback, max_retries, timeout,")
    click.echo("  chunk_size, default_sources, cache_enabled, cache_ttl")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value (KEY VALUE)."""
    # Encryption key must be set via environment variable - not stored in config
    if key in ("encryption-key", "encryption_key", "encryptionkey"):
        click.echo("Encryption key cannot be stored in config file.")
        click.echo("\nFor security, set it via environment variable:")
        click.echo("  export ANNCHIVE_ENCRYPTION_KEY='your-password'")
        click.echo("\nTo make it permanent:")
        click.echo("  echo \"export ANNCHIVE_ENCRYPTION_KEY='your-password'\" >> ~/.bashrc")
        click.echo("  source ~/.bashrc")
        return
    
    cfg = get_config()
    if hasattr(cfg, key):
        current = getattr(cfg, key)
        # Convert value to correct type based on current setting type
        if isinstance(current, bool):
            value = value.lower() in ("true", "1", "yes")
        elif isinstance(current, int):
            value = int(value)
        elif isinstance(current, Path):
            value = Path(value)
        setattr(cfg, key, value)
        click.echo(f"Set {key} = {value}")
    else:
        click.echo(f"Unknown config key: {key}", err=True)


# ============== INIT COMMAND ==============

@main.command()
@click.option("--library-path", type=click.Path(), help="Where to store downloads")
@click.option("--password", help="Set master password for encryption")
@click.option("--no-encrypt", is_flag=True, help="Disable database encryption")
def init(library_path, password, no_encrypt):
    """Initialize annchive with configuration.
    
    Example:
        annchive init --password mysecretpassword
    """
    from .config import Config
    
    cfg = Config.from_env()
    
    if library_path:
        cfg.library_path = Path(library_path)
        cfg.db_path = cfg.library_path / "annchive.db"
    
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"Initialized at: {cfg.library_path}")
    click.echo(f"Encryption: {'enabled' if not no_encrypt else 'disabled'}")
    
    if not no_encrypt:
        from .config import get_master_password_hash, set_master_password, get_encryption_key
        
        existing_hash = get_master_password_hash()
        
        if existing_hash:
            click.echo("\n✓ Already configured!")
            click.echo("Your library is ready to use!")
        elif password:
            # User provided password
            success = set_master_password(password)
            if success:
                click.echo("\n✓ Password saved securely!")
                click.echo("\nYour library is encrypted and ready to use!")
            else:
                click.echo("\n⚠️  Could not save to keyring.")
                click.echo("Set via environment variable:")
                click.echo(f"  export ANNCHIVE_ENCRYPTION_KEY='{password}'")
        else:
            # No password set
            click.echo("\n" + "="*50)
            click.echo("🔐 SET UP YOUR MASTER PASSWORD")
            click.echo("="*50)
            click.echo("\nThis password encrypts your library.")
            click.echo("If you forget it, you CANNOT recover your data.\n")
            click.echo("Set your password with:")
            click.echo("  annchive init --password 'your-password'")
            click.echo("\nOr set via environment variable:")
            click.echo("  export ANNCHIVE_ENCRYPTION_KEY='your-password'")
            click.echo("\n" + "="*50)
        
        click.echo("\nStart using:")
        click.echo("  annchive library list")
        click.echo("  annchive search arxiv \"quantum\"")


# ============== SEARCH COMMANDS ==============

@main.group()
def search():
    """Search for resources across sources."""
    pass


@search.command("annas-archive")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
def search_annas(query, limit):
    """Search Anna's Archive (books, papers)."""
    asyncio.run(_search_annas(query, limit))


async def _search_annas(query, limit):
    """Internal async implementation for searching Anna's Archive."""
    source = AnnaSource()
    results = await source.search(query, limit)
    
    if not results:
        click.echo("No results found.")
        return
    
    click.echo(f"Found {len(results)} results:")
    for r in results:
        size = f"{r.size or '?'}"
        title = r.title[:60] if r.title else 'Untitled'
        click.echo(f"  {title}")
        click.echo(f"    Author: {r.author or 'Unknown'}")
        click.echo(f"    Format: {r.format or '?'} | Size: {size}")
        if r.md5:
            click.echo(f"    MD5: {r.md5}")
        click.echo()


@search.command("arxiv")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
def search_arxiv(query, limit):
    """Search arXiv for research papers."""
    asyncio.run(_search_arxiv(query, limit))


async def _search_arxiv(query, limit):
    """Internal async implementation for searching arXiv."""
    from .sources.arxiv import ArxivSource
    
    source = ArxivSource()
    results = await source.search(query, limit)
    
    if not results:
        click.echo("No results found.")
        return
    
    click.echo(f"Found {len(results)} results:")
    for r in results:
        click.echo(f"  {r.title[:60] if r.title else 'Untitled'}")
        click.echo(f"    Authors: {r.author or 'Unknown'}")
        click.echo(f"    arXiv: {r.id or '?'}")
        click.echo(f"    Published: {r.published or '?'}")
        click.echo()


@search.command("github")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
def search_github(query, limit):
    """Search GitHub repositories."""
    asyncio.run(_search_github(query, limit))


async def _search_github(query, limit):
    """Internal async implementation for searching GitHub."""
    from .sources.github import GitHubSource
    
    source = GitHubSource()
    results = await source.search(query, limit)
    
    if not results:
        click.echo("No results found.")
        return
    
    click.echo(f"Found {len(results)} results:")
    for r in results:
        click.echo(f"  {r.title or 'Untitled'}")
        desc = r.description[:60] if r.description else 'N/A'
        click.echo(f"    Description: {desc}")
        stars = r.metadata.get('stars', '?') if r.metadata else '?'
        lang = r.metadata.get('language', '?') if r.metadata else '?'
        click.echo(f"    Stars: {stars} | Lang: {lang}")
        click.echo()


@search.command("semantic-scholar")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
def search_semantic_scholar(query, limit):
    """Search Semantic Scholar for academic papers."""
    asyncio.run(_search_semantic_scholar(query, limit))


async def _search_semantic_scholar(query, limit):
    """Internal async implementation for searching Semantic Scholar."""
    from .sources.semantic_scholar import SemanticScholarSource
    
    source = SemanticScholarSource()
    results = await source.search(query, limit)
    
    if not results:
        click.echo("No results found.")
        return
    
    click.echo(f"Found {len(results)} results:")
    for r in results:
        click.echo(f"  {r.title[:60]}")
        click.echo(f"    Author: {r.author or 'Unknown'}")
        click.echo(f"    Year: {r.published or '?'} | Citations: {r.metadata.get('citations', '?')}")
        if r.doi:
            click.echo(f"    DOI: {r.doi}")
        click.echo()


@search.command("pubmed")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
def search_pubmed(query, limit):
    """Search PubMed for medical/biological papers."""
    asyncio.run(_search_pubmed(query, limit))


async def _search_pubmed(query, limit):
    """Internal async implementation for searching PubMed."""
    from .sources.pubmed import PubMedSource
    
    source = PubMedSource()
    results = await source.search(query, limit)
    
    if not results:
        click.echo("No results found.")
        return
    
    click.echo(f"Found {len(results)} results:")
    for r in results:
        click.echo(f"  {r.title[:60]}")
        click.echo(f"    Author: {r.author or 'Unknown'}")
        click.echo(f"    Journal: {r.metadata.get('journal', '?') if r.metadata else '?'}")
        if r.metadata and r.metadata.get('pmid'):
            click.echo(f"    PMID: {r.metadata['pmid']}")
        click.echo()


# ============== GET/DOWNLOAD COMMANDS ==============

@main.group()
def get():
    """Download resources from sources."""
    pass


@get.command("arxiv")
@click.argument("arxiv_id")
@click.option("--to", "output_dir", type=click.Path(), help="Output directory")
def get_arxiv(arxiv_id, output_dir):
    """Download paper from arXiv by ID (e.g., 1706.03762)."""
    asyncio.run(_get_arxiv(arxiv_id, output_dir))


async def _get_arxiv(arxiv_id, output_dir):
    """Download from arXiv."""
    cfg = get_config()
    output_dir = Path(output_dir) if output_dir else cfg.library_path
    
    # Get encryption key from environment
    encryption_key = None
    key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
    if key_str:
        encryption_key = get_encryption_key(key_str)
    
    async with get_database(cfg.db_path, encryption_key) as db:
        source = ArxivSource()
        results = await source.search(f"id:{arxiv_id}", 1)
        
        if not results:
            click.echo(f"Paper {arxiv_id} not found.")
            return
        
        item = results[0]
        click.echo(f"Downloading: {item.title}")
        
        downloader = DownloadManager()
        success = await downloader.download(item.url, output_dir, item.title)
        
        if success:
            # Add to library
            lib_item = LibraryItem(
                source="arxiv",
                md5=item.md5,
                title=item.title,
                author=item.author,
                format="pdf",
                path=str(output_dir / f"{arxiv_id}.pdf"),
                url=item.url
            )
            await db.add_item(lib_item)
            click.echo(f"Saved to: {output_dir}")
        else:
            click.echo("Download failed.")


@get.command("github")
@click.argument("repo")
@click.option("--to", "output_dir", type=click.Path(), help="Output directory")
def get_github(repo, output_dir):
    """Download (clone) GitHub repository."""
    asyncio.run(_get_github(repo, output_dir))


async def _get_github(repo, output_dir):
    """Download from GitHub - clones the repository."""
    cfg = get_config()
    output_dir = Path(output_dir) if output_dir else cfg.library_path
    
    encryption_key = None
    key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
    if key_str:
        encryption_key = get_encryption_key(key_str)
    
    async with get_database(cfg.db_path, encryption_key) as db:
        source = GitHubSource()
        results = await source.search(repo, 1)
        
        if not results:
            click.echo(f"Repository {repo} not found.")
            return
        
        item = results[0]
        click.echo(f"Cloning: {item.title}")
        
        downloader = DownloadManager()
        success = await downloader.clone_github(item.url, output_dir)
        
        if success:
            lib_item = LibraryItem(
                source="github",
                md5=item.md5,
                title=item.title,
                author=item.author,
                format="repository",
                path=str(output_dir / item.id.split('/')[-1]),
                url=item.url
            )
            await db.add_item(lib_item)
            click.echo(f"Cloned to: {output_dir / item.id.split('/')[-1]}")
        else:
            click.echo("Clone failed.")


# ============== LIBRARY COMMANDS ==============

@main.group()
def library():
    """Manage local library."""
    pass


@library.command("list")
@click.option("--limit", default=DEFAULT_LIST_LIMIT, help="Max items to show")
@click.option("--source", help="Filter by source")
@click.option("--project", help="Filter by project")
def library_list(limit, source, project):
    """List all items in your library."""
    asyncio.run(_library_list(limit, source, project))


async def _library_list(limit, source, project):
    """Display library items."""
    cfg = get_config()
    
    encryption_key = None
    key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
    if key_str and cfg.encryption_enabled:
        encryption_key = get_encryption_key(key_str)
    
    async with get_database(cfg.db_path, encryption_key) as db:
        # Get items based on filters
        if source:
            items = await db.list_by_source(source, limit)
        elif project:
            items = await db.list_by_project(project)
        else:
            items = await db.list_all(limit=limit)
        
        if not items:
            click.echo("No items in library.")
            return
        
        click.echo(f"Your Library ({len(items)} items):")
        click.echo("-" * 60)
        for item in items:
            size = f"{item.size_bytes / 1024 / 1024:.1f}MB" if item.size_bytes else "?"
            click.echo(f"  {item.title[:50]}")
            click.echo(f"    Source: {item.source} | Format: {item.format or '?'} | Size: {size}")
            if item.path:
                click.echo(f"    Path: {item.path}")
            click.echo()


@library.command("search")
@click.argument("query")
def library_search(query):
    """Search within your library."""
    asyncio.run(_library_search(query))


async def _library_search(query):
    """Search library by title/author."""
    cfg = get_config()
    
    encryption_key = None
    key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
    if key_str and cfg.encryption_enabled:
        encryption_key = get_encryption_key(key_str)
    
    async with get_database(cfg.db_path, encryption_key) as db:
        items = await db.search(query)
        
        if not items:
            click.echo("No matching items found.")
            return
        
        click.echo(f"Found {len(items)} matches:")
        for item in items:
            click.echo(f"  {item.title}")
            click.echo(f"    Source: {item.source} | Path: {item.path}")


@library.command("stats")
def library_stats():
    """Show library statistics."""
    asyncio.run(_library_stats())


async def _library_stats():
    """Display library statistics."""
    cfg = get_config()
    
    encryption_key = None
    key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
    if key_str and cfg.encryption_enabled:
        encryption_key = get_encryption_key(key_str)
    
    async with get_database(cfg.db_path, encryption_key) as db:
        stats = await db.get_stats()
        
        click.echo("Library Statistics:")
        click.echo(f"  Total items: {stats.get('total', 0)}")
        click.echo(f"  Total size: {stats.get('total_size_mb', 0)} MB")
        
        by_source = stats.get('by_source', {})
        if by_source:
            click.echo("  By source:")
            for src, count in by_source.items():
                click.echo(f"    {src}: {count}")


# ============== TOR COMMANDS ==============

@main.group()
def tor():
    """Manage Tor connection."""
    pass


@tor.command("status")
def tor_status():
    """Check Tor connection status."""
    from .tor.proxy import get_tor_client
    
    try:
        client = get_tor_client()
        click.echo("Tor status: Connected")
        click.echo(f"IP: {client.ip()}")
    except Exception as e:
        click.echo(f"Tor status: Not connected ({e})")


@tor.command("enable")
def tor_enable():
    """Enable Tor routing."""
    cfg = get_config()
    cfg.tor_enabled = True
    click.echo("Tor enabled. Use 'annchive tor status' to verify.")


@tor.command("disable")
def tor_disable():
    """Disable Tor routing."""
    cfg = get_config()
    cfg.tor_enabled = False
    click.echo("Tor disabled.")


@tor.command("new-identity")
def tor_new_identity():
    """Request new Tor identity (new IP)."""
    from .tor.proxy import get_tor_client
    
    try:
        client = get_tor_client()
        client.new_identity()
        click.echo("New Tor identity requested.")
    except Exception as e:
        click.echo(f"Failed: {e}")


# Entry point
if __name__ == "__main__":
    main()
