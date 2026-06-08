import json
from datetime import datetime

from services.redis_runtime import require_redis
from services import runtime_store


DASHBOARD_VIEW_KEY = "gd:view:dashboard:{turn}"
ADMIN_OVERVIEW_KEY = "gd:view:admin:overview"
ADMIN_MATCHES_KEY = "gd:view:admin:matches"
CREATE_TABLE_VIEW_KEY = "gd:view:create_table"


def _dumps(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def _loads(raw, default):
    if raw is None or raw == "":
        return default
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def _row_value(row, key, index=None, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    if index is not None and isinstance(row, (list, tuple)) and len(row) > index:
        return row[index]
    return default


def _to_int(value, default=0):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _timer_message(state):
    return runtime_store.build_time_message()


def _team_name(row):
    return _row_value(row, "team_name", 0, "")


def _team_office(row):
    return _row_value(row, "office", 4, "")


def _team_members(row):
    if isinstance(row, (list, tuple)):
        if len(row) > 5:
            return row[5]
        return ""
    return (
        _row_value(row, "member_name", None)
        or _row_value(row, "members", 1, "")
    )


def _team_big_score(row):
    return _to_int(_row_value(row, "big_score", 2, 0))


def _team_small_score(row):
    return _to_int(_row_value(row, "small_score", 3, 0))


def _rank_items(score_map):
    ordered = sorted(
        score_map.items(),
        key=lambda item: (-item[1]["big"], -item[1]["small"], item[0]),
    )
    return [
        (rank, name, values["big"], values["small"])
        for rank, (name, values) in enumerate(ordered, start=1)
    ]


def _rank_team_rows(rows, turn):
    current_scores = {}
    total_scores = {}
    target_turn = str(turn)

    for row in rows:
        team_name = _team_name(row)
        if not team_name:
            continue
        row_turn = str(_row_value(row, "turn", 1, target_turn))
        big_score = _team_big_score(row)
        small_score = _team_small_score(row)

        total = total_scores.setdefault(team_name, {"big": 0, "small": 0})
        total["big"] += big_score
        total["small"] += small_score

        if row_turn == target_turn:
            current = current_scores.setdefault(team_name, {"big": 0, "small": 0})
            current["big"] += big_score
            current["small"] += small_score

    return {
        "current_turn": _rank_items(current_scores),
        "total_until_turn": _rank_items(total_scores),
    }


def _rank_office_rows(rows, turn):
    current_scores = {}
    total_scores = {}
    target_turn = str(turn)

    for row in rows:
        office = _team_office(row)
        if not office:
            continue
        row_turn = str(_row_value(row, "turn", 1, target_turn))
        big_score = _team_big_score(row)
        small_score = _team_small_score(row)
        if row_turn == target_turn:
            current = current_scores.setdefault(office, {"big": 0, "small": 0})
            current["big"] += big_score
            current["small"] += small_score
        total = total_scores.setdefault(office, {"big": 0, "small": 0})
        total["big"] += big_score
        total["small"] += small_score

    return {
        "current_turn": _rank_items(current_scores),
        "total_until_turn": _rank_items(total_scores),
    }


def _team_level_map():
    return {
        _row_value(row, "team_name", 0): _row_value(row, "level", 1)
        for row in runtime_store.read_team_levels()
        if _row_value(row, "team_name", 0)
    }


def _admin_team_rows():
    level_map = _team_level_map()
    teams = []

    for row in runtime_store.read_teams():
        if isinstance(row, dict) and any(f"team_name_{idx}" in row for idx in range(1, 5)):
            office = row.get("office", "")
            for idx in range(1, 5):
                team_name = row.get(f"team_name_{idx}")
                members = row.get(f"members_{idx}")
                if not team_name or not members or members == "空":
                    continue
                teams.append(
                    {
                        "team_name": team_name,
                        "members": members,
                        "office": office,
                        "level": level_map.get(team_name),
                    }
                )
            continue

        team_name = _row_value(row, "team_name", 0, "")
        if not team_name:
            continue
        teams.append(
            {
                "team_name": team_name,
                "members": _team_members(row),
                "office": _team_office(row),
                "level": level_map.get(team_name),
            }
        )

    return teams


def _mini_team_map(turn):
    return {
        _team_name(row): row
        for row in runtime_store.read_mini_teams(turn)
        if _team_name(row)
    }


def _fight_table(row):
    return _row_value(row, "id", 0)


def _fight_team_1(row):
    return _row_value(row, "team_name_1", 1, "")


def _fight_members_1(row):
    return _row_value(row, "members_1", 2, "")


def _fight_team_2(row):
    return _row_value(row, "team_name_2", 3, "")


def _fight_members_2(row):
    return _row_value(row, "members_2", 4, "")


def _snapshot_time():
    return datetime.now().isoformat(timespec="seconds")


def rebuild_dashboard_view(turn):
    turn = int(turn)
    state = runtime_store.get_state()
    fights = runtime_store.read_fights(turn)
    mini_teams = runtime_store.read_mini_teams(turn)
    level_map = _team_level_map()
    ranking_rows = []
    for ranking_turn in range(1, turn + 1):
        ranking_rows.extend(runtime_store.read_mini_teams(ranking_turn))

    view = {
        "TURN": str(turn),
        "time_message": _timer_message(state),
        "matchesinfo": [
            (
                _fight_table(row),
                _fight_team_1(row),
                _fight_members_1(row),
                _fight_team_2(row),
                _fight_members_2(row),
                level_map.get(_fight_team_1(row)),
                level_map.get(_fight_team_2(row)),
            )
            for row in fights
        ],
        "scoresinfo": [
            (
                _team_name(row),
                _team_members(row),
                _team_small_score(row),
            )
            for row in mini_teams
        ],
        "sumteaminfo": _rank_team_rows(ranking_rows, turn),
        "officescore": _rank_office_rows(ranking_rows, turn),
        "snapshot_updated_at": _snapshot_time(),
    }

    client = require_redis()
    client.set(DASHBOARD_VIEW_KEY.format(turn=turn), _dumps(view))
    return view


def rebuild_admin_overview_view():
    state = runtime_store.get_state()
    has_matches = any(runtime_store.read_fights(turn) for turn in (1, 2, 3))
    view = {
        "turn": state.get("current_turn", "null"),
        "time_message": _timer_message(state),
        "teams": _admin_team_rows(),
        "has_matches": has_matches,
        "runtime_status": "ok",
        "flush_status": state.get("flush_status", ""),
        "last_flush_at": state.get("last_flush_at", ""),
        "flush_error": state.get("flush_error", ""),
        "snapshot_updated_at": _snapshot_time(),
    }

    client = require_redis()
    client.set(ADMIN_OVERVIEW_KEY, _dumps(view))
    return view


def rebuild_admin_matches_view():
    level_map = _team_level_map()
    matches = []

    for turn in (1, 2, 3):
        mini_teams = _mini_team_map(turn)
        for row in runtime_store.read_fights(turn):
            team_name_1 = _fight_team_1(row)
            team_name_2 = _fight_team_2(row)
            team_1 = mini_teams.get(team_name_1, {})
            team_2 = mini_teams.get(team_name_2, {})
            matches.append(
                {
                    "table_no": _fight_table(row),
                    "team_name_1": team_name_1,
                    "members_1": _fight_members_1(row),
                    "team_name_2": team_name_2,
                    "members_2": _fight_members_2(row),
                    "turn": turn,
                    "team_level_1": level_map.get(team_name_1),
                    "team_level_2": level_map.get(team_name_2),
                    "team1_big_score": _team_big_score(team_1),
                    "team1_small_score": _team_small_score(team_1),
                    "team2_big_score": _team_big_score(team_2),
                    "team2_small_score": _team_small_score(team_2),
                }
            )

    view = {
        "matches": matches,
        "snapshot_updated_at": _snapshot_time(),
    }
    client = require_redis()
    client.set(ADMIN_MATCHES_KEY, _dumps(view))
    return view


def rebuild_create_table_view():
    table_by_team = {}
    for turn in (1, 2, 3):
        for row in runtime_store.read_fights(turn):
            table_no = _fight_table(row)
            table_by_team[(turn, _fight_team_1(row))] = table_no
            table_by_team[(turn, _fight_team_2(row))] = table_no

    rows = []
    for turn in (1, 2, 3):
        for row in runtime_store.read_mini_teams(turn):
            rows.append(
                {
                    "team": row,
                    "fight_id": table_by_team.get((turn, _team_name(row))),
                }
            )

    view = {"rows": rows}
    client = require_redis()
    client.set(CREATE_TABLE_VIEW_KEY, _dumps(view))
    return view


def read_view(key, default=None):
    client = require_redis()
    return _loads(client.get(key), default)


def read_dashboard_view(turn):
    return read_view(DASHBOARD_VIEW_KEY.format(turn=int(turn)), {})


def read_admin_overview_view():
    return read_view(ADMIN_OVERVIEW_KEY, {})


def read_admin_matches_view():
    return read_view(ADMIN_MATCHES_KEY, {"matches": []})


def read_create_table_view():
    return read_view(CREATE_TABLE_VIEW_KEY, {"rows": []})


def rebuild_all_views():
    views = {
        "dashboard": {
            str(turn): rebuild_dashboard_view(turn)
            for turn in (1, 2, 3)
        },
        "admin_overview": rebuild_admin_overview_view(),
        "admin_matches": rebuild_admin_matches_view(),
        "create_table": rebuild_create_table_view(),
    }
    return views
