"""Sci-Hub source connector - requires Tor for access.
    
Since Sci-Hub is often blocked or region-restricted, this source
relies on Tor routing to access .onion mirrors.
"""
# We're bringing in tools from another file
from pathlib import Path
# We're bringing in tools from another file
from typing import Optional

# We're bringing in tools from another file
from .base import BaseSource, SourceResult
# We're bringing in tools from another file
from ..config import get_config
# We're bringing in tools from another file
from ..utils.logger import get_logger

# Remember this: we're calling 'logger' something
logger = get_logger("sources.scihub")


# Think of this like a blueprint (class) for making things
class SciHubSource(BaseSource):
    """Sci-Hub connector - academic paper downloads.
    
    Access to 100M+ research papers.
    REQUIRES Tor: many mirrors are blocked or geo-restricted.
    """
    
    # Remember this: we're calling 'name' something
    name = "scihub"
    # Remember this: we're calling 'requires_tor' something
    requires_tor = True  # This source requires Tor
    # Remember this: we're calling 'requires_auth' something
    requires_auth = False
    
    # Known working .onion mirrors (may change)
    # These are placeholder examples - actual mirrors vary
    # Remember this: we're calling 'ONION_MIRRORS' something
    ONION_MIRRORS = [
        "sci-hub.se",  # May work directly or via Tor
    ]
    
    # Here's a recipe (function) - it does a specific job
    def __init__(self):
        super().__init__()
        # Remember this: we're calling 'cfg' something
        cfg = get_config()
        
        # Force Tor for this source
        # Checking if something is true - like asking a yes/no question
        if not cfg.tor_enabled:
            logger.warning("Sci-Hub requires Tor. Enable with: annchive tor enable")
    
    # Here's a recipe (function) - it does a specific job
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search Sci-Hub for papers.
        
        Note: Sci-Hub doesn't have a public search API.
        This uses DOI lookup or tries to find papers by title.
        """
        # Check if query looks like a DOI
        # Checking if something is true - like asking a yes/no question
        if self._is_doi(query):
            # We're giving back the result - like handing back what we made
            return await self._search_by_doi(query, limit)
        
        # Otherwise, try as title search
        # This is limited - Sci-Hub is primarily DOI-based
        logger.info(f"Sci-Hub search: {query} (limited - consider using DOI)")
        # We're giving back the result - like handing back what we made
        return []
    
    # Here's a recipe (function) - it does a specific job
    def _is_doi(self, query: str) -> bool:
        """Check if query is a DOI."""
        # We're giving back the result - like handing back what we made
        return "10." in query and ("/" in query or query.startswith("10."))
    
    # Here's a recipe (function) - it does a specific job
    async def _search_by_doi(self, doi: str, limit: int) -> list[SourceResult]:
        """Search by DOI - Sci-Hub's primary method."""
        # Remember this: we're calling 'results' something
        results = []
        
        # Clean DOI
        # Remember this: we're calling 'doi' something
        doi = doi.strip()
        # Checking if something is true - like asking a yes/no question
        if doi.startswith("https://doi.org/"):
            # Remember this: we're calling 'doi' something
            doi = doi.replace("https://doi.org/", "")
        # If the first answer was no, try this instead
        elif doi.startswith("http://doi.org/"):
            # Remember this: we're calling 'doi' something
            doi = doi.replace("http://doi.org/", "")
        
        # Try different mirror approaches
        # We're doing something over and over, like a repeat button
        for mirror in self.ONION_MIRRORS:
            # Remember this: we're calling 'result' something
            result = await self._try_mirror(doi, mirror)
            # Checking if something is true - like asking a yes/no question
            if result:
                results.append(result)
                # Checking if something is true - like asking a yes/no question
                if len(results) >= limit:
                    break
        
        # We're giving back the result - like handing back what we made
        return results
    
    # Here's a recipe (function) - it does a specific job
    async def _try_mirror(self, doi: str, mirror: str) -> Optional[SourceResult]:
        """Try to access paper via a specific mirror."""
        # Construct Sci-Hub URL
        # Note: The exact URL scheme varies by mirror
        
        # Some mirrors use: scihub.se/doi
        # Others use: scihub.se/analytics?doi=...
        
        # Remember this: we're calling 'urls_to_try' something
        urls_to_try = [
            f"https://{mirror}/{doi}",
            f"https://{mirror}/analytics?doi={doi}",
        ]
        
        # We're doing something over and over, like a repeat button
        for url in urls_to_try:
            # We're trying something that might go wrong
            try:
                # Remember this: we're calling 'response' something
                response = await self.client.get(url, follow_redirects=True)
                
                # Checking if something is true - like asking a yes/no question
                if response.status_code == 200:
                    # Got the paper
                    # Extract title from response if possible
                    # We're giving back the result - like handing back what we made
                    return SourceResult(
                        # Remember this: we're calling 'source' something
                        source=self.name,
                        # Remember this: we're calling 'id' something
                        id=doi,
                        # Remember this: we're calling 'title' something
                        title=f"Paper: {doi}",  # Would need HTML parsing for actual title
                        # Remember this: we're calling 'doi' something
                        doi=doi,
                        # Remember this: we're calling 'url' something
                        url=url,
                        # Remember this: we're calling 'format' something
                        format="pdf",
                    )
            except Exception as e:
                logger.debug(f"Mirror {mirror} failed for {doi}: {e}")
                continue
        
        # We're giving back the result - like handing back what we made
        return None
    
    # Here's a recipe (function) - it does a specific job
    async def get_download_url(self, doi: str) -> Optional[str]:
        """Get direct download URL for a paper by DOI."""
        # Same as search - Sci-Hub is DOI-centric
        # Remember this: we're calling 'results' something
        results = await self.search(doi, 1)
        # We're giving back the result - like handing back what we made
        return results[0].url if results else None
    
    # Here's a recipe (function) - it does a specific job
    async def download(
        self, 
        doi: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download paper from Sci-Hub."""
        # Remember this: we're calling 'url' something
        url = await self.get_download_url(doi)
        
        # Checking if something is true - like asking a yes/no question
        if not url:
            logger.error(f"Could not get download URL for DOI: {doi}")
            # We're giving back the result - like handing back what we made
            return None
        
        # Checking if something is true - like asking a yes/no question
        if not filename:
            # Clean DOI for filename
            # Remember this: we're calling 'clean_doi' something
            clean_doi = doi.replace("/", "_").replace(":", "_")
            # Remember this: we're calling 'filename' something
            filename = f"{clean_doi}.pdf"
        
        # Remember this: we're calling 'output_path' something
        output_path = output_dir / filename
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                # We're doing something over and over, like a repeat button
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded from Sci-Hub: {doi}")
            # We're giving back the result - like handing back what we made
            return output_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            # We're giving back the result - like handing back what we made
            return None