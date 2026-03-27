"""Sci-Hub source connector - requires Tor for access.
    
Since Sci-Hub is often blocked or region-restricted, this source
relies on Tor routing to access .onion mirrors.
"""
from pathlib import Path
from typing import Optional

from .base import BaseSource, SourceResult
from ..config import get_config
from ..utils.logger import get_logger

logger = get_logger("sources.scihub")


class SciHubSource(BaseSource):
    """Sci-Hub connector - academic paper downloads.
    
    Access to 100M+ research papers.
    REQUIRES Tor: many mirrors are blocked or geo-restricted.
    """
    
    name = "scihub"
    requires_tor = True  # This source requires Tor
    requires_auth = False
    
    # Known working .onion mirrors (may change)
    # These are placeholder examples - actual mirrors vary
    ONION_MIRRORS = [
        "sci-hub.se",  # May work directly or via Tor
    ]
    
    def __init__(self):
        super().__init__()
        cfg = get_config()
        
        # Force Tor for this source
        if not cfg.tor_enabled:
            logger.warning("Sci-Hub requires Tor. Enable with: annchive tor enable")
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search Sci-Hub for papers.
        
        Note: Sci-Hub doesn't have a public search API.
        This uses DOI lookup or tries to find papers by title.
        """
        # Check if query looks like a DOI
        if self._is_doi(query):
            return await self._search_by_doi(query, limit)
        
        # Otherwise, try as title search
        # This is limited - Sci-Hub is primarily DOI-based
        logger.info(f"Sci-Hub search: {query} (limited - consider using DOI)")
        return []
    
    def _is_doi(self, query: str) -> bool:
        """Check if query is a DOI."""
        return "10." in query and ("/" in query or query.startswith("10."))
    
    async def _search_by_doi(self, doi: str, limit: int) -> list[SourceResult]:
        """Search by DOI - Sci-Hub's primary method."""
        results = []
        
        # Clean DOI
        doi = doi.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")
        elif doi.startswith("http://doi.org/"):
            doi = doi.replace("http://doi.org/", "")
        
        # Try different mirror approaches
        for mirror in self.ONION_MIRRORS:
            result = await self._try_mirror(doi, mirror)
            if result:
                results.append(result)
                if len(results) >= limit:
                    break
        
        return results
    
    async def _try_mirror(self, doi: str, mirror: str) -> Optional[SourceResult]:
        """Try to access paper via a specific mirror."""
        # Construct Sci-Hub URL
        # Note: The exact URL scheme varies by mirror
        
        # Some mirrors use: scihub.se/doi
        # Others use: scihub.se/analytics?doi=...
        
        urls_to_try = [
            f"https://{mirror}/{doi}",
            f"https://{mirror}/analytics?doi={doi}",
        ]
        
        for url in urls_to_try:
            try:
                response = await self.client.get(url, follow_redirects=True)
                
                if response.status_code == 200:
                    # Got the paper
                    # Extract title from response if possible
                    return SourceResult(
                        source=self.name,
                        id=doi,
                        title=f"Paper: {doi}",  # Would need HTML parsing for actual title
                        doi=doi,
                        url=url,
                        format="pdf",
                    )
            except Exception as e:
                logger.debug(f"Mirror {mirror} failed for {doi}: {e}")
                continue
        
        return None
    
    async def get_download_url(self, doi: str) -> Optional[str]:
        """Get direct download URL for a paper by DOI."""
        # Same as search - Sci-Hub is DOI-centric
        results = await self.search(doi, 1)
        return results[0].url if results else None
    
    async def download(
        self, 
        doi: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download paper from Sci-Hub."""
        url = await self.get_download_url(doi)
        
        if not url:
            logger.error(f"Could not get download URL for DOI: {doi}")
            return None
        
        if not filename:
            # Clean DOI for filename
            clean_doi = doi.replace("/", "_").replace(":", "_")
            filename = f"{clean_doi}.pdf"
        
        output_path = output_dir / filename
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded from Sci-Hub: {doi}")
            return output_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None