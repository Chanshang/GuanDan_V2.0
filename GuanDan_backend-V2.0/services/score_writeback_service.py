import json
import os
import threading
import time

from services.score_service import apply_score_updates_batch
from services.redis_cache_service import get_redis_client

WRITEBACK_ENABLED = os.getenv("SCORE_WRITEBACK_ENABLED", "1") == "1"
WRITEBACK_BATCH_SIZE = int(os.getenv("SCORE_WRITEBACK_BATCH_SIZE", "50"))
WRITEBACK_FLUSH_INTERVAL = float(os.getenv("SCORE_WRITEBACK_FLUSH_INTERVAL", "1.5"))
WRITEBACK_QUEUE_KEY = os.getenv("SCORE_WRITEBACK_QUEUE_KEY", "gd:score_writeback:queue")

_worker_started = False
_worker_lock = threading.Lock()


def is_writeback_enabled():
    """只有开关开启且 Redis 可用，才启用写回队列。"""
    return WRITEBACK_ENABLED and get_redis_client() is not None


def enqueue_score_update(turn_num, small_scores, big_scores):
    """
    将单次比分更新放入 Redis 队列。
    返回 dict: {"ok": bool, "queued": bool, "error": str|None}
    """
    if not is_writeback_enabled():
        return {"ok": False, "queued": False, "error": "writeback_disabled"}

    payload = {
        "turn_num": int(turn_num),
        "small_scores": small_scores,
        "big_scores": big_scores,
        "ts": time.time(),
    }

    client = get_redis_client()
    if client is None:
        return {"ok": False, "queued": False, "error": "redis_unavailable"}

    try:
        client.rpush(WRITEBACK_QUEUE_KEY, json.dumps(payload, ensure_ascii=False))

        return {"ok": True, "queued": True, "error": None}
    except Exception as exc:
        return {"ok": False, "queued": False, "error": str(exc)}


def _drain_batch(client):
    """
    拉取一个批次的数据。
    先阻塞等待 1 条，随后尽可能补齐到 batch_size，兼顾时延与吞吐。
    """
    first = client.blpop(WRITEBACK_QUEUE_KEY, timeout=max(1, int(WRITEBACK_FLUSH_INTERVAL)))
    if not first:
        return []

    _, raw = first
    batch = [json.loads(raw)]

    while len(batch) < WRITEBACK_BATCH_SIZE:
        raw_next = client.lpop(WRITEBACK_QUEUE_KEY)
        if raw_next is None:
            break
        batch.append(json.loads(raw_next))

    return batch


def _compress_updates(batch):
    """
    批内去重压缩：
    - 键：turn_num + team_name
    - 规则：同一批里保留最后一次提交，减少重复 SQL 更新
    """
    latest_small = {}
    latest_big = {}

    for item in batch:
        turn_num = int(item["turn_num"])
        for team_name, score in item.get("small_scores", {}).items():
            latest_small[(turn_num, team_name)] = score
        for team_name, score in item.get("big_scores", {}).items():
            latest_big[(turn_num, team_name)] = score

    grouped = {}
    for (turn_num, team_name), score in latest_small.items():
        grouped.setdefault(turn_num, {"small_scores": {}, "big_scores": {}})
        grouped[turn_num]["small_scores"][team_name] = score

    for (turn_num, team_name), score in latest_big.items():
        grouped.setdefault(turn_num, {"small_scores": {}, "big_scores": {}})
        grouped[turn_num]["big_scores"][team_name] = score

    updates = []
    for turn_num, payload in grouped.items():
        updates.append(
            {
                "turn_num": turn_num,
                "small_scores": payload["small_scores"],
                "big_scores": payload["big_scores"],
            }
        )
    return updates


# 线程函数和启动逻辑
def _writeback_worker(get_db_connection):
    client = get_redis_client()
    if client is None:
        return

    # 持续工作
    while True:
        try:
            # 批量拉取待写回数据，达到批量大小后，压缩去重写入数据库
            batch = _drain_batch(client)
            if not batch:
                continue

            # 压缩去重
            compressed = _compress_updates(batch)
            
            # 批量写入数据库，单事务
            apply_score_updates_batch(get_db_connection, compressed)
        except Exception:
            # 后续可接入日志/告警系统
            time.sleep(0.3)


def ensure_writeback_worker_started(get_db_connection):
    """启动写回线程（仅一次）。"""
    global _worker_started
    if not is_writeback_enabled() or _worker_started:
        return

    with _worker_lock:
        if _worker_started:
            return
        worker = threading.Thread(target=_writeback_worker, args=(get_db_connection,), daemon=True)
        worker.start()
        _worker_started = True

