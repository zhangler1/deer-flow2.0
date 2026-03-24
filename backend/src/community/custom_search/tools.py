from __future__ import annotations

import json
import logging
from typing import Any

import requests
from langchain.tools import tool

from src.config.custom_search_config import CustomSearchRepositoryConfig, get_custom_search_config, get_custom_search_repository_choices

logger = logging.getLogger(__name__)


def _resolve_repository(repository_id: str | None, tool_name: str = "web_search") -> CustomSearchRepositoryConfig:
    config = get_custom_search_config(tool_name)
    selected_repository_id = repository_id or config.default_repository
    repository = config.repositories.get(selected_repository_id)
    if repository is not None:
        return repository

    for configured_repository in config.repositories.values():
        if configured_repository.repository == selected_repository_id:
            return configured_repository

    fallback_repository = config.repositories.get(config.default_repository)
    if fallback_repository is not None:
        logger.warning(
            "Custom search repository '%s' not found. Falling back to '%s'.",
            selected_repository_id,
            fallback_repository.id,
        )
        return fallback_repository

    return next(iter(config.repositories.values()))


def _build_payload(query: str, repository: CustomSearchRepositoryConfig, muwp_user: dict[str, str]) -> dict[str, Any]:
    return {
        "REQ_HEAD": {
            "TRANS_PROCESS": "",
            "TRAN_ID": "",
        },
        "REQ_BODY": {
            "param": {
                "messages": [
                    {
                        "content": query,
                        "role": "user",
                    }
                ],
                "repository": repository.repository,
                "param": {
                    "channelId": repository.channel_id,
                },
            },
            "muwpUser": muwp_user,
        },
    }


def _parse_response(payload: dict[str, Any], max_results: int) -> list[dict[str, Any]]:
    response_head = payload.get("RSP_HEAD", {})
    if response_head.get("TRAN_SUCCESS") != "1":
        logger.warning("Custom search API returned a non-success response head: %s", response_head)
        return []

    raw_results = payload.get("RSP_BODY", {}).get("result", [])
    normalized_results: list[dict[str, Any]] = []
    for item in raw_results:
        title = str(item.get("title", "")).strip()
        snippet = str(item.get("content", "") or item.get("absContent", "")).strip()
        if not title and not snippet:
            continue
        score_raw = item.get("score")
        try:
            score = float(score_raw) if score_raw is not None and score_raw != "" else 0.0
        except (TypeError, ValueError):
            score = 0.0
        normalized_results.append(
            {
                "title": title,
                "url": str(item.get("url") or ""),
                "snippet": snippet,
                "score": score,
                "source": str(item.get("source", "")),
                "category": str(item.get("fullCategoryName", "")),
                "create_time": str(item.get("createTime", "")),
            }
        )

    normalized_results.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return normalized_results[:max_results]


def search_custom_backend(query: str, repository_id: str | None = None, tool_name: str = "web_search") -> list[dict[str, Any]]:
    config = get_custom_search_config(tool_name)
    if not config.api_url:
        raise ValueError("CUSTOM_SEARCH_API_URL is required. Set it in config.yaml or the environment.")

    repository = _resolve_repository(repository_id, tool_name=tool_name)
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "User-Agent": "DeerFlow-CustomSearch/2.0",
        "jumpCloud-Env": "BASE",
    }
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    response = requests.post(
        config.api_url,
        headers=headers,
        json=_build_payload(query, repository, config.muwp_user),
        timeout=config.timeout,
    )
    response.raise_for_status()
    return _parse_response(response.json(), config.max_results)


@tool("web_search", parse_docstring=True)
def web_search_tool(query: str, repository_id: str | None = None) -> str:
    """Search the web with the custom search backend.

    Args:
        query: The query to search for.
        repository_id: Optional repository id from custom_search.repositories.
    """

    try:
        results = search_custom_backend(query, repository_id=repository_id, tool_name="web_search")
    except requests.RequestException as exc:
        logger.error("Custom search request failed: %s", exc, exc_info=True)
        return f"Error: custom search request failed: {exc}"
    except ValueError as exc:
        return f"Error: {exc}"
    except json.JSONDecodeError as exc:
        logger.error("Custom search returned invalid JSON: %s", exc, exc_info=True)
        return f"Error: custom search returned invalid JSON: {exc}"
    except Exception as exc:
        logger.error("Unexpected custom search error: %s", exc, exc_info=True)
        return f"Error: custom search failed: {exc}"

    return json.dumps(results, indent=2, ensure_ascii=False)


__all__ = [
    "get_custom_search_repository_choices",
    "search_custom_backend",
    "web_search_tool",
]
