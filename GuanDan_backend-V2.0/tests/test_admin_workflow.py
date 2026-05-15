import unittest

import services.admin_workflow as admin_workflow
from services.admin_workflow import (
    api_error,
    api_success,
    build_score_error,
    find_match_info,
    parse_table_number,
)


class TestAdminWorkflow(unittest.TestCase):
    def setUp(self):
        self._patched = {}

    def tearDown(self):
        for name, value in self._patched.items():
            setattr(admin_workflow, name, value)

    def patch_workflow(self, name, value):
        self._patched[name] = getattr(admin_workflow, name)
        setattr(admin_workflow, name, value)

    def test_api_success_returns_json_friendly_payload(self):
        self.assertEqual(
            api_success("完成", {"turn": "1"}),
            {"ok": True, "message": "完成", "data": {"turn": "1"}},
        )
        self.assertEqual(api_success("完成")["data"], {})

    def test_api_error_returns_json_friendly_payload(self):
        self.assertEqual(
            api_error("invalid_turn", "当前轮次未设置"),
            {
                "ok": False,
                "error": "invalid_turn",
                "message": "当前轮次未设置",
                "data": {},
            },
        )
        self.assertEqual(api_error("invalid_turn", "当前轮次未设置")["data"], {})

    def test_get_overview_returns_planned_overview_payload(self):
        self.patch_workflow("get_turn", lambda: "2")
        self.patch_workflow("build_time_message", lambda: "12:34")
        self.patch_workflow("get_snapshot_copy", lambda: {"updated_at": 123.45})
        self.patch_workflow("fetch_team_info_rows", lambda get_db_connection: [("A队",)])
        self.patch_workflow("fetch_all_fights", lambda get_db_connection: [(1,)])

        result = admin_workflow.get_overview(object())

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["data"],
            {
                "turn": "2",
                "time_message": "12:34",
                "teams": [("A队",)],
                "has_matches": True,
                "snapshot_updated_at": 123.45,
            },
        )

    def test_parse_table_number_accepts_only_valid_table_range(self):
        self.assertEqual(parse_table_number("3"), 3)
        self.assertIsNone(parse_table_number("0"))
        self.assertIsNone(parse_table_number("abc"))

    def test_find_match_info_returns_table_payload(self):
        fights = [("1", "A队", "张三、李四", "B队", "王五、赵六")]

        match_info = find_match_info(fights, 1)

        self.assertEqual(match_info["team1_name"], "A队")
        self.assertEqual(match_info["team2_members"], "王五、赵六")
        self.assertIsNone(find_match_info(fights, 2))

    def test_build_score_error_normalizes_known_score_errors(self):
        self.assertEqual(
            build_score_error("未选择最终局赢家"),
            "winner_required_when_tied",
        )
        self.assertEqual(
            build_score_error("winner_required_when_tied"),
            "winner_required_when_tied",
        )
        self.assertEqual(build_score_error("得分未输入"), "score_invalid")

    def test_get_all_matches_uses_matches_data_key(self):
        self.patch_workflow(
            "fetch_all_fights_with_scores",
            lambda get_db_connection: [{"table_no": 1, "team1_small_score": 4}],
        )

        result = admin_workflow.get_all_matches(object())

        self.assertEqual(
            result["data"],
            {"matches": [{"table_no": 1, "team1_small_score": 4}]},
        )

    def test_generate_matches_failure_uses_single_error_code(self):
        self.patch_workflow("fetch_match_generation_source", lambda get_db_connection: ([], []))
        self.patch_workflow(
            "generate_round_pairs",
            lambda teams, levels, rounds: {"success": False, "error": "unable_to_match"},
        )

        result = admin_workflow.generate_matches_workflow(object())

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "match_generation_failed")

    def test_generate_matches_save_failure_uses_single_error_code(self):
        self.patch_workflow("fetch_match_generation_source", lambda get_db_connection: ([], []))
        self.patch_workflow(
            "generate_round_pairs",
            lambda teams, levels, rounds: {
                "success": True,
                "pairs": [],
                "team_members": {},
                "team_levels": {},
            },
        )
        self.patch_workflow(
            "replace_fight_info",
            lambda get_db_connection, pairs, team_members, team_levels: {
                "ok": False,
                "error": "db_failed",
            },
        )

        result = admin_workflow.generate_matches_workflow(object())

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "match_generation_failed")

    def test_timer_success_payload_includes_time_message(self):
        self.patch_workflow("start_round_timer", lambda: True)
        self.patch_workflow("stop_round_timer", lambda: None)
        self.patch_workflow("build_time_message", lambda: "59:59")

        self.assertEqual(
            admin_workflow.start_timer_value()["data"],
            {"time_message": "59:59"},
        )
        self.assertEqual(
            admin_workflow.stop_timer_value()["data"],
            {"time_message": "59:59"},
        )

    def test_set_turn_value_empty_values_clear_turn_successfully(self):
        calls = []
        self.patch_workflow("reset_turn", lambda: calls.append("reset"))
        self.patch_workflow("set_current_turn", lambda turn: calls.append(("set", turn)))
        self.patch_workflow("mark_snapshot_stale", lambda: calls.append("stale"))
        self.patch_workflow("get_turn", lambda: "null")
        self.patch_workflow("is_valid_turn", lambda turn: turn in {"1", "2", "3"})

        for value in (None, "", "null"):
            result = admin_workflow.set_turn_value(value)
            self.assertTrue(result["ok"])
            self.assertEqual(result["data"], {"turn": "null"})

        self.assertEqual(calls.count("reset"), 3)


if __name__ == "__main__":
    unittest.main()
