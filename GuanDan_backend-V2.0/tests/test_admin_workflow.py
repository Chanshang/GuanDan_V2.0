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
            if value is _MISSING:
                delattr(admin_workflow, name)
            else:
                setattr(admin_workflow, name, value)

    def patch_workflow(self, name, value):
        self._patched[name] = getattr(admin_workflow, name, _MISSING)
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

    def test_get_overview_rebuilds_runtime_view_before_returning(self):
        overview = {"turn": "2", "time_message": "12:34", "teams": [{"team_name": "A队"}]}
        calls = []
        self.patch_workflow("rebuild_admin_overview_view", lambda: calls.append("rebuild") or overview)
        self.patch_workflow("read_admin_overview_view", lambda: calls.append("read"))

        result = admin_workflow.get_overview(object())

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], overview)
        self.assertEqual(calls, ["rebuild"])

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

    def test_get_all_matches_reads_runtime_view(self):
        matches_view = {"matches": [{"table_no": 1, "team1_small_score": 4}]}
        calls = []
        self.patch_workflow("read_admin_matches_view", lambda: calls.append("matches") or matches_view)

        result = admin_workflow.get_all_matches(object())

        self.assertEqual(result["data"], matches_view)
        self.assertEqual(calls, ["matches"])

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
        calls = []
        self.patch_workflow("runtime_start_round_timer", lambda: calls.append("start") or True)
        self.patch_workflow("runtime_stop_round_timer", lambda: calls.append("stop"))
        self.patch_workflow("runtime_build_time_message", lambda: "59:59")
        self.patch_workflow("runtime_get_current_turn", lambda: "2")
        self.patch_workflow("rebuild_dashboard_view", lambda turn: calls.append(("dashboard", turn)))
        self.patch_workflow("rebuild_admin_overview_view", lambda: calls.append("overview"))

        self.assertEqual(
            admin_workflow.start_timer_value()["data"],
            {"time_message": "59:59"},
        )
        self.assertEqual(
            admin_workflow.stop_timer_value()["data"],
            {"time_message": "59:59"},
        )
        self.assertEqual(
            calls,
            [
                "start",
                ("dashboard", 2),
                "overview",
                "stop",
                ("dashboard", 2),
                "overview",
            ],
        )

    def test_start_timer_value_uses_runtime_timer_and_rebuilds_views(self):
        calls = []

        def fail_old_timer():
            raise AssertionError("old timer must not run")

        self.patch_workflow("start_round_timer", fail_old_timer)
        self.patch_workflow("runtime_start_round_timer", lambda: calls.append("runtime_start") or True)
        self.patch_workflow("runtime_build_time_message", lambda: "59:59")
        self.patch_workflow("runtime_get_current_turn", lambda: "2")
        self.patch_workflow("rebuild_dashboard_view", lambda turn: calls.append(("dashboard", turn)))
        self.patch_workflow("rebuild_admin_overview_view", lambda: calls.append("overview"))

        result = admin_workflow.start_timer_value()

        self.assertTrue(result["ok"])
        self.assertEqual({"time_message": "59:59"}, result["data"])
        self.assertEqual(calls, ["runtime_start", ("dashboard", 2), "overview"])

    def test_set_turn_value_writes_runtime_turn_and_rebuilds_overview(self):
        calls = []
        self.patch_workflow("runtime_set_current_turn", lambda turn: calls.append(("set", turn)) or turn)
        self.patch_workflow("rebuild_dashboard_view", lambda turn: calls.append(("dashboard", turn)))
        self.patch_workflow("rebuild_admin_overview_view", lambda: calls.append("rebuild"))

        for value in (None, "", "null"):
            result = admin_workflow.set_turn_value(value)
            self.assertTrue(result["ok"])
            self.assertEqual(result["data"], {"turn": "null"})

        result = admin_workflow.set_turn_value("2")

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], {"turn": "2"})
        self.assertEqual(
            calls,
            [
                ("set", "null"),
                "rebuild",
                ("set", "null"),
                "rebuild",
                ("set", "null"),
                "rebuild",
                ("set", "2"),
                ("dashboard", 2),
                "rebuild",
            ],
        )

    def test_set_turn_value_rejects_invalid_turn_before_runtime_write(self):
        calls = []

        def reject_invalid_turn(turn):
            calls.append(("set", turn))
            raise ValueError("invalid_turn")

        self.patch_workflow("runtime_set_current_turn", reject_invalid_turn)
        self.patch_workflow("rebuild_admin_overview_view", lambda: calls.append("rebuild"))

        result = admin_workflow.set_turn_value("4")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "invalid_turn")
        self.assertEqual(calls, [("set", "4")])

    def test_get_match_for_score_reads_runtime_match_without_mysql_fallbacks(self):
        def fail(*args, **kwargs):
            raise AssertionError("MySQL fallback must not be called")

        self.patch_workflow("check_match_exists", fail)
        self.patch_workflow(
            "runtime_get_match",
            lambda turn, table: {
                "table_num": table,
                "team1_name": "A队",
                "team1_members": "张三、李四",
                "team2_name": "B队",
                "team2_members": "王五、赵六",
                "turn_num": turn,
            },
        )

        result = admin_workflow.get_match_for_score(object(), fail, "2", "3")

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["turn_num"], 2)
        self.assertEqual(result["data"]["table_num"], 3)

    def test_get_match_for_current_turn_reads_runtime_current_turn(self):
        def fail(*args, **kwargs):
            raise AssertionError("dashboard cache current turn must not be called")

        self.patch_workflow("get_turn", fail)
        self.patch_workflow("is_valid_turn", fail)
        self.patch_workflow("runtime_get_current_turn", lambda: "2")
        self.patch_workflow(
            "runtime_get_match",
            lambda turn, table: {
                "table_num": table,
                "team1_name": "A队",
                "team1_members": "张三、李四",
                "team2_name": "B队",
                "team2_members": "王五、赵六",
                "turn_num": turn,
            },
        )

        result = admin_workflow.get_match_for_current_turn(object(), fail, "3")

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["turn_num"], 2)
        self.assertEqual(result["data"]["table_num"], 3)

    def test_submit_score_for_current_turn_reads_runtime_current_turn(self):
        def fail(*args, **kwargs):
            raise AssertionError("dashboard cache current turn must not be called")

        calls = []
        self.patch_workflow("get_turn", fail)
        self.patch_workflow("is_valid_turn", fail)
        self.patch_workflow("runtime_get_current_turn", lambda: "3")
        self.patch_workflow(
            "submit_score",
            lambda get_db_connection, load_fight_info, turn, table, score_x, score_y, winner: calls.append(
                (turn, table, score_x, score_y, winner)
            )
            or api_success("得分已提交"),
        )

        result = admin_workflow.submit_score_for_current_turn(object(), fail, "5", "8", "6", "")

        self.assertTrue(result["ok"])
        self.assertEqual(calls, [("3", "5", "8", "6", "")])

    def test_get_match_for_score_invalid_inputs_do_not_read_runtime_or_mysql(self):
        def fail(*args, **kwargs):
            raise AssertionError("match lookup must not be called")

        self.patch_workflow("runtime_get_match", fail)
        self.patch_workflow("check_match_exists", fail)

        invalid_turn = admin_workflow.get_match_for_score(object(), fail, "4", "3")
        invalid_table = admin_workflow.get_match_for_score(object(), fail, "2", "abc")

        self.assertFalse(invalid_turn["ok"])
        self.assertEqual(invalid_turn["error"], "invalid_turn")
        self.assertFalse(invalid_table["ok"])
        self.assertEqual(invalid_table["error"], "invalid_table")

    def test_submit_score_applies_runtime_result_and_marks_dashboard_dirty(self):
        calls = []

        def fail(*args, **kwargs):
            raise AssertionError("old score writeback path must not be called")

        self.patch_workflow(
            "runtime_get_match",
            lambda turn, table: {
                "table_num": table,
                "team1_name": "A队",
                "team1_members": "张三、李四",
                "team2_name": "B队",
                "team2_members": "王五、赵六",
                "turn_num": turn,
            },
        )
        self.patch_workflow(
            "build_score_update",
            lambda **kwargs: {
                "ok": True,
                "small_scores": {"A队": 10, "B队": 8},
                "big_scores": {"A队": 2, "B队": 0},
            },
        )
        self.patch_workflow(
            "runtime_apply_score_result",
            lambda turn, small, big: calls.append(("runtime_apply", turn, small, big)) or {"ok": True},
        )
        self.patch_workflow("runtime_mark_dashboard_dirty", lambda turn: calls.append(("dirty", turn)))
        self.patch_workflow("save_score_log", lambda *args: calls.append(("log", args)))
        self.patch_workflow("is_writeback_enabled", fail)
        self.patch_workflow("enqueue_score_update", fail)
        self.patch_workflow("apply_score_update", fail)

        result = admin_workflow.submit_score(object(), fail, "2", "3", "10", "8", "")

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["data"],
            {"turn_num": 2, "table_num": 3, "queued": True, "snapshot_dirty": True},
        )
        self.assertEqual(calls[0][0], "runtime_apply")
        self.assertEqual(calls[1][0], "log")
        self.assertEqual(calls[2], ("dirty", 2))

    def test_submit_score_reset_clears_both_team_scores(self):
        calls = []

        self.patch_workflow(
            "runtime_get_match",
            lambda turn, table: {
                "table_num": table,
                "team1_name": "A队",
                "team1_members": "张三、李四",
                "team2_name": "B队",
                "team2_members": "王五、赵六",
                "turn_num": turn,
            },
        )
        self.patch_workflow(
            "runtime_apply_score_result",
            lambda turn, small, big: calls.append(("runtime_apply", turn, small, big)) or {"ok": True},
        )
        self.patch_workflow("runtime_mark_dashboard_dirty", lambda turn: calls.append(("dirty", turn)))
        self.patch_workflow("save_score_log", lambda *args: calls.append(("log", args)))

        result = admin_workflow.submit_score(
            object(),
            lambda *args: None,
            "2",
            "3",
            "",
            "",
            "",
            reset=True,
        )

        self.assertTrue(result["ok"])
        self.assertEqual("得分已重置", result["message"])
        self.assertEqual(
            calls[0],
            (
                "runtime_apply",
                2,
                {"A队": 0, "B队": 0},
                {"A队": 0, "B队": 0},
            ),
        )
        self.assertEqual(calls[2], ("dirty", 2))

    def test_submit_score_validation_failure_has_no_runtime_side_effects(self):
        def fail(*args, **kwargs):
            raise AssertionError("score failure must not write, rebuild, or log")

        self.patch_workflow(
            "runtime_get_match",
            lambda turn, table: {
                "table_num": table,
                "team1_name": "A队",
                "team1_members": "张三、李四",
                "team2_name": "B队",
                "team2_members": "王五、赵六",
                "turn_num": turn,
            },
        )
        self.patch_workflow("build_score_update", lambda **kwargs: {"ok": False, "error": "score_invalid"})
        self.patch_workflow("runtime_apply_score_result", fail)
        self.patch_workflow("runtime_mark_dashboard_dirty", fail)
        self.patch_workflow("save_score_log", fail)

        result = admin_workflow.submit_score(object(), fail, "2", "3", "40", "8", "")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "score_invalid")

    def test_submit_score_runtime_apply_error_bubbles_without_log_or_rebuild(self):
        calls = []

        def fail(*args, **kwargs):
            raise AssertionError("log or rebuild must not be called after apply failure")

        def raise_runtime_error(*args):
            calls.append("runtime_apply")
            raise RuntimeError("redis failed")

        self.patch_workflow(
            "runtime_get_match",
            lambda turn, table: {
                "table_num": table,
                "team1_name": "A队",
                "team1_members": "张三、李四",
                "team2_name": "B队",
                "team2_members": "王五、赵六",
                "turn_num": turn,
            },
        )
        self.patch_workflow(
            "build_score_update",
            lambda **kwargs: {
                "ok": True,
                "small_scores": {"A队": 10, "B队": 8},
                "big_scores": {"A队": 2, "B队": 0},
            },
        )
        self.patch_workflow("runtime_apply_score_result", raise_runtime_error)
        self.patch_workflow("save_score_log", fail)
        self.patch_workflow("runtime_mark_dashboard_dirty", fail)

        with self.assertRaises(RuntimeError):
            admin_workflow.submit_score(object(), fail, "2", "3", "10", "8", "")

        self.assertEqual(calls, ["runtime_apply"])

    def test_submit_score_dirty_mark_error_bubbles_after_log(self):
        calls = []

        def raise_dirty_error(turn):
            calls.append(("dirty", turn))
            raise RuntimeError("dirty failed")

        self.patch_workflow(
            "runtime_get_match",
            lambda turn, table: {
                "table_num": table,
                "team1_name": "A队",
                "team1_members": "张三、李四",
                "team2_name": "B队",
                "team2_members": "王五、赵六",
                "turn_num": turn,
            },
        )
        self.patch_workflow(
            "build_score_update",
            lambda **kwargs: {
                "ok": True,
                "small_scores": {"A队": 10, "B队": 8},
                "big_scores": {"A队": 2, "B队": 0},
            },
        )
        self.patch_workflow("runtime_apply_score_result", lambda *args: calls.append("runtime_apply"))
        self.patch_workflow("save_score_log", lambda *args: calls.append("log"))
        self.patch_workflow("runtime_mark_dashboard_dirty", raise_dirty_error)

        with self.assertRaises(RuntimeError):
            admin_workflow.submit_score(object(), lambda *args: None, "2", "3", "10", "8", "")

        self.assertEqual(
            calls,
            ["runtime_apply", "log", ("dirty", 2)],
        )

    def test_load_runtime_does_not_overwrite_patched_globals_in_same_group(self):
        sentinel = object()
        self.patch_workflow("read_admin_overview_view", sentinel)
        self.patch_workflow("read_admin_matches_view", None)

        admin_workflow._load_runtime(("read_admin_matches_view",))

        self.assertIs(admin_workflow.read_admin_overview_view, sentinel)
        self.assertIsNotNone(admin_workflow.read_admin_matches_view)


_MISSING = object()


if __name__ == "__main__":
    unittest.main()
