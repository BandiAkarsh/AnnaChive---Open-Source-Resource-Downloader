"""PubMed source connector - NCBI biomedical literature."""
from pathlib import Path
from typing import Optional

from .base import BaseSource, SourceResult
from ..utils.logger import get_logger

logger = get_logger("sources.pubmed")


class PubMedSource(BaseSource):
    """PubMed connector - NCBI biomedical literature database.
    
    Uses NCBI E-utilities API (free, no auth required).
    Provides access to 35M+ biomedical abstracts and some full text.
    """
    
    name = "pubmed"
    requires_tor = False
    requires_auth = False
    
    EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # Rate limit: 3 requests/second, 10 requests/second with API key
    def __init__(self):
        super().__init__()
        import os
        # Optional API key for higher rate limits
        self.api_key = os.getenv("NCBI_API_KEY", "")
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search PubMed for articles."""
        import urllib.parse
        
        # ESearch - find matching PMIDs
        url = f"{self.EUTILS_URL}/esearch.fcgi"
        
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": limit,
            "retmode": "json",
            "sort": "relevance",
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            pmids = data.get("esearchresult", {}).get("idlist", [])
            
            if not pmids:
                return []
            
            # Fetch details for these PMIDs
            return await self._fetch_details(pmids)
            
        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            return []
    
    async def _fetch_details(self, pmids: list[str]) -> list[SourceResult]:
        """Fetch details for a list of PMIDs."""
        # ESummary - get article details
        url = f"{self.EUTILS_URL}/esummary.fcgi"
        
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for pmid, details in data.get("result", {}).items():
                if pmid == "uids":
                    continue
                
                # Get authors
                authors = details.get("authors", [])
                author_str = ", ".join(
                    a.get("name", "") for a in authors[:3]
                )
                if len(authors) > 3:
                    author_str += " et al."
                
                # Get DOI
                article_ids = details.get("articleids", [])
                doi = None
                for aid in article_ids:
                    if aid.get("idtype") == "doi":
                        doi = aid.get("id")
                        break
                
                result = SourceResult(
                    source=self.name,
                    id=pmid,
                    title=details.get("title", "Unknown"),
                    author=author_str,
                    format="abstract",
                    published=details.get("pubdate"),
                    doi=doi,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    description=details.get("source"),  # Journal name
                    metadata={
                        "journal": details.get("source"),
                        "pubdate": details.get("pubdate"),
                        "pmcid": details.get("pmcid"),
                        "articleids": article_ids,
                    },
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch PubMed details: {e}")
            return []
    
    async def get_download_url(self, pmid: str) -> Optional[str]:
        """Get the PubMed URL for an article."""
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    
    async def fetch_abstract(self, pmid: str) -> Optional[str]:
        """Fetch the abstract text for a PubMed article."""
        url = f"{self.EUTILS_URL}/efetch.fcgi"
        
        params = {
            "db": "pubmed",
            "id": pmid,
            "rettype": "abstract",
            "retmode": "text",
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch abstract: {e}")
            return None
    
    async def download(
        self, 
        pmid: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download article metadata and abstract."""
        # Get the abstract
        abstract = await self.fetch_abstract(pmid)
        
        if not abstract:
            return None
        
        if not filename:
            filename = f"{pmid}.txt"
        
        output_path = output_dir / filename
        
        try:
            with open(output_path, "w") as f:
                f.write(abstract)
            
            logger.info(f"Downloaded PubMed abstract: {pmid}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to save: {e}")
            return None
    
    async def get_full_text_link(self, pmid: str) -> Optional[str]:
        """Get link to full text (PubMed Central if available)."""
        url = f"{self.EUTILS_URL}/elink.fcgi"
        
        params = {
            "dbfrom": "pubmed",
            "linkname": "pubmed_pmc",
            "id": pmid,
            "retmode": "json",
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            linksets = data.get("linksets", [])
            if linksets:
                links = linksets[0].get("links", [])
                for link in links:
                    if link.get("linkname") == "pubmed_pmc":
                        pmcid = link.get("links", [])[0]
                        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
            
            return None
        except Exception as e:
            logger.error(f"Failed to get full text link: {e}")
            return None