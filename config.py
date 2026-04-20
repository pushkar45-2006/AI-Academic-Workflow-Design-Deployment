"""
config.py
---------
Central configuration loader for the Academic AI Workflow Assistant.
Reads environment variables from a .env file and exposes typed settings
to the rest of the application.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file
load_dotenv()

@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration loaded from environment."""
    # LLM
    llm_provider: str
    anthropic_api_key: str
    anthropic_model: str
    openai_api_key: str
    openai_model: str
    # Search
    search_provider: str
    tavily_api_key: str
    serpapi_api_key: str
    # App behaviour
    max_tokens: int
    chunk_size: int
    chunk_overlap: int
    search_result_count: int

def load_config() -> AppConfig:
    """Load and validate configuration from environment variables."""
    return AppConfig(
        llm_provider=os.getenv("LLM_PROVIDER", "gemini").lower(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        search_provider=os.getenv("SEARCH_PROVIDER", "tavily").lower(),
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        serpapi_api_key=os.getenv("SERPAPI_API_KEY", ""),
        max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
        chunk_size=int(os.getenv("CHUNK_SIZE", "2000")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
        search_result_count=int(os.getenv("SEARCH_RESULT_COUNT", "5")),
    )

def validate_config(config: AppConfig) -> list[str]:
    """Check for missing keys to ensure the app runs smoothly."""
    errors: list[str] = []

    # LLM Validation
    if config.llm_provider == "gemini" and not os.getenv("GOOGLE_API_KEY"):
        errors.append("GOOGLE_API_KEY is not set.")
    elif config.llm_provider == "anthropic" and not config.anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY is not set.")
    elif config.llm_provider == "openai" and not config.openai_api_key:
        errors.append("OPENAI_API_KEY is not set.")

    # Search Validation
    if config.search_provider == "tavily" and not config.tavily_api_key:
        errors.append("TAVILY_API_KEY is not set. Get one at tavily.com")
        
    return errors