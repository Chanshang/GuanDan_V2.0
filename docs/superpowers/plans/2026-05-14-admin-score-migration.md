# 后台管理与录分迁移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Flask 模板后台和录分入口迁移为 Vue 路由页面，并新增稳定的 `/api/admin/*`、`/api/score/*` JSON 接口。

**Architecture:** 后端先抽 `services/admin_workflow.py` 作为业务编排层，旧模板路由和新 JSON API 共享同一套 helper。前端引入 `vue-router`，将现有大屏迁到 `/screen`，新增 `/admin` 和 `/score` 两组页面。旧 Flask 模板第一版保留，作为现场回滚兜底。

**Tech Stack:** Flask、unittest、Vue 3、Vite、vue-router、MySQL、Redis、Conda 环境 `flask_app_env`（`C:\Users\Administrator\miniconda3\envs\flask_app_env`）。

---

## 文件结构

后端新增或修改：

- Create: `GuanDan_backend-V2.0/services/admin_workflow.py`
  - 统一后台导入、清空、轮次、计时、对阵生成、对阵查询、比分提交等业务编排。
- Create: `GuanDan_backend-V2.0/api/admin_api.py`
  - 管理后台 JSON API。
- Create: `GuanDan_backend-V2.0/api/score_api.py`
  - 录分页面 JSON API。
- Modify: `GuanDan_backend-V2.0/run.py`
  - 注册新 Blueprint，并让旧模板路由复用 `admin_workflow`。
- Create: `GuanDan_backend-V2.0/tests/test_admin_workflow.py`
  - 针对 helper 的无数据库单元测试。
- Create: `GuanDan_backend-V2.0/tests/test_admin_score_api.py`
  - 针对 API 响应格式和关键分支的 Flask test client 测试。

前端新增或修改：

- Modify: `GuanDanFront-V2.0/package.json`
  - 增加 `vue-router` 依赖。
- Modify: `GuanDanFront-V2.0/package-lock.json`
  - 由 `npm install vue-router@4` 更新。
- Modify: `GuanDanFront-V2.0/src/main.js`
  - 挂载 router。
- Modify: `GuanDanFront-V2.0/src/App.vue`
  - 改为路由出口。
- Create: `GuanDanFront-V2.0/src/router/index.js`
  - 定义 `/`、`/screen`、`/admin`、`/score`、`/score/:turn/:table`。
- Create: `GuanDanFront-V2.0/src/views/ScreenView.vue`
  - 承接当前大屏页面逻辑。
- Create: `GuanDanFront-V2.0/src/views/AdminView.vue`
  - 管理后台第一版页面。
- Create: `GuanDanFront-V2.0/src/views/ScoreEntryView.vue`
  - 桌号录分入口。
- Create: `GuanDanFront-V2.0/src/views/ScoreFormView.vue`
  - 比分录入表单。
- Create: `GuanDanFront-V2.0/src/api/admin.js`
  - 后台管理 API 封装。
- Create: `GuanDanFront-V2.0/src/api/score.js`
  - 录分 API 封装。
- Modify: `GuanDanFront-V2.0/src/api.js`
  - 导出通用 `request`，供新 API wrapper 复用。
- Modify: `GuanDanFront-V2.0/src/components/QRCode.vue`
  - 将二维码指向 `/score`。

提交约束：

- 不使用 `git add .`。
- 不提交 `__pycache__`、运行日志、上传文件、`node_modules`。
- 不批量删除文件或目录。
- 当前仓库已有其他本地改动，实施时每个提交只暂存本任务相关文件。

---

### Task 1: 后端业务编排 helper

**Files:**
- Create: `GuanDan_backend-V2.0/services/admin_workflow.py`
- Create: `GuanDan_backend-V2.0/tests/test_admin_workflow.py`

- [ ] **Step 1: 编写失败测试**

Create `GuanDan_backend-V2.0/tests/test_admin_workflow.py`:

```python
import unittest

from services.admin_workflow import (
    api_error,
    api_success,
    parse_table_number,
    find_match_info,
    build_score_error,
)


class TestAdminWorkflowHelpers(unittest.TestCase):
    def test_api_success_shape(self):
        payload = api_success("完成", {"turn": "1"})
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["message"], "完成")
        self.assertEqual(payload["data"], {"turn": "1"})

    def test_api_error_shape(self):
        payload = api_error("invalid_turn", "当前轮次未设置")
        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["error"], "invalid_turn")
        self.assertEqual(payload["message"], "当前轮次未设置")

    def test_parse_table_number(self):
        self.assertEqual(parse_table_number("3"), 3)
        self.assertIsNone(parse_table_number("0"))
        self.assertIsNone(parse_table_number("abc"))

    def test_find_match_info(self):
        fights = [(1, "A队", "张三、李四", "B队", "王五、赵六")]
        match = find_match_info(fights, 1)
        self.assertEqual(match["team1_name"], "A队")
        self.assertEqual(match["team2_members"], "王五、赵六")
        self.assertIsNone(find_match_info(fights, 2))

    def test_build_score_error(self):
        self.assertEqual(build_score_error("未选择最终局赢家"), "winner_required_when_tied")
        self.assertEqual(build_score_error("得分未输入"), "score_invalid")
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
python -m unittest tests.test_admin_workflow -v
```

Expected: FAIL，错误包含 `No module named 'services.admin_workflow'`。

- [ ] **Step 3: 新增 helper 最小实现**

Create `GuanDan_backend-V2.0/services/admin_workflow.py`:

```python
import os

from werkzeug.utils import secure_filename

from api.dashboard_cache import (
    build_time_message,
    get_snapshot_copy,
    get_turn,
    is_valid_turn,
    mark_snapshot_stale,
    reset_turn,
    set_turn as set_current_turn,
    start_round_timer,
    stop_round_timer,
)
from services.clear_all_service import clear_all_tables
from services.import_service import import_registration_excel, fetch_team_info_rows
from services.log_service import save_score_log
from services.match_algorithm import generate_round_pairs
from services.match_service import (
    fetch_all_fights,
    fetch_fight_info_by_turn,
    fetch_match_generation_source,
    replace_fight_info,
)
from services.redis_cache_service import clear_all_fight_cache_in_redis
from services.score_service import apply_score_update
from services.score_writeback_service import is_writeback_enabled, enqueue_score_update
from services.scoring import build_score_update
from services.stats_service import check_match_exists


MAX_TABLE_NUMBER = 22


def api_success(message, data=None):
    return {"ok": True, "message": message, "data": data or {}}


def api_error(error, message, data=None):
    return {"ok": False, "error": error, "message": message, "data": data or {}}


def parse_table_number(value, max_table_number=MAX_TABLE_NUMBER):
    try:
        table_num = int(value)
    except (TypeError, ValueError):
        return None
    if table_num < 1 or table_num > max_table_number:
        return None
    return table_num


def build_score_error(raw_error):
    if raw_error == "未选择最终局赢家":
        return "winner_required_when_tied"
    return "score_invalid"


def clear_fight_cache(clear_local_cache=None):
    """清理对阵缓存，兼容 run.py 的本地缓存和 Redis 缓存。"""
    if clear_local_cache is not None:
        clear_local_cache()
    clear_all_fight_cache_in_redis()


def find_match_info(fights, table_num):
    for fight in fights:
        if int(fight[0]) == int(table_num):
            return {
                "table_num": int(table_num),
                "team1_name": fight[1],
                "team1_members": fight[2],
                "team2_name": fight[3],
                "team2_members": fight[4],
            }
    return None


def get_overview(get_db_connection):
    snapshot = get_snapshot_copy()
    rows = fetch_team_info_rows(get_db_connection)
    fights = fetch_all_fights(get_db_connection)
    return api_success("后台概览加载成功", {
        "turn": get_turn(),
        "time_message": build_time_message(),
        "teams": rows,
        "has_matches": bool(fights),
        "snapshot_updated_at": snapshot.get("updated_at"),
    })


def import_registration_file(file_storage, get_db_connection, upload_dir, clear_local_cache=None):
    if not file_storage or not file_storage.filename:
        return api_error("invalid_file", "请选择要上传的 .xlsx 文件")
    if not file_storage.filename.endswith(".xlsx"):
        return api_error("invalid_file", "只支持上传 .xlsx 文件")

    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(file_storage.filename)
    if not filename:
        return api_error("invalid_file", "文件名无效")

    filepath = os.path.join(upload_dir, filename)
    file_storage.save(filepath)
    result = import_registration_excel(filepath, get_db_connection)
    if not result.get("ok"):
        return api_error("import_failed", f"导入失败：{result.get('error', 'unknown error')}")

    clear_fight_cache(clear_local_cache)
    reset_turn()
    mark_snapshot_stale()
    return api_success("报名数据导入成功")


def clear_business_data(get_db_connection, clear_local_cache=None):
    result = clear_all_tables(get_db_connection)
    if not result.get("ok"):
        return api_error("clear_failed", f"清空失败：{result.get('error', 'unknown error')}")
    clear_fight_cache(clear_local_cache)
    reset_turn()
    mark_snapshot_stale()
    return api_success("业务数据已清空")


def set_turn_value(value):
    if value in (None, "", "null"):
        reset_turn()
        mark_snapshot_stale()
        return api_success("当前轮次已清空", {"turn": get_turn()})
    if is_valid_turn(value):
        set_current_turn(str(value))
        mark_snapshot_stale()
        return api_success("当前轮次已更新", {"turn": get_turn()})
    return api_error("invalid_turn", "轮次只能为 1、2、3 或空")


def start_timer_value():
    if not start_round_timer():
        return api_error("invalid_turn", "当前轮次未设置，无法启动倒计时")
    return api_success("倒计时已启动", {"time_message": build_time_message()})


def stop_timer_value():
    stop_round_timer()
    return api_success("倒计时已暂停", {"time_message": build_time_message()})


def generate_matches_workflow(get_db_connection, clear_local_cache=None):
    teams, team_levels = fetch_match_generation_source(get_db_connection)
    match_result = generate_round_pairs(teams, team_levels, rounds=3)
    if not match_result.get("success"):
        return api_error("match_generation_failed", "生成对阵失败，请重试")

    write_result = replace_fight_info(
        get_db_connection,
        match_result["pairs"],
        match_result["team_members"],
        match_result["team_levels"],
    )
    if not write_result.get("ok"):
        return api_error("match_generation_failed", f"保存对阵失败：{write_result.get('error', 'unknown error')}")

    clear_fight_cache(clear_local_cache)
    mark_snapshot_stale()
    return api_success("对阵已生成")


def get_all_matches(get_db_connection):
    return api_success("对阵加载成功", {"matches": fetch_all_fights(get_db_connection)})


def get_match_for_score(get_db_connection, load_fight_info, turn_num, table_num):
    if not is_valid_turn(turn_num):
        return api_error("invalid_turn", "轮次只能为 1、2、3")
    parsed_table = parse_table_number(table_num)
    if parsed_table is None:
        return api_error("invalid_table", "桌号无效")
    if not check_match_exists(get_db_connection, parsed_table, int(turn_num)):
        return api_error("match_not_found", "未找到该轮次和桌号的对阵")

    match_info = find_match_info(load_fight_info(int(turn_num)), parsed_table)
    if not match_info:
        return api_error("match_not_found", "未找到该轮次和桌号的对阵")
    match_info["turn_num"] = int(turn_num)
    return api_success("对阵加载成功", match_info)


def get_match_for_current_turn(get_db_connection, load_fight_info, table_num):
    turn = get_turn()
    if not is_valid_turn(turn):
        return api_error("invalid_turn", "当前轮次未设置")
    return get_match_for_score(get_db_connection, load_fight_info, turn, table_num)


def submit_score(get_db_connection, load_fight_info, turn_num, table_num, score_x, score_y, winner):
    match_result = get_match_for_score(get_db_connection, load_fight_info, turn_num, table_num)
    if not match_result["ok"]:
        return match_result
    match = match_result["data"]

    update_payload = build_score_update(
        team1_name=match["team1_name"],
        team2_name=match["team2_name"],
        score_x_raw=score_x,
        score_y_raw=score_y,
        winner_raw=winner,
    )
    if not update_payload["ok"]:
        return api_error(build_score_error(update_payload["error"]), "请输入合法比分，并在同等级时选择最后一局赢家")

    if is_writeback_enabled():
        write_result = enqueue_score_update(
            int(turn_num),
            update_payload["small_scores"],
            update_payload["big_scores"],
        )
        if write_result.get("ok") and write_result.get("queued"):
            queued = True
        else:
            queued = False
    else:
        write_result = apply_score_update(
            get_db_connection,
            int(turn_num),
            update_payload["small_scores"],
            update_payload["big_scores"],
        )
        queued = False

    if not write_result.get("ok"):
        return api_error("score_write_failed", f"比分写入失败：{write_result.get('error', 'unknown error')}")

    mark_snapshot_stale()
    save_score_log(
        int(turn_num),
        int(table_num),
        match["team1_name"],
        match["team1_members"],
        match["team2_name"],
        match["team2_members"],
        score_x,
        score_y,
    )
    message = "比分已进入更新队列" if queued else "比分已直接更新"
    return api_success(message, {"queued": queued})


def submit_score_for_current_turn(get_db_connection, load_fight_info, table_num, score_x, score_y, winner):
    turn = get_turn()
    if not is_valid_turn(turn):
        return api_error("invalid_turn", "当前轮次未设置")
    return submit_score(get_db_connection, load_fight_info, int(turn), table_num, score_x, score_y, winner)
```

- [ ] **Step 4: 运行 helper 测试**

Run:

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
python -m unittest tests.test_admin_workflow -v
```

Expected: PASS。

- [ ] **Step 5: 提交 helper**

Run:

```powershell
git add -- GuanDan_backend-V2.0/services/admin_workflow.py GuanDan_backend-V2.0/tests/test_admin_workflow.py
git commit -m "feat: add admin workflow helpers"
```

---

### Task 2: 后台管理与录分 JSON API

**Files:**
- Create: `GuanDan_backend-V2.0/api/admin_api.py`
- Create: `GuanDan_backend-V2.0/api/score_api.py`
- Modify: `GuanDan_backend-V2.0/run.py`
- Create: `GuanDan_backend-V2.0/tests/test_admin_score_api.py`

- [ ] **Step 1: 编写 API 响应测试**

Create `GuanDan_backend-V2.0/tests/test_admin_score_api.py`:

```python
import unittest
from unittest.mock import patch

from run import app


class TestAdminScoreApi(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    @patch("api.score_api.get_turn", return_value="null")
    def test_score_current_turn_invalid(self, _mock_turn):
        response = self.client.get("/api/score/current-turn")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "invalid_turn")

    @patch("api.admin_api.workflow.get_overview")
    def test_admin_overview_shape(self, mock_overview):
        mock_overview.return_value = {"ok": True, "message": "ok", "data": {"turn": "1"}}
        response = self.client.get("/api/admin/overview")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["turn"], "1")

    @patch("api.score_api.workflow.get_match_for_current_turn")
    def test_score_table_returns_workflow_payload(self, mock_lookup):
        mock_lookup.return_value = {"ok": False, "error": "invalid_turn", "message": "当前轮次未设置", "data": {}}
        response = self.client.get("/api/score/table?table=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["error"], "invalid_turn")
```

- [ ] **Step 2: 运行 API 测试并确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
python -m unittest tests.test_admin_score_api -v
```

Expected: FAIL，错误包含 `No module named 'api.admin_api'` 或路由 404。

- [ ] **Step 3: 新增 `admin_api.py`**

Create `GuanDan_backend-V2.0/api/admin_api.py`:

```python
from flask import Blueprint, jsonify, request

from services import admin_workflow as workflow


admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


def json_response(payload):
    return jsonify(payload)


@admin_api_bp.route("/overview", methods=["GET"])
def overview():
    return json_response(workflow.get_overview(current_app_get_db_connection()))


@admin_api_bp.route("/import", methods=["POST"])
def import_registration():
    file_storage = request.files.get("file")
    return json_response(workflow.import_registration_file(
        file_storage,
        current_app_get_db_connection(),
        current_app_upload_dir(),
        current_app_clear_fight_cache(),
    ))


@admin_api_bp.route("/clear", methods=["POST"])
def clear_data():
    return json_response(workflow.clear_business_data(
        current_app_get_db_connection(),
        current_app_clear_fight_cache(),
    ))


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
    return json_response(workflow.generate_matches_workflow(
        current_app_get_db_connection(),
        current_app_clear_fight_cache(),
    ))


@admin_api_bp.route("/score-match", methods=["GET"])
def score_match():
    return json_response(workflow.get_match_for_score(
        current_app_get_db_connection(),
        current_app_load_fight_info(),
        request.args.get("turn"),
        request.args.get("table"),
    ))


@admin_api_bp.route("/scores", methods=["POST"])
def submit_score():
    payload = request.get_json(silent=True) or {}
    return json_response(workflow.submit_score(
        current_app_get_db_connection(),
        current_app_load_fight_info(),
        payload.get("turn"),
        payload.get("table"),
        payload.get("score_x"),
        payload.get("score_y"),
        payload.get("winner"),
    ))


def current_app_get_db_connection():
    from flask import current_app
    return current_app.config["GUANDAN_GET_DB_CONNECTION"]


def current_app_upload_dir():
    from flask import current_app
    return current_app.config["GUANDAN_UPLOAD_DIR"]


def current_app_clear_fight_cache():
    from flask import current_app
    return current_app.config["GUANDAN_CLEAR_FIGHT_CACHE"]


def current_app_load_fight_info():
    from flask import current_app
    return current_app.config["GUANDAN_LOAD_FIGHT_INFO"]
```

- [ ] **Step 4: 新增 `score_api.py`**

Create `GuanDan_backend-V2.0/api/score_api.py`:

```python
from flask import Blueprint, jsonify, request

from api.dashboard_cache import get_turn, is_valid_turn
from services import admin_workflow as workflow


score_api_bp = Blueprint("score_api", __name__, url_prefix="/api/score")


def json_response(payload):
    return jsonify(payload)


@score_api_bp.route("/current-turn", methods=["GET"])
def current_turn():
    turn = get_turn()
    if not is_valid_turn(turn):
        return json_response(workflow.api_error("invalid_turn", "当前轮次未设置", {"turn": turn}))
    return json_response(workflow.api_success("当前轮次加载成功", {"turn": turn}))


@score_api_bp.route("/table", methods=["GET"])
def table_match():
    return json_response(workflow.get_match_for_current_turn(
        current_app_get_db_connection(),
        current_app_load_fight_info(),
        request.args.get("table"),
    ))


@score_api_bp.route("/table", methods=["POST"])
def submit_table_score():
    payload = request.get_json(silent=True) or {}
    return json_response(workflow.submit_score_for_current_turn(
        current_app_get_db_connection(),
        current_app_load_fight_info(),
        payload.get("table"),
        payload.get("score_x"),
        payload.get("score_y"),
        payload.get("winner"),
    ))


def current_app_get_db_connection():
    from flask import current_app
    return current_app.config["GUANDAN_GET_DB_CONNECTION"]


def current_app_load_fight_info():
    from flask import current_app
    return current_app.config["GUANDAN_LOAD_FIGHT_INFO"]
```

- [ ] **Step 5: 在 `run.py` 注册 Blueprint 和依赖注入**

Modify `GuanDan_backend-V2.0/run.py` imports:

```python
from api.admin_api import admin_api_bp
from api.score_api import score_api_bp
```

After `app.secret_key = app_config.SECRET_KEY`, add:

```python
app.config["GUANDAN_GET_DB_CONNECTION"] = get_db_connection
app.config["GUANDAN_UPLOAD_DIR"] = UPLOAD_DIR
app.config["GUANDAN_CLEAR_FIGHT_CACHE"] = clear_fight_cache
app.config["GUANDAN_LOAD_FIGHT_INFO"] = load_fight_info
```

After `app.register_blueprint(frontend_api_bp)`, add:

```python
app.register_blueprint(admin_api_bp)
app.register_blueprint(score_api_bp)
```

- [ ] **Step 6: 运行 API 测试**

Run:

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
python -m unittest tests.test_admin_score_api -v
```

Expected: PASS。

- [ ] **Step 7: 运行后端全量 unittest**

Run:

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: PASS；若现有用例因编码显示为乱码但断言通过，不把乱码显示当成失败。

- [ ] **Step 8: 提交 API**

Run:

```powershell
git add -- GuanDan_backend-V2.0/api/admin_api.py GuanDan_backend-V2.0/api/score_api.py GuanDan_backend-V2.0/run.py GuanDan_backend-V2.0/tests/test_admin_score_api.py
git commit -m "feat: add admin and score json apis"
```

---

### Task 3: 旧模板路由复用 helper

**Files:**
- Modify: `GuanDan_backend-V2.0/run.py`

- [ ] **Step 1: 改造导入、清空、轮次、计时和对阵生成路由**

In `GuanDan_backend-V2.0/run.py`, import:

```python
from services import admin_workflow as workflow
```

Use the helper result to keep old `flash` and redirect behavior. Example for `/set_turn`:

```python
@app.route('/set_turn', methods=['POST'])
def set_turn():
    result = workflow.set_turn_value(request.form.get('turn'))
    flash(result["message"], "success" if result["ok"] else "danger")
    return redirect(url_for('create_table'))
```

Apply the same pattern:

- `/clear_tables` uses `workflow.clear_business_data(get_db_connection, clear_fight_cache)`。
- `/generate_matches` POST uses `workflow.generate_matches_workflow(get_db_connection, clear_fight_cache)`。
- `/start_timer` uses `workflow.start_timer_value()`。
- `/stop_timer` uses `workflow.stop_timer_value()`。

- [ ] **Step 2: 改造录分路由提交逻辑**

In `/input_scores/<int:table_num>/<int:turn_num>/<int:modify_type>` POST branch, replace the duplicated score write logic with:

```python
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
```

- [ ] **Step 3: 运行后端测试**

Run:

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: PASS。

- [ ] **Step 4: 提交旧路由复用**

Run:

```powershell
git add -- GuanDan_backend-V2.0/run.py
git commit -m "refactor: share backend workflow helpers"
```

---

### Task 4: Vue Router 和大屏迁移

**Files:**
- Modify: `GuanDanFront-V2.0/package.json`
- Modify: `GuanDanFront-V2.0/package-lock.json`
- Modify: `GuanDanFront-V2.0/src/main.js`
- Modify: `GuanDanFront-V2.0/src/App.vue`
- Create: `GuanDanFront-V2.0/src/router/index.js`
- Create: `GuanDanFront-V2.0/src/views/ScreenView.vue`

- [ ] **Step 1: 安装路由依赖**

Run:

```powershell
cd GuanDanFront-V2.0
npm install vue-router@4
```

Expected: `package.json` and `package-lock.json` include `vue-router`。

- [ ] **Step 2: 新增 router**

Create `GuanDanFront-V2.0/src/router/index.js`:

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import ScreenView from '@/views/ScreenView.vue'
import AdminView from '@/views/AdminView.vue'
import ScoreEntryView from '@/views/ScoreEntryView.vue'
import ScoreFormView from '@/views/ScoreFormView.vue'

const routes = [
  { path: '/', redirect: '/screen' },
  { path: '/screen', name: 'screen', component: ScreenView },
  { path: '/admin', name: 'admin', component: AdminView },
  { path: '/score', name: 'score-entry', component: ScoreEntryView },
  { path: '/score/:turn/:table', name: 'score-form', component: ScoreFormView, props: true },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
```

- [ ] **Step 3: 移动大屏内容**

Create `GuanDanFront-V2.0/src/views/ScreenView.vue` by moving the current content of `GuanDanFront-V2.0/src/App.vue` into it unchanged except relative imports:

```javascript
import DynamicGroupingResult from "@/components/DynamicGroupingResult.vue";
import SeatingArrangement from "@/components/SeatingArrangement.vue";
```

Keep the existing `<template>` and `<style scoped>` so `/screen` visually matches the current app.

- [ ] **Step 4: 改造 App 和 main**

Replace `GuanDanFront-V2.0/src/App.vue` with:

```vue
<template>
  <router-view />
</template>
```

Modify `GuanDanFront-V2.0/src/main.js`:

```javascript
// import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'

createApp(App).use(router).mount('#app')
```

- [ ] **Step 5: 添加临时占位 view 让路由构建通过**

Create `GuanDanFront-V2.0/src/views/AdminView.vue`:

```vue
<template>
  <main class="admin-page">
    <h1>后台管理</h1>
  </main>
</template>
```

Create `GuanDanFront-V2.0/src/views/ScoreEntryView.vue`:

```vue
<template>
  <main class="score-page">
    <h1>扫码录分</h1>
  </main>
</template>
```

Create `GuanDanFront-V2.0/src/views/ScoreFormView.vue`:

```vue
<script setup>
defineProps({
  turn: { type: String, required: true },
  table: { type: String, required: true },
})
</script>

<template>
  <main class="score-page">
    <h1>第 {{ turn }} 轮 {{ table }} 桌录分</h1>
  </main>
</template>
```

- [ ] **Step 6: 构建验证**

Run:

```powershell
cd GuanDanFront-V2.0
npm run build
```

Expected: PASS。

- [ ] **Step 7: 提交路由迁移**

Run:

```powershell
git add -- GuanDanFront-V2.0/package.json GuanDanFront-V2.0/package-lock.json GuanDanFront-V2.0/src/main.js GuanDanFront-V2.0/src/App.vue GuanDanFront-V2.0/src/router/index.js GuanDanFront-V2.0/src/views/ScreenView.vue GuanDanFront-V2.0/src/views/AdminView.vue GuanDanFront-V2.0/src/views/ScoreEntryView.vue GuanDanFront-V2.0/src/views/ScoreFormView.vue
git commit -m "feat: move screen display behind vue router"
```

---

### Task 5: 前端 API 封装

**Files:**
- Modify: `GuanDanFront-V2.0/src/api.js`
- Create: `GuanDanFront-V2.0/src/api/admin.js`
- Create: `GuanDanFront-V2.0/src/api/score.js`

- [ ] **Step 1: 导出通用 request**

Modify `GuanDanFront-V2.0/src/api.js`:

```javascript
const BASE_URL = import.meta.env.VITE_BASE_API;
const PORT = import.meta.env.VITE_BASE_PORT;

export async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}:${PORT}${path}`, options);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} - ${res.statusText}`);
  }
  return res.json();
}

export const getDashboardSnapshot = () => request('/dashboard_snapshot');
```

- [ ] **Step 2: 新增 admin API**

Create `GuanDanFront-V2.0/src/api/admin.js`:

```javascript
import { request } from '@/api.js'

const jsonHeaders = { 'Content-Type': 'application/json' }

export const getAdminOverview = () => request('/api/admin/overview')

export const importRegistration = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return request('/api/admin/import', {
    method: 'POST',
    body: formData,
  })
}

export const clearBusinessData = () => request('/api/admin/clear', { method: 'POST' })

export const setAdminTurn = (turn) => request('/api/admin/turn', {
  method: 'POST',
  headers: jsonHeaders,
  body: JSON.stringify({ turn }),
})

export const startAdminTimer = () => request('/api/admin/timer/start', { method: 'POST' })
export const stopAdminTimer = () => request('/api/admin/timer/stop', { method: 'POST' })
export const getAdminMatches = () => request('/api/admin/matches')
export const generateAdminMatches = () => request('/api/admin/matches/generate', { method: 'POST' })

export const getAdminScoreMatch = ({ turn, table }) =>
  request(`/api/admin/score-match?turn=${encodeURIComponent(turn)}&table=${encodeURIComponent(table)}`)

export const submitAdminScore = (payload) => request('/api/admin/scores', {
  method: 'POST',
  headers: jsonHeaders,
  body: JSON.stringify(payload),
})
```

- [ ] **Step 3: 新增 score API**

Create `GuanDanFront-V2.0/src/api/score.js`:

```javascript
import { request } from '@/api.js'

const jsonHeaders = { 'Content-Type': 'application/json' }

export const getCurrentScoreTurn = () => request('/api/score/current-turn')

export const getScoreTable = (table) =>
  request(`/api/score/table?table=${encodeURIComponent(table)}`)

export const submitScoreTable = (payload) => request('/api/score/table', {
  method: 'POST',
  headers: jsonHeaders,
  body: JSON.stringify(payload),
})
```

- [ ] **Step 4: 构建验证**

Run:

```powershell
cd GuanDanFront-V2.0
npm run build
```

Expected: PASS。

- [ ] **Step 5: 提交 API 封装**

Run:

```powershell
git add -- GuanDanFront-V2.0/src/api.js GuanDanFront-V2.0/src/api/admin.js GuanDanFront-V2.0/src/api/score.js
git commit -m "feat: add frontend admin score api clients"
```

---

### Task 6: Vue 录分页面

**Files:**
- Modify: `GuanDanFront-V2.0/src/views/ScoreEntryView.vue`
- Modify: `GuanDanFront-V2.0/src/views/ScoreFormView.vue`
- Modify: `GuanDanFront-V2.0/src/components/QRCode.vue`

- [ ] **Step 1: 实现 `/score` 入口**

Replace `GuanDanFront-V2.0/src/views/ScoreEntryView.vue`:

```vue
<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCurrentScoreTurn } from '@/api/score.js'

const router = useRouter()
const turn = ref('null')
const table = ref('')
const message = ref('')
const error = ref('')
const loading = ref(false)

async function loadTurn() {
  loading.value = true
  error.value = ''
  try {
    const payload = await getCurrentScoreTurn()
    if (!payload.ok) {
      turn.value = payload.data?.turn ?? 'null'
      error.value = payload.message
      return
    }
    turn.value = payload.data.turn
    message.value = payload.message
  } catch (err) {
    error.value = `读取当前轮次失败：${err.message}`
  } finally {
    loading.value = false
  }
}

function goScoreForm() {
  const tableValue = String(table.value || '').trim()
  if (!tableValue) {
    error.value = '请输入桌号'
    return
  }
  router.push(`/score/${turn.value}/${tableValue}`)
}

onMounted(loadTurn)
</script>

<template>
  <main class="score-entry-page">
    <section class="score-panel">
      <h1>扫码录分</h1>
      <p v-if="loading">正在读取当前轮次...</p>
      <p v-else>当前轮次：{{ turn === 'null' ? '未设置' : `第 ${turn} 轮` }}</p>
      <p v-if="message" class="success">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>

      <label>
        桌号
        <input v-model="table" type="number" min="1" placeholder="请输入桌号" :disabled="turn === 'null'" />
      </label>
      <button type="button" :disabled="turn === 'null'" @click="goScoreForm">进入录分</button>
    </section>
  </main>
</template>

<style scoped>
.score-entry-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: #f6f7fb;
}
.score-panel {
  width: min(420px, 100%);
  padding: 24px;
  background: #fff;
  border: 1px solid #dde2ee;
  border-radius: 8px;
}
label {
  display: grid;
  gap: 8px;
  margin: 18px 0;
}
input {
  padding: 12px;
  font-size: 16px;
}
button {
  width: 100%;
  padding: 12px;
  font-size: 16px;
}
.success { color: #0b7a3b; }
.error { color: #b42318; }
</style>
```

- [ ] **Step 2: 实现 `/score/:turn/:table` 表单**

Replace `GuanDanFront-V2.0/src/views/ScoreFormView.vue`:

```vue
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getAdminScoreMatch, submitAdminScore } from '@/api/admin.js'
import { getScoreTable, submitScoreTable } from '@/api/score.js'

const props = defineProps({
  turn: { type: String, required: true },
  table: { type: String, required: true },
})

const router = useRouter()
const match = ref(null)
const scoreX = ref('')
const scoreY = ref('')
const winner = ref('')
const message = ref('')
const error = ref('')
const loading = ref(false)
const submitting = ref(false)

const isAdminMode = computed(() => router.currentRoute.value.query.mode === 'admin')
const isTie = computed(() => scoreX.value && scoreY.value && String(scoreX.value) === String(scoreY.value))

async function loadMatch() {
  loading.value = true
  error.value = ''
  try {
    const payload = isAdminMode.value
      ? await getAdminScoreMatch({ turn: props.turn, table: props.table })
      : await getScoreTable(props.table)
    if (!payload.ok) {
      error.value = payload.message
      return
    }
    match.value = payload.data
  } catch (err) {
    error.value = `读取对阵失败：${err.message}`
  } finally {
    loading.value = false
  }
}

async function submitScore() {
  if (!match.value) return
  if (isTie.value && !winner.value) {
    error.value = '同等级时必须选择最后一局赢家'
    return
  }
  submitting.value = true
  error.value = ''
  message.value = ''
  try {
    const payload = {
      turn: props.turn,
      table: props.table,
      score_x: scoreX.value,
      score_y: scoreY.value,
      winner: winner.value,
    }
    const result = isAdminMode.value ? await submitAdminScore(payload) : await submitScoreTable(payload)
    if (!result.ok) {
      error.value = result.message
      return
    }
    message.value = result.message
  } catch (err) {
    error.value = `提交比分失败：${err.message}`
  } finally {
    submitting.value = false
  }
}

onMounted(loadMatch)
</script>

<template>
  <main class="score-form-page">
    <section class="score-panel">
      <h1>第 {{ turn }} 轮 {{ table }} 桌录分</h1>
      <p v-if="loading">正在读取对阵...</p>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="message" class="success">{{ message }}</p>

      <form v-if="match" @submit.prevent="submitScore">
        <div class="teams">
          <section>
            <h2>{{ match.team1_name }}</h2>
            <p>{{ match.team1_members }}</p>
            <label>最终等级<input v-model="scoreX" type="number" min="2" max="32" required /></label>
          </section>
          <section>
            <h2>{{ match.team2_name }}</h2>
            <p>{{ match.team2_members }}</p>
            <label>最终等级<input v-model="scoreY" type="number" min="2" max="32" required /></label>
          </section>
        </div>

        <fieldset v-if="isTie">
          <legend>最后一局赢家</legend>
          <label><input v-model="winner" type="radio" :value="match.team1_name" /> {{ match.team1_name }}</label>
          <label><input v-model="winner" type="radio" :value="match.team2_name" /> {{ match.team2_name }}</label>
        </fieldset>

        <button type="submit" :disabled="submitting">{{ submitting ? '提交中...' : '确认提交' }}</button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.score-form-page {
  min-height: 100vh;
  padding: 24px;
  background: #f6f7fb;
}
.score-panel {
  max-width: 840px;
  margin: 0 auto;
  padding: 24px;
  background: #fff;
  border: 1px solid #dde2ee;
  border-radius: 8px;
}
.teams {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}
label {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}
input {
  padding: 10px;
  font-size: 16px;
}
button {
  margin-top: 18px;
  padding: 12px 18px;
  font-size: 16px;
}
.success { color: #0b7a3b; }
.error { color: #b42318; }
</style>
```

- [ ] **Step 3: 更新二维码目标**

Open `GuanDanFront-V2.0/src/components/QRCode.vue` and replace any hardcoded old score URL with `/score` relative to current host. If it renders an image from assets and has no URL generation, leave the image unchanged and add a visible link next to it:

```vue
<a class="score-link" href="/score">扫码录分入口</a>
```

- [ ] **Step 4: 构建验证**

Run:

```powershell
cd GuanDanFront-V2.0
npm run build
```

Expected: PASS。

- [ ] **Step 5: 提交录分页面**

Run:

```powershell
git add -- GuanDanFront-V2.0/src/views/ScoreEntryView.vue GuanDanFront-V2.0/src/views/ScoreFormView.vue GuanDanFront-V2.0/src/components/QRCode.vue
git commit -m "feat: add vue score entry pages"
```

---

### Task 7: Vue 管理后台页面

**Files:**
- Modify: `GuanDanFront-V2.0/src/views/AdminView.vue`

- [ ] **Step 1: 实现后台管理页面**

Replace `GuanDanFront-V2.0/src/views/AdminView.vue`:

```vue
<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  clearBusinessData,
  generateAdminMatches,
  getAdminMatches,
  getAdminOverview,
  importRegistration,
  setAdminTurn,
  startAdminTimer,
  stopAdminTimer,
} from '@/api/admin.js'

const router = useRouter()
const overview = ref(null)
const matches = ref([])
const selectedFile = ref(null)
const turn = ref('')
const scoreTurn = ref('')
const scoreTable = ref('')
const message = ref('')
const error = ref('')
const loading = ref(false)

async function refreshOverview() {
  loading.value = true
  error.value = ''
  try {
    const payload = await getAdminOverview()
    if (!payload.ok) {
      error.value = payload.message
      return
    }
    overview.value = payload.data
    turn.value = payload.data.turn === 'null' ? '' : payload.data.turn
  } catch (err) {
    error.value = `加载后台概览失败：${err.message}`
  } finally {
    loading.value = false
  }
}

async function refreshMatches() {
  const payload = await getAdminMatches()
  if (payload.ok) matches.value = payload.data.matches || []
}

async function runAction(action) {
  error.value = ''
  message.value = ''
  try {
    const payload = await action()
    if (!payload.ok) {
      error.value = payload.message
      return
    }
    message.value = payload.message
    await refreshOverview()
    await refreshMatches()
  } catch (err) {
    error.value = err.message
  }
}

function onFileChange(event) {
  selectedFile.value = event.target.files?.[0] || null
}

function uploadFile() {
  if (!selectedFile.value) {
    error.value = '请选择 .xlsx 文件'
    return
  }
  runAction(() => importRegistration(selectedFile.value))
}

function clearData() {
  if (window.confirm('确认清空所有业务数据吗？')) {
    runAction(clearBusinessData)
  }
}

function generateMatches() {
  if (window.confirm('确认重新生成并覆盖对阵吗？')) {
    runAction(generateAdminMatches)
  }
}

function saveTurn() {
  runAction(() => setAdminTurn(turn.value || 'null'))
}

function goAdminScore() {
  if (!scoreTurn.value || !scoreTable.value) {
    error.value = '请输入轮次和桌号'
    return
  }
  router.push(`/score/${scoreTurn.value}/${scoreTable.value}?mode=admin`)
}

onMounted(async () => {
  await refreshOverview()
  await refreshMatches()
})
</script>

<template>
  <main class="admin-page">
    <header>
      <h1>掼蛋赛事后台</h1>
      <a href="/screen">打开大屏</a>
    </header>

    <p v-if="loading">正在加载...</p>
    <p v-if="message" class="success">{{ message }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <section class="admin-grid">
      <section>
        <h2>赛事初始化</h2>
        <input type="file" accept=".xlsx" @change="onFileChange" />
        <button type="button" @click="uploadFile">上传并导入</button>
        <button type="button" class="danger" @click="clearData">清空业务数据</button>
      </section>

      <section>
        <h2>轮次与计时</h2>
        <p>当前轮次：{{ overview?.turn === 'null' ? '未设置' : overview?.turn }}</p>
        <p>倒计时：{{ overview?.time_message || '未开始' }}</p>
        <select v-model="turn">
          <option value="">未设置</option>
          <option value="1">第 1 轮</option>
          <option value="2">第 2 轮</option>
          <option value="3">第 3 轮</option>
        </select>
        <button type="button" @click="saveTurn">保存轮次</button>
        <button type="button" @click="runAction(startAdminTimer)">启动倒计时</button>
        <button type="button" @click="runAction(stopAdminTimer)">暂停倒计时</button>
      </section>

      <section>
        <h2>对阵管理</h2>
        <p>已有对阵：{{ overview?.has_matches ? '是' : '否' }}</p>
        <button type="button" @click="generateMatches">生成/覆盖对阵</button>
        <button type="button" @click="refreshMatches">刷新对阵</button>
      </section>

      <section>
        <h2>后台改分</h2>
        <input v-model="scoreTurn" type="number" min="1" max="3" placeholder="轮次" />
        <input v-model="scoreTable" type="number" min="1" placeholder="桌号" />
        <button type="button" @click="goAdminScore">进入改分</button>
      </section>
    </section>

    <section>
      <h2>队伍预览</h2>
      <table>
        <tbody>
          <tr v-for="(row, index) in overview?.teams || []" :key="index">
            <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <h2>对阵列表</h2>
      <table>
        <tbody>
          <tr v-for="(row, index) in matches" :key="index">
            <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>

<style scoped>
.admin-page {
  min-height: 100vh;
  padding: 24px;
  background: #f5f6fa;
  color: #1f2933;
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.admin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}
section {
  margin-top: 18px;
  padding: 16px;
  background: #fff;
  border: 1px solid #dde2ee;
  border-radius: 8px;
}
button, input, select {
  margin: 6px 8px 6px 0;
  padding: 9px 12px;
}
table {
  width: 100%;
  border-collapse: collapse;
}
td {
  border-bottom: 1px solid #e6eaf2;
  padding: 8px;
}
.danger { color: #b42318; }
.success { color: #0b7a3b; }
.error { color: #b42318; }
</style>
```

- [ ] **Step 2: 构建验证**

Run:

```powershell
cd GuanDanFront-V2.0
npm run build
```

Expected: PASS。

- [ ] **Step 3: 提交管理后台页面**

Run:

```powershell
git add -- GuanDanFront-V2.0/src/views/AdminView.vue
git commit -m "feat: add vue admin console"
```

---

### Task 8: 联合验证与收尾

**Files:**
- No planned code changes unless verification finds a defect.

- [ ] **Step 1: 后端全量测试**

Run:

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: PASS。

- [ ] **Step 2: 前端构建**

Run:

```powershell
cd GuanDanFront-V2.0
npm run build
```

Expected: PASS。

- [ ] **Step 3: 手动启动后端**

Run:

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
python run.py
```

Expected: Flask starts on configured host/port, default `0.0.0.0:5000`。

- [ ] **Step 4: 手动启动前端**

Run in a second terminal:

```powershell
cd GuanDanFront-V2.0
npm run dev
```

Expected: Vite starts on configured `0.0.0.0:5001`。

- [ ] **Step 5: 浏览器手工检查**

Open:

- `http://localhost:5001/screen`
- `http://localhost:5001/admin`
- `http://localhost:5001/score`

Expected:

- `/screen` 显示原大屏。
- `/admin` 能加载后台概览；数据库未准备好时应显示可读错误，不出现空白页。
- `/score` 能显示当前轮次；未设置轮次时禁用桌号入口。

- [ ] **Step 6: 最终状态检查**

Run:

```powershell
git status --short
git log --oneline -8
```

Expected:

- 只剩用户原有本地改动或明确不提交的生成物。
- 新增实现提交按任务拆分存在。

---

## 计划自检

- 覆盖 spec：后端 helper、JSON API、前端路由、大屏迁移、`/admin`、`/score`、测试、Conda 环境、提交策略均已包含。
- 类型一致：后端响应统一使用 `ok/message/error/data`；前端 API wrapper 与页面调用字段一致。
- 范围控制：不实现二维码登录、权限系统、不删除旧 Flask 模板、不替换技术栈、不批量删除文件。
