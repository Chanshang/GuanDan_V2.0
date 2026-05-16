from flask import Flask, render_template, request, redirect, url_for, flash
import os
from flask_cors import CORS
from werkzeug.utils import secure_filename

from app.config import Config
from services import admin_workflow as workflow
from services.clear_all_service import clear_all_tables
from services.import_service import import_registration_excel, fetch_team_info_rows
from services.log_service import save_score_log
from services.match_algorithm import generate_round_pairs
from services.match_service import (
    fetch_match_generation_source,
    replace_fight_info,
    fetch_all_fights,
    fetch_fight_info_by_turn,
)
from services.scoring import build_score_update
from services.score_service import apply_score_update
from services.redis_cache_service import (
    read_fight_info_from_redis,
    write_fight_info_to_redis,
    clear_all_fight_cache_in_redis,
)
from services.score_writeback_service import (
    is_writeback_enabled,
    enqueue_score_update,
)
from services.runtime_flush_service import ensure_runtime_flush_worker_started
from services.runtime_views import read_create_table_view, read_admin_matches_view
from api.frontend_api import frontend_api_bp
from api.admin_api import admin_api_bp
from api.score_api import score_api_bp
from api.dashboard_cache import (
    get_turn,
    set_turn as set_current_turn,
    reset_turn,
    start_round_timer,
    stop_round_timer,
    mark_snapshot_stale,
)

app = Flask(__name__)
CORS(app, supports_credentials=True)  # 全局允许跨域请求

# 如需限制来源，可改为：
# CORS(app, origins="http://localhost:5173", supports_credentials=True)
# CORS(app, origins=["http://8.138.251.93:6888"], supports_credentials=True)

app.secret_key = 'your_secret_key'
app.register_blueprint(frontend_api_bp)
app.register_blueprint(admin_api_bp)
app.register_blueprint(score_api_bp)

get_db_connection = Config().get_db_connection

MAX_TABLE_NUMBER = 22
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
app.config["GUANDAN_GET_DB_CONNECTION"] = get_db_connection
app.config["GUANDAN_UPLOAD_DIR"] = UPLOAD_DIR


# 对阵信息缓存（用于录分页面）
_fight_cache = {}
CACHE_TTL = 60000000  # 缓存有效期（秒）
# Redis 读缓存生存时间（秒）
REDIS_FIGHT_CACHE_TTL = 300
play_button_message = False


def _adapt_create_table_row(rank, row):
    if isinstance(row, dict):
        team = row.get("team", row)
        fight_id = row.get("fight_id", "")
    else:
        team = row
        fight_id = ""

    if isinstance(team, dict):
        return (
            rank,
            team.get("id", ""),
            team.get("office", ""),
            team.get("team_name", ""),
            team.get("member_name", ""),
            team.get("big_score", ""),
            team.get("small_score", ""),
            team.get("turn", ""),
            fight_id,
        )

    if isinstance(team, (list, tuple)):
        team_name = team[0] if len(team) > 0 else ""
        turn = team[1] if len(team) > 1 else ""
        big_score = team[2] if len(team) > 2 else ""
        small_score = team[3] if len(team) > 3 else ""
        return (rank, "", "", team_name, "", big_score, small_score, turn, fight_id)

    return (rank, "", "", "", "", "", "", "", fight_id)


def _adapt_admin_match_row(row):
    if isinstance(row, (list, tuple)):
        return tuple(row)
    if not isinstance(row, dict):
        return tuple()
    return (
        row.get("table_no", ""),
        row.get("team_name_1", ""),
        row.get("members_1", ""),
        row.get("team_name_2", ""),
        row.get("members_2", ""),
        row.get("turn", ""),
        row.get("team_level_1", ""),
        row.get("team_level_2", ""),
    )


def clear_fight_cache():
    # 同时清理本地进程缓存和 Redis 缓存，避免读到旧对阵
    _fight_cache.clear()
    clear_all_fight_cache_in_redis()


def load_fight_info(turn_num):
    """读取某轮对阵信息（本地缓存 -> Redis -> MySQL）。"""
    from time import time
    global _fight_cache

    # 1) 本地进程缓存
    if turn_num in _fight_cache:
        data, expire_time = _fight_cache[turn_num]
        if time() < expire_time:
            return data

    # 2) Redis 跨进程缓存
    redis_rows = read_fight_info_from_redis(turn_num)
    if redis_rows is not None:
        _fight_cache[turn_num] = (redis_rows, time() + CACHE_TTL)

        # 若 Redis 中有数据，说明之前的 MySQL 写入已经完成了，直接返回即可
        return redis_rows

    # 3) 回源 MySQL
    rows = fetch_fight_info_by_turn(get_db_connection, turn_num)

    # 回写双层缓存
    _fight_cache[turn_num] = (rows, time() + CACHE_TTL)
    write_fight_info_to_redis(turn_num, rows, ttl_seconds=REDIS_FIGHT_CACHE_TTL)
    return rows


app.config["GUANDAN_CLEAR_FIGHT_CACHE"] = clear_fight_cache
app.config["GUANDAN_LOAD_FIGHT_INFO"] = load_fight_info

################################################################
# 下面是后台功能接口

@app.route('/play_button', methods=['POST'])
def play_button():
    global play_button_message
    play_button_message = True
    flash("已点击播放按钮", 'success')
    return redirect(url_for('create_table'))


@app.route('/stop_timer', methods=['POST'])
def stop_timer():
    result = workflow.stop_timer_value()
    flash(result["message"], "success" if result["ok"] else "danger")
    return redirect(url_for('create_table'))


@app.route('/start_timer', methods=['POST'])
def start_timer():
    result = workflow.start_timer_value()
    flash(result["message"], "success" if result["ok"] else "danger")
    return redirect(url_for('create_table'))


# 清空所有业务表
@app.route('/clear_tables', methods=['POST'])
def clear_tables():
    result = workflow.clear_business_data(get_db_connection, clear_fight_cache)
    flash(result["message"], "success" if result["ok"] else "danger")
    return redirect(url_for('index'))


# 首页：上传 Excel 并导入数据库
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        result = workflow.import_registration_file(file, get_db_connection, UPLOAD_DIR, clear_fight_cache)
        flash(result["message"], "success" if result["ok"] else "danger")
        return redirect(url_for('index'))

    rows = fetch_team_info_rows(get_db_connection)
    return render_template('index.html', rows=rows)


@app.route('/set_turn', methods=['POST'])
def set_turn():
    result = workflow.set_turn_value(request.form.get('turn'))
    flash(result["message"], "success" if result["ok"] else "danger")
    return redirect(url_for('create_table'))


# 第二个页面：展示 mini_team_info 得分表
@app.route('/create_table', methods=['GET'])
def create_table():
    view = read_create_table_view()
    rows = view.get('rows', [])
    mini_team_info_with_rank = [
        _adapt_create_table_row(i + 1, row)
        for i, row in enumerate(rows)
    ]
    return render_template(
        'create_table.html',
        mini_team_info=mini_team_info_with_rank,
        current_turn=get_turn(),
    )


# 点击按钮触发 post，随机分配对战信息并覆盖 fight_info 表
@app.route('/generate_matches', methods=['POST', 'GET'])
def generate_matches():
    if request.method == 'POST':
        result = workflow.generate_matches_workflow(get_db_connection, clear_fight_cache)
        flash(result["message"], "success" if result["ok"] else "danger")
        return redirect(url_for('generate_matches'))

    view = read_admin_matches_view()
    fights = [_adapt_admin_match_row(row) for row in view.get('matches', [])]
    return render_template('generate_matches.html', fights=fights)


@app.route('/select_table', methods=['GET', 'POST'])
def select_table():
    if request.method == 'POST':
        result = workflow.get_match_for_current_turn(
            get_db_connection,
            load_fight_info,
            request.form.get('table_num'),
        )
        if not result["ok"]:
            flash(result["message"], 'danger')
            return redirect(url_for('select_table'))

        match_info = result["data"]
        return redirect(
            url_for(
                'input_scores',
                table_num=match_info["table_num"],
                turn_num=match_info["turn_num"],
                modify_type=0,
            )
        )

    return render_template('select_table.html')


# 第五个页面：后台修改比分（提供桌号和轮次）
@app.route('/modify_select_table', methods=['GET', 'POST'])
def modify_select_table():
    if request.method == 'POST':
        result = workflow.get_match_for_score(
            get_db_connection,
            load_fight_info,
            request.form.get('turn_num'),
            request.form.get('table_num'),
        )
        if not result["ok"]:
            if result.get("error") in {"invalid_table", "match_not_found"}:
                flash(f"无效的桌号 {request.form.get('table_num')}", 'danger')
            else:
                flash(result["message"], 'danger')
            return redirect(url_for('modify_select_table'))

        match_info = result["data"]
        return redirect(
            url_for(
                'input_scores',
                table_num=match_info["table_num"],
                turn_num=match_info["turn_num"],
                modify_type=1,
            )
        )

    return render_template('modify_select_table.html')


# 第六个页面：根据桌号更新比分
@app.route('/input_scores/<int:table_num>/<int:turn_num>/<int:modify_type>', methods=['GET', 'POST'])
def input_scores(table_num, turn_num, modify_type):
    if request.method == 'GET':
        result = workflow.get_match_for_score(
            get_db_connection,
            load_fight_info,
            turn_num,
            table_num,
        )
        if not result["ok"]:
            flash(result["message"], "danger")
            if modify_type:
                return redirect(url_for('modify_select_table'))
            return redirect(url_for('select_table'))

        match_info = result["data"]
        return render_template(
            'input_scores.html',
            turn_num=turn_num,
            table_num=table_num,
            modify_type=modify_type,
            team1_name=match_info["team1_name"],
            team2_name=match_info["team2_name"],
            team1_members=match_info["team1_members"],
            team2_members=match_info["team2_members"],
        )

    result = workflow.submit_score(
        get_db_connection,
        load_fight_info,
        turn_num,
        table_num,
        request.form.get('score_x', '').strip().lower(),
        request.form.get('score_y', '').strip().lower(),
        request.form.get('winner', '').strip().lower(),
    )

    if not result["ok"]:
        flash(result["message"], "danger")
        return redirect(url_for('input_scores', table_num=table_num, turn_num=turn_num, modify_type=modify_type))

    flash(result["message"], "success")
    if modify_type:
        return redirect(url_for('modify_select_table'))
    return redirect(url_for('select_table'))


if __name__ == '__main__':
    # 启动 Redis runtime 写回线程。
    ensure_runtime_flush_worker_started(get_db_connection)
    app.run(host="0.0.0.0", port=5000, debug=True)
