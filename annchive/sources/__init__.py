"""Sources package for annchive."""
from .base import BaseSource, SourceResult
from .annas_archive import AnnaSource
from .arxiv import ArxivSource
from .github import GitHubSource
from .internet_archive import InternetArchiveSource
from .scihub import SciHubSource
from .semantic_scholar import SemanticScholarSource
from .pubmed import PubMedSource

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