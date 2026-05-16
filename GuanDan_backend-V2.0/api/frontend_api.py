from flask import Blueprint, jsonify

from api.dashboard_cache import (
    is_valid_turn,
    build_time_message,
)
from services.redis_runtime import RedisRuntimeError, runtime_error_to_api_payload
from services.runtime_store import get_current_turn
from services.runtime_views import read_dashboard_view

frontend_api_bp = Blueprint("frontend_api", __name__)


def _empty_dashboard_snapshot(turn):
    return {
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
    }


def get_runtime_dashboard_snapshot():
    """读取 Redis 运行态大屏视图，并补齐进程内倒计时兼容文案。"""
    turn = get_current_turn()
    if not is_valid_turn(turn):
        return _empty_dashboard_snapshot(turn)

    snapshot = dict(read_dashboard_view(turn) or {})
    snapshot["time_message"] = build_time_message()
    return snapshot


def _runtime_error_response(exc):
    return jsonify(runtime_error_to_api_payload(exc))


@frontend_api_bp.route('/TURNsinfo', methods=['GET'])
def turns_info():
    """返回当前轮次（前端状态栏展示用）。"""
    try:
        return jsonify({"TURN": get_current_turn()})
    except RedisRuntimeError as exc:
        return _runtime_error_response(exc)


@frontend_api_bp.route('/timesinfo', methods=['GET'])
def times_info():
    """返回当前倒计时文案。"""
    return jsonify({"time_message": build_time_message()})


@frontend_api_bp.route('/matchesinfo', methods=['GET'])
def matches_info():
    """返回当前轮次对阵信息。"""
    try:
        snapshot = get_runtime_dashboard_snapshot()
    except RedisRuntimeError as exc:
        return _runtime_error_response(exc)
    return jsonify({"matchesinfo": snapshot.get("matchesinfo", [])})


@frontend_api_bp.route('/scoresinfo', methods=['GET'])
def scores_info():
    """返回当前轮次小分信息。"""
    try:
        snapshot = get_runtime_dashboard_snapshot()
    except RedisRuntimeError as exc:
        return _runtime_error_response(exc)
    return jsonify({"scoresinfo": snapshot.get("scoresinfo", [])})


@frontend_api_bp.route('/sumteaminfo', methods=['GET'])
def sum_team_info():
    """返回队伍维度的当前轮积分与累计积分。"""
    try:
        snapshot = get_runtime_dashboard_snapshot()
    except RedisRuntimeError as exc:
        return _runtime_error_response(exc)
    return jsonify(snapshot.get("sumteaminfo", {
        "current_turn": [],
        "total_until_turn": [],
    }))


@frontend_api_bp.route('/officescore', methods=['GET'])
def office_score():
    """返回办公室维度的当前轮积分与累计积分。"""
    try:
        snapshot = get_runtime_dashboard_snapshot()
    except RedisRuntimeError as exc:
        return _runtime_error_response(exc)
    return jsonify(snapshot.get("officescore", {
        "current_turn": [],
        "total_until_turn": [],
    }))


@frontend_api_bp.route('/dashboard_snapshot', methods=['GET'])
def dashboard_snapshot():
    """聚合快照接口：前端一次请求拿齐展示数据。"""
    try:
        return jsonify(get_runtime_dashboard_snapshot())
    except RedisRuntimeError as exc:
        return _runtime_error_response(exc)
