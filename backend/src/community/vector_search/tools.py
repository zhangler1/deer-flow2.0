from __future__ import annotations

import json
import logging
from typing import Any

import requests
from langchain.tools import tool

from src.config.vector_search_config import VectorSearchConfig, get_vector_search_config

logger = logging.getLogger(__name__)


def _build_request_body(keyword: str, config: VectorSearchConfig) -> dict[str, Any]:
    param = {
        "keyword": keyword,
        "userCode": config.user_code,
        "searchType": config.search_type,
        "qaType": [0],
        "vectorTopN": config.vector_top_n,
        "spaceCodeList": config.space_code_list,
        "caller": config.caller,
    }
    if config.customized_tag_list is not None:
        param["customizedTagList"] = config.customized_tag_list
    if config.pub_time_start:
        param["pubTimeStart"] = config.pub_time_start
    if config.pub_time_end:
        param["pubTimeEnd"] = config.pub_time_end

    return {
        "REQ_HEAD": {},
        "REQ_BODY": {
            "param": param
        },
    }


def _extract_entry_info(entry: dict[str, Any]) -> str:
    title = str(entry.get("paraTitle") or "无标题")
    content = str(entry.get("content") or "")
    score_raw = entry.get("score")
    rerank_score_raw = entry.get("rerankScore")

    try:
        score = float(score_raw) if score_raw not in (None, "") else 0.0
    except (TypeError, ValueError):
        score = 0.0

    info = f"名称: {title}\n匹配度: {score:.4f}"

    try:
        if rerank_score_raw not in (None, ""):
            info += f"\n重排序得分: {float(rerank_score_raw):.4f}"
    except (TypeError, ValueError):
        info += f"\n重排序得分: {rerank_score_raw}"

    if content:
        shortened_content = content if len(content) <= 300 else f"{content[:300]}..."
        info += f"\n详情:\n{shortened_content}"

    return info


def _extract_results(payload: dict[str, Any], keyword: str) -> str:
    response_head = payload.get("RSP_HEAD", {})
    if response_head and response_head.get("TRAN_SUCCESS") != "1":
        return f"API返回错误: {response_head.get('PROCESS_STATUS_CODE', '未知错误')}"

    result_data = payload.get("RSP_BODY", {}).get("result", {})
    vector_list = result_data.get("vectorGroupList", [])
    text_list = result_data.get("textGroupList", [])
    all_entries = vector_list if vector_list else text_list

    if not all_entries:
        return f"未找到相关内容。关键词: {keyword}"

    entry_infos = [f"【结果 {index}】\n{_extract_entry_info(entry)}" for index, entry in enumerate(all_entries, start=1)]
    summary = (
        "查询成功！\n"
        f"关键词: {keyword}\n"
        f"返回数量: {len(all_entries)}\n\n"
        f"{'=' * 80}\n\n"
    )
    separator = f"\n\n{'-' * 80}\n\n"
    return summary + separator.join(entry_infos)


def search_vector_backend(keyword: str, tool_name: str = "vector_search") -> str:
    config = get_vector_search_config(tool_name)
    if not config.api_url:
        raise ValueError("VECTOR_SEARCH_API_URL, PRODUCT_SEARCH_API_URL, or EUVD_API_URL is required. Set it in config.yaml or the environment.")

    response = requests.post(
        config.api_url,
        headers=config.headers,
        cookies=config.cookies,
        data={"REQ_MESSAGE": json.dumps(_build_request_body(keyword, config), ensure_ascii=False)},
        timeout=config.timeout,
    )
    response.raise_for_status()
    logger.info("Vector search raw response body: %s", response.text)

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(f"vector search returned invalid JSON: {exc}") from exc

    return _extract_results(payload, keyword)


@tool("vector_search", parse_docstring=True)
def vector_search_tool(keyword: str) -> str:
    """Search structured knowledge in the dedicated internal knowledge backend.

    Prefer this tool when the user is asking for internal or domain-specific knowledge
    instead of general web information. In particular, use this tool first when the
    request mentions "交通银行", "交行", or phrases like "搜索交通银行xxx", "查询交通银行xxx",
    "了解交通银行xxx", especially for products, policies, procedures, knowledge base entries,
    FAQs, internal topics, or other structured enterprise content. If the user is
    clearly asking for public internet information, use web search instead.

    Args:
        keyword: Search keyword for the internal knowledge base, such as a bank entity
            name, topic, product, policy, procedure, region, customer segment, or a
            combined query like "交通银行 理财产品" or "交行 信用卡 积分规则".
    """

    try:
        return search_vector_backend(keyword)
    except requests.Timeout:
        logger.error("Vector search request timed out.", exc_info=True)
        return "Error: vector search request timed out."
    except requests.RequestException as exc:
        logger.error("Vector search request failed: %s", exc, exc_info=True)
        return f"Error: vector search request failed: {exc}"
    except ValueError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        logger.error("Unexpected vector search error: %s", exc, exc_info=True)
        return f"Error: vector search failed: {exc}"


__all__ = ["vector_search_tool", "search_vector_backend"]
