import unittest

from services import runtime_store
from services.redis_runtime import RedisRuntimeError
from tests.fakes import FakeRedis


class RuntimeStoreTestCase(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.original_require_redis = runtime_store.require_redis
        runtime_store.require_redis = lambda: self.redis

    def tearDown(self):
        runtime_store.require_redis = self.original_require_redis

    def test_get_current_turn_requires_initialized_state(self):
        with self.assertRaises(RedisRuntimeError) as ctx:
            runtime_store.get_current_turn()

        self.assertEqual("redis_not_initialized", ctx.exception.code)

    def test_set_and_get_current_turn_after_initialize(self):
        runtime_store.initialize_empty_state()

        saved = runtime_store.set_current_turn("2")

        self.assertEqual("2", saved)
        self.assertEqual("2", runtime_store.get_current_turn())

    def test_initialize_empty_state_records_blank_loaded_at_and_returns_state(self):
        runtime_store.initialize_empty_state()

        state = runtime_store._require_initialized(self.redis)

        self.assertIs(self.redis.hashes, self.redis.hashs)
        self.assertIn(runtime_store.STATE_KEY, self.redis.hashes)
        self.assertEqual("", state["last_loaded_at"])
        self.assertEqual("1", state["schema_version"])

    def test_write_fights_and_get_match(self):
        runtime_store.initialize_empty_state()

        runtime_store.write_fights(
            1,
            [
                (1, "A队", "张三-李四", "B队", "王五-赵六"),
                (2, "C队", "甲-乙", "D队", "丙-丁"),
            ],
        )

        match = runtime_store.get_match(1, 2)

        self.assertEqual("C队", match["team1_name"])
        self.assertEqual("丙-丁", match["team2_members"])

    def test_runtime_keys_include_turn_namespace(self):
        runtime_store.initialize_empty_state()

        runtime_store.write_mini_teams(1, [{"team_name": "A队"}])
        runtime_store.write_fights(
            1,
            [(1, "A队", "张三-李四", "B队", "王五-赵六")],
        )

        self.assertIn("gd:mini_teams:turn:1", self.redis.values)
        self.assertIn("gd:fights:turn:1", self.redis.values)

    def test_write_teams_and_levels_only_mark_dirty_when_requested(self):
        runtime_store.initialize_empty_state()

        runtime_store.write_teams([{"team_name": "A队"}])
        runtime_store.write_team_levels([{"team_name": "A队", "level": 2}])

        self.assertEqual(
            set(),
            self.redis.smembers(runtime_store.DIRTY_TEAMS_KEY),
        )

        runtime_store.write_teams([{"team_name": "B队"}], mark_dirty=True)
        runtime_store.write_team_levels(
            [{"team_name": "B队", "level": 3}],
            mark_dirty=True,
        )

        self.assertEqual(
            {"teams", "team_levels"},
            self.redis.smembers(runtime_store.DIRTY_TEAMS_KEY),
        )

    def test_apply_score_result_updates_mini_teams_and_marks_dirty(self):
        runtime_store.initialize_empty_state()
        runtime_store.write_mini_teams(
            1,
            [
                {
                    "team_name": "A队",
                    "turn": 1,
                    "big_score": 0,
                    "small_score": 0,
                },
                {
                    "team_name": "B队",
                    "turn": 1,
                    "big_score": 0,
                    "small_score": 0,
                },
            ],
        )
        runtime_store.write_fights(
            1,
            [(1, "A队", "张三-李四", "B队", "王五-赵六")],
        )

        runtime_store.apply_score_result(
            1,
            {"A队": 4, "B队": -4},
            {"A队": 2, "B队": 0},
        )

        rows = {
            row["team_name"]: row
            for row in runtime_store.read_mini_teams(1)
        }
        self.assertEqual(4, rows["A队"]["small_score"])
        self.assertEqual(2, rows["A队"]["big_score"])
        self.assertEqual(-4, rows["B队"]["small_score"])
        self.assertEqual(0, rows["B队"]["big_score"])
        self.assertEqual(
            {"1:A队", "1:B队"},
            self.redis.smembers(runtime_store.DIRTY_SCORE_KEY),
        )

    def test_apply_score_result_ignores_unknown_team_without_dirty_mark(self):
        runtime_store.initialize_empty_state()
        runtime_store.write_mini_teams(
            1,
            [
                {
                    "team_name": "A队",
                    "turn": 1,
                    "big_score": 0,
                    "small_score": 0,
                },
            ],
        )

        runtime_store.apply_score_result(1, {"不存在队": 5}, None)

        rows = runtime_store.read_mini_teams(1)
        self.assertEqual(0, rows[0]["small_score"])
        self.assertEqual(0, rows[0]["big_score"])
        self.assertEqual(
            set(),
            self.redis.smembers(runtime_store.DIRTY_SCORE_KEY),
        )

    def test_apply_score_result_updates_list_mini_team_rows(self):
        runtime_store.initialize_empty_state()
        runtime_store.write_mini_teams(1, [("A队", 1, 0, 0)])

        runtime_store.apply_score_result(1, {"A队": 3}, {"A队": 1})

        rows = runtime_store.read_mini_teams(1)
        self.assertEqual(["A队", 1, 1, 3], rows[0])
        self.assertEqual(
            {"1:A队"},
            self.redis.smembers(runtime_store.DIRTY_SCORE_KEY),
        )

    def test_apply_score_result_accepts_none_big_scores(self):
        runtime_store.initialize_empty_state()
        runtime_store.write_mini_teams(
            1,
            [
                {
                    "team_name": "A队",
                    "turn": 1,
                    "big_score": 0,
                    "small_score": 0,
                },
            ],
        )

        runtime_store.apply_score_result(1, {"A队": 5}, None)

        rows = runtime_store.read_mini_teams(1)
        self.assertEqual(5, rows[0]["small_score"])
        self.assertEqual(0, rows[0]["big_score"])
        self.assertEqual(
            {"1:A队"},
            self.redis.smembers(runtime_store.DIRTY_SCORE_KEY),
        )

    def test_apply_score_result_accepts_none_small_scores(self):
        runtime_store.initialize_empty_state()
        runtime_store.write_mini_teams(
            1,
            [
                {
                    "team_name": "A队",
                    "turn": 1,
                    "big_score": 0,
                    "small_score": 7,
                },
            ],
        )

        runtime_store.apply_score_result(1, None, {"A队": 1})

        rows = runtime_store.read_mini_teams(1)
        self.assertEqual(7, rows[0]["small_score"])
        self.assertEqual(1, rows[0]["big_score"])
        self.assertEqual(
            {"1:A队"},
            self.redis.smembers(runtime_store.DIRTY_SCORE_KEY),
        )


if __name__ == "__main__":
    unittest.main()
