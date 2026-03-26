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
    def test_get_vector_search_config_reads_pub_time_range(self, mock_get_app_config):
        mock_get_app_config.return_value = _make_app_config(
            tool_extra={"api_url": "https://example.com/vector-search"},
            vector_search_section={
                "vector_search": {
                    "pubTimeStart": "2024-12-29 00:00:00",
                    "pubTimeEnd": "2025-01-29 23:59:59",
                }
            },
        )

        config = get_vector_search_config()

        assert config.pub_time_start == "2024-12-29 00:00:00"
        assert config.pub_time_end == "2025-01-29 23:59:59"

    @patch("src.config.vector_search_config.get_app_config")
    def test_get_vector_search_config_omits_customized_tag_list_when_not_configured(self, mock_get_app_config):
        mock_get_app_config.return_value = _make_app_config(
            tool_extra={"api_url": "https://example.com/vector-search"},
            vector_search_section={"vector_search": {}},
        )

        config = get_vector_search_config()

        assert config.customized_tag_list is None

    @patch("src.config.vector_search_config.get_app_config")
    def test_get_vector_search_config_keeps_explicit_empty_customized_tag_list(self, mock_get_app_config):
        mock_get_app_config.return_value = _make_app_config(
            tool_extra={"api_url": "https://example.com/vector-search"},
            vector_search_section={"vector_search": {"customizedTagList": []}},
        )

        config = get_vector_search_config()

        assert config.customized_tag_list == []
