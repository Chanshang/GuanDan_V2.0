from flask import Blueprint, current_app, jsonify, request

from services import admin_workflow as workflow

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


def json_response(payload):
    return jsonify(payload)


def current_app_get_db_connection():
    return current_app.config["GUANDAN_GET_DB_CONNECTION"]


def current_app_upload_dir():
    return current_app.config["GUANDAN_UPLOAD_DIR"]


def current_app_clear_fight_cache():
    return current_app.config["GUANDAN_CLEAR_FIGHT_CACHE"]


def current_app_load_fight_info():
    return current_app.config["GUANDAN_LOAD_FIGHT_INFO"]


@admin_api_bp.route("/overview", methods=["GET"])
def overview():
    return json_response(workflow.get_overview(current_app_get_db_connection()))


@admin_api_bp.route("/import", methods=["POST"])
def import_registration():
    return json_response(
        workflow.import_registration_file(
            request.files.get("file"),
            current_app_get_db_connection(),
            current_app_upload_dir(),
            current_app_clear_fight_cache(),
        )
    )


@admin_api_bp.route("/clear", methods=["POST"])
def clear_business_data():
    return json_response(
        workflow.clear_business_data(
            current_app_get_db_connection(),
            current_app_clear_fight_cache(),
        )
    )


@admin_api_bp.route("/turn", methods=["POST"])
def set_turn():
    payload = request.get_json(silent=True) or {}
    return json_response(workflow.set_turn_value(payload.get("turn")))


@admin_api_bp.route("/timer/start", methods=["POST"])
def start_timer():
    return json_response(workflow.start_timer_value())


@admin_api_bp.route("/timer/stop", methods=["POST"])
def stop_timer():
    return json_response(workflow.stop_timer_value())


@admin_api_bp.route("/matches", methods=["GET"])
def matches():
    return json_response(workflow.get_all_matches(current_app_get_db_connection()))


@admin_api_bp.route("/matches/generate", methods=["POST"])
def generate_matches():
    return json_response(
        workflow.generate_matches_workflow(
            current_app_get_db_connection(),
            current_app_clear_fight_cache(),
        )
    )


@admin_api_bp.route("/score-match", methods=["GET"])
def score_match():
    return json_response(
        workflow.get_match_for_score(
            current_app_get_db_connection(),
            current_app_load_fight_info(),
            request.args.get("turn"),
            request.args.get("table"),
        )
    )


@admin_api_bp.route("/scores", methods=["POST"])
def submit_scores():
    payload = request.get_json(silent=True) or {}
    return json_response(
        workflow.submit_score(
            current_app_get_db_connection(),
            current_app_load_fight_info(),
            payload.get("turn"),
            payload.get("table"),
            payload.get("score_x"),
            payload.get("score_y"),
            payload.get("winner"),
        )
    )
