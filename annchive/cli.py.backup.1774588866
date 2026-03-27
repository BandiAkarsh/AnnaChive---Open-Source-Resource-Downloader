"""Main CLI entry point for annchive."""
import asyncio
import sys
from pathlib import Path

import click

from .config import get_config
from .storage.database import get_database, key_from_master
from .utils.logger import setup_logging, get_logger

logger = get_logger("cli")


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def main(ctx, debug):
    """AnnaChive - Local CLI for open-access resources with Tor anonymity."""
    # Setup logging (no-op by default for security)
    setup_logging(enable_handler=debug)
    
    # Store config in context
    ctx.ensure_object(dict)
    ctx.obj["config"] = get_config()
    ctx.obj["debug"] = debug


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


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    cfg = get_config()
    if hasattr(cfg, key):
        # Try to convert type
        current = getattr(cfg, key)
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


@main.group()
def library():
    """Manage local library."""
    pass


@library.command("list")
@click.option("--limit", default=20, help="Number of items to show")
@click.option("--offset", default=0, help="Offset for pagination")
@click.option("--source", help="Filter by source")
@click.option("--project", help="Filter by project")
@click.option("--search", help="Search in title/author")
async def library_list(limit, offset, source, project, search):
    """List items in the library."""
    cfg = get_config()
    
    # Get encryption key from keyring or environment
    encryption_key = None
    if cfg.encryption_enabled:
        import os
        key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
        if key_str:
            encryption_key = key_from_master(key_str).encode()
    
    async with get_database(cfg.db_path, encryption_key) as db:
        if search:
            items = await db.search(search, limit)
        elif source:
            items = await db.list_by_source(source, limit)
        elif project:
            items = await db.list_by_project(project)
        else:
            items = await db.list_all(limit, offset)
        
        if not items:
            click.echo("No items in library.")
            return
        
        click.echo(f"Library ({await db.count()} items):")
        for item in items:
            size = f"{item.size_bytes / 1024 / 1024:.1f}MB" if item.size_bytes else "?"
            click.echo(
                f"  [{item.source}] {item.title[:50]}"
                f" ({item.format or '?'}, {size})"
            )


@library.command("add")
@click.option("--source", required=True, help="Source name")
@click.option("--title", required=True, help="Title")
@click.option("--author", help="Author")
@click.option("--md5", help="MD5 hash")
@click.option("--format", help="File format (pdf, epub, etc)")
@click.option("--size", type=int, help="Size in bytes")
@click.option("--path", help="Local file path")
@click.option("--doi", help="DOI")
@click.option("--url", help="Source URL")
@click.option("--project", help="Project name")
@click.option("--tags", help="Comma-separated tags")
async def library_add(source, title, author, md5, format, size, path, doi, url, project, tags):
    """Add an item to the library."""
    from .storage.database import LibraryItem
    
    cfg = get_config()
    
    # Get encryption key
    encryption_key = None
    if cfg.encryption_enabled:
        import os
        key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
        if key_str:
            encryption_key = key_from_master(key_str).encode()
    
    item = LibraryItem(
        source=source,
        title=title,
        author=author,
        md5=md5,
        format=format,
        size_bytes=size,
        path=path,
        doi=doi,
        url=url,
        project=project,
        tags=tags or "",
    )
    
    async with get_database(cfg.db_path, encryption_key) as db:
        item_id = await db.add_item(item)
        click.echo(f"Added item with ID: {item_id}")


@library.command("search")
@click.argument("query")
@click.option("--limit", default=20, help="Max results")
async def library_search(query, limit):
    """Search library for items."""
    cfg = get_config()
    
    encryption_key = None
    if cfg.encryption_enabled:
        import os
        key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
        if key_str:
            encryption_key = key_from_master(key_str).encode()
    
    async with get_database(cfg.db_path, encryption_key) as db:
        items = await db.search(query, limit)
        
        if not items:
            click.echo(f"No results for: {query}")
            return
        
        click.echo(f"Found {len(items)} results:")
        for item in items:
            click.echo(f"  [{item.source}] {item.title}")


@library.command("stats")
async def library_stats():
    """Show library statistics."""
    cfg = get_config()
    
    encryption_key = None
    if cfg.encryption_enabled:
        import os
        key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
        if key_str:
            encryption_key = key_from_master(key_str).encode()
    
    async with get_database(cfg.db_path, encryption_key) as db:
        total = await db.count()
        click.echo(f"Total items: {total}")
        
        # Stats by source
        sources = ["annas-archive", "arxiv", "github", "internet-archive", "scihub"]
        for src in sources:
            count = await db.count_by_source(src)
            if count:
                click.echo(f"  {src}: {count}")


@main.group()
def search():
    """Search for resources across sources."""
    pass


@search.command("annas-archive")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
async def search_annas(query, limit):
    """Search Anna's Archive."""
    from .sources.annas_archive import AnnaSource
    
    source = AnnaSource()
    results = await source.search(query, limit)
    
    if not results:
        click.echo("No results found.")
        return
    
    click.echo(f"Found {len(results)} results:")
    for r in results:
        size = f"{r.get('size', '?')}"
        click.echo(f"  {r.get('title', 'Untitled')[:60]}")
        click.echo(f"    Author: {r.get('author', 'Unknown')}")
        click.echo(f"    Format: {r.get('format', '?')} | Size: {size}")
        if r.get("md5"):
            click.echo(f"    MD5: {r['md5']}")
        click.echo()


@search.command("arxiv")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
async def search_arxiv(query, limit):
    """Search arXiv."""
    from .sources.arxiv import ArxivSource
    
    source = ArxivSource()
    results = await source.search(query, limit)
    
    if not results:
        click.echo("No results found.")
        return
    
    click.echo(f"Found {len(results)} results:")
    for r in results:
        click.echo(f"  {r.get('title', 'Untitled')[:60]}")
        click.echo(f"    Authors: {r.get('authors', 'Unknown')}")
        click.echo(f"    arXiv: {r.get('id', '?')}")
        click.echo(f"    Published: {r.get('published', '?')}")
        click.echo()


@search.command("github")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
async def search_github(query, limit):
    """Search GitHub."""
    from .sources.github import GitHubSource
    
    source = GitHubSource()
    results = await source.search(query, limit)
    
    if not results:
        click.echo("No results found.")
        return
    
    click.echo(f"Found {len(results)} results:")
    for r in results:
        click.echo(f"  {r.get('name', 'Untitled')}")
        click.echo(f"    Description: {r.get('description', 'N/A')[:60]}")
        click.echo(f"    Stars: {r.get('stars', '?')} | Lang: {r.get('language', '?')}")
        click.echo()


@search.command("semantic-scholar")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
async def search_semantic_scholar(query, limit):
    """Search Semantic Scholar for academic papers."""
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
async def search_pubmed(query, limit):
    """Search PubMed for biomedical literature."""
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
        click.echo(f"    Journal: {r.description or '?'}")
        click.echo(f"    PMID: {r.id}")
        if r.doi:
            click.echo(f"    DOI: {r.doi}")
        click.echo()


@main.group()
def get():
    """Download resources."""
    pass


@get.command("annas-archive")
@click.argument("md5")
@click.option("--to", "output_dir", default=".", help="Output directory")
@click.option("--format", help="Preferred format")
async def get_annas(md5, output_dir, format):
    """Download from Anna's Archive by MD5."""
    from .sources.annas_archive import AnnaSource
    from .storage.downloader import DownloadManager
    
    cfg = get_config()
    source = AnnaSource()
    dm = DownloadManager(cfg)
    
    click.echo(f"Searching for MD5: {md5}...")
    
    # First search to find the item
    results = await source.search(f"md5:{md5}", 1)
    if not results:
        click.echo("Item not found.", err=True)
        return
    
    item = results[0]
    click.echo(f"Found: {item.get('title', 'Unknown')}")
    
    # Try download with fallback
    success = await dm.download_with_fallback(source, item, Path(output_dir))
    
    if success:
        click.echo("Download complete!")
    else:
        click.echo("Download failed. Try enabling Tor for alternative sources.", err=True)


@get.command("arxiv")
@click.argument("arxiv_id")
@click.option("--to", "output_dir", default=".", help="Output directory")
async def get_arxiv(arxiv_id, output_dir):
    """Download from arXiv by ID."""
    from .sources.arxiv import ArxivSource
    
    cfg = get_config()
    source = ArxivSource()
    
    click.echo(f"Downloading arXiv paper: {arxiv_id}...")
    
    result = await source.download(arxiv_id, Path(output_dir))
    
    if result:
        click.echo(f"Downloaded to: {result}")
    else:
        click.echo("Download failed.", err=True)


@main.group()
def tor():
    """Manage Tor connection."""
    pass


@tor.command("status")
async def tor_status():
    """Check Tor status."""
    from .tor.manager import TorManager
    
    tm = TorManager()
    status = await tm.get_status()
    
    click.echo(f"Tor enabled: {status.get('enabled', False)}")
    click.echo(f"Connected: {status.get('connected', False)}")
    click.echo(f"IP: {status.get('ip', 'Unknown')}")


@tor.command("enable")
async def tor_enable():
    """Enable Tor routing."""
    from .tor.manager import TorManager
    
    tm = TorManager()
    await tm.enable()
    click.echo("Tor enabled.")


@tor.command("disable")
async def tor_disable():
    """Disable Tor routing."""
    from .tor.manager import TorManager
    
    tm = TorManager()
    await tm.disable()
    click.echo("Tor disabled.")


@tor.command("new-identity")
async def tor_new_identity():
    """Get new Tor circuit (new IP)."""
    from .tor.manager import TorManager
    
    tm = TorManager()
    await tm.new_identity()
    click.echo("New Tor identity obtained.")


@main.command("init")
@click.option("--library-path", help="Path for library storage")
@click.option("--encrypt/--no-encrypt", default=True, help="Enable encryption")
async def init(library_path, encrypt):
    """Initialize annchive with configuration."""
    cfg = get_config()
    
    if library_path:
        cfg.library_path = Path(library_path)
    
    cfg.encryption_enabled = encrypt
    
    # Create directories
    cfg.library_path.mkdir(parents=True, exist_ok=True)
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"Initialized at: {cfg.library_path}")
    click.echo(f"Encryption: {'enabled' if encrypt else 'disabled'}")
    
    if encrypt:
        click.echo("\nIMPORTANT: Set encryption key:")
        click.echo("  export ANNCHIVE_ENCRYPTION_KEY='your-master-key'")
        click.echo("Or run: annchive config set encryption-key")


if __name__ == "__main__":
    main()