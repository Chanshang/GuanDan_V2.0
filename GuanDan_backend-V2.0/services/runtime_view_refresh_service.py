import os
import threading
import time

from services.redis_runtime import require_redis
from services import runtime_store
from services import runtime_views


VIEW_REFRESH_INTERVAL_SECONDS = float(os.getenv("RUNTIME_VIEW_REFRESH_INTERVAL_SECONDS", "2.0"))
VIEW_REFRESH_LOCK_KEY = "gd:view:refresh:lock"

_worker_started = False
_worker_lock = threading.Lock()


# 每2秒检查一次dashboard_dirty_turns，如果有dirty的turn就重建dashboard_view，并清除dirty状态


def refresh_dirty_views_once():
    client = require_redis()
    dirty = runtime_store.read_dashboard_dirty_turns()
    dirty_turns = dirty["valid_turns"]
    malformed_turns = dirty["malformed_turns"]
    dirty_count = len(dirty_turns) + len(malformed_turns)

    if dirty_count == 0:
        return {"ok": True, "dirty_count": 0}

    if not client.setnx(VIEW_REFRESH_LOCK_KEY, str(time.time())):
        return {"ok": True, "dirty_count": dirty_count, "skipped": "locked"}

    client.expire(VIEW_REFRESH_LOCK_KEY, max(1, int(VIEW_REFRESH_INTERVAL_SECONDS * 4)))
    try:
        for turn in dirty_turns:
            runtime_views.rebuild_dashboard_view(turn)
        runtime_views.rebuild_admin_matches_view()
        runtime_views.rebuild_admin_overview_view()
        runtime_store.clear_dashboard_dirty_turns(
            [*dirty_turns, *malformed_turns]
        )
        return {
            "ok": True,
            "dirty_count": dirty_count,
            "rebuilt_dashboard_turns": dirty_turns,
        }
    except Exception as exc:
        try:
            runtime_store.update_state(
                flush_status="failed",
                flush_error=f"view refresh failed: {exc}",
            )
        except Exception:
            pass
        return {"ok": False, "dirty_count": dirty_count, "error": str(exc)}
    finally:
        client.delete(VIEW_REFRESH_LOCK_KEY)


def _worker():
    while True:
        try:
            refresh_dirty_views_once()
        except Exception:
            pass
        time.sleep(VIEW_REFRESH_INTERVAL_SECONDS)


def ensure_runtime_view_refresh_worker_started():
    global _worker_started

    with _worker_lock:
        if _worker_started:
            return False
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        _worker_started = True
        return True
