"""AI package for Clicky macOS."""
from ai.base_provider import BaseAIProvider
from ai.mlx_engine import MLXEngine
from ai.universal_locator import UniversalLocator
from ai.web_search import WebSearcher

__all__ = [
    "BaseAIProvider",
    "MLXEngine",
    "UniversalLocator",
    "WebSearcher",
]
