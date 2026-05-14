import os

try:
    from werkzeug.utils import secure_filename
except ModuleNotFoundError:  # pragma: no cover - 兼容未安装 Flask 依赖的单元测试环境
    def secure_filename(filename):
        keep_chars = (" ", ".", "_", "-")
        safe_name = "".join(c for c in filename if c.isalnum() or c in keep_chars)
        return safe_name.strip().replace(" ", "_")

get_turn = None
is_valid_turn = None
build_time_message = None
get_snapshot_copy = None
mark_snapshot_stale = None
reset_turn = None
set_current_turn = None
start_round_timer = None
stop_round_timer = None
clear_all_tables = None
fetch_team_info_rows = None
import_registration_excel = None
save_score_log = None
generate_round_pairs = None
fetch_all_fights = None
fetch_match_generation_source = None
replace_fight_info = None
clear_all_fight_cache_in_redis = None
apply_score_update = None
enqueue_score_update = None
is_writeback_enabled = None
build_score_update = None
check_match_exists = None


MAX_TABLE_NUMBER = 22


def _load_dashboard_cache(required=None):
    global get_turn, is_valid_turn, build_time_message, get_snapshot_copy
    global mark_snapshot_stale, reset_turn
    global set_current_turn, start_round_timer, stop_round_timer
    required = required or ()
    if required and all(globals()[name] is not None for name in required):
        return
    if not required and all(
        func is not None
        for func in (
            get_turn,
            is_valid_turn,
            build_time_message,
            get_snapshot_copy,
            mark_snapshot_stale,
            reset_turn,
            set_current_turn,
            start_round_timer,
            stop_round_timer,
        )
    ):
        return
    from api.dashboard_cache import (
        get_turn as _get_turn,
        is_valid_turn as _is_valid_turn,
        build_time_message as _build_time_message,
        get_snapshot_copy as _get_snapshot_copy,
        mark_snapshot_stale as _mark_snapshot_stale,
        reset_turn as _reset_turn,
        set_turn as _set_current_turn,
        start_round_timer as _start_round_timer,
        stop_round_timer as _stop_round_timer,
    )

    get_turn = _get_turn
    is_valid_turn = _is_valid_turn
    build_time_message = _build_time_message
    get_snapshot_copy = _get_snapshot_copy
    mark_snapshot_stale = _mark_snapshot_stale
    reset_turn = _reset_turn
    set_current_turn = _set_current_turn
    start_round_timer = _start_round_timer
    stop_round_timer = _stop_round_timer


def _load_services(required=None):
    global clear_all_tables, fetch_team_info_rows, import_registration_excel
    global save_score_log, generate_round_pairs, fetch_all_fights
    global fetch_match_generation_source, replace_fight_info
    global clear_all_fight_cache_in_redis, apply_score_update
    global enqueue_score_update, is_writeback_enabled, build_score_update
    global check_match_exists
    required = required or (
        "clear_all_tables",
        "fetch_team_info_rows",
        "import_registration_excel",
        "save_score_log",
        "generate_round_pairs",
        "fetch_all_fights",
        "fetch_match_generation_source",
        "replace_fight_info",
        "clear_all_fight_cache_in_redis",
        "apply_score_update",
        "enqueue_score_update",
        "is_writeback_enabled",
        "build_score_update",
        "check_match_exists",
    )
    if required and all(globals()[name] is not None for name in required):
        return
    required = set(required)

    if "clear_all_tables" in required and clear_all_tables is None:
        from services.clear_all_service import clear_all_tables as _clear_all_tables
        clear_all_tables = _clear_all_tables

    if (
        {"fetch_team_info_rows", "import_registration_excel"} & required
        and (fetch_team_info_rows is None or import_registration_excel is None)
    ):
        from services.import_service import (
            fetch_team_info_rows as _fetch_team_info_rows,
            import_registration_excel as _import_registration_excel,
        )
        fetch_team_info_rows = _fetch_team_info_rows
        import_registration_excel = _import_registration_excel

    if "save_score_log" in required and save_score_log is None:
        from services.log_service import save_score_log as _save_score_log
        save_score_log = _save_score_log

    if "generate_round_pairs" in required and generate_round_pairs is None:
        from services.match_algorithm import generate_round_pairs as _generate_round_pairs
        generate_round_pairs = _generate_round_pairs

    if (
        {"fetch_all_fights", "fetch_match_generation_source", "replace_fight_info"} & required
        and (
            fetch_all_fights is None
            or fetch_match_generation_source is None
            or replace_fight_info is None
        )
    ):
        from services.match_service import (
            fetch_all_fights as _fetch_all_fights,
            fetch_match_generation_source as _fetch_match_generation_source,
            replace_fight_info as _replace_fight_info,
        )
        fetch_all_fights = _fetch_all_fights
        fetch_match_generation_source = _fetch_match_generation_source
        replace_fight_info = _replace_fight_info

    if "clear_all_fight_cache_in_redis" in required and clear_all_fight_cache_in_redis is None:
        from services.redis_cache_service import clear_all_fight_cache_in_redis as _clear_all_fight_cache_in_redis
        clear_all_fight_cache_in_redis = _clear_all_fight_cache_in_redis

    if "apply_score_update" in required and apply_score_update is None:
        from services.score_service import apply_score_update as _apply_score_update
        apply_score_update = _apply_score_update

    if (
        {"enqueue_score_update", "is_writeback_enabled"} & required
        and (enqueue_score_update is None or is_writeback_enabled is None)
    ):
        from services.score_writeback_service import (
            enqueue_score_update as _enqueue_score_update,
            is_writeback_enabled as _is_writeback_enabled,
        )
        enqueue_score_update = _enqueue_score_update
        is_writeback_enabled = _is_writeback_enabled

    if "build_score_update" in required and build_score_update is None:
        from services.scoring import build_score_update as _build_score_update
        build_score_update = _build_score_update

    if "check_match_exists" in required and check_match_exists is None:
        from services.stats_service import check_match_exists as _check_match_exists
        check_match_exists = _check_match_exists


def api_success(message, data=None):
    return {"ok": True, "message": message, "data": data or {}}


def api_error(error, message, data=None):
    return {"ok": False, "error": error, "message": message, "data": data or {}}


def parse_table_number(value, max_table_number=MAX_TABLE_NUMBER):
    try:
        table_num = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if 1 <= table_num <= max_table_number:
        return table_num
    return None


def build_score_error(error):
    tied_winner_errors = {
        "未选择最终局赢家",
        "winner_required_when_tied",
        "鏈€夋嫨鏈€缁堝眬璧㈠",
    }
    return "winner_required_when_tied" if error in tied_winner_errors else "score_invalid"


def clear_fight_cache(clear_local_cache=None):
    _load_services(("clear_all_fight_cache_in_redis",))
    if clear_local_cache is not None:
        clear_local_cache()
    clear_all_fight_cache_in_redis()


def find_match_info(fights, table_num):
    try:
        target_table_num = int(table_num)
    except (TypeError, ValueError):
        return None

    for row in fights or []:
        if len(row) < 5:
            continue
        try:
            row_table_num = int(row[0])
        except (TypeError, ValueError):
            continue
        if row_table_num != target_table_num:
            continue
        return {
            "table_num": row_table_num,
            "team1_name": row[1],
            "team1_members": row[2],
            "team2_name": row[3],
            "team2_members": row[4],
        }
    return None


def get_overview(get_db_connection):
    _load_dashboard_cache(("get_turn", "build_time_message", "get_snapshot_copy"))
    _load_services(("fetch_team_info_rows", "fetch_all_fights"))
    teams = fetch_team_info_rows(get_db_connection)
    matches = fetch_all_fights(get_db_connection)
    snapshot = get_snapshot_copy()
    return api_success(
        "后台概览已获取",
        {
            "turn": get_turn(),
            "time_message": build_time_message(),
            "teams": teams,
            "has_matches": bool(matches),
            "snapshot_updated_at": snapshot.get("updated_at"),
        },
    )


def import_registration_file(file_storage, get_db_connection, upload_dir, clear_local_cache=None):
    _load_dashboard_cache(("reset_turn", "mark_snapshot_stale"))
    _load_services(("import_registration_excel", "clear_all_fight_cache_in_redis"))
    if not file_storage:
        return api_error("invalid_file", "请选择要上传的报名文件")

    filename = getattr(file_storage, "filename", "")
    if not filename or not filename.lower().endswith(".xlsx"):
        return api_error("invalid_file", "请上传 .xlsx 报名文件")

    os.makedirs(upload_dir, exist_ok=True)
    safe_name = secure_filename(filename)
    if not safe_name:
        return api_error("invalid_file", "文件名无效")

    filepath = os.path.join(upload_dir, safe_name)
    file_storage.save(filepath)

    result = import_registration_excel(filepath, get_db_connection)
    if not result.get("ok"):
        return api_error(
            "import_failed",
            "报名文件导入失败",
            {"error": result.get("error"), "imported_rows": result.get("imported_rows", 0)},
        )

    clear_fight_cache(clear_local_cache)
    reset_turn()
    mark_snapshot_stale()
    return api_success("报名文件导入成功", result)


def clear_business_data(get_db_connection, clear_local_cache=None):
    _load_dashboard_cache(("reset_turn", "mark_snapshot_stale"))
    _load_services(("clear_all_tables", "clear_all_fight_cache_in_redis"))
    result = clear_all_tables(get_db_connection)
    if not result.get("ok"):
        return api_error("clear_failed", "业务数据清理失败", {"error": result.get("error")})

    clear_fight_cache(clear_local_cache)
    reset_turn()
    mark_snapshot_stale()
    return api_success("业务数据已清理")


def set_turn_value(value):
    _load_dashboard_cache(("is_valid_turn", "reset_turn", "set_current_turn", "mark_snapshot_stale", "get_turn"))
    turn = str(value).strip() if value is not None else ""
    if turn in {"", "null"}:
        reset_turn()
    elif turn and turn.isdigit() and is_valid_turn(turn):
        set_current_turn(turn)
    else:
        return api_error("invalid_turn", "轮次值无效")

    mark_snapshot_stale()
    return api_success("当前轮次已更新", {"turn": get_turn()})


def start_timer_value():
    _load_dashboard_cache(("start_round_timer", "build_time_message"))
    if not start_round_timer():
        return api_error("invalid_turn", "当前轮次未设置")
    return api_success("计时已开始", {"time_message": build_time_message()})


def stop_timer_value():
    _load_dashboard_cache(("stop_round_timer", "build_time_message"))
    stop_round_timer()
    return api_success("计时已暂停", {"time_message": build_time_message()})


def generate_matches_workflow(get_db_connection, clear_local_cache=None):
    _load_services(("fetch_match_generation_source", "generate_round_pairs"))
    teams, team_levels_list = fetch_match_generation_source(get_db_connection)
    match_result = generate_round_pairs(teams, team_levels_list, rounds=3)
    if not match_result.get("success"):
        return api_error(
            "match_generation_failed",
            "对阵生成失败",
            {"error": match_result.get("error")},
        )

    _load_services(("replace_fight_info",))
    write_result = replace_fight_info(
        get_db_connection,
        match_result["pairs"],
        match_result["team_members"],
        match_result["team_levels"],
    )
    if not write_result.get("ok"):
        return api_error("match_generation_failed", "对阵保存失败", {"error": write_result.get("error")})

    _load_dashboard_cache(("mark_snapshot_stale",))
    clear_fight_cache(clear_local_cache)
    mark_snapshot_stale()
    return api_success("对阵已生成", {"tables": len(match_result["pairs"])})


def get_all_matches(get_db_connection):
    _load_services(("fetch_all_fights",))
    return api_success("对阵列表已获取", {"matches": fetch_all_fights(get_db_connection)})


def get_match_for_score(get_db_connection, load_fight_info, turn_num, table_num):
    _load_dashboard_cache(("is_valid_turn",))
    _load_services(("check_match_exists",))
    turn = str(turn_num).strip() if turn_num is not None else ""
    if not turn.isdigit() or not is_valid_turn(turn):
        return api_error("invalid_turn", "轮次值无效")

    table = parse_table_number(table_num)
    if table is None:
        return api_error("invalid_table", "桌号无效")

    turn_int = int(turn)
    if not check_match_exists(get_db_connection, table, turn_int):
        return api_error("match_not_found", "未找到该桌对阵")

    match_info = find_match_info(load_fight_info(turn_int), table)
    if match_info is None:
        return api_error("match_not_found", "未找到该桌对阵")

    match_info["turn_num"] = turn_int
    return api_success("录分对阵已获取", match_info)


def get_match_for_current_turn(get_db_connection, load_fight_info, table_num):
    _load_dashboard_cache(("get_turn", "is_valid_turn"))
    current_turn = get_turn()
    if not is_valid_turn(current_turn):
        return api_error("invalid_turn", "当前轮次未设置")
    return get_match_for_score(get_db_connection, load_fight_info, current_turn, table_num)


def submit_score(get_db_connection, load_fight_info, turn_num, table_num, score_x, score_y, winner):
    _load_dashboard_cache(("is_valid_turn", "mark_snapshot_stale"))
    _load_services(
        (
            "check_match_exists",
            "build_score_update",
            "is_writeback_enabled",
            "enqueue_score_update",
            "apply_score_update",
            "save_score_log",
        )
    )
    match_result = get_match_for_score(get_db_connection, load_fight_info, turn_num, table_num)
    if not match_result.get("ok"):
        return match_result

    match_info = match_result["data"]
    update_payload = build_score_update(
        team1_name=match_info["team1_name"],
        team2_name=match_info["team2_name"],
        score_x_raw=score_x,
        score_y_raw=score_y,
        winner_raw=winner,
    )
    if not update_payload.get("ok"):
        error = build_score_error(update_payload.get("error"))
        message = "未选择最终局赢家" if error == "winner_required_when_tied" else "请输入合法的得分范围(2~32)"
        return api_error(error, message)

    if is_writeback_enabled():
        write_result = enqueue_score_update(
            int(match_info["turn_num"]),
            update_payload["small_scores"],
            update_payload["big_scores"],
        )
        if not (write_result.get("ok") and write_result.get("queued")):
            return api_error(
                "score_write_failed",
                "得分写回队列提交失败",
                {"error": write_result.get("error")},
            )
        queued = True
    else:
        write_result = apply_score_update(
            get_db_connection,
            int(match_info["turn_num"]),
            update_payload["small_scores"],
            update_payload["big_scores"],
        )
        if not write_result.get("ok"):
            return api_error("score_write_failed", "得分写入失败", {"error": write_result.get("error")})
        queued = False

    mark_snapshot_stale()
    save_score_log(
        match_info["turn_num"],
        match_info["table_num"],
        match_info["team1_name"],
        match_info["team1_members"],
        match_info["team2_name"],
        match_info["team2_members"],
        score_x,
        score_y,
    )
    return api_success(
        "得分已提交",
        {
            "turn_num": match_info["turn_num"],
            "table_num": match_info["table_num"],
            "queued": queued,
        },
    )


def submit_score_for_current_turn(get_db_connection, load_fight_info, table_num, score_x, score_y, winner):
    _load_dashboard_cache(("get_turn", "is_valid_turn"))
    current_turn = get_turn()
    if not is_valid_turn(current_turn):
        return api_error("invalid_turn", "当前轮次未设置")
    return submit_score(
        get_db_connection,
        load_fight_info,
        current_turn,
        table_num,
        score_x,
        score_y,
        winner,
    )
