import os

try:
    import redis
except ImportError:
    redis = None


_redis_client = None


class RedisRuntimeError(Exception):
    def __init__(self, code, message, original_error=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.original_error = original_error


def _build_redis_client():
    if redis is None:
        raise RedisRuntimeError("redis_unavailable", "Redis 依赖未安装")

    return redis.Redis(
        host=os.environ.get("REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        db=int(os.environ.get("REDIS_DB", "0")),
        password=os.environ.get("REDIS_PASSWORD") or None,
        socket_timeout=float(os.environ.get("REDIS_TIMEOUT_SECONDS", "0.5")),
        socket_connect_timeout=float(os.environ.get("REDIS_TIMEOUT_SECONDS", "0.5")),
        decode_responses=True,
    )


def require_redis():
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        client = _build_redis_client()
        client.ping()
    except RedisRuntimeError:
        raise
    except Exception as exc:
        raise RedisRuntimeError("redis_unavailable", f"Redis 不可用：{exc}", exc) from exc

    _redis_client = client
    return _redis_client


def reset_redis_client_for_tests():
    global _redis_client
    _redis_client = None


def runtime_error_to_api_payload(exc):
    return {
        "ok": False,
        "error": exc.code,
        "message": exc.message,
        "data": {},
    }
