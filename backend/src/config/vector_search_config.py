from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from src.config import get_app_config

MISSING = object()

DEFAULT_SPACE_CODE_LIST = ["SP0000082"]
DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "User-Agent": os.getenv("VECTOR_SEARCH_USER_AGENT") or os.getenv("PRODUCT_SEARCH_USER_AGENT", "DeerFlow-VectorSearch/2.0"),
    "caller": os.getenv("VECTOR_SEARCH_HEADER_CALLER") or os.getenv("PRODUCT_SEARCH_HEADER_CALLER", "sjyh"),
    "jumpcloud-ENV": os.getenv("VECTOR_SEARCH_JUMPCLOUD_ENV") or os.getenv("PRODUCT_SEARCH_JUMPCLOUD_ENV", "BASE"),
}


@dataclass(frozen=True)
class VectorSearchConfig:
    """Resolved vector search configuration."""

    api_url: str
    timeout: int
    user_code: str
    search_type: str
    vector_top_n: int
    space_code_list: list[str]
    caller: str
    customized_tag_list: list[str] | None
    pub_time_start: str
    pub_time_end: str
    headers: dict[str, str]
    cookies: dict[str, str]


def _get_vector_search_section() -> dict[str, Any]:
    app_config = get_app_config()
    if app_config.model_extra is None:
        return {}

    for key in ("vector_search", "VECTOR_SEARCH", "product_search", "PRODUCT_SEARCH"):
        section = app_config.model_extra.get(key)
        if isinstance(section, dict):
            return section
    return {}


def _get_tool_extra(tool_name: str) -> dict[str, Any]:
    tool_config = get_app_config().get_tool_config(tool_name)
    if tool_config is None or tool_config.model_extra is None:
        return {}
    return dict(tool_config.model_extra)


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


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not MISSING:
            return value
    return None


def _coerce_str_list(value: Any, default: list[str], allow_empty: bool = False) -> list[str]:
    if value is None:
        return list(default)
    if isinstance(value, list):
        items = [str(item) for item in value if item is not None]
        if items:
            return items
        return [] if allow_empty else list(default)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return list(default)
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            items = [str(item) for item in parsed if item is not None]
            if items:
                return items
            return [] if allow_empty else list(default)
        return [item.strip() for item in stripped.split(",") if item.strip()] or list(default)
    return list(default)


def _coerce_optional_str_list(value: Any, allow_empty: bool = False) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        items = [str(item) for item in value if item is not None]
        if items:
            return items
        return [] if allow_empty else None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            items = [str(item) for item in parsed if item is not None]
            if items:
                return items
            return [] if allow_empty else None
        split_items = [item.strip() for item in stripped.split(",") if item.strip()]
        return split_items or None
    return None


def get_vector_search_config(tool_name: str = "vector_search") -> VectorSearchConfig:
    """Resolve the vector search config from tool config, top-level config, and env vars."""

    section = _get_vector_search_section()
    tool_extra = _get_tool_extra(tool_name)

    api_url = str(
        tool_extra.get("api_url")
        or section.get("api_url")
        or os.getenv("VECTOR_SEARCH_API_URL")
        or os.getenv("PRODUCT_SEARCH_API_URL")
        or os.getenv("EUVD_API_URL", "")
    )
    timeout_value = tool_extra.get(
        "timeout",
        section.get("timeout", os.getenv("VECTOR_SEARCH_TIMEOUT") or os.getenv("PRODUCT_SEARCH_TIMEOUT", 30)),
    )
    vector_top_n_value = tool_extra.get(
        "vector_top_n",
        section.get("vector_top_n", os.getenv("VECTOR_SEARCH_VECTOR_TOP_N") or os.getenv("PRODUCT_SEARCH_VECTOR_TOP_N", 10)),
    )
    space_code_list_value = _first_present(
        tool_extra.get("spaceCodeList", MISSING),
        tool_extra.get("space_code_list", MISSING),
        section.get("spaceCodeList", MISSING),
        section.get("space_code_list", MISSING),
    )
    customized_tag_list_value = _first_present(
        tool_extra.get("customizedTagList", MISSING),
        tool_extra.get("customized_tag_list", MISSING),
        section.get("customizedTagList", MISSING),
        section.get("customized_tag_list", MISSING),
    )
    pub_time_start_value = _first_present(
        tool_extra.get("pubTimeStart", MISSING),
        tool_extra.get("pub_time_start", MISSING),
        section.get("pubTimeStart", MISSING),
        section.get("pub_time_start", MISSING),
        os.getenv("VECTOR_SEARCH_PUB_TIME_START"),
        os.getenv("PRODUCT_SEARCH_PUB_TIME_START"),
    )
    pub_time_end_value = _first_present(
        tool_extra.get("pubTimeEnd", MISSING),
        tool_extra.get("pub_time_end", MISSING),
        section.get("pubTimeEnd", MISSING),
        section.get("pub_time_end", MISSING),
        os.getenv("VECTOR_SEARCH_PUB_TIME_END"),
        os.getenv("PRODUCT_SEARCH_PUB_TIME_END"),
    )

    return VectorSearchConfig(
        api_url=api_url,
        timeout=int(timeout_value),
        user_code=str(tool_extra.get("user_code") or section.get("user_code") or os.getenv("VECTOR_SEARCH_USER_CODE") or os.getenv("PRODUCT_SEARCH_USER_CODE", "147852")),
        search_type=str(tool_extra.get("search_type") or section.get("search_type") or os.getenv("VECTOR_SEARCH_SEARCH_TYPE") or os.getenv("PRODUCT_SEARCH_SEARCH_TYPE", "0")),
        vector_top_n=int(vector_top_n_value),
        space_code_list=_coerce_str_list(
            space_code_list_value,
            DEFAULT_SPACE_CODE_LIST,
        ),
        caller=str(tool_extra.get("caller") or section.get("caller") or os.getenv("VECTOR_SEARCH_CALLER") or os.getenv("PRODUCT_SEARCH_CALLER", "P2025094")),
        customized_tag_list=_coerce_optional_str_list(
            customized_tag_list_value,
            allow_empty=True,
        ),
        pub_time_start=str(pub_time_start_value or ""),
        pub_time_end=str(pub_time_end_value or ""),
        headers=_merge_dict_values(
            DEFAULT_HEADERS,
            section.get("headers"),
            tool_extra.get("headers"),
        ),
        cookies=_merge_dict_values(
            section.get("cookies"),
            tool_extra.get("cookies"),
        ),
    )


__all__ = ["VectorSearchConfig", "get_vector_search_config"]
