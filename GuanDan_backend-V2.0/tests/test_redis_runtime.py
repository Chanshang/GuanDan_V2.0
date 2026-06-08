import os
import unittest
from unittest.mock import patch

from services import redis_runtime


class TestRedisRuntime(unittest.TestCase):
    def setUp(self):
        redis_runtime.reset_redis_client_for_tests()

    def tearDown(self):
        redis_runtime.reset_redis_client_for_tests()

    def test_require_redis_raises_clear_error_when_package_missing(self):
        with patch.object(redis_runtime, "redis", None):
            with self.assertRaises(redis_runtime.RedisRuntimeError) as ctx:
                redis_runtime.require_redis()

        self.assertEqual("redis_unavailable", ctx.exception.code)
        self.assertIn("Redis", str(ctx.exception))

    def test_require_redis_raises_clear_error_when_ping_fails(self):
        class BrokenRedis:
            def ping(self):
                raise RuntimeError("connection refused")

        with patch.object(redis_runtime, "_build_redis_client", return_value=BrokenRedis()):
            with self.assertRaises(redis_runtime.RedisRuntimeError) as ctx:
                redis_runtime.require_redis()

        self.assertEqual("redis_unavailable", ctx.exception.code)
        self.assertIn("connection refused", ctx.exception.message)
        self.assertIsNone(redis_runtime._redis_client)

    def test_require_redis_wraps_invalid_environment_config(self):
        class FakeRedisModule:
            class Redis:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs

                def ping(self):
                    return True

        with patch.dict(os.environ, {"REDIS_PORT": "bad"}):
            with patch.object(redis_runtime, "redis", FakeRedisModule):
                with self.assertRaises(redis_runtime.RedisRuntimeError) as ctx:
                    redis_runtime.require_redis()

        self.assertEqual("redis_unavailable", ctx.exception.code)
        self.assertTrue(
            "bad" in ctx.exception.message or "invalid literal" in ctx.exception.message
        )
        self.assertIsNone(redis_runtime._redis_client)

    def test_require_redis_returns_cached_client(self):
        class WorkingRedis:
            def __init__(self):
                self.ping_count = 0

            def ping(self):
                self.ping_count += 1
                return True

        working_redis = WorkingRedis()

        with patch.object(redis_runtime, "_build_redis_client", return_value=working_redis):
            first_client = redis_runtime.require_redis()
            second_client = redis_runtime.require_redis()

        self.assertIs(first_client, second_client)
        self.assertEqual(1, first_client.ping_count)

    def test_runtime_error_to_api_payload(self):
        exc = redis_runtime.RedisRuntimeError("redis_not_initialized", "Redis 未初始化")

        payload = redis_runtime.runtime_error_to_api_payload(exc)

        self.assertEqual(
            {
                "ok": False,
                "error": "redis_not_initialized",
                "message": "Redis 未初始化",
                "data": {},
            },
            payload,
        )


if __name__ == "__main__":
    unittest.main()
