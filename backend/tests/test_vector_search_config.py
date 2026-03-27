from unittest.mock import MagicMock, patch

from src.config.vector_search_config import get_vector_search_config


def _make_app_config(tool_extra=None, vector_search_section=None):
    config = MagicMock()
    tool_config = MagicMock()
    tool_config.model_extra = tool_extra or {}
    config.get_tool_config.return_value = tool_config
    config.model_extra = vector_search_section or {}
    return config


class TestVectorSearchConfig:
    @patch("src.config.vector_search_config.get_app_config")
    def test_get_vector_search_config_reads_new_request_fields(self, mock_get_app_config):
        mock_get_app_config.return_value = _make_app_config(
            tool_extra={"api_url": "https://example.com/vector-search"},
            vector_search_section={
                "vector_search": {
                    "page_size": 10,
                    "repository": "aggregation-search",
                    "search_type": "2",
                    "text_top_n": 7,
                    "vector_top_n": 10,
                    "spaceCodes": ["SP0999999"],
                    "rerank_flag": 1,
                    "channel_id": "0",
                    "qaType": [0, 1],
                    "matchFields": ["title", "content"],
                    "knowStatus": ["3", "4"],
                    "onlineStatus": ["3", "4"],
                    "kpStatus": ["3", "4"],
                    "trans_process": "demo-process",
                    "tran_id": "demo-tran-id",
                    "muwp_user": {
                        "muwp_userCode": "9743616",
                        "muwp_userName": "薛巍",
                    },
                }
            },
        )

        config = get_vector_search_config()

        assert config.page_size == 10
        assert config.repository == "aggregation-search"
        assert config.search_type == "2"
        assert config.text_top_n == 7
        assert config.vector_top_n == 10
        assert config.space_codes == ["SP0999999"]
        assert config.rerank_flag == 1
        assert config.channel_id == "0"
        assert config.qa_type == [0, 1]
        assert config.match_fields == ["title", "content"]
        assert config.know_status == ["3", "4"]
        assert config.online_status == ["3", "4"]
        assert config.kp_status == ["3", "4"]
        assert config.trans_process == "demo-process"
        assert config.tran_id == "demo-tran-id"
        assert config.muwp_user["muwp_userCode"] == "9743616"
        assert config.muwp_user["muwp_userName"] == "薛巍"

    @patch("src.config.vector_search_config.get_app_config")
    def test_get_vector_search_config_accepts_legacy_space_code_list_alias(self, mock_get_app_config):
        mock_get_app_config.return_value = _make_app_config(
            tool_extra={"api_url": "https://example.com/vector-search"},
            vector_search_section={"vector_search": {"spaceCodeList": ["SP0000082"]}},
        )

        config = get_vector_search_config()

        assert config.space_codes == ["SP0000082"]

    @patch("src.config.vector_search_config.get_app_config")
    def test_get_vector_search_config_uses_default_qa_type_when_not_configured(self, mock_get_app_config):
        mock_get_app_config.return_value = _make_app_config(
            tool_extra={"api_url": "https://example.com/vector-search"},
            vector_search_section={"vector_search": {}},
        )

        config = get_vector_search_config()

        assert config.qa_type == [0, 1]
