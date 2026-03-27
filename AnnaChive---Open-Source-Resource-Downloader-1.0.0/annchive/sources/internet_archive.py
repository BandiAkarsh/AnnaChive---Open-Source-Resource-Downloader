"""Internet Archive source connector."""
# We're bringing in tools from another file
from pathlib import Path
# We're bringing in tools from another file
from typing import Optional

# We need help from outside - bringing in tools
import httpx

# We're bringing in tools from another file
from .base import BaseSource, SourceResult
# We're bringing in tools from another file
from ..utils.logger import get_logger

# Remember this: we're calling 'logger' something
logger = get_logger("sources.internet_archive")


# Think of this like a blueprint (class) for making things
class InternetArchiveSource(BaseSource):
    """Internet Archive (archive.org) connector.
    
    Access to 20M+ books, media, and archived websites.
    Uses CDX API and download endpoints.
    """
    
    # Remember this: we're calling 'name' something
    name = "internet-archive"
    # Remember this: we're calling 'requires_tor' something
    requires_tor = False
    # Remember this: we're calling 'requires_auth' something
    requires_auth = False
    
    # Remember this: we're calling 'BASE_URL' something
    BASE_URL = "https://archive.org"
    # Remember this: we're calling 'CDX_API' something
    CDX_API = "https://archive.org/wayback/available"
    
    # Here's a recipe (function) - it does a specific job
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search Internet Archive."""
        # Use the advanced search API
        # Remember this: we're calling 'url' something
        url = f"{self.BASE_URL}/advancedsearch.php"
        
        # Remember this: we're calling 'params' something
        params = {
            "q": query,
            "fl[]": "identifier,title,creator,date,format,downloads",
            "sort[]": "downloads desc",
            "rows": limit,
            "page": 1,
            "output": "json",
        }
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            
            # We're giving back the result - like handing back what we made
            return self._parse_results(data.get("response", {}).get("docs", []))
        except Exception as e:
            logger.error(f"Internet Archive search failed: {e}")
            # We're giving back the result - like handing back what we made
            return []
    
    # Here's a recipe (function) - it does a specific job
    def _parse_results(self, items: list) -> list[SourceResult]:
        """Parse Internet Archive search results."""
        # Remember this: we're calling 'results' something
        results = []
        
        # We're doing something over and over, like a repeat button
        for item in items:
            # Remember this: we're calling 'identifier' something
            identifier = item.get("identifier", "")
            
            # Remember this: we're calling 'result' something
            result = SourceResult(
                # Remember this: we're calling 'source' something
                source=self.name,
                # Remember this: we're calling 'id' something
                id=identifier,
                # Remember this: we're calling 'title' something
                title=item.get("title", "Unknown"),
                # Remember this: we're calling 'author' something
                author=item.get("creator"),
                # Remember this: we're calling 'format' something
                format=item.get("format"),
                # Remember this: we're calling 'published' something
                published=item.get("date"),
                # Remember this: we're calling 'url' something
                url=f"{self.BASE_URL}/details/{identifier}",
                # Remember this: we're calling 'metadata' something
                metadata={
                    "downloads": item.get("downloads", 0),
                },
            )
            results.append(result)
        
        # We're giving back the result - like handing back what we made
        return results
    
    # Here's a recipe (function) - it does a specific job
    async def get_download_url(self, identifier: str, format: str = "pdf") -> Optional[str]:
        """Get download URL for a specific format.
        
        Common formats: pdf, epub, mobi, djvu, txt
        """
        # Try to get the file metadata first
        # Remember this: we're calling 'url' something
        url = f"{self.BASE_URL}/metadata/{identifier}"
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url)
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            
            # Find file with requested format
            # Remember this: we're calling 'files' something
            files = data.get("files", [])
            # We're doing something over and over, like a repeat button
            for f in files:
                # Checking if something is true - like asking a yes/no question
                if f.get("format", "").lower() == format.lower():
                    # Construct download URL
                    # We're giving back the result - like handing back what we made
                    return f"{self.BASE_URL}/download/{identifier}/{f.get('name')}"
            
            # If exact format not found, try first available format
            # Checking if something is true - like asking a yes/no question
            if files:
                # Remember this: we're calling 'first_file' something
                first_file = files[0]
                # We're giving back the result - like handing back what we made
                return f"{self.BASE_URL}/download/{identifier}/{first_file.get('name')}"
                
        except Exception as e:
            logger.error(f"Failed to get download URL for {identifier}: {e}")
        
        # We're giving back the result - like handing back what we made
        return None
    
    # Here's a recipe (function) - it does a specific job
    async def download(
        self, 
        identifier: str, 
        output_dir: Path,
        format: str = "pdf",
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download from Internet Archive."""
        # Remember this: we're calling 'url' something
        url = await self.get_download_url(identifier, format)
        
        # Checking if something is true - like asking a yes/no question
        if not url:
            # We're giving back the result - like handing back what we made
            return None
        
        # Checking if something is true - like asking a yes/no question
        if not filename:
            # Remember this: we're calling 'filename' something
            filename = f"{identifier}.{format}"
        
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
            
            logger.info(f"Downloaded from Internet Archive: {identifier}")
            # We're giving back the result - like handing back what we made
            return output_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            # We're giving back the result - like handing back what we made
            return None
    
    # Here's a recipe (function) - it does a specific job
    async def get_wayback_url(self, url: str) -> Optional[str]:
        """Get archived version of a URL from Wayback Machine."""
        # Remember this: we're calling 'params' something
        params = {"url": url}
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(self.CDX_API, params=params)
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            
            # Checking if something is true - like asking a yes/no question
            if data.get("archived_snapshots", {}).get("closest"):
                # We're giving back the result - like handing back what we made
                return data["archived_snapshots"]["closest"]["url"]
        except Exception as e:
            logger.error(f"Wayback lookup failed: {e}")
        
        # We're giving back the result - like handing back what we made
        return None