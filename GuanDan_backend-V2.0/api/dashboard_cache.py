import threading
import time

from app.config import Config
from services.stats_service import (
    fetch_matches_by_turn,
    fetch_scores_by_turn,
    fetch_team_rankings,
    fetch_office_rankings,
)

# 前端展示相关全局状态
VALID_TURNS = {"1", "2", "3"}
TURN = "null"
TOTAL_SECONDS = 60 * 60  # 每轮 60 分钟
timer_start = None

# 聚合快照配置
SNAPSHOT_REFRESH_SECONDS = 5  # 后台线程每 5 秒刷新一次快照
SNAPSHOT_STALE_SECONDS = 8  # 超过 8 秒未更新则认为快照过期（允许一定的刷新延迟）

get_db_connection = Config().get_db_connection

_snapshot_lock = threading.Lock()
_snapshot_worker_started = False
_dashboard_snapshot = {
    "turn": "null",
    "updated_at": 0.0,
    "matchesinfo": [],
    "scoresinfo": [],
    "team_current_full": [],
    "team_total_full": [],
    "office_current": [],
    "office_total": [],
}


def is_valid_turn(turn):
    """校验轮次是否在允许范围内。"""
    return str(turn) in VALID_TURNS


def get_turn():
    """读取当前轮次。"""
    return TURN


def set_turn(value):
    """设置当前轮次。"""
    global TURN
    TURN = str(value)


def reset_turn():
    """重置当前轮次。"""
    set_turn("null")


def start_round_timer():
    """开始计时；若轮次未设置则返回 False。"""
    global timer_start
    if TURN == "null":
        return False
    timer_start = time.time()
    return True


def stop_round_timer():
    """暂停计时。"""
    global timer_start
    timer_start = None


def build_time_message():
    """统一构造倒计时文案，不触发数据库查询。"""
    global timer_start
    if timer_start is None:
        return "倒计时未开始"

    elapsed = int(time.time() - timer_start)
    remaining = max(0, TOTAL_SECONDS - elapsed)
    minutes = remaining // 60
    seconds = remaining % 60
    return f"{minutes:02d}:{seconds:02d}"


def mark_snapshot_stale():
    """将聚合快照标记为过期，下次会触发刷新。"""
    with _snapshot_lock:
        _dashboard_snapshot["updated_at"] = 0.0


def refresh_dashboard_snapshot_once():
    """执行一次数据库读取并更新聚合快照。"""
    turn = TURN
    new_snapshot = {
        "turn": turn,
        "updated_at": time.time(),  # 这个部分关键，每次更新会刷新这个时间戳，过期逻辑会基于它判断
        "matchesinfo": [],
        "scoresinfo": [],
        "team_current_full": [],
        "team_total_full": [],
        "office_current": [],
        "office_total": [],
    }

    if is_valid_turn(turn):
        matches = fetch_matches_by_turn(get_db_connection, turn)
        scores = fetch_scores_by_turn(get_db_connection, turn)
        team_current, team_total = fetch_team_rankings(get_db_connection, turn)
        office_current, office_total = fetch_office_rankings(get_db_connection, turn)

        new_snapshot["matchesinfo"] = matches
        new_snapshot["scoresinfo"] = scores
        new_snapshot["team_current_full"] = team_current
        new_snapshot["team_total_full"] = team_total
        new_snapshot["office_current"] = office_current
        new_snapshot["office_total"] = office_total

    with _snapshot_lock:
        _dashboard_snapshot.update(new_snapshot)
        print(f"Dashboard snapshot refreshed for turn {turn} at {new_snapshot['updated_at']}")


def ensure_dashboard_snapshot_fresh(force_refresh=False):
    """确保聚合快照可用：过期则刷新。"""
    with _snapshot_lock:
        last_updated = _dashboard_snapshot["updated_at"]

    # 防止进程猝死，仍有 8s 的过期刷新保护
    should_refresh = force_refresh or (time.time() - last_updated > SNAPSHOT_STALE_SECONDS)
    if should_refresh:
        try:
            refresh_dashboard_snapshot_once()
        except Exception:
            # 快照刷新失败时，仍返回旧快照，避免直接把接口打挂
            pass


def get_snapshot_copy():
    """读取快照副本，避免直接暴露内部结构。"""
    # 读取也上锁了，但速度够快可以忽略性能影响
    with _snapshot_lock:
        return dict(_dashboard_snapshot)


def slice_team_rankings_for_screen(team_current_full, team_total_full):
    """维持原有大屏轮播逻辑：计时中每 5 秒切换一次 6 条数据。"""
    if timer_start is None:
        return team_current_full, team_total_full

    elapsed = int(time.time() - timer_start)
    split_id = int((elapsed / 5) % 8)
    start_idx = split_id * 6
    end_idx = min(start_idx + 6, len(team_current_full))

    current_slice = team_current_full[start_idx:end_idx]
    total_slice = team_total_full[start_idx:min(start_idx + 6, len(team_total_full))]
    return current_slice, total_slice


# 防止进程猝死，仍有 8s 的过期刷新保护
def background_snapshot_worker():
    """后台定时刷新聚合快照。"""
    while True:
        try:
            refresh_dashboard_snapshot_once()
        except Exception:
            pass
        time.sleep(SNAPSHOT_REFRESH_SECONDS)


def ensure_snapshot_worker_started():
    """确保后台刷新线程只启动一次。"""
    global _snapshot_worker_started
    if _snapshot_worker_started:
        return

    with _snapshot_lock:
        if _snapshot_worker_started:
            return

        worker = threading.Thread(target=background_snapshot_worker, daemon=True)
        worker.start()
        _snapshot_worker_started = True

