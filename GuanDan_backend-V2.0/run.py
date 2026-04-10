from flask import Flask, render_template, request, redirect, url_for, flash
import os
from flask_cors import CORS
from werkzeug.utils import secure_filename

from app.config import Config
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
    ensure_writeback_worker_started,
)
from services.stats_service import (
    fetch_create_table_rows,
    check_match_exists,
)
from api.frontend_api import frontend_api_bp
from api.dashboard_cache import (
    is_valid_turn,
    get_turn,
    set_turn as set_current_turn,
    reset_turn,
    start_round_timer,
    stop_round_timer,
    mark_snapshot_stale,
    ensure_snapshot_worker_started,
)

app = Flask(__name__)
CORS(app, supports_credentials=True)  # 全局允许跨域请求

# 如需限制来源，可改为：
# CORS(app, origins="http://localhost:5173", supports_credentials=True)
# CORS(app, origins=["http://8.138.251.93:6888"], supports_credentials=True)

app.secret_key = 'your_secret_key'
app.register_blueprint(frontend_api_bp)

get_db_connection = Config().get_db_connection

MAX_TABLE_NUMBER = 22
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")


# 对阵信息缓存（用于录分页面）
_fight_cache = {}
CACHE_TTL = 60000000  # 缓存有效期（秒）
# Redis 读缓存生存时间（秒）
REDIS_FIGHT_CACHE_TTL = 300
play_button_message = False


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
    stop_round_timer()
    flash("已暂停计时", 'success')
    return redirect(url_for('create_table'))


@app.route('/start_timer', methods=['POST'])
def start_timer():
    if start_round_timer():
        flash("已开始计时", 'success')
    else:
        flash("当前轮次未设置，无法开始计时", 'danger')
    return redirect(url_for('create_table'))


# 清空所有业务表
@app.route('/clear_tables', methods=['POST'])
def clear_tables():
    result = clear_all_tables(get_db_connection)
    if result.get('ok'):
        clear_fight_cache()
        reset_turn()
        mark_snapshot_stale()
        flash('All tables have been cleared', 'success')
    else:
        flash(f"Failed to clear tables: {result.get('error', 'unknown error')}", 'danger')
    return redirect(url_for('index'))


# 首页：上传 Excel 并导入数据库
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('Please choose a file to upload', 'danger')
            return redirect(url_for('index'))

        if not file.filename or not file.filename.endswith('.xlsx'):
            flash('Please upload an .xlsx file', 'danger')
            return redirect(url_for('index'))

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filename = secure_filename(file.filename)
        if not filename:
            flash('Invalid filename', 'danger')
            return redirect(url_for('index'))

        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)

        import_result = import_registration_excel(filepath, get_db_connection)
        if not import_result.get('ok'):
            flash(f"Import failed: {import_result.get('error', 'unknown error')}", 'danger')
            return redirect(url_for('index'))

        clear_fight_cache()
        reset_turn()
        mark_snapshot_stale()
        flash('File imported successfully', 'success')
        return redirect(url_for('index'))

    rows = fetch_team_info_rows(get_db_connection)
    return render_template('index.html', rows=rows)


@app.route('/set_turn', methods=['POST'])
def set_turn():
    new_turn = request.form.get('turn')
    if new_turn == 'null':
        reset_turn()
    elif new_turn and new_turn.isdigit() and is_valid_turn(new_turn):
        set_current_turn(str(new_turn))
    else:
        flash('Invalid TURN value', 'danger')

    mark_snapshot_stale()
    return redirect(url_for('create_table'))


# 第二个页面：展示 mini_team_info 得分表
@app.route('/create_table', methods=['GET'])
def create_table():
    mini_team_info = fetch_create_table_rows(get_db_connection)
    mini_team_info_with_rank = [(i + 1, *row) for i, row in enumerate(mini_team_info)]
    return render_template(
        'create_table.html',
        mini_team_info=mini_team_info_with_rank,
        current_turn=get_turn(),
    )


# 点击按钮触发 post，随机分配对战信息并覆盖 fight_info 表
@app.route('/generate_matches', methods=['POST', 'GET'])
def generate_matches():
    if request.method == 'POST':
        teams, team_levels_list = fetch_match_generation_source(get_db_connection)

        match_result = generate_round_pairs(teams, team_levels_list, rounds=3)
        if not match_result['success']:
            flash('Failed to generate matches, please try again', 'danger')
            return redirect(url_for('generate_matches'))

        write_result = replace_fight_info(
            get_db_connection,
            match_result['pairs'],
            match_result['team_members'],
            match_result['team_levels'],
        )
        clear_fight_cache()
        mark_snapshot_stale()
        if not write_result.get('ok'):
            flash(f"Failed to save matches: {write_result.get('error', 'unknown error')}", 'danger')
            return redirect(url_for('generate_matches'))

        return redirect(url_for('generate_matches'))

    fights = fetch_all_fights(get_db_connection)
    return render_template('generate_matches.html', fights=fights)


@app.route('/select_table', methods=['GET', 'POST'])
def select_table():
    if request.method == 'POST':
        table_num = int(request.form['table_num'])
        current_turn = get_turn()
        if not is_valid_turn(current_turn):
            flash('Current turn is not set', 'danger')
            return redirect(url_for('select_table'))

        turn_num = int(current_turn)
        if table_num > MAX_TABLE_NUMBER or table_num < 1:
            flash(f'Invalid table number: {table_num}', 'danger')
            return redirect(url_for('select_table'))

        return redirect(url_for('input_scores', table_num=table_num, turn_num=turn_num, modify_type=0))

    return render_template('select_table.html')


# 第五个页面：后台修改比分（提供桌号和轮次）
@app.route('/modify_select_table', methods=['GET', 'POST'])
def modify_select_table():
    if request.method == 'POST':
        table_num = int(request.form['table_num'])
        turn_num = int(request.form['turn_num'])

        if not is_valid_turn(turn_num):
            flash(f"无效的轮次 {turn_num}", 'danger')
            return redirect(url_for('modify_select_table'))

        match_exists = check_match_exists(get_db_connection, table_num, turn_num)
        if not match_exists:
            flash(f"无效的桌号 {table_num}", 'danger')
            return redirect(url_for('modify_select_table'))

        return redirect(url_for('input_scores', table_num=table_num, turn_num=turn_num, modify_type=1))

    return render_template('modify_select_table.html')


# 第六个页面：根据桌号更新比分
@app.route('/input_scores/<int:table_num>/<int:turn_num>/<int:modify_type>', methods=['GET', 'POST'])
def input_scores(table_num, turn_num, modify_type):
    fights = load_fight_info(turn_num)
    match_info = next((f[1:] for f in fights if f[0] == table_num), None)

    if not match_info:
        flash("Match info not found for this table", "danger")
        return redirect(url_for('select_table'))

    team1_name, team1_members, team2_name, team2_members = match_info

    if request.method == 'GET':
        return render_template(
            'input_scores.html',
            turn_num=turn_num,
            table_num=table_num,
            modify_type=modify_type,
            team1_name=team1_name,
            team2_name=team2_name,
            team1_members=team1_members,
            team2_members=team2_members,
        )

    score_x = request.form.get('score_x', '').strip().lower()
    score_y = request.form.get('score_y', '').strip().lower()
    winner = request.form.get('winner', '').strip().lower()

    update_payload = build_score_update(
        team1_name=team1_name,
        team2_name=team2_name,
        score_x_raw=score_x,
        score_y_raw=score_y,
        winner_raw=winner,
    )

    if not update_payload["ok"]:
        if update_payload["error"] == "未选择最终局赢家":
            flash("未选择该轮最后一局的赢家", "danger")
        else:
            flash("请输入合法的得分范围(2~32)", "danger")
        return redirect(url_for('input_scores', table_num=table_num, turn_num=turn_num, modify_type=modify_type))

    # 写路径策略：
    if is_writeback_enabled():
        # 1) 开启写回队列：先入 Redis 队列，达到批量阈值/时间窗口后落库 MySQL
        write_result = enqueue_score_update(
            turn_num,
            update_payload["small_scores"],
            update_payload["big_scores"],
        )
        # 入队成功时视为“已接收请求”
        if write_result.get("ok") and write_result.get("queued"):
            write_result = {"ok": True, "queued": True}
    else:
        # 2) 未开启或 Redis 不可用：直接写 MySQL（兼容旧模式）
        write_result = apply_score_update(
            get_db_connection,
            turn_num,
            update_payload["small_scores"],
            update_payload["big_scores"],
        )

    if not write_result.get("ok"):
        flash(f"Failed to update score: {write_result.get('error', 'unknown error')}", "danger")
        return redirect(url_for('input_scores', table_num=table_num, turn_num=turn_num, modify_type=modify_type))

    # 对阵缓存与比分无关，这里不清空 fight_info 缓存
    mark_snapshot_stale()
    save_score_log(turn_num, table_num, team1_name, team1_members, team2_name, team2_members, score_x, score_y)

    if write_result.get("queued"):
        flash(f"Round {turn_num}, table {table_num} 得分进入更新队列", 'success')
    else:
        flash(f"Round {turn_num}, table {table_num} 得分已直接更新", 'success')
    if modify_type:
        return redirect(url_for('modify_select_table'))
    return redirect(url_for('select_table'))


if __name__ == '__main__':
    # 启动快照线程
    ensure_snapshot_worker_started()
    # 启动比分写回线程（仅在 SCORE_WRITEBACK_ENABLED=1 且 Redis 可用时生效）
    ensure_writeback_worker_started(get_db_connection)
    app.run(host="0.0.0.0", port=5000, debug=True)
