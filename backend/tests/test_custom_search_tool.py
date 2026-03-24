import json
from unittest.mock import MagicMock, patch

import requests

from src.community.custom_search import tools
from src.config.custom_search_config import get_custom_search_config


def _make_app_config(tool_extra=None, custom_search_section=None):
    config = MagicMock()
    tool_config = MagicMock()
    tool_config.model_extra = tool_extra or {}
    config.get_tool_config.return_value = tool_config
    config.model_extra = custom_search_section or {}
    return config


class TestCustomSearchTool:
    @patch("src.config.custom_search_config.get_app_config")
    def test_get_custom_search_config_uses_top_level_repositories(self, mock_get_app_config):
        mock_get_app_config.return_value = _make_app_config(
            tool_extra={"api_url": "https://example.com/search"},
            custom_search_section={
                "custom_search": {
                    "default_repository": "aggregation_search",
                    "repositories": {
                        "aggregation_search": {
                            "name": "聚合搜索",
                            "description": "聚合多个数据源的搜索服务",
                            "repository": "aggregation-search",
                            "channel_id": "8",
                        }
                    },
                }
            },
        )

        config = get_custom_search_config()

        assert config.api_url == "https://example.com/search"
        assert config.default_repository == "aggregation_search"
        assert config.repositories["aggregation_search"].channel_id == "8"

    @patch("src.community.custom_search.tools.requests.post")
    @patch("src.community.custom_search.tools.get_custom_search_config")
    def test_web_search_tool_success(self, mock_get_config, mock_post):
        mock_get_config.return_value = MagicMock(
            api_url="https://example.com/search",
            api_key="secret",
            timeout=15,
            max_results=2,
            default_repository="dynamic_search",
            repositories={
                "dynamic_search": MagicMock(
                    id="dynamic_search",
                    name="交行知道",
                    repository="okic-dynamicSearch",
                    channel_id="0",
                )
            },
            muwp_user={"muwp_userID": "132298"},
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "RSP_HEAD": {"TRAN_SUCCESS": "1"},
            "RSP_BODY": {
                "result": [
                    {
                        "title": "结果二",
                        "content": "内容二",
                        "score": "0.1",
                        "url": "https://example.com/2",
                    },
                    {
                        "title": "结果一",
                        "content": "内容一",
                        "score": "0.9",
                        "url": "https://example.com/1",
                    },
                ]
            },
        }
        mock_post.return_value = mock_response

        result = tools.web_search_tool.run({"query": "测试查询"})

        parsed = json.loads(result)
        assert [item["title"] for item in parsed] == ["结果一", "结果二"]
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer secret"
        assert kwargs["json"]["REQ_BODY"]["param"]["repository"] == "okic-dynamicSearch"
        assert kwargs["json"]["REQ_BODY"]["param"]["messages"][0]["content"] == "测试查询"

    @patch("src.community.custom_search.tools.requests.post")
    @patch("src.community.custom_search.tools.get_custom_search_config")
    def test_web_search_tool_supports_repository_override(self, mock_get_config, mock_post):
        mock_get_config.return_value = MagicMock(
            api_url="https://example.com/search",
            api_key="",
            timeout=15,
            max_results=5,
            default_repository="dynamic_search",
            repositories={
                "dynamic_search": MagicMock(
                    id="dynamic_search",
                    name="交行知道",
                    repository="okic-dynamicSearch",
                    channel_id="0",
                ),
                "aggregation_search": MagicMock(
                    id="aggregation_search",
                    name="聚合搜索",
                    repository="aggregation-search",
                    channel_id="9",
                ),
            },
            muwp_user={"muwp_userID": "132298"},
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"RSP_HEAD": {"TRAN_SUCCESS": "1"}, "RSP_BODY": {"result": []}}
        mock_post.return_value = mock_response

        tools.web_search_tool.run({"query": "测试查询", "repository_id": "aggregation_search"})

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["REQ_BODY"]["param"]["repository"] == "aggregation-search"
        assert kwargs["json"]["REQ_BODY"]["param"]["param"]["channelId"] == "9"

    @patch("src.community.custom_search.tools.requests.post")
    @patch("src.community.custom_search.tools.get_custom_search_config")
    def test_web_search_tool_returns_error_when_request_fails(self, mock_get_config, mock_post):
        mock_get_config.return_value = MagicMock(
            api_url="https://example.com/search",
            api_key="",
            timeout=15,
            max_results=5,
            default_repository="dynamic_search",
            repositories={
                "dynamic_search": MagicMock(
                    id="dynamic_search",
                    name="交行知道",
                    repository="okic-dynamicSearch",
                    channel_id="0",
                )
            },
            muwp_user={"muwp_userID": "132298"},
        )
        mock_post.side_effect = requests.RequestException("network down")

        result = tools.web_search_tool.run({"query": "测试查询"})

        assert result.startswith("Error: custom search request failed:")

    @patch("src.community.custom_search.tools.get_custom_search_config")
    def test_web_search_tool_requires_api_url(self, mock_get_config):
        mock_get_config.return_value = MagicMock(
            api_url="",
            api_key="",
            timeout=15,
            max_results=5,
            default_repository="dynamic_search",
            repositories={
                "dynamic_search": MagicMock(
                    id="dynamic_search",
                    name="交行知道",
                    repository="okic-dynamicSearch",
                    channel_id="0",
                )
            },
            muwp_user={"muwp_userID": "132298"},
        )

        result = tools.web_search_tool.run({"query": "测试查询"})

        assert result == "Error: CUSTOM_SEARCH_API_URL is required. Set it in config.yaml or the environment."
