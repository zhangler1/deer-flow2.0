import json
from unittest.mock import MagicMock, patch

import requests

from src.community.online_search import tools


class TestOnlineSearchTool:
    @patch("src.community.online_search.tools.search_custom_backend")
    def test_online_search_tool_uses_fixed_repository(self, mock_search_custom_backend):
        mock_search_custom_backend.return_value = [
            {
                "title": "互联网结果",
                "url": "https://example.com",
                "snippet": "内容",
            }
        ]

        result = tools.online_search_tool.run({"query": "最新行业动态"})

        parsed = json.loads(result)
        assert parsed[0]["title"] == "互联网结果"
        mock_search_custom_backend.assert_called_once_with(
            "最新行业动态",
            repository_id="online-search",
            tool_name="online_search",
        )

    @patch("src.community.online_search.tools.search_custom_backend")
    def test_online_search_tool_returns_error_when_request_fails(self, mock_search_custom_backend):
        mock_search_custom_backend.side_effect = requests.RequestException("network down")

        result = tools.online_search_tool.run({"query": "最新行业动态"})

        assert result.startswith("Error: online search request failed:")

    @patch("src.community.custom_search.tools.requests.post")
    @patch("src.community.custom_search.tools.get_custom_search_config")
    def test_custom_search_backend_accepts_repository_alias(self, mock_get_config, mock_post):
        from src.community.custom_search.tools import search_custom_backend

        mock_get_config.return_value = MagicMock(
            api_url="https://example.com/search",
            api_key="",
            timeout=15,
            max_results=5,
            default_repository="aggregation_search",
            repositories={
                "online_search": MagicMock(
                    id="online_search",
                    name="互联网检索",
                    repository="online-search",
                    channel_id="0",
                )
            },
            muwp_user={"muwp_userID": "132298"},
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"RSP_HEAD": {"TRAN_SUCCESS": "1"}, "RSP_BODY": {"result": []}}
        mock_post.return_value = mock_response

        search_custom_backend("行业趋势", repository_id="online-search", tool_name="online_search")

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["REQ_BODY"]["param"]["repository"] == "online-search"
