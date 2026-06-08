import unittest

from services import runtime_store
from tests.fakes import FakeRedis


class FakeCursor:
    def __init__(self, fail_on_execute=False):
        self.fail_on_execute = fail_on_execute
        self.statements = []
        self.closed = False

    def execute(self, sql, params=None):
        if self.fail_on_execute:
            raise RuntimeError("db down")
        self.statements.append((sql, params))

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, fail_on_execute=False):
        self.cursor_obj = FakeCursor(fail_on_execute=fail_on_execute)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class RuntimeFlushServiceTestCase(unittest.TestCase):
    def setUp(self):
        from services import runtime_flush_service

        self.runtime_flush_service = runtime_flush_service
        self.redis = FakeRedis()
        self.original_store_require_redis = runtime_store.require_redis
        self.original_flush_require_redis = runtime_flush_service.require_redis
        runtime_store.require_redis = lambda: self.redis
        runtime_flush_service.require_redis = lambda: self.redis
        runtime_store.initialize_empty_state()

    def tearDown(self):
        runtime_store.require_redis = self.original_store_require_redis
        self.runtime_flush_service.require_redis = self.original_flush_require_redis
        self.runtime_flush_service._worker_started = False

    def test_flush_once_writes_latest_dirty_scores_and_clears_dirty(self):
        conn = FakeConnection()
        runtime_store.write_mini_teams(
            1,
            [
                {
                    "team_name": "A队",
                    "turn": 1,
                    "big_score": 2,
                    "small_score": 4,
                },
                {
                    "team_name": "B队",
                    "turn": 1,
                    "big_score": 0,
                    "small_score": -4,
                },
            ],
        )
        self.redis.sadd(runtime_store.DIRTY_SCORE_KEY, "1:A队", "1:B队")

        result = self.runtime_flush_service.flush_once(lambda: conn)

        self.assertTrue(result["ok"])
        self.assertTrue(conn.committed)
        self.assertFalse(conn.rolled_back)
        self.assertEqual(4, len(conn.cursor_obj.statements))
        self.assertEqual(set(), self.redis.smembers(runtime_store.DIRTY_SCORE_KEY))
        state = runtime_store.get_state()
        self.assertEqual("ok", state["flush_status"])
        self.assertEqual("", state["flush_error"])

    def test_flush_once_rolls_back_and_keeps_dirty_scores_when_db_down(self):
        conn = FakeConnection(fail_on_execute=True)
        runtime_store.write_mini_teams(
            1,
            [{"team_name": "A队", "turn": 1, "big_score": 2, "small_score": 4}],
        )
        self.redis.sadd(runtime_store.DIRTY_SCORE_KEY, "1:A队")

        result = self.runtime_flush_service.flush_once(lambda: conn)

        self.assertFalse(result["ok"])
        self.assertTrue(conn.rolled_back)
        self.assertFalse(conn.committed)
        self.assertEqual({"1:A队"}, self.redis.smembers(runtime_store.DIRTY_SCORE_KEY))
        state = runtime_store.get_state()
        self.assertEqual("failed", state["flush_status"])
        self.assertIn("db down", state["flush_error"])

    def test_flush_once_writes_dirty_matches_and_clears_dirty(self):
        conn = FakeConnection()
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
                    "team_level_1": 2,
                    "team_level_2": 3,
                }
            ],
        )

        result = self.runtime_flush_service.flush_once(lambda: conn)

        self.assertTrue(result["ok"])
        self.assertEqual(set(), self.redis.smembers(runtime_store.DIRTY_MATCHES_KEY))
        sql_text = "\n".join(sql for sql, _params in conn.cursor_obj.statements)
        self.assertIn("DELETE FROM fight_info", sql_text)
        self.assertIn("INSERT INTO fight_info", sql_text)

    def test_flush_once_fails_for_dirty_teams_without_opening_db(self):
        opened = []
        self.redis.sadd(runtime_store.DIRTY_TEAMS_KEY, "teams")

        result = self.runtime_flush_service.flush_once(
            lambda: opened.append(True),
        )

        self.assertFalse(result["ok"])
        self.assertEqual([], opened)
        self.assertEqual({"teams"}, self.redis.smembers(runtime_store.DIRTY_TEAMS_KEY))
        state = runtime_store.get_state()
        self.assertEqual("failed", state["flush_status"])
        self.assertIn("teams", state["flush_error"])

    def test_flush_once_cleans_malformed_score_dirty_after_valid_commit(self):
        conn = FakeConnection()
        runtime_store.write_mini_teams(
            1,
            [{"team_name": "A队", "turn": 1, "big_score": 2, "small_score": 4}],
        )
        self.redis.sadd(
            runtime_store.DIRTY_SCORE_KEY,
            "1:A队",
            "bad:A队",
            "1",
            "",
        )

        result = self.runtime_flush_service.flush_once(lambda: conn)

        self.assertTrue(result["ok"])
        self.assertTrue(conn.committed)
        self.assertFalse(conn.rolled_back)
        self.assertEqual(2, len(conn.cursor_obj.statements))
        self.assertEqual(set(), self.redis.smembers(runtime_store.DIRTY_SCORE_KEY))

    def test_flush_once_keeps_unknown_team_dirty_score(self):
        conn = FakeConnection()
        runtime_store.write_mini_teams(
            1,
            [{"team_name": "A队", "turn": 1, "big_score": 2, "small_score": 4}],
        )
        self.redis.sadd(runtime_store.DIRTY_SCORE_KEY, "1:不存在队")

        result = self.runtime_flush_service.flush_once(lambda: conn)

        self.assertTrue(result["ok"])
        self.assertTrue(conn.committed)
        self.assertEqual(0, len(conn.cursor_obj.statements))
        self.assertEqual(
            {"1:不存在队"},
            self.redis.smembers(runtime_store.DIRTY_SCORE_KEY),
        )

    def test_flush_once_cleans_malformed_match_dirty_after_valid_commit(self):
        conn = FakeConnection()
        runtime_store.write_fights(
            1,
            [(1, "A队", "张三-李四", "B队", "王五-赵六", 1, 2, 3)],
        )
        self.redis.sadd(runtime_store.DIRTY_MATCHES_KEY, "bad", "")

        result = self.runtime_flush_service.flush_once(lambda: conn)

        self.assertTrue(result["ok"])
        self.assertTrue(conn.committed)
        self.assertEqual(set(), self.redis.smembers(runtime_store.DIRTY_MATCHES_KEY))
        sql_text = "\n".join(sql for sql, _params in conn.cursor_obj.statements)
        self.assertIn("DELETE FROM fight_info", sql_text)
        self.assertIn("INSERT INTO fight_info", sql_text)

    def test_flush_once_writes_tuple_fight_insert_params(self):
        conn = FakeConnection()
        runtime_store.write_fights(
            1,
            [(1, "A队", "张三-李四", "B队", "王五-赵六", 1, 2, 3)],
        )

        result = self.runtime_flush_service.flush_once(lambda: conn)

        self.assertTrue(result["ok"])
        insert_params = conn.cursor_obj.statements[1][1]
        self.assertEqual(1, insert_params[0])
        self.assertIn("A队", insert_params)
        self.assertIn("B队", insert_params)
        self.assertEqual(1, insert_params[5])

    def test_flush_once_skips_locked_flush_without_opening_db(self):
        opened = []
        self.redis.sadd(runtime_store.DIRTY_SCORE_KEY, "1:A队")
        self.redis.setnx(self.runtime_flush_service.FLUSH_LOCK_KEY, "held")

        result = self.runtime_flush_service.flush_once(lambda: opened.append(True))

        self.assertTrue(result["ok"])
        self.assertEqual("locked", result["skipped"])
        self.assertEqual([], opened)
        self.assertEqual({"1:A队"}, self.redis.smembers(runtime_store.DIRTY_SCORE_KEY))

    def test_ensure_runtime_flush_worker_started_is_idempotent(self):
        starts = []
        created = []
        original_thread = self.runtime_flush_service.threading.Thread

        class FakeThread:
            def __init__(self, target, args, daemon):
                self.target = target
                self.args = args
                self.daemon = daemon
                created.append(self)

            def start(self):
                starts.append(self)

        try:
            self.runtime_flush_service._worker_started = False
            self.runtime_flush_service.threading.Thread = FakeThread

            first = self.runtime_flush_service.ensure_runtime_flush_worker_started(
                lambda: None,
            )
            second = self.runtime_flush_service.ensure_runtime_flush_worker_started(
                lambda: None,
            )
        finally:
            self.runtime_flush_service.threading.Thread = original_thread
            self.runtime_flush_service._worker_started = False

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(1, len(starts))
        self.assertEqual(1, len(created))
        self.assertTrue(created[0].daemon)


if __name__ == "__main__":
    unittest.main()
