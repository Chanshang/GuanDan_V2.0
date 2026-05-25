# Redis 运行态管理页与录分同步修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Redis 运行态替换后 `/admin` 队伍列表字段错位、`/score` 当前轮次读取旧状态、后台改分后大屏读模型不刷新的问题。

**Architecture:** 继续坚持 Redis runtime 作为运行态事实源，不恢复 MySQL 高频读路径。后端在 `runtime_views.py` 生成页面专用读模型，在 `score_api.py` 和 `admin_workflow.py` 统一读写 Redis 轮次和比分，并在比分变更后重建受影响的大屏视图。

**Tech Stack:** Flask、unittest、Redis runtime fake、Vue 3 + Vite、PowerShell、Conda 环境 `flask_app_env`。

---

## 文件结构

- Modify: `GuanDan_backend-V2.0/services/runtime_views.py`
  - 增加后台队伍列表扁平化读模型。
  - 修正大屏累计榜，按 `turn <= 当前轮次` 聚合。
- Modify: `GuanDan_backend-V2.0/services/admin_workflow.py`
  - 设置轮次后同步重建大屏视图。
  - 提交比分后重建受影响轮次的大屏视图。
- Modify: `GuanDan_backend-V2.0/api/score_api.py`
  - `/api/score/current-turn` 改读 Redis runtime 当前轮次。
- Modify: `GuanDan_backend-V2.0/tests/test_runtime_views.py`
  - 覆盖后台队伍列表字段契约和累计榜跨轮次聚合。
- Modify: `GuanDan_backend-V2.0/tests/test_admin_workflow.py`
  - 覆盖设置轮次、提交比分时的大屏视图重建调用。
- Modify: `GuanDan_backend-V2.0/tests/test_admin_score_api.py`
  - 覆盖 `/api/score/current-turn` 不再读取旧 `dashboard_cache`。

不删除任何文件或目录，不使用批量删除命令。

---

### Task 1: 锁定后台队伍列表读模型

**Files:**
- Modify: `GuanDan_backend-V2.0/tests/test_runtime_views.py`
- Modify: `GuanDan_backend-V2.0/services/runtime_views.py`

- [ ] **Step 1: 写失败测试**

在 `test_runtime_views.py` 增加测试：`rebuild_admin_overview_view()` 返回的 `teams` 应该是前端可直接渲染的扁平队伍行，而不是 `team_info` 原始办公室行。

```python
def test_admin_overview_flattens_team_info_rows_for_vue_table(self):
    self.redis = FakeRedis()
    runtime_store.require_redis = lambda: self.redis
    runtime_views.require_redis = lambda: self.redis
    runtime_store.initialize_empty_state()
    runtime_store.write_teams(
        [
            {
                "id": 1,
                "office": "702",
                "team_name_1": "702-A",
                "members_1": "张三-李四",
                "team_name_2": "702-B",
                "members_2": "王五-赵六",
                "team_name_3": "702-C",
                "members_3": "空",
                "team_name_4": "702-D",
                "members_4": "甲-乙",
            }
        ]
    )
    runtime_store.write_team_levels(
        [
            {"team_name": "702-A", "level": "A"},
            {"team_name": "702-B", "level": "B"},
            {"team_name": "702-D", "level": "C"},
        ]
    )

    overview = runtime_views.rebuild_admin_overview_view()

    self.assertEqual(
        [
            {"team_name": "702-A", "members": "张三-李四", "office": "702", "level": "A"},
            {"team_name": "702-B", "members": "王五-赵六", "office": "702", "level": "B"},
            {"team_name": "702-D", "members": "甲-乙", "office": "702", "level": "C"},
        ],
        overview["teams"],
    )
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_views.RuntimeViewsTestCase.test_admin_overview_flattens_team_info_rows_for_vue_table -v
```

Expected: FAIL，实际返回仍包含 `team_name_1` / `members_1` 原始字段。

- [ ] **Step 3: 实现扁平化 helper**

在 `runtime_views.py` 增加 `_admin_team_rows()`，优先展开 `team_name_1..4` / `members_1..4`，跳过成员为 `空` 的占位队伍；如果数据已经是 `team_name/member_name` 形状，则兼容返回。

- [ ] **Step 4: 运行测试确认通过**

Run 同 Step 2。Expected: PASS。

---

### Task 2: 修复大屏累计榜跨轮次聚合

**Files:**
- Modify: `GuanDan_backend-V2.0/tests/test_runtime_views.py`
- Modify: `GuanDan_backend-V2.0/services/runtime_views.py`

- [ ] **Step 1: 写失败测试**

在 `test_runtime_views.py` 增加测试：第 2 轮 dashboard 的 `total_until_turn` 应包含第 1 轮和第 2 轮得分之和。

```python
def test_dashboard_total_rankings_include_previous_turns(self):
    self.redis = FakeRedis()
    runtime_store.require_redis = lambda: self.redis
    runtime_views.require_redis = lambda: self.redis
    runtime_store.initialize_empty_state()
    for turn, small_score in ((1, 4), (2, 6)):
        runtime_store.write_mini_teams(
            turn,
            [
                {
                    "team_name": "A队",
                    "turn": turn,
                    "big_score": 2,
                    "small_score": small_score,
                    "office": "一办",
                    "member_name": "张三-李四",
                }
            ],
        )

    dashboard = runtime_views.rebuild_dashboard_view(2)

    self.assertEqual([[1, "A队", 2, 6]], dashboard["sumteaminfo"]["current_turn"])
    self.assertEqual([[1, "A队", 4, 10]], dashboard["sumteaminfo"]["total_until_turn"])
    self.assertEqual([[1, "一办", 4, 10]], dashboard["officescore"]["total_until_turn"])
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_views.RuntimeViewsTestCase.test_dashboard_total_rankings_include_previous_turns -v
```

Expected: FAIL，累计榜只统计当前轮。

- [ ] **Step 3: 修改 `rebuild_dashboard_view(turn)`**

让当前轮对阵和当前轮小分仍读 `read_fights(turn)` / `read_mini_teams(turn)`；累计榜使用 `1..turn` 的所有 `mini_team` 行计算。

- [ ] **Step 4: 运行测试确认通过**

Run 同 Step 2。Expected: PASS。

---

### Task 3: 修复 `/api/score/current-turn` 旧状态读取

**Files:**
- Modify: `GuanDan_backend-V2.0/tests/test_admin_score_api.py`
- Modify: `GuanDan_backend-V2.0/api/score_api.py`

- [ ] **Step 1: 写失败测试**

在 `test_admin_score_api.py` 增加测试：接口应调用 Redis runtime 当前轮次，而不是旧 `dashboard_cache.get_turn()`。

```python
def test_score_current_turn_reads_runtime_turn(self):
    with patch("api.score_api.workflow.runtime_get_current_turn", return_value="2"), patch(
        "api.score_api.get_turn",
        side_effect=AssertionError("old dashboard cache turn must not be read"),
    ):
        response = self.client.get("/api/score/current-turn")

    self.assertEqual(response.status_code, 200)
    self.assertEqual(
        {"ok": True, "message": "当前轮次加载成功", "data": {"turn": "2"}},
        response.get_json(),
    )
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_admin_score_api.TestAdminScoreApi.test_score_current_turn_reads_runtime_turn -v
```

Expected: FAIL，接口仍调用旧 `get_turn()`。

- [ ] **Step 3: 修改 `score_api.current_turn()`**

调用 `workflow._load_runtime(("runtime_get_current_turn",))` 后读取 `workflow.runtime_get_current_turn()`；轮次不在 `{"1", "2", "3"}` 时返回 `invalid_turn`。

- [ ] **Step 4: 运行测试确认通过**

Run 同 Step 2。Expected: PASS。

---

### Task 4: 提交比分后重建大屏读模型

**Files:**
- Modify: `GuanDan_backend-V2.0/tests/test_admin_workflow.py`
- Modify: `GuanDan_backend-V2.0/services/admin_workflow.py`

- [ ] **Step 1: 写失败测试**

修改 `test_submit_score_applies_runtime_result_and_rebuilds_views`，加入 `rebuild_dashboard_view` 断言：第 2 轮比分变动后，应重建第 2、3 轮 dashboard，并重建后台 matches / overview。

```python
self.patch_workflow("rebuild_dashboard_view", lambda turn: calls.append(("dashboard", turn)))
...
self.assertEqual(calls[2:6], [("dashboard", 2), ("dashboard", 3), "matches", "overview"])
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_admin_workflow.TestAdminWorkflow.test_submit_score_applies_runtime_result_and_rebuilds_views -v
```

Expected: FAIL，当前没有调用 `rebuild_dashboard_view`。

- [ ] **Step 3: 修改 `admin_workflow._load_runtime()`**

引入 `rebuild_dashboard_view` 全局依赖，保证测试和生产代码都能按需加载。

- [ ] **Step 4: 修改 `submit_score()`**

在 `runtime_apply_score_result()` 和 `save_score_log()` 成功后，按 `range(turn_num, 4)` 重建 dashboard view，再重建后台 matches / overview。

- [ ] **Step 5: 运行测试确认通过**

Run 同 Step 2。Expected: PASS。

---

### Task 5: 设置轮次后同步重建当前大屏视图

**Files:**
- Modify: `GuanDan_backend-V2.0/tests/test_admin_workflow.py`
- Modify: `GuanDan_backend-V2.0/services/admin_workflow.py`

- [ ] **Step 1: 写失败测试**

修改 `test_set_turn_value_writes_runtime_turn_and_rebuilds_overview`，当设置为 `"2"` 时断言会调用 `rebuild_dashboard_view(2)`。

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_admin_workflow.TestAdminWorkflow.test_set_turn_value_writes_runtime_turn_and_rebuilds_overview -v
```

Expected: FAIL，当前只重建 overview。

- [ ] **Step 3: 修改 `set_turn_value()`**

轮次为 `1/2/3` 时调用 `rebuild_dashboard_view(int(saved_turn))`，轮次为 `null` 时只重建 overview。

- [ ] **Step 4: 运行测试确认通过**

Run 同 Step 2。Expected: PASS。

---

### Task 6: 集成验证

**Files:**
- No additional code files.

- [ ] **Step 1: 运行聚焦后端测试**

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_views tests.test_admin_workflow tests.test_admin_score_api -v
```

Expected: PASS。

- [ ] **Step 2: 运行前端构建**

```powershell
cd GuanDanFront-V2.0
npm run build
```

Expected: PASS。

- [ ] **Step 3: 手工接口复核**

在本地服务运行时请求：

```powershell
Invoke-RestMethod -Uri 'http://localhost:5000/api/admin/overview'
Invoke-RestMethod -Uri 'http://localhost:5000/api/score/current-turn'
Invoke-RestMethod -Uri 'http://localhost:5000/dashboard_snapshot'
```

Expected:

- `/api/admin/overview` 的 `data.teams[0]` 有 `team_name`、`members`、`office`、`level`。
- `/api/score/current-turn` 与 `/api/admin/overview` 的 `turn` 一致。
- 提交比分后 `/dashboard_snapshot` 的当前轮或累计榜立即反映 Redis 分数。
