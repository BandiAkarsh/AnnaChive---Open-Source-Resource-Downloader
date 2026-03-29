"""
AnnaChive - arXiv Source Connector

This module connects to arXiv.org, a free repository of research papers.
It allows users to search for and download papers from arXiv.
"""

from pathlib import Path
from typing import Optional

import httpx

from .base import BaseSource, SourceResult
from ..utils.logger import get_logger
from ..constants import DEFAULT_SEARCH_LIMIT, DOWNLOAD_CHUNK_SIZE

logger = get_logger("sources.arxiv")


class ArxivSource(BaseSource):
    """arXiv.org API connector for searching and downloading research papers."""
    
    name = "arxiv"
    requires_tor = False
    requires_auth = False
    BASE_URL = "https://export.arxiv.org/api"
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search for papers on arXiv.
        
        Args:
            query: Search query (e.g., "machine learning")
            limit: Maximum number of results to return
        
        Returns:
            List of SourceResult objects matching the query
        """
        url = f"{self.BASE_URL}/query"
        
        # The format is "all:your query" which searches everywhere
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
            
            # arXiv returns XML format, parse it
            return self._parse_atom(response.text)
        except httpx.HTTPError as e:
            logger.error(f"arXiv HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return []
    
    def _parse_atom(self, xml_content: str) -> list[SourceResult]:
        """
        Convert arXiv's XML response into our standard format.
        
        arXiv returns data in XML format (like HTML but for data).
        This function reads that XML and creates SourceResult objects.
        """
        try:
            import xml.etree.ElementTree as ET
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(xml_content)
            entries = root.findall(".//atom:entry", ns)
            return [self._parse_entry(entry, ns) for entry in entries]
        except Exception as e:
            logger.error(f"Failed to parse Atom response: {e}")
            return []
    
    def _parse_entry(self, entry, ns) -> SourceResult:
        """Parse a single arXiv entry into SourceResult."""
        title = self._extract_text(entry, "atom:title", ns) or "Untitled"
        author_text = self._extract_author(entry, ns)
        description = self._extract_text(entry, "atom:summary", ns)
        arxiv_id = self._extract_arxiv_id(entry, ns)
        published_str = self._extract_text(entry, "atom:published", ns)
        pdf_url = self._extract_pdf_url(entry, ns)
        tags = self._extract_tags(entry, ns)
        
        return SourceResult(
            source=self.name,
            id=arxiv_id,
            title=title,
            author=author_text,
            format="pdf",
            url=pdf_url,
            published=published_str,
            description=description,
            metadata={"tags": tags},
        )
    
    def _extract_text(self, entry, path: str, ns: dict) -> Optional[str]:
        """Extract text from XML element."""
        elem = entry.find(path, ns)
        return elem.text.strip() if elem is not None and elem.text else None
    
    def _extract_author(self, entry, ns) -> Optional[str]:
        """Extract author names from entry."""
        authors = entry.findall("atom:author/atom:name", ns)
        return ", ".join(a.text for a in authors) if authors else None
    
    def _extract_arxiv_id(self, entry, ns) -> str:
        """Extract arXiv ID from entry."""
        id_elem = entry.find("atom:id", ns)
        if id_elem is None:
            return ""
        url = id_elem.text or ""
        return url.split("/")[-1] if "/" in url else url
    
    def _extract_pdf_url(self, entry, ns) -> Optional[str]:
        """Extract PDF URL from entry."""
        links = entry.findall("atom:link", ns)
        for link in links:
            if link.get("title") == "pdf":
                return link.get("href")
        return None
    
    def _extract_tags(self, entry, ns) -> str:
        """Extract category tags from entry."""
        categories = entry.findall("atom:category", ns)
        return ", ".join(c.get("term", "") for c in categories)
    
    async def get_download_url(self, arxiv_id: str) -> Optional[str]:
        """
        Get the direct PDF download URL for an arXiv paper.
        
        Args:
            arxiv_id: The paper's ID (e.g., "1706.03762")
        
        Returns:
            The URL to download the PDF
        """
        # arXiv PDFs are always at this pattern:
        # https://arxiv.org/pdf/ID.pdf
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    
    async def download(
        self, 
        arxiv_id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """
        Download an arXiv paper as PDF.
        
        Args:
            arxiv_id: The paper's ID
            output_dir: Where to save the file
            filename: Optional custom filename
        
        Returns:
            Path to the downloaded file, or None if failed
        """
        # Get the download URL
        url = await self.get_download_url(arxiv_id)
        
        if not url:
            return None
        
        # Use default filename if not provided
        if not filename:
            filename = f"{arxiv_id}.pdf"
        
        # Create the full path where we'll save the file
        output_path = output_dir / filename
        
        try:
            # Download the file
            response = await self.client.get(url)
            response.raise_for_status()
            
            # Write it to disk
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    f.write(chunk)
            
            logger.info(f"Downloaded arXiv paper: {arxiv_id} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to download {arxiv_id}: {e}")
            return None
