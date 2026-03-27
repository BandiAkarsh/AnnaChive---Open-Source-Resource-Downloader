"""
AnnaChive - arXiv Source Connector

This module connects to arXiv.org, a free repository of research papers.
It allows users to search for and download papers from arXiv.

What is arXiv?
- A free website where researchers share their papers before formal publication
- Contains 2 million+ papers in physics, math, computer science, and more
- No login or payment required - completely free!

How it works:
1. Send search query to arXiv's API
2. Get back list of matching papers
3. Convert the results into our standard format
4. Provide download links for PDFs
"""

from pathlib import Path  # For handling file paths
from typing import Optional  # For type hints

from .base import BaseSource, SourceResult  # Base classes for all sources
from ..utils.logger import get_logger  # For logging messages

# Set up a logger for this file (helps debug issues)
logger = get_logger("sources.arxiv")


class ArxivSource(BaseSource):
    """
    This class handles all interactions with arXiv.org
    
    Think of it as a bridge between AnnaChive and arXiv.
    It knows how to:
    - Search for papers
    - Get download links
    - Download papers to your computer
    """
    
    # What type of source is this?
    name = "arxiv"
    
    # Does this source need Tor? (No - arXiv is open)
    requires_tor = False
    
    # Do you need a password? (No - arXiv is free)
    requires_auth = False
    
    # The web address of arXiv's search API
    BASE_URL = "https://export.arxiv.org/api"
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """
        Search for papers on arXiv.
        
        Args:
            query: What to search for (e.g., "machine learning")
            limit: How many results to return (default: 10)
        
        Returns:
            A list of papers that match your search
        """
        # Step 1: Build the search URL
        url = f"{self.BASE_URL}/query"
        
        # Step 2: Tell arXiv what to search for
        # The format is "all:your query" which searches everywhere
        params = {
            "search_query": f"all:{query}",
            "start": 0,  # Start from the first result
            "max_results": limit,  # Don't return more than requested
            "sortBy": "relevance",  # Show most relevant first
            "sortOrder": "descending",  # Best results first
        }
        
        try:
            # Step 3: Send the request to arXiv
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            # Step 4: arXiv returns XML (a text format), so we need to parse it
            return self._parse_atom(response.text)
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return []
    
    def _parse_atom(self, xml_content: str) -> list[SourceResult]:
        """
        Convert arXiv's XML response into our standard format.
        
        arXiv returns data in XML format (like HTML but for data).
        This function reads that XML and creates SourceResult objects.
        """
        results = []
        
        try:
            # Import XML parser
            import xml.etree.ElementTree as ET
            
            # arXiv uses "namespaces" - think of it as a prefix for their tags
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            
            # Parse the XML
            root = ET.fromstring(xml_content)
            
            # Find all paper entries in the response
            entries = root.findall(".//atom:entry", ns)
            
            # Loop through each paper and extract info
            for entry in entries:
                # Get the title
                title = entry.find("atom:title", ns)
                title = title.text.strip() if title is not None else "Untitled"
                
                # Get authors (could be multiple)
                authors = entry.findall("atom:author/atom:name", ns)
                author = ", ".join(a.text for a in authors) if authors else None
                
                # Get the summary/abstract
                summary = entry.find("atom:summary", ns)
                description = summary.text.strip() if summary is not None else None
                
                # Get arXiv's unique ID for this paper
                id_elem = entry.find("atom:id", ns)
                arxiv_id = ""
                if id_elem is not None:
                    # The URL looks like: http://arxiv.org/abs/YYMM.NNNNN
                    url = id_elem.text or ""
                    arxiv_id = url.split("/")[-1] if "/" in url else url
                
                # Get the date it was published
                published = entry.find("atom:published", ns)
                published_str = published.text if published is not None else None
                
                # Find the PDF download link
                links = entry.findall("atom:link", ns)
                pdf_url = None
                for link in links:
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href")
                        break
                
                # Get the categories/tags
                categories = entry.findall("atom:category", ns)
                tags = ", ".join(c.get("term", "") for c in categories)
                
                # Create our standard result object
                result = SourceResult(
                    source=self.name,  # "arxiv"
                    id=arxiv_id,  # The paper's ID like "1706.03762"
                    title=title,
                    author=author,
                    format="pdf",  # Papers come as PDF
                    url=pdf_url,  # Where to download
                    published=published_str,
                    description=description,
                    metadata={"tags": tags},  # Extra info
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"Failed to parse Atom response: {e}")
        
        return results
    
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
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded arXiv paper: {arxiv_id} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to download {arxiv_id}: {e}")
            return None
