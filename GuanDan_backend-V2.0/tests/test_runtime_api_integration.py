import unittest
from unittest.mock import patch

from flask import Flask

from api import dashboard_cache
from api.frontend_api import frontend_api_bp
from services.redis_runtime import RedisRuntimeError


class RuntimeApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(frontend_api_bp)
        self.client = app.test_client()

    def test_dashboard_snapshot_returns_runtime_redis_error(self):
        error = RedisRuntimeError("redis_unavailable", "Redis 不可用")
        with patch(
            "api.frontend_api.get_runtime_dashboard_snapshot",
            side_effect=error,
        ):
            response = self.client.get("/dashboard_snapshot")

        payload = response.get_json()
        self.assertEqual(200, response.status_code)
        self.assertFalse(payload["ok"])
        self.assertEqual("redis_unavailable", payload["error"])
        self.assertEqual("Redis 不可用", payload["message"])
        self.assertEqual({}, payload["data"])

    def test_turns_info_reads_runtime_current_turn(self):
        with patch("api.frontend_api.get_current_turn", return_value="2"):
            response = self.client.get("/TURNsinfo")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"TURN": "2"}, response.get_json())

    def test_turns_info_returns_runtime_redis_error(self):
        error = RedisRuntimeError("redis_unavailable", "Redis 不可用")

        with patch("api.frontend_api.get_current_turn", side_effect=error):
            response = self.client.get("/TURNsinfo")

        payload = response.get_json()
        self.assertEqual(200, response.status_code)
        self.assertFalse(payload["ok"])
        self.assertEqual("redis_unavailable", payload["error"])
        self.assertEqual("Redis 不可用", payload["message"])
        self.assertEqual({}, payload["data"])

    def test_dashboard_snapshot_reads_runtime_view(self):
        snapshot = {
            "TURN": "1",
            "matchesinfo": [[1, "A队", "甲/乙", "B队", "丙/丁"]],
            "scoresinfo": [["A队", "甲/乙", 10]],
            "sumteaminfo": {
                "current_turn": [[1, "A队", 2, 10]],
                "total_until_turn": [[1, "A队", 2, 10]],
            },
            "officescore": {
                "current_turn": [[1, "办公室A", 2, 10]],
                "total_until_turn": [[1, "办公室A", 2, 10]],
            },
            "snapshot_updated_at": "2026-05-16T10:00:00",
        }

        with patch("api.frontend_api.get_current_turn", return_value="1"), patch(
            "api.frontend_api.read_dashboard_view",
            return_value=snapshot,
        ) as read_dashboard_view_mock, patch(
            "api.frontend_api.build_time_message",
            return_value="倒计时未开始",
        ):
            response = self.client.get("/dashboard_snapshot")

        payload = response.get_json()
        self.assertEqual(200, response.status_code)
        self.assertEqual("1", payload["TURN"])
        self.assertEqual("2026-05-16T10:00:00", payload["snapshot_updated_at"])
        self.assertEqual("倒计时未开始", payload["time_message"])
        self.assertEqual(snapshot["matchesinfo"], payload["matchesinfo"])
        read_dashboard_view_mock.assert_called_once_with("1")

    def test_split_endpoints_read_runtime_view(self):
        snapshot = {
            "TURN": "1",
            "time_message": "12:34",
            "matchesinfo": [[1, "A队", "甲/乙", "B队", "丙/丁"]],
            "scoresinfo": [["A队", "甲/乙", 10]],
            "sumteaminfo": {
                "current_turn": [[1, "A队", 2, 10]],
                "total_until_turn": [[1, "A队", 2, 10]],
            },
            "officescore": {
                "current_turn": [[1, "办公室A", 2, 10]],
                "total_until_turn": [[1, "办公室A", 2, 10]],
            },
            "snapshot_updated_at": "2026-05-16T10:00:00",
        }

        with patch(
            "api.frontend_api.get_runtime_dashboard_snapshot",
            return_value=snapshot,
        ):
            matches_response = self.client.get("/matchesinfo")
            scores_response = self.client.get("/scoresinfo")
            sumteam_response = self.client.get("/sumteaminfo")
            officescore_response = self.client.get("/officescore")

        self.assertEqual({"matchesinfo": snapshot["matchesinfo"]}, matches_response.get_json())
        self.assertEqual({"scoresinfo": snapshot["scoresinfo"]}, scores_response.get_json())
        self.assertEqual(snapshot["sumteaminfo"], sumteam_response.get_json())
        self.assertEqual(snapshot["officescore"], officescore_response.get_json())

    def test_split_endpoints_return_runtime_redis_error(self):
        error = RedisRuntimeError("redis_unavailable", "Redis 不可用")

        with patch(
            "api.frontend_api.get_runtime_dashboard_snapshot",
            side_effect=error,
        ):
            response = self.client.get("/matchesinfo")

        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual("redis_unavailable", payload["error"])
        self.assertEqual("Redis 不可用", payload["message"])
        self.assertEqual({}, payload["data"])

    def test_dashboard_cache_runtime_refresh_hooks_are_noop(self):
        def fail_if_called(*args, **kwargs):
            raise AssertionError("old MySQL snapshot fetch should not run")

        with patch(
            "api.dashboard_cache.refresh_dashboard_snapshot_once",
        ) as refresh_mock, patch("api.dashboard_cache.threading.Thread") as thread_mock:
            dashboard_cache.ensure_dashboard_snapshot_fresh(force_refresh=True)
            dashboard_cache.ensure_snapshot_worker_started()

        refresh_mock.assert_not_called()
        thread_mock.assert_not_called()

        with patch(
            "api.dashboard_cache.fetch_matches_by_turn",
            side_effect=fail_if_called,
        ) as matches_mock, patch(
            "api.dashboard_cache.fetch_scores_by_turn",
            side_effect=fail_if_called,
        ) as scores_mock, patch(
            "api.dashboard_cache.fetch_team_rankings",
            side_effect=fail_if_called,
        ) as team_mock, patch(
            "api.dashboard_cache.fetch_office_rankings",
            side_effect=fail_if_called,
        ) as office_mock:
            dashboard_cache.set_turn("1")
            try:
                dashboard_cache.refresh_dashboard_snapshot_once()
            finally:
                dashboard_cache.reset_turn()

        matches_mock.assert_not_called()
        scores_mock.assert_not_called()
        team_mock.assert_not_called()
        office_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
