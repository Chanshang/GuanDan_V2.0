import unittest
from unittest.mock import patch

from flask import Flask

from api.admin_api import admin_api_bp
from api.score_api import score_api_bp


class TestAdminScoreApi(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["GUANDAN_GET_DB_CONNECTION"] = lambda: "db"
        self.app.config["GUANDAN_UPLOAD_DIR"] = "uploads"
        self.app.config["GUANDAN_CLEAR_FIGHT_CACHE"] = lambda: None
        self.app.config["GUANDAN_LOAD_FIGHT_INFO"] = lambda turn: []
        self.app.register_blueprint(admin_api_bp)
        self.app.register_blueprint(score_api_bp)
        self.client = self.app.test_client()

    def test_score_current_turn_returns_invalid_turn_when_turn_is_null(self):
        with patch(
            "api.score_api.workflow.runtime_get_current_turn",
            return_value=None,
        ):
            response = self.client.get("/api/score/current-turn")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ok"], False)
        self.assertEqual(response.get_json()["error"], "invalid_turn")

    def test_score_current_turn_reads_runtime_turn(self):
        with patch(
            "api.score_api.workflow.runtime_get_current_turn",
            return_value="2",
        ):
            response = self.client.get("/api/score/current-turn")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "ok": True,
                "message": "当前轮次加载成功",
                "data": {"turn": "2"},
            },
        )

    def test_admin_overview_returns_workflow_payload_unchanged(self):
        payload = {"ok": True, "message": "ok", "data": {"turn": "1"}}

        with patch("api.admin_api.workflow.get_overview", return_value=payload) as get_overview:
            response = self.client.get("/api/admin/overview")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), payload)
        get_overview.assert_called_once()
        self.assertEqual(get_overview.call_args.args[0](), "db")

    def test_score_table_returns_workflow_payload_unchanged(self):
        payload = {"ok": True, "message": "ok", "data": {"table_num": 1}}

        with patch(
            "api.score_api.workflow.get_match_for_current_turn",
            return_value=payload,
        ) as get_match:
            response = self.client.get("/api/score/table?table=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), payload)
        get_match.assert_called_once()
        self.assertEqual(get_match.call_args.args[0](), "db")
        self.assertEqual(get_match.call_args.args[2], "1")

    def test_admin_scores_passes_reset_flag_to_workflow(self):
        payload = {"ok": True, "message": "得分已重置", "data": {}}

        with patch("api.admin_api.workflow.submit_score", return_value=payload) as submit_score:
            response = self.client.post(
                "/api/admin/scores",
                json={"turn": "2", "table": "3", "reset": True},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), payload)
        self.assertEqual(submit_score.call_args.args[0](), "db")
        self.assertEqual(submit_score.call_args.args[2:7], ("2", "3", None, None, None))
        self.assertTrue(submit_score.call_args.kwargs["reset"])


if __name__ == "__main__":
    unittest.main()
