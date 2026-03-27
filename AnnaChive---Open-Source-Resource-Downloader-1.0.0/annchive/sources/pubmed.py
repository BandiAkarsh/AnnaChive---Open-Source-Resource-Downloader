"""PubMed source connector - NCBI biomedical literature."""
# We're bringing in tools from another file
from pathlib import Path
# We're bringing in tools from another file
from typing import Optional

# We're bringing in tools from another file
from .base import BaseSource, SourceResult
# We're bringing in tools from another file
from ..utils.logger import get_logger

# Remember this: we're calling 'logger' something
logger = get_logger("sources.pubmed")


# Think of this like a blueprint (class) for making things
class PubMedSource(BaseSource):
    """PubMed connector - NCBI biomedical literature database.
    
    Uses NCBI E-utilities API (free, no auth required).
    Provides access to 35M+ biomedical abstracts and some full text.
    """
    
    # Remember this: we're calling 'name' something
    name = "pubmed"
    # Remember this: we're calling 'requires_tor' something
    requires_tor = False
    # Remember this: we're calling 'requires_auth' something
    requires_auth = False
    
    # Remember this: we're calling 'EUTILS_URL' something
    EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # Rate limit: 3 requests/second, 10 requests/second with API key
    # Here's a recipe (function) - it does a specific job
    def __init__(self):
        super().__init__()
        # We need help from outside - bringing in tools
        import os
        # Optional API key for higher rate limits
        self.api_key = os.getenv("NCBI_API_KEY", "")
    
    # Here's a recipe (function) - it does a specific job
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search PubMed for articles."""
        # We need help from outside - bringing in tools
        import urllib.parse
        
        # ESearch - find matching PMIDs
        # Remember this: we're calling 'url' something
        url = f"{self.EUTILS_URL}/esearch.fcgi"
        
        # Remember this: we're calling 'params' something
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": limit,
            "retmode": "json",
            "sort": "relevance",
        }
        
        # Checking if something is true - like asking a yes/no question
        if self.api_key:
            params["api_key"] = self.api_key
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            
            # Remember this: we're calling 'pmids' something
            pmids = data.get("esearchresult", {}).get("idlist", [])
            
            # Checking if something is true - like asking a yes/no question
            if not pmids:
                # We're giving back the result - like handing back what we made
                return []
            
            # Fetch details for these PMIDs
            # We're giving back the result - like handing back what we made
            return await self._fetch_details(pmids)
            
        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            # We're giving back the result - like handing back what we made
            return []
    
    # Here's a recipe (function) - it does a specific job
    async def _fetch_details(self, pmids: list[str]) -> list[SourceResult]:
        """Fetch details for a list of PMIDs."""
        # ESummary - get article details
        # Remember this: we're calling 'url' something
        url = f"{self.EUTILS_URL}/esummary.fcgi"
        
        # Remember this: we're calling 'params' something
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
        }
        
        # Checking if something is true - like asking a yes/no question
        if self.api_key:
            params["api_key"] = self.api_key
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            
            # Remember this: we're calling 'results' something
            results = []
            # We're doing something over and over, like a repeat button
            for pmid, details in data.get("result", {}).items():
                # Checking if something is true - like asking a yes/no question
                if pmid == "uids":
                    continue
                
                # Get authors
                # Remember this: we're calling 'authors' something
                authors = details.get("authors", [])
                # Remember this: we're calling 'author_str' something
                author_str = ", ".join(
                    a.get("name", "") for a in authors[:3]
                )
                # Checking if something is true - like asking a yes/no question
                if len(authors) > 3:
                    author_str += " et al."
                
                # Get DOI
                # Remember this: we're calling 'article_ids' something
                article_ids = details.get("articleids", [])
                # Remember this: we're calling 'doi' something
                doi = None
                # We're doing something over and over, like a repeat button
                for aid in article_ids:
                    # Checking if something is true - like asking a yes/no question
                    if aid.get("idtype") == "doi":
                        # Remember this: we're calling 'doi' something
                        doi = aid.get("id")
                        break
                
                # Remember this: we're calling 'result' something
                result = SourceResult(
                    # Remember this: we're calling 'source' something
                    source=self.name,
                    # Remember this: we're calling 'id' something
                    id=pmid,
                    # Remember this: we're calling 'title' something
                    title=details.get("title", "Unknown"),
                    # Remember this: we're calling 'author' something
                    author=author_str,
                    # Remember this: we're calling 'format' something
                    format="abstract",
                    # Remember this: we're calling 'published' something
                    published=details.get("pubdate"),
                    # Remember this: we're calling 'doi' something
                    doi=doi,
                    # Remember this: we're calling 'url' something
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    # Remember this: we're calling 'description' something
                    description=details.get("source"),  # Journal name
                    # Remember this: we're calling 'metadata' something
                    metadata={
                        "journal": details.get("source"),
                        "pubdate": details.get("pubdate"),
                        "pmcid": details.get("pmcid"),
                        "articleids": article_ids,
                    },
                )
                results.append(result)
            
            # We're giving back the result - like handing back what we made
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch PubMed details: {e}")
            # We're giving back the result - like handing back what we made
            return []
    
    # Here's a recipe (function) - it does a specific job
    async def get_download_url(self, pmid: str) -> Optional[str]:
        """Get the PubMed URL for an article."""
        # We're giving back the result - like handing back what we made
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    
    # Here's a recipe (function) - it does a specific job
    async def fetch_abstract(self, pmid: str) -> Optional[str]:
        """Fetch the abstract text for a PubMed article."""
        # Remember this: we're calling 'url' something
        url = f"{self.EUTILS_URL}/efetch.fcgi"
        
        # Remember this: we're calling 'params' something
        params = {
            "db": "pubmed",
            "id": pmid,
            "rettype": "abstract",
            "retmode": "text",
        }
        
        # Checking if something is true - like asking a yes/no question
        if self.api_key:
            params["api_key"] = self.api_key
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # We're giving back the result - like handing back what we made
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch abstract: {e}")
            # We're giving back the result - like handing back what we made
            return None
    
    # Here's a recipe (function) - it does a specific job
    async def download(
        self, 
        pmid: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download article metadata and abstract."""
        # Get the abstract
        # Remember this: we're calling 'abstract' something
        abstract = await self.fetch_abstract(pmid)
        
        # Checking if something is true - like asking a yes/no question
        if not abstract:
            # We're giving back the result - like handing back what we made
            return None
        
        # Checking if something is true - like asking a yes/no question
        if not filename:
            # Remember this: we're calling 'filename' something
            filename = f"{pmid}.txt"
        
        # Remember this: we're calling 'output_path' something
        output_path = output_dir / filename
        
        # We're trying something that might go wrong
        try:
            with open(output_path, "w") as f:
                f.write(abstract)
            
            logger.info(f"Downloaded PubMed abstract: {pmid}")
            # We're giving back the result - like handing back what we made
            return output_path
        except Exception as e:
            logger.error(f"Failed to save: {e}")
            # We're giving back the result - like handing back what we made
            return None
    
    # Here's a recipe (function) - it does a specific job
    async def get_full_text_link(self, pmid: str) -> Optional[str]:
        """Get link to full text (PubMed Central if available)."""
        # Remember this: we're calling 'url' something
        url = f"{self.EUTILS_URL}/elink.fcgi"
        
        # Remember this: we're calling 'params' something
        params = {
            "dbfrom": "pubmed",
            "linkname": "pubmed_pmc",
            "id": pmid,
            "retmode": "json",
        }
        
        # Checking if something is true - like asking a yes/no question
        if self.api_key:
            params["api_key"] = self.api_key
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            
            # Remember this: we're calling 'linksets' something
            linksets = data.get("linksets", [])
            # Checking if something is true - like asking a yes/no question
            if linksets:
                # Remember this: we're calling 'links' something
                links = linksets[0].get("links", [])
                # We're doing something over and over, like a repeat button
                for link in links:
                    # Checking if something is true - like asking a yes/no question
                    if link.get("linkname") == "pubmed_pmc":
                        # Remember this: we're calling 'pmcid' something
                        pmcid = link.get("links", [])[0]
                        # We're giving back the result - like handing back what we made
                        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
            
            # We're giving back the result - like handing back what we made
            return None
        except Exception as e:
            logger.error(f"Failed to get full text link: {e}")
            # We're giving back the result - like handing back what we made
            return None