"""GitHub source connector - free, no auth required for public repos."""
# We're bringing in tools from another file
from pathlib import Path
# We're bringing in tools from another file
from typing import Optional

# We're bringing in tools from another file
from .base import BaseSource, SourceResult
# We're bringing in tools from another file
from ..utils.logger import get_logger

# Remember this: we're calling 'logger' something
logger = get_logger("sources.github")


# Think of this like a blueprint (class) for making things
class GitHubSource(BaseSource):
    """GitHub connector - search public repositories.
    
    Uses GitHub REST API (no auth needed for public search).
    Rate limit: 10 requests/min without auth, 30 with auth.
    """
    
    # Remember this: we're calling 'name' something
    name = "github"
    # Remember this: we're calling 'requires_tor' something
    requires_tor = False
    # Remember this: we're calling 'requires_auth' something
    requires_auth = False
    
    # Remember this: we're calling 'BASE_URL' something
    BASE_URL = "https://api.github.com"
    
    # Optional: set GH_TOKEN env var for higher rate limits
    # Here's a recipe (function) - it does a specific job
    def __init__(self):
        super().__init__()
        # We need help from outside - bringing in tools
        import os
        self.token = os.getenv("GITHUB_TOKEN")  # Optional for higher limits
        
        # Checking if something is true - like asking a yes/no question
        if self.token:
            self._client.headers["Authorization"] = f"token {self.token}"
    
    # Here's a recipe (function) - it does a specific job
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search GitHub repositories."""
        # Remember this: we're calling 'url' something
        url = f"{self.BASE_URL}/search/repositories"
        
        # Remember this: we're calling 'params' something
        params = {
            "q": query,
            "per_page": limit,
            "sort": "stars",
            "order": "desc",
        }
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            
            # Handle rate limiting
            # Checking if something is true - like asking a yes/no question
            if response.status_code == 403:
                logger.warning("GitHub rate limit exceeded")
                # We're giving back the result - like handing back what we made
                return []
            
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            
            # We're giving back the result - like handing back what we made
            return self._parse_results(data.get("items", []))
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            # We're giving back the result - like handing back what we made
            return []
    
    # Here's a recipe (function) - it does a specific job
    def _parse_results(self, items: list) -> list[SourceResult]:
        """Parse GitHub search results."""
        # Remember this: we're calling 'results' something
        results = []
        
        # We're doing something over and over, like a repeat button
        for item in items:
            # Remember this: we're calling 'result' something
            result = SourceResult(
                # Remember this: we're calling 'source' something
                source=self.name,
                # Remember this: we're calling 'id' something
                id=item.get("full_name", ""),
                # Remember this: we're calling 'title' something
                title=item.get("name", ""),
                # Remember this: we're calling 'author' something
                author=item.get("owner", {}).get("login"),
                # Remember this: we're calling 'description' something
                description=item.get("description"),
                # Remember this: we're calling 'format' something
                format="repository",  # It's a repo, not a file
                # Remember this: we're calling 'url' something
                url=item.get("html_url"),
                # Remember this: we're calling 'metadata' something
                metadata={
                    "stars": item.get("stargazers_count", 0),
                    "forks": item.get("forks_count", 0),
                    "language": item.get("language"),
                    "license": item.get("license", {}).get("name"),
                    "updated": item.get("updated_at"),
                },
            )
            results.append(result)
        
        # We're giving back the result - like handing back what we made
        return results
    
    # Here's a recipe (function) - it does a specific job
    async def get_download_url(self, id: str) -> Optional[str]:
        """Get download URL for repository.
        
        Returns the URL to clone the repository.
        """
        # id is in format "owner/repo"
        # We're giving back the result - like handing back what we made
        return f"https://github.com/{id}.git"
    
    # Here's a recipe (function) - it does a specific job
    async def download(
        self, 
        id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Clone a GitHub repository.
        
        Note: This requires git to be installed.
        """
        # We need help from outside - bringing in tools
        import subprocess
        
        # Remember this: we're calling 'clone_url' something
        clone_url = await self.get_download_url(id)
        # Checking if something is true - like asking a yes/no question
        if not clone_url:
            # We're giving back the result - like handing back what we made
            return None
        
        # Default directory name
        # Checking if something is true - like asking a yes/no question
        if not filename:
            # Extract repo name from owner/repo
            # Remember this: we're calling 'filename' something
            filename = id.split("/")[-1]
        
        # Remember this: we're calling 'output_path' something
        output_path = output_dir / filename
        
        # We're trying something that might go wrong
        try:
            # Use git to clone
            subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(output_path)],
                # Remember this: we're calling 'check' something
                check=True,
                # Remember this: we're calling 'capture_output' something
                capture_output=True,
            )
            logger.info(f"Cloned repository: {id} -> {output_path}")
            # We're giving back the result - like handing back what we made
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone {id}: {e}")
            # We're giving back the result - like handing back what we made
            return None
        except FileNotFoundError:
            logger.error("git not found - cannot clone repositories")
            # We're giving back the result - like handing back what we made
            return None
    
    # Here's a recipe (function) - it does a specific job
    async def get_file_download_url(self, repo: str, path: str, branch: str = "main") -> Optional[str]:
        """Get raw file URL for a specific file in a repo.
        
        Args:
            repo: "owner/repo"
            path: path/to/file
            branch: branch name (default: main)
        
        Returns:
            URL to download raw file
        """
        # We're giving back the result - like handing back what we made
        return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    
    # Here's a recipe (function) - it does a specific job
    async def download_file(
        self, 
        repo: str, 
        path: str,
        output_dir: Path,
        branch: str = "main"
    ) -> Optional[Path]:
        """Download a specific file from a repository."""
        # Remember this: we're calling 'url' something
        url = await self.get_file_download_url(repo, path, branch)
        
        # Checking if something is true - like asking a yes/no question
        if not url:
            # We're giving back the result - like handing back what we made
            return None
        
        # Remember this: we're calling 'filename' something
        filename = path.split("/")[-1]
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
            
            # We're giving back the result - like handing back what we made
            return output_path
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            # We're giving back the result - like handing back what we made
            return None