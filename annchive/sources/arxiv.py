"""arXiv source connector - free, no auth required."""
from pathlib import Path
from typing import Optional

from .base import BaseSource, SourceResult
from ..utils.logger import get_logger

logger = get_logger("sources.arxiv")


class ArxivSource(BaseSource):
    """arXiv.org connector - completely free, no auth needed.
    
    Provides access to 2M+ preprints in physics, math, CS, etc.
    """
    
    name = "arxiv"
    requires_tor = False
    requires_auth = False
    
    BASE_URL = "https://export.arxiv.org/api"
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search arXiv.
        
        Uses the public arXiv API: https://arxiv.org/help/api
        """
        url = f"{self.BASE_URL}/query"
        
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            # Parse Atom XML response
            return self._parse_atom(response.text)
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return []
    
    def _parse_atom(self, xml_content: str) -> list[SourceResult]:
        """Parse arXiv Atom XML response."""
        results = []
        
        try:
            import xml.etree.ElementTree as ET
            
            # arXiv namespace
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            
            root = ET.fromstring(xml_content)
            entries = root.findall(".//atom:entry", ns)
            
            for entry in entries:
                # Extract fields
                title = entry.find("atom:title", ns)
                title = title.text.strip() if title is not None else "Untitled"
                
                authors = entry.findall("atom:author/atom:name", ns)
                author = ", ".join(a.text for a in authors) if authors else None
                
                summary = entry.find("atom:summary", ns)
                description = summary.text.strip() if summary is not None else None
                
                # arXiv ID
                id_elem = entry.find("atom:id", ns)
                arxiv_id = ""
                if id_elem is not None:
                    # Extract ID from URL: http://arxiv.org/abs/YYMM.NNNNN
                    url = id_elem.text or ""
                    arxiv_id = url.split("/")[-1] if "/" in url else url
                
                # Published date
                published = entry.find("atom:published", ns)
                published_str = published.text if published is not None else None
                
                # PDF link
                links = entry.findall("atom:link", ns)
                pdf_url = None
                for link in links:
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href")
                        break
                
                # Categories
                categories = entry.findall("atom:category", ns)
                tags = ", ".join(c.get("term", "") for c in categories)
                
                result = SourceResult(
                    source=self.name,
                    id=arxiv_id,
                    title=title,
                    author=author,
                    format="pdf",
                    url=pdf_url,
                    published=published_str,
                    description=description,
                    metadata={"tags": tags},
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"Failed to parse Atom response: {e}")
        
        return results
    
    async def get_download_url(self, id: str) -> Optional[str]:
        """Get PDF download URL for an arXiv paper."""
        # arXiv IDs can be in formats like:
        # - YYMM.NNNNN (new style)
        # - arch-ive/YYMMNNNN (old style)
        
        # Convert to PDF URL
        # https://arxiv.org/pdf/YYMM.NNNNN.pdf
        return f"https://arxiv.org/pdf/{id}.pdf"
    
    async def download(
        self, 
        id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download arXiv paper as PDF."""
        url = await self.get_download_url(id)
        
        if not url:
            return None
        
        # Default filename
        if not filename:
            filename = f"{id}.pdf"
        
        output_path = output_dir / filename
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded arXiv paper: {id} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to download {id}: {e}")
            return None