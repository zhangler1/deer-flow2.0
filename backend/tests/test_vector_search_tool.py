from unittest.mock import MagicMock, patch

from src.community.vector_search import tools


class TestVectorSearchTool:
    @patch("src.community.vector_search.tools.logger")
    @patch("src.community.vector_search.tools.requests.post")
    @patch("src.community.vector_search.tools.get_vector_search_config")
    def test_vector_search_tool_sends_new_json_payload(self, mock_get_config, mock_post, mock_logger):
        mock_get_config.return_value = MagicMock(
            api_url="https://example.com/vector-search",
            timeout=20,
            page_size=10,
            repository="aggregation-search",
            search_type="2",
            text_top_n=7,
            vector_top_n=10,
            space_codes=["SP0999999"],
            rerank_flag=1,
            channel_id="0",
            qa_type=[0, 1],
            match_fields=["title", "content", "attachTitles", "attachContent"],
            know_status=["3", "4"],
            online_status=["3", "4"],
            kp_status=["3", "4"],
            muwp_user={
                "muwp_branchID": "1000027159",
                "muwp_loginName": "xuew_4",
                "muwp_userCode": "9743616",
                "muwp_userName": "薛巍",
                "muwp_userID": "132298",
            },
            trans_process="",
            tran_id="",
            headers={"Content-Type": "application/json"},
            cookies={},
        )
        mock_response = MagicMock()
        mock_response.text = '{"RSP_HEAD":{"TRAN_SUCCESS":"1"}}'
        mock_response.json.return_value = {
            "RSP_HEAD": {"TRAN_SUCCESS": "1"},
            "RSP_BODY": {"result": []},
        }
        mock_post.return_value = mock_response

        tools.vector_search_tool.run({"keyword": "测试关键词"})

        _, kwargs = mock_post.call_args
        assert kwargs["json"] == {
            "REQ_HEAD": {
                "TRANS_PROCESS": "",
                "TRAN_ID": "",
            },
            "REQ_BODY": {
                "param": {
                    "summaryQuestion": "测试关键词",
                    "pageSize": 10,
                    "repository": "aggregation-search",
                    "param": {
                        "searchType": "2",
                        "spaceCodes": ["SP0999999"],
                        "rerankFlag": 1,
                        "channelId": "0",
                        "textTopN": 7,
                        "vectorTopN": 10,
                        "qaType": [0, 1],
                        "matchFields": ["title", "content", "attachTitles", "attachContent"],
                        "knowStatus": ["3", "4"],
                        "onlineStatus": ["3", "4"],
                        "kpStatus": ["3", "4"],
                    },
                },
                "muwpUser": {
                    "muwp_branchID": "1000027159",
                    "muwp_loginName": "xuew_4",
                    "muwp_userCode": "9743616",
                    "muwp_userName": "薛巍",
                    "muwp_userID": "132298",
                },
            },
        }
        assert "data" not in kwargs
        mock_logger.info.assert_called_once_with(
            "Vector search raw response body: %s",
            mock_response.text,
        )

    @patch("src.community.vector_search.tools.logger")
    @patch("src.community.vector_search.tools.requests.post")
    @patch("src.community.vector_search.tools.get_vector_search_config")
    def test_vector_search_tool_formats_new_result_list(self, mock_get_config, mock_post, mock_logger):
        mock_get_config.return_value = MagicMock(
            api_url="https://example.com/vector-search",
            timeout=20,
            page_size=10,
            repository="aggregation-search",
            search_type="2",
            text_top_n=7,
            vector_top_n=10,
            space_codes=["SP0999999"],
            rerank_flag=1,
            channel_id="0",
            qa_type=[0, 1],
            match_fields=["title", "content", "attachTitles", "attachContent"],
            know_status=["3", "4"],
            online_status=["3", "4"],
            kp_status=["3", "4"],
            muwp_user={},
            trans_process="",
            tran_id="",
            headers={"Content-Type": "application/json"},
            cookies={},
        )
        mock_response = MagicMock()
        mock_response.text = '{"RSP_HEAD":{"TRAN_SUCCESS":"1"}}'
        mock_response.json.return_value = {
            "RSP_HEAD": {"TRAN_SUCCESS": "1"},
            "RSP_BODY": {
                "result": [
                    {
                        "title": "深圳分行积分大派送活动（2025年7月1日至2026年4月30日）",
                        "content": "活动期间，当月发薪≥3000元的代发客户，单人每月可领取600积分奖励。",
                        "score": "0.9142907",
                        "repository": "euvd-searchKnowledgeStandard",
                        "docId": "FILE755211519706821",
                        "url": "https://example.com/doc/1",
                    }
                ]
            },
        }
        mock_post.return_value = mock_response

        result = tools.vector_search_tool.run({"keyword": "深圳分行特邀活动的奖励是什么"})

        assert "查询成功！" in result
        assert "返回数量: 1" in result
        assert "名称: 深圳分行积分大派送活动（2025年7月1日至2026年4月30日）" in result
        assert "匹配度: 0.9143" in result
        assert "知识库: euvd-searchKnowledgeStandard" in result
        assert "文档ID: FILE755211519706821" in result
        assert "链接: https://example.com/doc/1" in result
        assert "600积分奖励" in result
        mock_logger.info.assert_called_once_with(
            "Vector search raw response body: %s",
            mock_response.text,
        )
