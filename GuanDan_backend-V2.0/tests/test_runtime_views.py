import unittest

from services import runtime_store, runtime_views
from tests.fakes import FakeRedis


class RuntimeViewsTestCase(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.original_store_require_redis = runtime_store.require_redis
        self.original_views_require_redis = runtime_views.require_redis
        runtime_store.require_redis = lambda: self.redis
        runtime_views.require_redis = lambda: self.redis

        runtime_store.initialize_empty_state()
        runtime_store.set_current_turn(1)
        runtime_store.write_teams(
            [
                {
                    "team_name": "A队",
                    "member_name": "张三-李四",
                    "office": "一办",
                },
                {
                    "team_name": "B队",
                    "member_name": "王五-赵六",
                    "office": "二办",
                },
            ],
        )
        runtime_store.write_team_levels(
            [
                {"team_name": "A队", "level": 5},
                {"team_name": "B队", "level": 4},
            ],
        )
        runtime_store.write_mini_teams(
            1,
            [
                {
                    "team_name": "A队",
                    "turn": 1,
                    "big_score": 2,
                    "small_score": 4,
                    "office": "一办",
                    "member_name": "张三-李四",
                },
                {
                    "team_name": "B队",
                    "turn": 1,
                    "big_score": 0,
                    "small_score": -4,
                    "office": "二办",
                    "member_name": "王五-赵六",
                },
            ],
        )
        runtime_store.write_fights(
            1,
            [
                {
                    "id": 1,
                    "team_name_1": "A队",
                    "members_1": "张三-李四",
                    "team_name_2": "B队",
                    "members_2": "王五-赵六",
                    "turn": 1,
                },
            ],
        )

    def tearDown(self):
        runtime_store.require_redis = self.original_store_require_redis
        runtime_views.require_redis = self.original_views_require_redis

    def test_build_dashboard_view(self):
        view = runtime_views.rebuild_dashboard_view(1)

        self.assertEqual("1", view["TURN"])
        self.assertEqual(1, len(view["matchesinfo"]))
        self.assertEqual(
            (1, "A队", "张三-李四", "B队", "王五-赵六", 5, 4),
            view["matchesinfo"][0],
        )
        self.assertEqual("A队", view["scoresinfo"][0][0])
        self.assertEqual("A队", view["sumteaminfo"]["current_turn"][0][1])
        self.assertIn("total_until_turn", view["sumteaminfo"])
        self.assertIn("total_until_turn", view["officescore"])

    def test_build_admin_matches_view_includes_scores(self):
        view = runtime_views.rebuild_admin_matches_view()

        match = view["matches"][0]
        self.assertEqual("A队", match["team_name_1"])
        self.assertEqual(2, match["team1_big_score"])
        self.assertEqual(-4, match["team2_small_score"])

    def test_rebuild_all_views_writes_to_redis(self):
        runtime_views.rebuild_all_views()

        dashboard = runtime_views.read_dashboard_view(1)
        overview = runtime_views.read_admin_overview_view()
        matches = runtime_views.read_admin_matches_view()
        create_table = runtime_views.read_create_table_view()

        self.assertEqual("1", dashboard["TURN"])
        self.assertEqual("1", overview["turn"])
        self.assertIs(True, overview["has_matches"])
        self.assertIn("matches", matches)
        self.assertEqual(
            [
                {
                    "team": {
                        "team_name": "A队",
                        "turn": 1,
                        "big_score": 2,
                        "small_score": 4,
                        "office": "一办",
                        "member_name": "张三-李四",
                    },
                    "fight_id": 1,
                },
                {
                    "team": {
                        "team_name": "B队",
                        "turn": 1,
                        "big_score": 0,
                        "small_score": -4,
                        "office": "二办",
                        "member_name": "王五-赵六",
                    },
                    "fight_id": 1,
                },
            ],
            create_table["rows"],
        )

    def test_read_missing_view_keys_returns_default_shapes(self):
        self.redis = FakeRedis()
        runtime_store.require_redis = lambda: self.redis
        runtime_views.require_redis = lambda: self.redis

        self.assertEqual(
            {"matches": []},
            runtime_views.read_admin_matches_view(),
        )
        self.assertEqual(
            {"rows": []},
            runtime_views.read_create_table_view(),
        )

    def test_admin_overview_keeps_null_turn_string(self):
        runtime_store.set_current_turn(None)

        overview = runtime_views.rebuild_admin_overview_view()

        self.assertEqual("null", overview["turn"])

    def test_admin_overview_flattens_team_info_rows_for_vue_table(self):
        self.redis = FakeRedis()
        runtime_store.require_redis = lambda: self.redis
        runtime_views.require_redis = lambda: self.redis
        runtime_store.initialize_empty_state()
        runtime_store.write_teams(
            [
                {
                    "id": 1,
                    "office": "702",
                    "team_name_1": "702-A",
                    "members_1": "张三-李四",
                    "team_name_2": "702-B",
                    "members_2": "王五-赵六",
                    "team_name_3": "702-C",
                    "members_3": "空",
                    "team_name_4": "702-D",
                    "members_4": "甲-乙",
                }
            ]
        )
        runtime_store.write_team_levels(
            [
                {"team_name": "702-A", "level": "A"},
                {"team_name": "702-B", "level": "B"},
                {"team_name": "702-D", "level": "C"},
            ]
        )

        overview = runtime_views.rebuild_admin_overview_view()

        self.assertEqual(
            [
                {
                    "team_name": "702-A",
                    "members": "张三-李四",
                    "office": "702",
                    "level": "A",
                },
                {
                    "team_name": "702-B",
                    "members": "王五-赵六",
                    "office": "702",
                    "level": "B",
                },
                {
                    "team_name": "702-D",
                    "members": "甲-乙",
                    "office": "702",
                    "level": "C",
                },
            ],
            overview["teams"],
        )

    def test_dashboard_total_rankings_include_previous_turns(self):
        self.redis = FakeRedis()
        runtime_store.require_redis = lambda: self.redis
        runtime_views.require_redis = lambda: self.redis
        runtime_store.initialize_empty_state()
        for turn, small_score in ((1, 4), (2, 6)):
            runtime_store.write_mini_teams(
                turn,
                [
                    {
                        "team_name": "A队",
                        "turn": turn,
                        "big_score": 2,
                        "small_score": small_score,
                        "office": "一办",
                        "member_name": "张三-李四",
                    }
                ],
            )

        dashboard = runtime_views.rebuild_dashboard_view(2)

        self.assertEqual(
            [(1, "A队", 2, 6)],
            dashboard["sumteaminfo"]["current_turn"],
        )
        self.assertEqual(
            [(1, "A队", 4, 10)],
            dashboard["sumteaminfo"]["total_until_turn"],
        )
        self.assertEqual(
            [(1, "一办", 4, 10)],
            dashboard["officescore"]["total_until_turn"],
        )

    def test_list_mini_team_rows_do_not_use_turn_as_member_name(self):
        self.redis = FakeRedis()
        runtime_store.require_redis = lambda: self.redis
        runtime_views.require_redis = lambda: self.redis
        runtime_store.initialize_empty_state()
        runtime_store.set_current_turn(1)
        runtime_store.write_team_levels(
            [
                ("A队", 5),
                ("B队", 4),
            ],
        )
        runtime_store.write_mini_teams(
            1,
            [
                ("A队", 1, 2, 4),
                ("B队", 1, 0, -4),
            ],
        )
        runtime_store.write_fights(
            1,
            [
                (1, "A队", "张三-李四", "B队", "王五-赵六"),
            ],
        )

        dashboard = runtime_views.rebuild_dashboard_view(1)
        admin_matches = runtime_views.rebuild_admin_matches_view()

        self.assertEqual("A队", dashboard["scoresinfo"][0][0])
        self.assertNotEqual(1, dashboard["scoresinfo"][0][1])
        self.assertEqual(
            (1, "A队", "张三-李四", "B队", "王五-赵六", 5, 4),
            dashboard["matchesinfo"][0],
        )
        match = admin_matches["matches"][0]
        self.assertEqual(2, match["team1_big_score"])
        self.assertEqual(4, match["team1_small_score"])
        self.assertEqual(0, match["team2_big_score"])
        self.assertEqual(-4, match["team2_small_score"])

    def test_rebuild_all_views_writes_empty_dashboards_for_turns_two_and_three(self):
        runtime_views.rebuild_all_views()

        turn_2 = runtime_views.read_dashboard_view(2)
        turn_3 = runtime_views.read_dashboard_view(3)

        self.assertEqual("2", turn_2["TURN"])
        self.assertEqual([], turn_2["matchesinfo"])
        self.assertEqual([], turn_2["scoresinfo"])
        self.assertEqual("3", turn_3["TURN"])
        self.assertEqual([], turn_3["matchesinfo"])
        self.assertEqual([], turn_3["scoresinfo"])


if __name__ == "__main__":
    unittest.main()
