"""Main CLI entry point for annchive."""
# We need help from outside - bringing in tools
import asyncio
# We need help from outside - bringing in tools
import sys
# We're bringing in tools from another file
from pathlib import Path

# We need help from outside - bringing in tools
import click

# We're bringing in tools from another file
from .config import get_config
# We're bringing in tools from another file
from .storage.database import get_database, key_from_master
# We're bringing in tools from another file
from .utils.logger import setup_logging, get_logger
# Shared constants - avoid magic numbers
from .constants import DEFAULT_LIST_LIMIT, TITLE_TRUNCATE_LENGTH, DEFAULT_SEARCH_LIMIT, MD5_LENGTH
# We're bringing in tools from another file
from .sources.annas_archive import AnnaSource
# We're bringing in tools from another file
from .storage.downloader import DownloadManager

# Remember this: we're calling 'logger' something
logger = get_logger("cli")


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
# Here's a recipe (function) - it does a specific job
def main(ctx, debug):
    """AnnaChive - Local CLI for open-access resources with Tor anonymity."""
    # Setup logging (no-op by default for security)
    setup_logging(enable_handler=debug)
    
    # Store config in context
    ctx.ensure_object(dict)
    ctx.obj["config"] = get_config()
    ctx.obj["debug"] = debug


@main.group()
# Here's a recipe (function) - it does a specific job
def config():
    """Manage configuration settings."""
    pass


@config.command("show")
# Here's a recipe (function) - it does a specific job
def config_show():
    """Show current configuration."""
    # Remember this: we're calling 'cfg' something
    cfg = get_config()
    click.echo("Current Configuration:")
    # We're doing something over and over, like a repeat button
    for key, value in cfg.to_dict().items():
        click.echo(f"  {key}: {value}")


@config.command("set")
@click.argument("key")
@click.argument("value")
# Here's a recipe (function) - it does a specific job
def config_set(key, value):
    """Set a configuration value."""
    # Remember this: we're calling 'cfg' something
    cfg = get_config()
    # Checking if something is true - like asking a yes/no question
    if hasattr(cfg, key):
        # Try to convert type
        # Remember this: we're calling 'current' something
        current = getattr(cfg, key)
        # Checking if something is true - like asking a yes/no question
        if isinstance(current, bool):
            # Remember this: we're calling 'value' something
            value = value.lower() in ("true", "1", "yes")
        # If the first answer was no, try this instead
        elif isinstance(current, int):
            # Remember this: we're calling 'value' something
            value = int(value)
        # If the first answer was no, try this instead
        elif isinstance(current, Path):
            # Remember this: we're calling 'value' something
            value = Path(value)
        setattr(cfg, key, value)
        click.echo(f"Set {key} = {value}")
    # If nothing else worked, we do this
    else:
        click.echo(f"Unknown config key: {key}", err=True)


@main.group()
# Here's a recipe (function) - it does a specific job
def library():
    """Manage local library."""
    pass


@library.command("list")
@click.option("--limit", default=DEFAULT_LIST_LIMIT, help="Number of items to show")
@click.option("--offset", default=0, help="Offset for pagination")
@click.option("--source", help="Filter by source")
@click.option("--project", help="Filter by project")
@click.option("--search", help="Search in title/author")
def library_list(limit, offset, source, project, search):
    """List items in the library."""
    asyncio.run(_library_list(limit, offset, source, project, search))


async def _library_list(limit, offset, source, project, search):
    """Internal async implementation for library list."""
    cfg = get_config()
    
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
            truncated_title = item.title[:TITLE_TRUNCATE_LENGTH]
            click.echo(
                f"  [{item.source}] {truncated_title}"
                f" ({item.format or '?'}, {size})"
            )


def validate_md5(ctx, param, value):
    """Validate MD5 hash is 32 hex characters."""
    if value is None:
        return value
    import re
    md5_pattern = f"[a-fA-F0-9]{{{MD5_LENGTH}}}"
    if not re.fullmatch(md5_pattern, value):
        raise click.BadParameter(f"MD5 must be exactly {MD5_LENGTH} hexadecimal characters")
    return value


@library.command("add")
@click.option("--source", required=True, help="Source name")
@click.option("--title", required=True, help="Title")
@click.option("--author", help="Author")
@click.option("--md5", help="MD5 hash", callback=validate_md5)
@click.option("--format", help="File format (pdf, epub, etc)")
@click.option("--size", type=int, help="Size in bytes")
@click.option("--path", help="Local file path")
@click.option("--doi", help="DOI")
@click.option("--url", help="Source URL")
@click.option("--project", help="Project name")
@click.option("--tags", help="Comma-separated tags")
# Here's a recipe (function) - it does a specific job
def library_add(source, title, author, md5, format, size, path, doi, url, project, tags):
    """Add an item to the library."""
    asyncio.run(_library_add(source, title, author, md5, format, size, path, doi, url, project, tags))


async def _library_add(source, title, author, md5, format, size, path, doi, url, project, tags):
    """Internal async implementation for library add."""
    # We're bringing in tools from another file
    from .storage.database import LibraryItem
    
    # Remember this: we're calling 'cfg' something
    cfg = get_config()
    
    # Get encryption key
    # Remember this: we're calling 'encryption_key' something
    encryption_key = None
    # Checking if something is true - like asking a yes/no question
    if cfg.encryption_enabled:
        # We need help from outside - bringing in tools
        import os
        # Remember this: we're calling 'key_str' something
        key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
        # Checking if something is true - like asking a yes/no question
        if key_str:
            # Remember this: we're calling 'encryption_key' something
            encryption_key = key_from_master(key_str).encode()
    
    # Remember this: we're calling 'item' something
    item = LibraryItem(
        # Remember this: we're calling 'source' something
        source=source,
        # Remember this: we're calling 'title' something
        title=title,
        # Remember this: we're calling 'author' something
        author=author,
        # Remember this: we're calling 'md5' something
        md5=md5,
        # Remember this: we're calling 'format' something
        format=format,
        # Remember this: we're calling 'size_bytes' something
        size_bytes=size,
        # Remember this: we're calling 'path' something
        path=path,
        # Remember this: we're calling 'doi' something
        doi=doi,
        # Remember this: we're calling 'url' something
        url=url,
        # Remember this: we're calling 'project' something
        project=project,
        # Remember this: we're calling 'tags' something
        tags=tags or "",
    )
    
    async with get_database(cfg.db_path, encryption_key) as db:
        # Remember this: we're calling 'item_id' something
        item_id = await db.add_item(item)
        click.echo(f"Added item with ID: {item_id}")


@library.command("search")
@click.argument("query")
@click.option("--limit", default=DEFAULT_LIST_LIMIT, help="Max results")
# Here's a recipe (function) - it does a specific job
def library_search(query, limit):
    """Search library for items."""
    asyncio.run(_library_search(query, limit))


async def _library_search(query, limit):
    """Internal async implementation for library search."""
    # Remember this: we're calling 'cfg' something
    cfg = get_config()
    
    # Remember this: we're calling 'encryption_key' something
    encryption_key = None
    # Checking if something is true - like asking a yes/no question
    if cfg.encryption_enabled:
        # We need help from outside - bringing in tools
        import os
        # Remember this: we're calling 'key_str' something
        key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
        # Checking if something is true - like asking a yes/no question
        if key_str:
            # Remember this: we're calling 'encryption_key' something
            encryption_key = key_from_master(key_str).encode()
    
    async with get_database(cfg.db_path, encryption_key) as db:
        # Remember this: we're calling 'items' something
        items = await db.search(query, limit)
        
        # Checking if something is true - like asking a yes/no question
        if not items:
            click.echo(f"No results for: {query}")
            # We're giving back the result - like handing back what we made
            return
        
        click.echo(f"Found {len(items)} results:")
        # We're doing something over and over, like a repeat button
        for item in items:
            click.echo(f"  [{item.source}] {item.title}")


@library.command("stats")
# Here's a recipe (function) - it does a specific job
def library_stats():
    """Show library statistics."""
    asyncio.run(_library_stats())


async def _library_stats():
    """Internal async implementation for library stats."""
    # Remember this: we're calling 'cfg' something
    cfg = get_config()
    
    # Remember this: we're calling 'encryption_key' something
    encryption_key = None
    # Checking if something is true - like asking a yes/no question
    if cfg.encryption_enabled:
        # We need help from outside - bringing in tools
        import os
        # Remember this: we're calling 'key_str' something
        key_str = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
        # Checking if something is true - like asking a yes/no question
        if key_str:
            # Remember this: we're calling 'encryption_key' something
            encryption_key = key_from_master(key_str).encode()
    
    async with get_database(cfg.db_path, encryption_key) as db:
        # Remember this: we're calling 'total' something
        total = await db.count()
        click.echo(f"Total items: {total}")
        
        # Stats by source
        # Remember this: we're calling 'sources' something
        sources = ["annas-archive", "arxiv", "github", "internet-archive", "scihub"]
        # We're doing something over and over, like a repeat button
        for src in sources:
            # Remember this: we're calling 'count' something
            count = await db.count_by_source(src)
            # Checking if something is true - like asking a yes/no question
            if count:
                click.echo(f"  {src}: {count}")


@main.group()
# Here's a recipe (function) - it does a specific job
def search():
    """Search for resources across sources."""
    pass


@search.command("annas-archive")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
# Here's a recipe (function) - it does a specific job
def search_annas(query, limit):
    """Search Anna's Archive."""
    asyncio.run(_search_annas(query, limit))


async def _search_annas(query, limit):
    """Internal async implementation for searching Anna's Archive."""
    # We're bringing in tools from another file
    from .sources.annas_archive import AnnaSource
    
    # Remember this: we're calling 'source' something
    source = AnnaSource()
    # Remember this: we're calling 'results' something
    results = await source.search(query, limit)
    
    # Checking if something is true - like asking a yes/no question
    if not results:
        click.echo("No results found.")
        # We're giving back the result - like handing back what we made
        return
    
    click.echo(f"Found {len(results)} results:")
    # We're doing something over and over, like a repeat button
    for r in results:
        # Remember this: we're calling 'size' something
        size = f"{r.size or '?'}"
        title = r.title[:60] if r.title else 'Untitled'
        click.echo(f"  {title}")
        click.echo(f"    Author: {r.author or 'Unknown'}")
        click.echo(f"    Format: {r.format or '?'} | Size: {size}")
        # Checking if something is true - like asking a yes/no question
        if r.md5:
            click.echo(f"    MD5: {r.md5}")
        click.echo()


@search.command("arxiv")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
# Here's a recipe (function) - it does a specific job
def search_arxiv(query, limit):
    """Search arXiv."""
    asyncio.run(_search_arxiv(query, limit))


async def _search_arxiv(query, limit):
    """Internal async implementation for searching arXiv."""
    # We're bringing in tools from another file
    from .sources.arxiv import ArxivSource
    
    # Remember this: we're calling 'source' something
    source = ArxivSource()
    # Remember this: we're calling 'results' something
    results = await source.search(query, limit)
    
    # Checking if something is true - like asking a yes/no question
    if not results:
        click.echo("No results found.")
        # We're giving back the result - like handing back what we made
        return
    
    click.echo(f"Found {len(results)} results:")
    # We're doing something over and over, like a repeat button
    for r in results:
        click.echo(f"  {r.title[:60] if r.title else 'Untitled'}")
        click.echo(f"    Authors: {r.author or 'Unknown'}")
        click.echo(f"    arXiv: {r.id or '?'}")
        click.echo(f"    Published: {r.published or '?'}")
        click.echo()


@search.command("github")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
# Here's a recipe (function) - it does a specific job
def search_github(query, limit):
    """Search GitHub."""
    asyncio.run(_search_github(query, limit))


async def _search_github(query, limit):
    """Internal async implementation for searching GitHub."""
    # We're bringing in tools from another file
    from .sources.github import GitHubSource
    
    # Remember this: we're calling 'source' something
    source = GitHubSource()
    # Remember this: we're calling 'results' something
    results = await source.search(query, limit)
    
    # Checking if something is true - like asking a yes/no question
    if not results:
        click.echo("No results found.")
        # We're giving back the result - like handing back what we made
        return
    
    click.echo(f"Found {len(results)} results:")
    # We're doing something over and over, like a repeat button
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
# Here's a recipe (function) - it does a specific job
def search_semantic_scholar(query, limit):
    """Search Semantic Scholar for academic papers."""
    asyncio.run(_search_semantic_scholar(query, limit))


async def _search_semantic_scholar(query, limit):
    """Internal async implementation for searching Semantic Scholar."""
    # We're bringing in tools from another file
    from .sources.semantic_scholar import SemanticScholarSource
    
    # Remember this: we're calling 'source' something
    source = SemanticScholarSource()
    # Remember this: we're calling 'results' something
    results = await source.search(query, limit)
    
    # Checking if something is true - like asking a yes/no question
    if not results:
        click.echo("No results found.")
        # We're giving back the result - like handing back what we made
        return
    
    click.echo(f"Found {len(results)} results:")
    # We're doing something over and over, like a repeat button
    for r in results:
        click.echo(f"  {r.title[:60]}")
        click.echo(f"    Author: {r.author or 'Unknown'}")
        click.echo(f"    Year: {r.published or '?'} | Citations: {r.metadata.get('citations', '?')}")
        # Checking if something is true - like asking a yes/no question
        if r.doi:
            click.echo(f"    DOI: {r.doi}")
        click.echo()


@search.command("pubmed")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
# Here's a recipe (function) - it does a specific job
def search_pubmed(query, limit):
    """Search PubMed for biomedical literature."""
    asyncio.run(_search_pubmed(query, limit))


async def _search_pubmed(query, limit):
    """Internal async implementation for searching PubMed."""
    # We're bringing in tools from another file
    from .sources.pubmed import PubMedSource
    
    # Remember this: we're calling 'source' something
    source = PubMedSource()
    # Remember this: we're calling 'results' something
    results = await source.search(query, limit)
    
    # Checking if something is true - like asking a yes/no question
    if not results:
        click.echo("No results found.")
        # We're giving back the result - like handing back what we made
        return
    
    click.echo(f"Found {len(results)} results:")
    # We're doing something over and over, like a repeat button
    for r in results:
        click.echo(f"  {r.title[:60]}")
        click.echo(f"    Author: {r.author or 'Unknown'}")
        click.echo(f"    Journal: {r.description or '?'}")
        click.echo(f"    PMID: {r.id}")
        # Checking if something is true - like asking a yes/no question
        if r.doi:
            click.echo(f"    DOI: {r.doi}")
        click.echo()


@main.group()
# Here's a recipe (function) - it does a specific job
def get():
    """Download resources."""
    pass


@get.command("annas-archive")
@click.argument("md5")
@click.option("--to", "output_dir", default=".", help="Output directory")
@click.option("--format", help="Preferred format")
# Here's a recipe (function) - it does a specific job
def get_annas(md5, output_dir, format):
    """Download from Anna's Archive by MD5."""
    asyncio.run(_get_annas(md5, output_dir, format))


async def _get_annas(md5, output_dir, format):
    """Internal async implementation for downloading from Anna's Archive."""
    source = AnnaSource()
    dm = DownloadManager(get_config())
    
    item = await _find_annas_item(source, md5)
    if not item:
        return
    
    await _download_annas_item(dm, source, item, output_dir)


async def _find_annas_item(source, md5):
    """Search for item by MD5 in Anna's Archive."""
    click.echo(f"Searching for MD5: {md5}...")
    results = await source.search(f"md5:{md5}", 1)
    
    if not results:
        click.echo("Item not found.", err=True)
        return None
    
    item = results[0]
    click.echo(f"Found: {item.get('title', 'Unknown')}")
    return item


async def _download_annas_item(dm, source, item, output_dir):
    """Download item using fallback chain."""
    success = await dm.download_with_fallback(source, item, Path(output_dir))
    
    if success:
        click.echo("Download complete!")
    else:
        click.echo("Download failed. Try enabling Tor for alternative sources.", err=True)


@get.command("arxiv")
@click.argument("arxiv_id")
@click.option("--to", "output_dir", default=".", help="Output directory")
# Here's a recipe (function) - it does a specific job
def get_arxiv(arxiv_id, output_dir):
    """Download from arXiv by ID."""
    asyncio.run(_get_arxiv(arxiv_id, output_dir))


async def _get_arxiv(arxiv_id, output_dir):
    """Internal async implementation for downloading from arXiv."""
    # We're bringing in tools from another file
    from .sources.arxiv import ArxivSource
    
    # Remember this: we're calling 'cfg' something
    cfg = get_config()
    # Remember this: we're calling 'source' something
    source = ArxivSource()
    
    click.echo(f"Downloading arXiv paper: {arxiv_id}...")
    
    # Remember this: we're calling 'result' something
    result = await source.download(arxiv_id, Path(output_dir))
    
    # Checking if something is true - like asking a yes/no question
    if result:
        click.echo(f"Downloaded to: {result}")
    # If nothing else worked, we do this
    else:
        click.echo("Download failed.", err=True)


@main.group()
# Here's a recipe (function) - it does a specific job
def tor():
    """Manage Tor connection."""
    pass


@tor.command("status")
# Here's a recipe (function) - it does a specific job
def tor_status():
    """Check Tor status."""
    asyncio.run(_tor_status())


async def _tor_status():
    """Internal async implementation for checking Tor status."""
    # We're bringing in tools from another file
    from .tor.manager import TorManager
    
    # Remember this: we're calling 'tm' something
    tm = TorManager()
    # Remember this: we're calling 'status' something
    status = await tm.get_status()
    
    click.echo(f"Tor enabled: {status.get('enabled', False)}")
    click.echo(f"Connected: {status.get('connected', False)}")
    click.echo(f"IP: {status.get('ip', 'Unknown')}")


@tor.command("enable")
# Here's a recipe (function) - it does a specific job
def tor_enable():
    """Enable Tor routing."""
    asyncio.run(_tor_enable())


async def _tor_enable():
    """Internal async implementation for enabling Tor."""
    # We're bringing in tools from another file
    from .tor.manager import TorManager
    
    # Remember this: we're calling 'tm' something
    tm = TorManager()
    await tm.enable()
    click.echo("Tor enabled.")


@tor.command("disable")
# Here's a recipe (function) - it does a specific job
def tor_disable():
    """Disable Tor routing."""
    asyncio.run(_tor_disable())


async def _tor_disable():
    """Internal async implementation for disabling Tor."""
    # We're bringing in tools from another file
    from .tor.manager import TorManager
    
    # Remember this: we're calling 'tm' something
    tm = TorManager()
    await tm.disable()
    click.echo("Tor disabled.")


@tor.command("new-identity")
# Here's a recipe (function) - it does a specific job
def tor_new_identity():
    """Get new Tor circuit (new IP)."""
    asyncio.run(_tor_new_identity())


async def _tor_new_identity():
    """Internal async implementation for getting new Tor identity."""
    # We're bringing in tools from another file
    from .tor.manager import TorManager
    
    # Remember this: we're calling 'tm' something
    tm = TorManager()
    await tm.new_identity()
    click.echo("New Tor identity obtained.")


@main.command("init")
@click.option("--library-path", help="Path for library storage")
@click.option("--encrypt/--no-encrypt", default=True, help="Enable encryption")
# Here's a recipe (function) - it does a specific job
def init(library_path, encrypt):
    """Initialize annchive with configuration."""
    asyncio.run(_init(library_path, encrypt))


async def _init(library_path, encrypt):
    """Internal async implementation for initialization."""
    # Remember this: we're calling 'cfg' something
    cfg = get_config()
    
    # Checking if something is true - like asking a yes/no question
    if library_path:
        cfg.library_path = Path(library_path)
    
    cfg.encryption_enabled = encrypt
    
    # Create directories
    cfg.library_path.mkdir(parents=True, exist_ok=True)
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"Initialized at: {cfg.library_path}")
    click.echo(f"Encryption: {'enabled' if encrypt else 'disabled'}")
    
    # Checking if something is true - like asking a yes/no question
    if encrypt:
        click.echo("\nIMPORTANT: Set encryption key:")
        click.echo("  export ANNCHIVE_ENCRYPTION_KEY='your-master-key'")
        click.echo("Or run: annchive config set encryption-key")


# Checking if something is true - like asking a yes/no question
if __name__ == "__main__":
    main()