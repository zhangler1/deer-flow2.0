from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from src.config import get_app_config

MISSING = object()

DEFAULT_SPACE_CODE_LIST = ["SP0999999"]
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "User-Agent": os.getenv("VECTOR_SEARCH_USER_AGENT") or os.getenv("PRODUCT_SEARCH_USER_AGENT", "DeerFlow-VectorSearch/2.0"),
}


@dataclass(frozen=True)
class VectorSearchConfig:
    """Resolved vector search configuration."""

    api_url: str
    timeout: int
    page_size: int
    repository: str
    search_type: str
    text_top_n: int
    vector_top_n: int
    space_codes: list[str]
    rerank_flag: int
    channel_id: str
    qa_type: list[int]
    match_fields: list[str]
    know_status: list[str]
    online_status: list[str]
    kp_status: list[str]
    muwp_user: dict[str, str]
    trans_process: str
    tran_id: str
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


def _coerce_int_list(value: Any, default: list[int]) -> list[int]:
    if value is None:
        return list(default)
    if isinstance(value, list):
        items: list[int] = []
        for item in value:
            if item is None:
                continue
            try:
                items.append(int(item))
            except (TypeError, ValueError):
                continue
        return items or list(default)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return list(default)
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return _coerce_int_list(parsed, default)
        items: list[int] = []
        for part in stripped.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                items.append(int(part))
            except ValueError:
                continue
        return items or list(default)
    return list(default)


def _default_muwp_user() -> dict[str, str]:
    return {
        "muwp_branchID": os.getenv("MUWP_BRANCH_ID", "1000027159"),
        "muwp_loginName": os.getenv("MUWP_LOGIN_NAME", "xuew_4"),
        "muwp_userCode": os.getenv("MUWP_USER_CODE", "9743616"),
        "muwp_userName": os.getenv("MUWP_USER_NAME", "薛巍"),
        "muwp_userID": os.getenv("MUWP_USER_ID", "132298"),
    }


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
    page_size_value = tool_extra.get(
        "page_size",
        section.get("page_size", os.getenv("VECTOR_SEARCH_PAGE_SIZE") or os.getenv("PRODUCT_SEARCH_PAGE_SIZE", 10)),
    )
    repository_value = tool_extra.get(
        "repository",
        section.get("repository", os.getenv("VECTOR_SEARCH_REPOSITORY") or os.getenv("PRODUCT_SEARCH_REPOSITORY", "aggregation-search")),
    )
    text_top_n_value = tool_extra.get(
        "text_top_n",
        section.get("text_top_n", os.getenv("VECTOR_SEARCH_TEXT_TOP_N") or os.getenv("PRODUCT_SEARCH_TEXT_TOP_N", 7)),
    )
    vector_top_n_value = tool_extra.get(
        "vector_top_n",
        section.get("vector_top_n", os.getenv("VECTOR_SEARCH_VECTOR_TOP_N") or os.getenv("PRODUCT_SEARCH_VECTOR_TOP_N", 10)),
    )
    space_codes_value = _first_present(
        tool_extra.get("spaceCodes", MISSING),
        tool_extra.get("space_codes", MISSING),
        tool_extra.get("spaceCodeList", MISSING),
        tool_extra.get("space_code_list", MISSING),
        section.get("spaceCodes", MISSING),
        section.get("space_codes", MISSING),
        section.get("spaceCodeList", MISSING),
        section.get("space_code_list", MISSING),
    )
    qa_type_value = _first_present(
        tool_extra.get("qaType", MISSING),
        tool_extra.get("qa_type", MISSING),
        section.get("qaType", MISSING),
        section.get("qa_type", MISSING),
    )
    match_fields_value = _first_present(
        tool_extra.get("matchFields", MISSING),
        tool_extra.get("match_fields", MISSING),
        section.get("matchFields", MISSING),
        section.get("match_fields", MISSING),
    )
    know_status_value = _first_present(
        tool_extra.get("knowStatus", MISSING),
        tool_extra.get("know_status", MISSING),
        section.get("knowStatus", MISSING),
        section.get("know_status", MISSING),
    )
    online_status_value = _first_present(
        tool_extra.get("onlineStatus", MISSING),
        tool_extra.get("online_status", MISSING),
        section.get("onlineStatus", MISSING),
        section.get("online_status", MISSING),
    )
    kp_status_value = _first_present(
        tool_extra.get("kpStatus", MISSING),
        tool_extra.get("kp_status", MISSING),
        section.get("kpStatus", MISSING),
        section.get("kp_status", MISSING),
    )
    muwp_user = _merge_dict_values(
        _default_muwp_user(),
        section.get("muwp_user"),
        tool_extra.get("muwp_user"),
    )

    return VectorSearchConfig(
        api_url=api_url,
        timeout=int(timeout_value),
        page_size=int(page_size_value),
        repository=str(repository_value),
        search_type=str(tool_extra.get("search_type") or section.get("search_type") or os.getenv("VECTOR_SEARCH_SEARCH_TYPE") or os.getenv("PRODUCT_SEARCH_SEARCH_TYPE", "2")),
        text_top_n=int(text_top_n_value),
        vector_top_n=int(vector_top_n_value),
        space_codes=_coerce_str_list(
            space_codes_value,
            DEFAULT_SPACE_CODE_LIST,
        ),
        rerank_flag=int(tool_extra.get("rerank_flag", section.get("rerank_flag", os.getenv("VECTOR_SEARCH_RERANK_FLAG") or os.getenv("PRODUCT_SEARCH_RERANK_FLAG", 1)))),
        channel_id=str(tool_extra.get("channel_id") or section.get("channel_id") or os.getenv("VECTOR_SEARCH_CHANNEL_ID") or os.getenv("PRODUCT_SEARCH_CHANNEL_ID", "0")),
        qa_type=_coerce_int_list(
            qa_type_value,
            [0, 1],
        ),
        match_fields=_coerce_str_list(
            match_fields_value,
            ["title", "content", "attachTitles", "attachContent"],
        ),
        know_status=_coerce_str_list(
            know_status_value,
            ["3", "4"],
        ),
        online_status=_coerce_str_list(
            online_status_value,
            ["3", "4"],
        ),
        kp_status=_coerce_str_list(
            kp_status_value,
            ["3", "4"],
        ),
        muwp_user=muwp_user,
        trans_process=str(tool_extra.get("trans_process") or section.get("trans_process") or ""),
        tran_id=str(tool_extra.get("tran_id") or section.get("tran_id") or ""),
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
