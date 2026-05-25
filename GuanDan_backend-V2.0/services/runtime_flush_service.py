import os
import threading
import time

from services.redis_runtime import require_redis
from services import runtime_store


FLUSH_INTERVAL_SECONDS = float(os.getenv("RUNTIME_FLUSH_INTERVAL_SECONDS", "10"))
FLUSH_LOCK_KEY = "gd:flush:lock"

_worker_started = False
_worker_lock = threading.Lock()


# 每10秒将dirty的比分和对阵信息写回数据库

def _member_to_text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _row_value(row, key, index=None, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    if isinstance(row, (list, tuple)) and index is not None and len(row) > index:
        return row[index]
    return default


def _mini_team_team_name_index():
    return getattr(runtime_store, "MINI_TEAM_TEAM_NAME_INDEX", 0)


def _mini_team_big_score_index():
    return getattr(runtime_store, "MINI_TEAM_BIG_SCORE_INDEX", 2)


def _mini_team_small_score_index():
    return getattr(runtime_store, "MINI_TEAM_SMALL_SCORE_INDEX", 3)


def _score_by_team(turn):
    rows = runtime_store.read_mini_teams(turn)
    result = {}
    for row in rows:
        team_name = _row_value(row, "team_name", _mini_team_team_name_index())
        if team_name:
            result[str(team_name)] = row
    return result


def _score_value(row, key):
    if key == "small_score":
        return _row_value(row, "small_score", _mini_team_small_score_index())
    return _row_value(row, "big_score", _mini_team_big_score_index())


def _parse_dirty_score_member(member):
    text = _member_to_text(member)
    if not text or ":" not in text:
        return None, None, text
    turn, team_name = text.split(":", 1)
    if not turn or not team_name:
        return None, None, text
    try:
        return str(int(turn)), team_name, text
    except ValueError:
        return None, None, text


def _flush_score_updates(cursor, dirty_members):
    grouped = {}
    malformed_members = set()
    written_members = set()
    for member in dirty_members:
        turn, team_name, text = _parse_dirty_score_member(member)
        if turn is None:
            malformed_members.add(text)
            continue
        grouped.setdefault(turn, set()).add(team_name)

    for turn in sorted(grouped, key=lambda item: int(item)):
        rows_by_team = _score_by_team(turn)
        for team_name in sorted(grouped[turn]):
            row = rows_by_team.get(team_name)
            if row is None:
                continue
            cursor.execute(
                """
                UPDATE mini_team_info
                SET small_score = %s
                WHERE team_name = %s AND turn = %s
                """,
                (_score_value(row, "small_score"), team_name, int(turn)),
            )
            cursor.execute(
                """
                UPDATE mini_team_info
                SET big_score = %s
                WHERE team_name = %s AND turn = %s
                """,
                (_score_value(row, "big_score"), team_name, int(turn)),
            )
            written_members.add(f"{turn}:{team_name}")

    return {
        "written_members": written_members,
        "malformed_members": malformed_members,
    }


def _fight_value(row, key, default=None):
    indexes = {
        "id": 0,
        "team_name_1": 1,
        "members_1": 2,
        "team_name_2": 3,
        "members_2": 4,
        "turn": 5,
        "team_level_1": 6,
        "team_level_2": 7,
    }
    return _row_value(row, key, indexes.get(key), default)


def _parse_dirty_match_turn(dirty_turn):
    text = _member_to_text(dirty_turn)
    if not text:
        return None, text
    try:
        return int(text), text
    except ValueError:
        return None, text


def _flush_matches(cursor, dirty_turns):
    valid_turns = []
    malformed_turns = set()
    processed_turns = set()
    for dirty_turn in dirty_turns:
        turn, text = _parse_dirty_match_turn(dirty_turn)
        if turn is None:
            malformed_turns.add(text)
        else:
            valid_turns.append(turn)

    for turn in sorted(valid_turns):
        cursor.execute("DELETE FROM fight_info WHERE turn = %s", (turn,))

        for row in runtime_store.read_fights(turn):
            cursor.execute(
                """
                INSERT INTO fight_info
                (id, team_name_1, members_1, team_name_2, members_2, turn, team_level_1, team_level_2)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    _fight_value(row, "id"),
                    _fight_value(row, "team_name_1"),
                    _fight_value(row, "members_1"),
                    _fight_value(row, "team_name_2"),
                    _fight_value(row, "members_2"),
                    int(_fight_value(row, "turn", turn) or turn),
                    _fight_value(row, "team_level_1"),
                    _fight_value(row, "team_level_2"),
                ),
            )
        processed_turns.add(str(turn))

    return {
        "processed_turns": processed_turns,
        "malformed_turns": malformed_turns,
    }


def _dirty_count(dirty_scores, dirty_matches, dirty_teams):
    return len(dirty_scores) + len(dirty_matches) + len(dirty_teams)


def flush_once(get_db_connection):
    client = require_redis()
    dirty_scores = set(client.smembers(runtime_store.DIRTY_SCORE_KEY))
    dirty_matches = set(client.smembers(runtime_store.DIRTY_MATCHES_KEY))
    dirty_teams = set(client.smembers(runtime_store.DIRTY_TEAMS_KEY))
    dirty_count = _dirty_count(dirty_scores, dirty_matches, dirty_teams)

    if dirty_teams:
        error = "dirty teams writeback is not implemented"
        runtime_store.update_state(flush_status="failed", flush_error=error)
        return {"ok": False, "dirty_count": dirty_count, "error": error}

    if dirty_count == 0:
        runtime_store.update_state(flush_status="ok", flush_error="")
        return {"ok": True, "dirty_count": 0}

    if not client.setnx(FLUSH_LOCK_KEY, str(time.time())):
        return {"ok": True, "dirty_count": dirty_count, "skipped": "locked"}

    client.expire(FLUSH_LOCK_KEY, max(1, int(FLUSH_INTERVAL_SECONDS * 2)))
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        score_result = _flush_score_updates(cursor, dirty_scores)
        match_result = _flush_matches(cursor, dirty_matches)
        conn.commit()
        finished_scores = (
            score_result["written_members"]
            | score_result["malformed_members"]
        )
        finished_matches = (
            match_result["processed_turns"]
            | match_result["malformed_turns"]
        )
        if finished_scores:
            client.srem(runtime_store.DIRTY_SCORE_KEY, *finished_scores)
        if finished_matches:
            client.srem(runtime_store.DIRTY_MATCHES_KEY, *finished_matches)
        runtime_store.update_state(
            last_flush_at=time.time(),
            flush_status="ok",
            flush_error="",
        )
        return {
            "ok": True,
            "dirty_count": dirty_count,
            "written_scores": len(score_result["written_members"]),
            "skipped_scores": len(dirty_scores) - len(score_result["written_members"]),
        }
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        runtime_store.update_state(flush_status="failed", flush_error=str(exc))
        return {"ok": False, "dirty_count": dirty_count, "error": str(exc)}
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
        client.delete(FLUSH_LOCK_KEY)


def _worker(get_db_connection):
    while True:
        try:
            flush_once(get_db_connection)
        except Exception as exc:
            try:
                runtime_store.update_state(
                    flush_status="failed",
                    flush_error=str(exc),
                )
            except Exception:
                pass
        time.sleep(FLUSH_INTERVAL_SECONDS)


def ensure_runtime_flush_worker_started(get_db_connection):
    global _worker_started

    with _worker_lock:
        if _worker_started:
            return False
        thread = threading.Thread(
            target=_worker,
            args=(get_db_connection,),
            daemon=True,
        )
        thread.start()
        _worker_started = True
        return True
