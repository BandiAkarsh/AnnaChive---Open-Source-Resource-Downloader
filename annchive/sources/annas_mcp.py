"""Anna's Archive via annas-mcp CLI tool.

This module integrates with the annas-mcp CLI tool to search and download
from Anna's Archive.

Requirements:
1. Download annas-mcp from: https://github.com/iosifache/annas-mcp/releases
2. Make a donation to Anna's Archive to get an API key
3. Set the API key via: annchive config apikey set annas-archive YOUR-KEY
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .base import BaseSource, SourceResult
from ..utils.logger import get_logger

logger = get_logger("sources.annas_mcp")


def _check_annas_mcp_installed() -> bool:
    """Check if annas-mcp is installed."""
    return shutil.which("annas-mcp") is not None


def _get_api_key() -> Optional[str]:
    """Get Anna's Archive API key from environment or keyring."""
    import keyring
    
    # First try environment variable
    key = os.getenv("ANNCHIVE_ANNAS_KEY")
    if key:
        return key
    
    # Then try keyring
    try:
        key = keyring.get_password("annchive", "annchive_annas_key")
        if key:
            return key
    except Exception:
        pass
    
    return None


class AnnaMcpSource(BaseSource):
    """Anna's Archive connector via annas-mcp CLI.
    
    Requires:
    - annas-mcp CLI tool installed (https://github.com/iosifache/annas-mcp/releases)
    - Anna's Archive API key (requires donation at https://annas-archive.org/donate)
    
    Features:
    - Search books by title, author, topic
    - Search articles by DOI or keywords  
    - Download books/articles by ID
    """
    
    name = "annas-mcp"
    requires_tor = False
    requires_auth = True  # Requires API key
    
    def __init__(self):
        super().__init__()
        self._installed = _check_annas_mcp_installed()
        self._api_key = _get_api_key()
        
        if not self._installed:
            logger.warning(
                "annas-mcp not installed. Download from: "
                "https://github.com/iosifache/annas-mcp/releases"
            )
        
        if not self._api_key:
            logger.warning(
                "Anna's Archive API key not set. "
                "Set via: annchive config apikey set annas-archive YOUR-KEY"
            )
    
    def _run_command(self, args: list) -> Optional[dict]:
        """Run annas-mcp command and return JSON output."""
        if not self._installed:
            logger.error("annas-mcp not installed")
            return None
        
        if not self._api_key:
            logger.error("Anna's Archive API key not set")
            return None
        
        # Set environment
        env = os.environ.copy()
        env["ANNAS_SECRET_KEY"] = self._api_key
        env["ANNAS_BASE_URL"] = "https://annas-archive.gl"  # Use working mirror
        env["ANNAS_DOWNLOAD_PATH"] = str(Path.home() / "Downloads")
        
        try:
            result = subprocess.run(
                ["annas-mcp"] + args,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )
            
            if result.returncode != 0:
                logger.error(f"annas-mcp error: {result.stderr}")
                return None
            
            # Try to parse JSON output
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # Some commands return plain text
                return {"output": result.stdout}
                
        except subprocess.TimeoutExpired:
            logger.error("annas-mcp command timed out")
            return None
        except Exception as e:
            logger.error(f"annas-mcp failed: {e}")
            return None
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search for books/articles via annas-mcp."""
        if not self._installed or not self._api_key:
            # Return helpful error message
            logger.error(
                "annas-mcp not fully configured. "
                "Install CLI and set API key."
            )
            return []
        
        # Try book search first
        results = await self._search_books(query, limit)
        if results:
            return results
        
        # Try article search
        return await self._search_articles(query, limit)
    
    async def _search_books(self, query: str, limit: int) -> list[SourceResult]:
        """Search for books."""
        output = self._run_command(["book-search", query])
        
        if not output:
            return []
        
        results = []
        books = output.get("books", [output]) if isinstance(output, dict) else []
        
        for book in books[:limit]:
            result = SourceResult(
                source="annas-archive",
                id=book.get("md5", book.get("id", "")),
                title=book.get("title", "Unknown"),
                author=book.get("author"),
                format=book.get("format", "ebook"),
                size=book.get("size"),
                url=book.get("url"),
                md5=book.get("md5"),
                metadata={
                    "type": "book",
                    "isbn": book.get("isbn"),
                    "publisher": book.get("publisher"),
                },
            )
            results.append(result)
        
        return results
    
    async def _search_articles(self, query: str, limit: int) -> list[SourceResult]:
        """Search for articles."""
        output = self._run_command(["article-search", query])
        
        if not output:
            return []
        
        results = []
        articles = output.get("articles", [output]) if isinstance(output, dict) else []
        
        for article in articles[:limit]:
            result = SourceResult(
                source="annas-archive",
                id=article.get("doi", article.get("id", "")),
                title=article.get("title", "Unknown"),
                author=article.get("author"),
                format="article",
                doi=article.get("doi"),
                url=article.get("url"),
                metadata={
                    "type": "article",
                    "journal": article.get("journal"),
                    "year": article.get("year"),
                },
            )
            results.append(result)
        
        return results
    
    async def get_download_url(self, md5: str) -> Optional[str]:
        """Get download URL for a book by MD5."""
        if not self._installed or not self._api_key:
            return None
        
        output = self._run_command(["book-download", md5])
        
        if output and "download_url" in output:
            return output["download_url"]
        
        return None
    
    async def download(
        self, 
        id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download a book/article by ID (MD5 for books, DOI for articles)."""
        if not self._installed or not self._api_key:
            logger.error("annas-mcp not configured for download")
            return None
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine if it's a book (MD5) or article (DOI)
        if len(id) == 32:  # MD5 hash
            cmd = ["book-download", id]
        else:  # Assume DOI
            cmd = ["article-download", id]
        
        # Set download path
        env = os.environ.copy()
        env["ANNAS_SECRET_KEY"] = self._api_key
        env["ANNAS_BASE_URL"] = "https://annas-archive.gl"
        env["ANNAS_DOWNLOAD_PATH"] = str(output_dir)
        
        try:
            result = subprocess.run(
                ["annas-mcp"] + cmd,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )
            
            if result.returncode == 0:
                # Find downloaded file
                files = list(output_dir.glob("*"))
                if files:
                    return files[0]
            
            logger.error(f"Download failed: {result.stderr}")
            return None
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if annas-mcp is properly configured."""
        return self._installed and self._api_key is not None
