"""GitHub source connector - free, no auth required for public repos."""

from pathlib import Path
from typing import Optional

from .base import BaseSource, SourceResult
from ..utils.logger import get_logger
from ..constants import DEFAULT_SEARCH_LIMIT, GIT_CLONE_TIMEOUT, DOWNLOAD_CHUNK_SIZE

logger = get_logger("sources.github")


class GitHubSource(BaseSource):
    """GitHub connector - search public repositories.
    
    Uses GitHub REST API (no auth needed for public search).
    Rate limit: 10 requests/min without auth, 30 with auth.
    """
    
    name = "github"
    requires_tor = False
    requires_auth = False
    BASE_URL = "https://api.github.com"
    
    def __init__(self):
        super().__init__()
        import os
        self.token = os.getenv("GITHUB_TOKEN")  # Optional for higher limits
        
        if self.token:
            self._client.headers["Authorization"] = f"token {self.token}"
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search GitHub repositories."""
        url = f"{self.BASE_URL}/search/repositories"
        
        params = {
            "q": query,
            "per_page": limit,
            "sort": "stars",
            "order": "desc",
        }
        
        try:
            response = await self.client.get(url, params=params)
            
            # Handle rate limiting
            if response.status_code == 403:
                logger.warning("GitHub rate limit exceeded")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            return self._parse_results(data.get("items", []))
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            return []
    
    def _parse_results(self, items: list) -> list[SourceResult]:
        """Parse GitHub search results."""
        results = []
        for item in items:
            result = self._parse_single_result(item)
            results.append(result)
        return results
    
    def _parse_single_result(self, item: dict) -> SourceResult:
        """Parse a single GitHub item into SourceResult."""
        return SourceResult(
            source=self.name,
            id=item.get("full_name", ""),
            title=item.get("name", ""),
            author=item.get("owner", {}).get("login"),
            description=item.get("description"),
            format="repository",
            url=item.get("html_url"),
            metadata=self._extract_metadata(item),
        )
    
    def _extract_metadata(self, item: dict) -> dict:
        """Extract metadata from GitHub API response."""
        return {
            "stars": item.get("stargazers_count", 0),
            "forks": item.get("forks_count", 0),
            "language": item.get("language"),
            "license": item.get("license", {}).get("name"),
            "updated": item.get("updated_at"),
        }
    
    async def get_download_url(self, id: str) -> Optional[str]:
        """Get download URL for repository.
        
        Returns the URL to clone the repository.
        """
        # id is in format "owner/repo"
        return f"https://github.com/{id}.git"
    
    async def download(
        self, 
        id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Clone a GitHub repository.
        
        Note: This requires git to be installed.
        """
        import subprocess
        
        clone_url = await self.get_download_url(id)
        if not clone_url:
            return None
        
        # Default directory name
        if not filename:
            # Extract repo name from owner/repo
            filename = id.split("/")[-1]
        
        output_path = output_dir / filename
        
        try:
            # Use git to clone with timeout to prevent hanging forever
            subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(output_path)],
                check=True,
                capture_output=True,
                timeout=300,
            )
            logger.info(f"Cloned repository: {id} -> {output_path}")
            return output_path
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout cloning {id} - repository may be too large")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone {id}: {e}")
            return None
        except FileNotFoundError:
            logger.error("git not found - cannot clone repositories")
            return None
    
    async def get_file_download_url(self, repo: str, path: str, branch: str = "main") -> Optional[str]:
        """Get raw file URL for a specific file in a repo.
        
        Args:
            repo: "owner/repo"
            path: path/to/file
            branch: branch name (default: main)
        
        Returns:
            URL to download raw file
        """
        # URL-encode the path to handle special characters
        from urllib.parse import quote
        encoded_path = quote(path, safe="/")
        return f"https://raw.githubusercontent.com/{repo}/{branch}/{encoded_path}"
    
    async def download_file(
        self, 
        repo: str, 
        path: str,
        output_dir: Path,
        branch: str = "main"
    ) -> Optional[Path]:
        """Download a specific file from a repository."""
        url = await self.get_file_download_url(repo, path, branch)
        
        if not url:
            return None
        
        filename = path.split("/")[-1]
        output_path = output_dir / filename
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    f.write(chunk)
            
            return output_path
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return None