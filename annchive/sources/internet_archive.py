"""Internet Archive source connector."""
from pathlib import Path
from typing import Optional

import httpx

from .base import BaseSource, SourceResult
from ..utils.logger import get_logger

logger = get_logger("sources.internet_archive")


class InternetArchiveSource(BaseSource):
    """Internet Archive (archive.org) connector.
    
    Access to 20M+ books, media, and archived websites.
    Uses CDX API and download endpoints.
    """
    
    name = "internet-archive"
    requires_tor = False
    requires_auth = False
    
    BASE_URL = "https://archive.org"
    CDX_API = "https://archive.org/wayback/available"
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search Internet Archive."""
        # Use the advanced search API
        url = f"{self.BASE_URL}/advancedsearch.php"
        
        params = {
            "q": query,
            "fl[]": "identifier,title,creator,date,format,downloads",
            "sort[]": "downloads desc",
            "rows": limit,
            "page": 1,
            "output": "json",
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_results(data.get("response", {}).get("docs", []))
        except Exception as e:
            logger.error(f"Internet Archive search failed: {e}")
            return []
    
    def _parse_results(self, items: list) -> list[SourceResult]:
        """Parse Internet Archive search results."""
        results = []
        
        for item in items:
            identifier = item.get("identifier", "")
            
            result = SourceResult(
                source=self.name,
                id=identifier,
                title=item.get("title", "Unknown"),
                author=item.get("creator"),
                format=item.get("format"),
                published=item.get("date"),
                url=f"{self.BASE_URL}/details/{identifier}",
                metadata={
                    "downloads": item.get("downloads", 0),
                },
            )
            results.append(result)
        
        return results
    
    async def get_download_url(self, identifier: str, format: str = "pdf") -> Optional[str]:
        """Get download URL for a specific format.
        
        Common formats: pdf, epub, mobi, djvu, txt
        """
        # Try to get the file metadata first
        url = f"{self.BASE_URL}/metadata/{identifier}"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Find file with requested format
            files = data.get("files", [])
            for f in files:
                if f.get("format", "").lower() == format.lower():
                    # Construct download URL
                    return f"{self.BASE_URL}/download/{identifier}/{f.get('name')}"
            
            # If exact format not found, try first available format
            if files:
                first_file = files[0]
                return f"{self.BASE_URL}/download/{identifier}/{first_file.get('name')}"
                
        except Exception as e:
            logger.error(f"Failed to get download URL for {identifier}: {e}")
        
        return None
    
    async def download(
        self, 
        identifier: str, 
        output_dir: Path,
        format: str = "pdf",
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download from Internet Archive."""
        url = await self.get_download_url(identifier, format)
        
        if not url:
            return None
        
        if not filename:
            filename = f"{identifier}.{format}"
        
        output_path = output_dir / filename
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded from Internet Archive: {identifier}")
            return output_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    async def get_wayback_url(self, url: str) -> Optional[str]:
        """Get archived version of a URL from Wayback Machine."""
        params = {"url": url}
        
        try:
            response = await self.client.get(self.CDX_API, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("archived_snapshots", {}).get("closest"):
                return data["archived_snapshots"]["closest"]["url"]
        except Exception as e:
            logger.error(f"Wayback lookup failed: {e}")
        
        return None