from unittest.mock import MagicMock, patch

from src.community.vector_search import tools


class TestVectorSearchTool:
    @patch("src.community.vector_search.tools.logger")
    @patch("src.community.vector_search.tools.requests.post")
    @patch("src.community.vector_search.tools.get_vector_search_config")
    def test_vector_search_tool_includes_pub_time_range(self, mock_get_config, mock_post, mock_logger):
        mock_get_config.return_value = MagicMock(
            api_url="https://example.com/vector-search",
            timeout=20,
            user_code="147852",
            search_type="0",
            vector_top_n=10,
            space_code_list=["SP0000082"],
            caller="P2025094",
            customized_tag_list=["s1"],
            pub_time_start="2024-12-29 00:00:00",
            pub_time_end="2025-01-29 23:59:59",
            headers={"caller": "sjyh"},
            cookies={},
        )
        mock_response = MagicMock()
        mock_response.text = '{"RSP_HEAD":{"TRAN_SUCCESS":"1"}}'
        mock_response.json.return_value = {
            "RSP_HEAD": {"TRAN_SUCCESS": "1"},
            "RSP_BODY": {"result": {"vectorGroupList": []}},
        }
        mock_post.return_value = mock_response

        tools.vector_search_tool.run({"keyword": "测试关键词"})

        _, kwargs = mock_post.call_args
        assert '"pubTimeStart": "2024-12-29 00:00:00"' in kwargs["data"]["REQ_MESSAGE"]
        assert '"pubTimeEnd": "2025-01-29 23:59:59"' in kwargs["data"]["REQ_MESSAGE"]
        mock_logger.info.assert_called_once_with(
            "Vector search raw response body: %s",
            mock_response.text,
        )

    @patch("src.community.vector_search.tools.logger")
    @patch("src.community.vector_search.tools.requests.post")
    @patch("src.community.vector_search.tools.get_vector_search_config")
    def test_vector_search_tool_omits_customized_tag_list_when_not_configured(self, mock_get_config, mock_post, mock_logger):
        mock_get_config.return_value = MagicMock(
            api_url="https://example.com/vector-search",
            timeout=20,
            user_code="147852",
            search_type="0",
            vector_top_n=10,
            space_code_list=["SP0000082"],
            caller="P2025094",
            customized_tag_list=None,
            pub_time_start="2024-12-29 00:00:00",
            pub_time_end="2025-01-29 23:59:59",
            headers={"caller": "sjyh"},
            cookies={},
        )
        mock_response = MagicMock()
        mock_response.text = '{"RSP_HEAD":{"TRAN_SUCCESS":"1"}}'
        mock_response.json.return_value = {
            "RSP_HEAD": {"TRAN_SUCCESS": "1"},
            "RSP_BODY": {"result": {"vectorGroupList": []}},
        }
        mock_post.return_value = mock_response

        tools.vector_search_tool.run({"keyword": "测试关键词"})

        _, kwargs = mock_post.call_args
        assert '"customizedTagList"' not in kwargs["data"]["REQ_MESSAGE"]
        mock_logger.info.assert_called_once_with(
            "Vector search raw response body: %s",
            mock_response.text,
        )

    @patch("src.community.vector_search.tools.logger")
    @patch("src.community.vector_search.tools.requests.post")
    @patch("src.community.vector_search.tools.get_vector_search_config")
    def test_vector_search_tool_keeps_explicit_empty_customized_tag_list(self, mock_get_config, mock_post, mock_logger):
        mock_get_config.return_value = MagicMock(
            api_url="https://example.com/vector-search",
            timeout=20,
            user_code="147852",
            search_type="0",
            vector_top_n=10,
            space_code_list=["SP0000082"],
            caller="P2025094",
            customized_tag_list=[],
            pub_time_start="2024-12-29 00:00:00",
            pub_time_end="2025-01-29 23:59:59",
            headers={"caller": "sjyh"},
            cookies={},
        )
        mock_response = MagicMock()
        mock_response.text = '{"RSP_HEAD":{"TRAN_SUCCESS":"1"}}'
        mock_response.json.return_value = {
            "RSP_HEAD": {"TRAN_SUCCESS": "1"},
            "RSP_BODY": {"result": {"vectorGroupList": []}},
        }
        mock_post.return_value = mock_response

        tools.vector_search_tool.run({"keyword": "测试关键词"})

        _, kwargs = mock_post.call_args
        assert '"customizedTagList": []' in kwargs["data"]["REQ_MESSAGE"]
        mock_logger.info.assert_called_once_with(
            "Vector search raw response body: %s",
            mock_response.text,
        )
