from __future__ import annotations

import json
import logging

import requests
from langchain.tools import tool

from src.community.custom_search.tools import search_custom_backend

logger = logging.getLogger(__name__)

DEFAULT_ONLINE_SEARCH_REPOSITORY = "online-search"


@tool("online_search", parse_docstring=True)
def online_search_tool(query: str) -> str:
    """Search public internet information with the fixed online-search repository.

    Args:
        query: The query to search for.
    """

    try:
        results = search_custom_backend(
            query,
            repository_id=DEFAULT_ONLINE_SEARCH_REPOSITORY,
            tool_name="online_search",
        )
    except requests.RequestException as exc:
        logger.error("Online search request failed: %s", exc, exc_info=True)
        return f"Error: online search request failed: {exc}"
    except ValueError as exc:
        return f"Error: {exc}"
    except json.JSONDecodeError as exc:
        logger.error("Online search returned invalid JSON: %s", exc, exc_info=True)
        return f"Error: online search returned invalid JSON: {exc}"
    except Exception as exc:
        logger.error("Unexpected online search error: %s", exc, exc_info=True)
        return f"Error: online search failed: {exc}"

    return json.dumps(results, indent=2, ensure_ascii=False)


__all__ = ["online_search_tool"]
