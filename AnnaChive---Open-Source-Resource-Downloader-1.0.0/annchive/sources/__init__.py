"""Sources package for annchive."""
# We're bringing in tools from another file
from .base import BaseSource, SourceResult
# We're bringing in tools from another file
from .annas_archive import AnnaSource
# We're bringing in tools from another file
from .arxiv import ArxivSource
# We're bringing in tools from another file
from .github import GitHubSource
# We're bringing in tools from another file
from .internet_archive import InternetArchiveSource
# We're bringing in tools from another file
from .scihub import SciHubSource
# We're bringing in tools from another file
from .semantic_scholar import SemanticScholarSource
# We're bringing in tools from another file
from .pubmed import PubMedSource

# Remember this: we're calling '__all__' something
__all__ = [
    "BaseSource",
    "SourceResult",
    "AnnaSource",
    "ArxivSource", 
    "GitHubSource",
    "InternetArchiveSource",
    "SciHubSource",
    "SemanticScholarSource",
    "PubMedSource",
]