from flask import Blueprint, jsonify

from api.dashboard_cache import (
    get_turn,
    is_valid_turn,
    build_time_message,
    ensure_snapshot_worker_started,
    ensure_dashboard_snapshot_fresh,
    get_snapshot_copy,
    slice_team_rankings_for_screen,
)

frontend_api_bp = Blueprint("frontend_api", __name__)


@frontend_api_bp.route('/TURNsinfo', methods=['GET'])
def turns_info():
    """返回当前轮次（前端状态栏展示用）。"""
    return jsonify({"TURN": get_turn()})


@frontend_api_bp.route('/timesinfo', methods=['GET'])
def times_info():
    """返回当前倒计时文案。"""
    return jsonify({"time_message": build_time_message()})


@frontend_api_bp.route('/matchesinfo', methods=['GET'])
def matches_info():
    """返回当前轮次对阵信息。"""

    # 确保后台快照线程已启动，并且快照是新鲜的（过期则刷新）
    ensure_snapshot_worker_started()
    ensure_dashboard_snapshot_fresh()

    turn = get_turn()
    if not is_valid_turn(turn):
        return jsonify({"error": "invalid turn"})

    snapshot = get_snapshot_copy()
    return jsonify({"matchesinfo": snapshot["matchesinfo"]})


@frontend_api_bp.route('/scoresinfo', methods=['GET'])
def scores_info():
    """返回当前轮次小分信息。"""
    ensure_snapshot_worker_started()
    ensure_dashboard_snapshot_fresh()

    turn = get_turn()
    if not is_valid_turn(turn):
        return jsonify({"error": "invalid turn"})

    snapshot = get_snapshot_copy()
    return jsonify({"scoresinfo": snapshot["scoresinfo"]})


@frontend_api_bp.route('/sumteaminfo', methods=['GET'])
def sum_team_info():
    """返回队伍维度的当前轮积分与累计积分。"""
    ensure_snapshot_worker_started()
    ensure_dashboard_snapshot_fresh()

    turn = get_turn()
    if not is_valid_turn(turn):
        return jsonify({"error": "invalid turn"})

    snapshot = get_snapshot_copy()
    # 维持原有大屏轮播分段逻辑
    current_results, total_results = slice_team_rankings_for_screen(
        snapshot["team_current_full"], snapshot["team_total_full"]
    )
    return jsonify({
        "current_turn": current_results,
        "total_until_turn": total_results,
    })


@frontend_api_bp.route('/officescore', methods=['GET'])
def office_score():
    """返回办公室维度的当前轮积分与累计积分。"""
    ensure_snapshot_worker_started()
    ensure_dashboard_snapshot_fresh()

    turn = get_turn()
    if not is_valid_turn(turn):
        return jsonify({"error": "invalid turn"})

    snapshot = get_snapshot_copy()
    return jsonify({
        "current_turn": snapshot["office_current"],
        "total_until_turn": snapshot["office_total"],
    })


@frontend_api_bp.route('/dashboard_snapshot', methods=['GET'])
def dashboard_snapshot():
    """聚合快照接口：前端一次请求拿齐展示数据。"""
    ensure_snapshot_worker_started()
    ensure_dashboard_snapshot_fresh()

    turn = get_turn()
    if not is_valid_turn(turn):
        # 轮次未设置时返回空结构，前端可无异常渲染
        return jsonify({
            "TURN": turn,
            "time_message": build_time_message(),
            "error": "invalid turn",
            "matchesinfo": [],
            "scoresinfo": [],
            "sumteaminfo": {
                "current_turn": [],
                "total_until_turn": [],
            },
            "officescore": {
                "current_turn": [],
                "total_until_turn": [],
            },
        })

    snapshot = get_snapshot_copy()
    team_current, team_total = slice_team_rankings_for_screen(
        snapshot["team_current_full"], snapshot["team_total_full"]
    )
    return jsonify({
        "TURN": turn,
        "time_message": build_time_message(),
        "matchesinfo": snapshot["matchesinfo"],
        "scoresinfo": snapshot["scoresinfo"],
        "sumteaminfo": {
            "current_turn": team_current,
            "total_until_turn": team_total,
        },
        "officescore": {
            "current_turn": snapshot["office_current"],
            "total_until_turn": snapshot["office_total"],
        },
        "snapshot_updated_at": snapshot["updated_at"],
    })

