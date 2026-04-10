import json
import os
from typing import Any


try:
    # 可选依赖：未安装 redis 包时自动降级为“仅本地内存缓存”
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


_redis_client = None


def _build_redis_client():
    """按环境变量创建 Redis 客户端。"""
    if redis is None:
        return None

    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    password = os.getenv("REDIS_PASSWORD") or None
    socket_timeout = float(os.getenv("REDIS_TIMEOUT_SECONDS", "0.5"))

    client = redis.Redis(
        host=host,
        port=port,
        db=db,
        password=password,
        socket_timeout=socket_timeout,
        decode_responses=True,  # 直接返回 str，便于 JSON 处理
    )
    # 先 ping 一次，尽早发现连接不可用，避免业务路径阻塞
    client.ping()
    return client


def get_redis_client():
    """获取 Redis 客户端（懒加载 + 失败降级）。"""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        _redis_client = _build_redis_client()
    except Exception:
        _redis_client = None
    return _redis_client


def _turn_fight_key(turn_num: int) -> str:
    return f"gd:fight_info:turn:{turn_num}"


def read_fight_info_from_redis(turn_num: int):
    """
    读取某轮对阵缓存。
    返回 None 表示 Redis 不可用或缓存未命中。
    """
    client = get_redis_client()
    if client is None:
        return None

    try:
        raw = client.get(_turn_fight_key(turn_num))
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None


def write_fight_info_to_redis(turn_num: int, rows: Any, ttl_seconds: int = 300):
    """
    写入某轮对阵缓存。
    注意：这里存的是“可序列化快照”，不是事务主数据。
    """
    client = get_redis_client()
    if client is None:
        return

    try:
        # JSON 序列化，确保 Redis 存储的是字符串，且支持复杂结构（列表/字典等）
        payload = json.dumps(rows, ensure_ascii=False)

        # 基于键存储值，并定义过期时间，避免缓存雪崩和数据过时问题
        client.setex(_turn_fight_key(turn_num), ttl_seconds, payload)
    except Exception:
        # 缓存写失败不影响主流程
        return


def delete_fight_info_from_redis(turn_num: int):
    """删除某轮对阵缓存。"""
    client = get_redis_client()
    if client is None:
        return
    try:
        client.delete(_turn_fight_key(turn_num))
    except Exception:
        return


def clear_all_fight_cache_in_redis():
    """清空全部对阵缓存键。"""
    client = get_redis_client()
    if client is None:
        return
    try:
        for key in client.scan_iter(match="gd:fight_info:turn:*", count=200):
            client.delete(key)
    except Exception:
        return

