from flask import Blueprint, current_app, jsonify, request

from api.dashboard_cache import get_turn, is_valid_turn
from services import admin_workflow as workflow

score_api_bp = Blueprint("score_api", __name__, url_prefix="/api/score")


def json_response(payload):
    return jsonify(payload)


def current_app_get_db_connection():
    return current_app.config["GUANDAN_GET_DB_CONNECTION"]


def current_app_load_fight_info():
    return current_app.config["GUANDAN_LOAD_FIGHT_INFO"]


@score_api_bp.route("/current-turn", methods=["GET"])
def current_turn():
    turn = get_turn()
    if not is_valid_turn(turn):
        return json_response(
            workflow.api_error("invalid_turn", "当前轮次未设置", {"turn": turn})
        )
    return json_response(workflow.api_success("当前轮次加载成功", {"turn": turn}))


@score_api_bp.route("/table", methods=["GET"])
def table():
    return json_response(
        workflow.get_match_for_current_turn(
            current_app_get_db_connection(),
            current_app_load_fight_info(),
            request.args.get("table"),
        )
    )


@score_api_bp.route("/table", methods=["POST"])
def submit_table_score():
    payload = request.get_json(silent=True) or {}
    return json_response(
        workflow.submit_score_for_current_turn(
            current_app_get_db_connection(),
            current_app_load_fight_info(),
            payload.get("table"),
            payload.get("score_x"),
            payload.get("score_y"),
            payload.get("winner"),
        )
    )
