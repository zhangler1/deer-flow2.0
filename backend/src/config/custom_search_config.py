from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from src.config import get_app_config

DEFAULT_REPOSITORY_ID = "aggregation_search"


@dataclass(frozen=True)
class CustomSearchRepositoryConfig:
    """Repository configuration for the custom search backend."""

    id: str
    name: str
    description: str
    repository: str
    channel_id: str = "0"


@dataclass(frozen=True)
class CustomSearchConfig:
    """Resolved custom search configuration."""

    api_url: str
    api_key: str
    timeout: int
    max_results: int
    default_repository: str
    repositories: dict[str, CustomSearchRepositoryConfig]
    muwp_user: dict[str, str]


def _get_custom_search_section() -> dict[str, Any]:
    app_config = get_app_config()
    if app_config.model_extra is None:
        return {}

    for key in ("custom_search", "CUSTOM_SEARCH"):
        section = app_config.model_extra.get(key)
        if isinstance(section, dict):
            return section
    return {}


def _get_tool_extra(tool_name: str) -> dict[str, Any]:
    tool_config = get_app_config().get_tool_config(tool_name)
    if tool_config is None or tool_config.model_extra is None:
        return {}
    return dict(tool_config.model_extra)


def _default_repositories() -> dict[str, CustomSearchRepositoryConfig]:
    repositories = [
        CustomSearchRepositoryConfig(
            id="aggregation_search",
            name="聚合搜索",
            description="聚合多个数据源的搜索服务",
            repository="aggregation-search",
            channel_id="0",
        ),
        CustomSearchRepositoryConfig(
            id="vector_search",
            name="向量库",
            description="基于向量相似度的搜索服务",
            repository="euvd-searchByChannelId",
            channel_id="0",
        ),
        CustomSearchRepositoryConfig(
            id="dynamic_search",
            name="交行知道",
            description="交通银行内部知识库搜索",
            repository="okic-dynamicSearch",
            channel_id="0",
        ),
        CustomSearchRepositoryConfig(
            id="online_search",
            name="互联网检索",
            description="互联网公开信息搜索服务",
            repository="online-search",
            channel_id="0",
        ),
    ]
    return {repository.id: repository for repository in repositories}


def _parse_repositories(raw_repositories: Any) -> dict[str, CustomSearchRepositoryConfig]:
    if not isinstance(raw_repositories, dict) or not raw_repositories:
        return _default_repositories()

    repositories: dict[str, CustomSearchRepositoryConfig] = {}
    for repository_id, raw_repository in raw_repositories.items():
        if not isinstance(raw_repository, dict):
            continue
        repositories[str(repository_id)] = CustomSearchRepositoryConfig(
            id=str(repository_id),
            name=str(raw_repository.get("name", repository_id)),
            description=str(raw_repository.get("description", "")),
            repository=str(raw_repository.get("repository", repository_id)),
            channel_id=str(raw_repository.get("channel_id", "0")),
        )

    return repositories or _default_repositories()


def _default_muwp_user() -> dict[str, str]:
    return {
        "muwp_branchID": os.getenv("MUWP_BRANCH_ID", "1000027159"),
        "muwp_loginName": os.getenv("MUWP_LOGIN_NAME", "xuew_4"),
        "muwp_userCode": os.getenv("MUWP_USER_CODE", "9743616"),
        "muwp_userName": os.getenv("MUWP_USER_NAME", "薛巍"),
        "muwp_userID": os.getenv("MUWP_USER_ID", "132298"),
    }


def _merge_dict_values(*values: Any) -> dict[str, str]:
    merged: dict[str, str] = {}
    for value in values:
        if not isinstance(value, dict):
            continue
        for key, item in value.items():
            if item is None:
                continue
            merged[str(key)] = str(item)
    return merged


def get_custom_search_config(tool_name: str = "web_search") -> CustomSearchConfig:
    """Resolve the custom search config from tool config, top-level config, and env vars."""

    section = _get_custom_search_section()
    tool_extra = _get_tool_extra(tool_name)

    repositories = _parse_repositories(tool_extra.get("repositories") or section.get("repositories"))
    default_repository = str(tool_extra.get("default_repository") or section.get("default_repository") or DEFAULT_REPOSITORY_ID)

    api_url = str(tool_extra.get("api_url") or section.get("api_url") or os.getenv("CUSTOM_SEARCH_API_URL", ""))
    api_key = str(tool_extra.get("api_key") or section.get("api_key") or os.getenv("CUSTOM_SEARCH_API_KEY", ""))

    timeout_value = tool_extra.get("timeout", section.get("timeout", 30))
    max_results_value = tool_extra.get("max_results", section.get("max_results", 5))
    timeout = int(timeout_value)
    max_results = int(max_results_value)

    muwp_user = _merge_dict_values(
        _default_muwp_user(),
        section.get("muwp_user"),
        tool_extra.get("muwp_user"),
    )

    return CustomSearchConfig(
        api_url=api_url,
        api_key=api_key,
        timeout=timeout,
        max_results=max_results,
        default_repository=default_repository,
        repositories=repositories,
        muwp_user=muwp_user,
    )


def get_custom_search_repository_choices() -> list[dict[str, str]]:
    """Return the configured repository choices for UI or debugging."""

    config = get_custom_search_config()
    return [
        {
            "id": repository.id,
            "name": repository.name,
            "description": repository.description,
            "repository": repository.repository,
            "channel_id": repository.channel_id,
        }
        for repository in config.repositories.values()
    ]
