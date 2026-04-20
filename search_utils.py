"""
search_utils.py
---------------
Academic and web search utilities.

Supports two search providers (configured via SEARCH_PROVIDER in .env):
  - "tavily"  → Tavily AI Search (recommended — natively LLM-friendly)
  - "serpapi" → SerpAPI Google Scholar / web search

Both providers return a normalised list of PaperResult objects so the
rest of the app is provider-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from config import AppConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalised result type
# ---------------------------------------------------------------------------

@dataclass
class PaperResult:
    """A single academic paper or search result."""
    title: str
    url: str
    authors: str = "Unknown"
    abstract: str = "No abstract available."
    source: str = ""
    year: Optional[str] = None

    def to_markdown(self, index: int) -> str:
        """Render this result as a numbered Markdown entry."""
        year_str = f" ({self.year})" if self.year else ""
        return (
            f"**{index}. {self.title}**{year_str}  \n"
            f"*Authors:* {self.authors}  \n"
            f"*Source:* {self.source}  \n"
            f"*Abstract:* {self.abstract}  \n"
            f"🔗 [{self.url}]({self.url})"
        )


# ---------------------------------------------------------------------------
# Tavily provider
# ---------------------------------------------------------------------------

def _search_tavily(query: str, config: AppConfig) -> list[PaperResult]:
    """
    Search using the Tavily AI Search API.

    Tavily returns structured results with titles, URLs, and content snippets.
    We map these to PaperResult objects.
    """
    from tavily import TavilyClient

    client = TavilyClient(api_key=config.tavily_api_key)

    # Bias towards academic sources
    academic_query = f"academic research paper: {query} site:arxiv.org OR site:semanticscholar.org OR site:scholar.google.com OR site:pubmed.ncbi.nlm.nih.gov"

    logger.info("Querying Tavily for: %s", query)
    response = client.search(
        query=academic_query,
        search_depth="advanced",
        max_results=config.search_result_count,
        include_answer=False,
    )

    results: list[PaperResult] = []
    for item in response.get("results", []):
        # Truncate abstract to a single readable sentence
        content: str = item.get("content", "No abstract available.")
        abstract = content.split(". ")[0] + "." if ". " in content else content[:200]

        results.append(PaperResult(
            title=item.get("title", "Untitled"),
            url=item.get("url", ""),
            abstract=abstract,
            source=_infer_source(item.get("url", "")),
        ))

    return results


# ---------------------------------------------------------------------------
# SerpAPI provider
# ---------------------------------------------------------------------------

def _search_serpapi(query: str, config: AppConfig) -> list[PaperResult]:
    """
    Search using SerpAPI (Google Scholar engine).

    Requires the `google-search-results` package.
    """
    from serpapi import GoogleSearch

    logger.info("Querying SerpAPI (Google Scholar) for: %s", query)
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": config.serpapi_api_key,
        "num": config.search_result_count,
    }

    search = GoogleSearch(params)
    raw = search.get_dict()

    results: list[PaperResult] = []
    for item in raw.get("organic_results", []):
        pub_info = item.get("publication_info", {})
        authors_list = pub_info.get("authors", [])
        authors = ", ".join(a.get("name", "") for a in authors_list) if authors_list else "Unknown"

        snippet: str = item.get("snippet", "No abstract available.")
        abstract = snippet.split(". ")[0] + "." if ". " in snippet else snippet

        year = pub_info.get("summary", "").split(" ")[-1]  # last token is often the year
        year = year if year.isdigit() and len(year) == 4 else None

        results.append(PaperResult(
            title=item.get("title", "Untitled"),
            url=item.get("link", ""),
            authors=authors,
            abstract=abstract,
            source="Google Scholar",
            year=year,
        ))

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_academic_papers(query: str, config: AppConfig) -> list[PaperResult]:
    """
    Search for academic papers using the configured provider.

    Args:
        query:  Natural language research query.
        config: Application configuration (determines which provider to use).

    Returns:
        List of PaperResult objects (up to config.search_result_count).

    Raises:
        ValueError: If the configured provider is not supported.
        RuntimeError: If the search API call fails.
    """
    provider = config.search_provider

    try:
        if provider == "tavily":
            return _search_tavily(query, config)
        elif provider == "serpapi":
            return _search_serpapi(query, config)
        else:
            raise ValueError(f"Unsupported search provider: '{provider}'")
    except Exception as exc:
        logger.exception("Search failed with provider '%s': %s", provider, exc)
        raise RuntimeError(f"Search failed: {exc}") from exc


def _infer_source(url: str) -> str:
    """Infer a human-friendly source name from a URL."""
    if "arxiv.org" in url:
        return "arXiv"
    if "semanticscholar.org" in url:
        return "Semantic Scholar"
    if "pubmed" in url:
        return "PubMed"
    if "scholar.google" in url:
        return "Google Scholar"
    if "springer" in url:
        return "Springer"
    if "nature.com" in url:
        return "Nature"
    if "ieee" in url:
        return "IEEE Xplore"
    if "acm.org" in url:
        return "ACM Digital Library"
    # Fallback: extract domain
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return "Web"
