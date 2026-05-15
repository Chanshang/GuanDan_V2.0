import json

from services.redis_runtime import RedisRuntimeError, require_redis


STATE_KEY = "gd:state"
TEAMS_KEY = "gd:teams"
TEAM_LEVELS_KEY = "gd:team_levels"
DIRTY_SCORE_KEY = "gd:dirty:score_updates"
DIRTY_MATCHES_KEY = "gd:dirty:matches"
DIRTY_TEAMS_KEY = "gd:dirty:teams"
SCHEMA_VERSION = "1"
VALID_TURNS = {"1", "2", "3"}
MINI_TEAM_TEAM_NAME_INDEX = 0
MINI_TEAM_BIG_SCORE_INDEX = 2
MINI_TEAM_SMALL_SCORE_INDEX = 3


def _json_default(value):
    return str(value)


def _dumps(value):
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _loads(raw, default):
    if raw is None or raw == "":
        return default
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def _mini_teams_key(turn):
    return f"gd:mini_teams:turn:{int(turn)}"


def _fights_key(turn):
    return f"gd:fights:turn:{int(turn)}"


def _normalize_row(row, columns=None):
    if isinstance(row, dict):
        return dict(row)
    if columns:
        return dict(zip(columns, row))
    return list(row)


def _require_initialized(client):
    state = client.hgetall(STATE_KEY)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise RedisRuntimeError(
            "redis_not_initialized",
            "Redis 运行态数据未初始化",
        )
    return state


def initialize_empty_state():
    client = require_redis()
    client.hset(
        STATE_KEY,
        mapping={
            "current_turn": "null",
            "timer_started_at": "",
            "timer_total_seconds": "3600",
            "schema_version": SCHEMA_VERSION,
            "last_loaded_at": "",
            "last_flush_at": "",
            "flush_status": "ok",
            "flush_error": "",
        },
    )


def get_state():
    client = require_redis()
    return _require_initialized(client)


def update_state(**fields):
    client = require_redis()
    _require_initialized(client)
    if fields:
        client.hset(
            STATE_KEY,
            mapping={
                key: "" if value is None else str(value)
                for key, value in fields.items()
            },
        )
    return get_state()


def get_current_turn():
    client = require_redis()
    _require_initialized(client)
    return client.hget(STATE_KEY, "current_turn")


def set_current_turn(turn):
    if turn is None or turn == "":
        saved = "null"
    else:
        saved = str(turn)
        if saved != "null" and saved not in VALID_TURNS:
            raise ValueError("invalid_turn")

    update_state(current_turn=saved)
    return saved


def write_teams(rows, columns=None, mark_dirty=False):
    client = require_redis()
    _require_initialized(client)
    normalized = [_normalize_row(row, columns) for row in rows]
    client.set(TEAMS_KEY, _dumps(normalized))
    if mark_dirty:
        client.sadd(DIRTY_TEAMS_KEY, "teams")
    return normalized


def read_teams():
    client = require_redis()
    _require_initialized(client)
    return _loads(client.get(TEAMS_KEY), [])


def write_team_levels(rows, columns=None, mark_dirty=False):
    client = require_redis()
    _require_initialized(client)
    normalized = [_normalize_row(row, columns) for row in rows]
    client.set(TEAM_LEVELS_KEY, _dumps(normalized))
    if mark_dirty:
        client.sadd(DIRTY_TEAMS_KEY, "team_levels")
    return normalized


def read_team_levels():
    client = require_redis()
    _require_initialized(client)
    return _loads(client.get(TEAM_LEVELS_KEY), [])


def write_mini_teams(turn, rows, columns=None):
    client = require_redis()
    _require_initialized(client)
    normalized = [_normalize_row(row, columns) for row in rows]
    client.set(_mini_teams_key(turn), _dumps(normalized))
    return normalized


def read_mini_teams(turn):
    client = require_redis()
    _require_initialized(client)
    return _loads(client.get(_mini_teams_key(turn)), [])


def write_fights(turn, rows, columns=None, mark_dirty=True):
    client = require_redis()
    _require_initialized(client)
    normalized = [_normalize_row(row, columns) for row in rows]
    client.set(_fights_key(turn), _dumps(normalized))
    if mark_dirty:
        client.sadd(DIRTY_MATCHES_KEY, str(int(turn)))
    return normalized


def read_fights(turn):
    client = require_redis()
    _require_initialized(client)
    return _loads(client.get(_fights_key(turn)), [])


def _value_from_row(row, key, index=None):
    if isinstance(row, dict):
        return row.get(key)
    if index is None:
        return None
    if isinstance(row, (list, tuple)) and len(row) > index:
        return row[index]
    return None


def get_match(turn, table_num):
    target_table = int(table_num)
    for row in read_fights(turn):
        row_table = _value_from_row(row, "id", 0)
        if row_table is None or int(row_table) != target_table:
            continue
        return {
            "table_num": target_table,
            "team1_name": _value_from_row(row, "team_name_1", 1),
            "team1_members": _value_from_row(row, "members_1", 2),
            "team2_name": _value_from_row(row, "team_name_2", 3),
            "team2_members": _value_from_row(row, "members_2", 4),
            "turn_num": int(turn),
        }
    return None


def apply_score_result(turn, small_scores, big_scores):
    client = require_redis()
    _require_initialized(client)
    small_scores = small_scores or {}
    big_scores = big_scores or {}
    rows = read_mini_teams(turn)
    changed_teams = set(small_scores) | set(big_scores)
    dirty_teams = set()

    for row in rows:
        team_name = _value_from_row(
            row,
            "team_name",
            MINI_TEAM_TEAM_NAME_INDEX,
        )
        if not team_name or team_name not in changed_teams:
            continue
        if isinstance(row, dict):
            if team_name in small_scores:
                row["small_score"] = small_scores[team_name]
            if team_name in big_scores:
                row["big_score"] = big_scores[team_name]
            dirty_teams.add(team_name)
        elif isinstance(row, list):
            if team_name in small_scores:
                row[MINI_TEAM_SMALL_SCORE_INDEX] = small_scores[team_name]
            if team_name in big_scores:
                row[MINI_TEAM_BIG_SCORE_INDEX] = big_scores[team_name]
            dirty_teams.add(team_name)

    # 录分结果先落 Redis，并记录后续写回 MySQL 的最小 dirty 范围。
    for team_name in dirty_teams:
        client.sadd(DIRTY_SCORE_KEY, f"{int(turn)}:{team_name}")

    write_mini_teams(turn, rows)
    return rows
