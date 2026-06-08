# 管理页分页、Redis 倒计时与大屏榜单轮播 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化管理页对阵查看方式，修复 Redis 运行态下倒计时启动失败，并让大屏小队排行榜按 5 秒一页持续轮播。

**Architecture:** 管理页分页只在前端按已有 matches 数据过滤，不增加后端接口。倒计时继续以 Redis runtime 为事实源，启动、暂停和大屏展示都读写 `gd:state` 的 timer 字段。大屏小队榜单轮播在前端按完整排名数组和时间窗口切片，办公室榜单保持完整展示。

**Tech Stack:** Vue 3 + Vite、Flask、unittest、PowerShell、Conda 环境 `flask_app_env`。

---

## 文件结构

- Modify: `GuanDanFront-V2.0/src/views/AdminView.vue`
  - 增加对阵列表右下角轮次切换按钮。
  - 每轮对阵列表在原表格区域内继续滚动。
- Create: `GuanDanFront-V2.0/src/utils/rankingRotation.js`
  - 提供 `getRotatingPage()` / `sliceRotatingPage()`，便于用 Node 做无框架测试。
- Modify: `GuanDanFront-V2.0/src/composables/useGuandanData.js`
  - 小队当前榜和累计榜使用 5 秒轮播切片。
- Modify: `GuanDan_backend-V2.0/services/runtime_store.py`
  - 增加 Redis runtime 计时器启动、暂停和时间文案函数。
- Modify: `GuanDan_backend-V2.0/services/runtime_views.py`
  - 大屏读模型使用 runtime 计时文案。
- Modify: `GuanDan_backend-V2.0/api/frontend_api.py`
  - `/dashboard_snapshot` 不再用旧 `dashboard_cache.build_time_message()` 覆盖 runtime time_message。
- Modify: `GuanDan_backend-V2.0/services/admin_workflow.py`
  - 启动/暂停倒计时改走 Redis runtime，并重建当前大屏视图和后台 overview。
- Modify: `GuanDan_backend-V2.0/tests/test_runtime_store.py`
  - 覆盖 Redis runtime 计时器。
- Modify: `GuanDan_backend-V2.0/tests/test_admin_workflow.py`
  - 覆盖启动倒计时不再读取旧 `dashboard_cache.TURN`。

---

### Task 1: Redis runtime 倒计时

**Files:**
- Modify: `GuanDan_backend-V2.0/tests/test_runtime_store.py`
- Modify: `GuanDan_backend-V2.0/services/runtime_store.py`
- Modify: `GuanDan_backend-V2.0/services/runtime_views.py`
- Modify: `GuanDan_backend-V2.0/api/frontend_api.py`

- [ ] **Step 1: 写失败测试**

在 `test_runtime_store.py` 增加测试：

```python
def test_start_and_stop_timer_use_runtime_state(self):
    with self.patch_redis():
        runtime_store.initialize_empty_state()
        self.assertFalse(runtime_store.start_round_timer())
        runtime_store.set_current_turn("2")
        self.assertTrue(runtime_store.start_round_timer(started_at=100.0))
        state = runtime_store.get_state()
        self.assertEqual("100.0", state["timer_started_at"])
        self.assertEqual("59:50", runtime_store.build_time_message(now=110.0))

        runtime_store.stop_round_timer()
        self.assertEqual("", runtime_store.get_state()["timer_started_at"])
        self.assertEqual("倒计时未开始", runtime_store.build_time_message(now=120.0))
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_store.TestRuntimeStore.test_start_and_stop_timer_use_runtime_state -v
```

Expected: FAIL，缺少 runtime timer 函数。

- [ ] **Step 3: 实现 runtime timer**

在 `runtime_store.py` 中新增 `start_round_timer(started_at=None)`、`stop_round_timer()`、`build_time_message(now=None)`，只读写 Redis `gd:state`。

- [ ] **Step 4: 切换展示接口**

`runtime_views._timer_message()` 调用 `runtime_store.build_time_message()`；`frontend_api.get_runtime_dashboard_snapshot()` 不再使用旧 `dashboard_cache.build_time_message()` 覆盖 snapshot。

- [ ] **Step 5: 运行测试确认通过**

Run 同 Step 2。Expected: PASS。

---

### Task 2: 管理后台启动/暂停倒计时走 Redis

**Files:**
- Modify: `GuanDan_backend-V2.0/tests/test_admin_workflow.py`
- Modify: `GuanDan_backend-V2.0/services/admin_workflow.py`

- [ ] **Step 1: 写失败测试**

在 `test_admin_workflow.py` 增加测试：

```python
def test_start_timer_value_uses_runtime_timer_and_rebuilds_views(self):
    calls = []
    self.patch_workflow("start_round_timer", lambda: (_ for _ in ()).throw(AssertionError("old timer must not run")))
    self.patch_workflow("runtime_start_round_timer", lambda: calls.append("runtime_start") or True)
    self.patch_workflow("runtime_build_time_message", lambda: "59:59")
    self.patch_workflow("runtime_get_current_turn", lambda: "2")
    self.patch_workflow("rebuild_dashboard_view", lambda turn: calls.append(("dashboard", turn)))
    self.patch_workflow("rebuild_admin_overview_view", lambda: calls.append("overview"))

    result = admin_workflow.start_timer_value()

    self.assertTrue(result["ok"])
    self.assertEqual({"time_message": "59:59"}, result["data"])
    self.assertEqual(calls, ["runtime_start", ("dashboard", 2), "overview"])
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_admin_workflow.TestAdminWorkflow.test_start_timer_value_uses_runtime_timer_and_rebuilds_views -v
```

Expected: FAIL，当前仍调用旧 timer。

- [ ] **Step 3: 修改 `admin_workflow._load_runtime()` 和 timer workflow**

引入 runtime timer 函数。`start_timer_value()` 和 `stop_timer_value()` 改为调用 Redis runtime timer；当前轮次合法时重建当前 dashboard view，再重建 overview。

- [ ] **Step 4: 运行测试确认通过**

Run 同 Step 2。Expected: PASS。

---

### Task 3: 大屏小队排行榜 5 秒轮播

**Files:**
- Create: `GuanDanFront-V2.0/src/utils/rankingRotation.js`
- Modify: `GuanDanFront-V2.0/src/composables/useGuandanData.js`

- [ ] **Step 1: 写失败测试命令**

先运行不存在的 helper，确认失败：

```powershell
cd GuanDanFront-V2.0
node --input-type=module -e "import { sliceRotatingPage } from './src/utils/rankingRotation.js'; const rows = Array.from({length: 13}, (_, i) => i + 1); const page = sliceRotatingPage(rows, 6, 5000, 5000); if (JSON.stringify(page) !== JSON.stringify([7,8,9,10,11,12])) process.exit(1);"
```

Expected: FAIL，模块不存在。

- [ ] **Step 2: 实现 helper**

`sliceRotatingPage(rows, pageSize, intervalMs, nowMs)` 使用 `Math.floor(nowMs / intervalMs) % pageCount` 计算页码，最后一页不足 6 条时显示剩余条目。

- [ ] **Step 3: 运行 Node 测试确认通过**

Run 同 Step 1。Expected: PASS。

- [ ] **Step 4: 接入 `useGuandanData.js`**

保留办公室榜单完整展示；小队当前榜和累计榜改为：

```javascript
const nowMs = Date.now()
guandanDatas.cur_teamScores = sliceRotatingPage(toArray(teamData.current_turn), TEAM_DATA_CONFIG.MAX_TEAMS, TEAM_DATA_CONFIG.ROTATION_INTERVAL_MS, nowMs)
guandanDatas.sum_teamScores = sliceRotatingPage(toArray(teamData.total_until_turn), TEAM_DATA_CONFIG.MAX_TEAMS, TEAM_DATA_CONFIG.ROTATION_INTERVAL_MS, nowMs)
```

---

### Task 4: 管理页对阵列表按轮次切换

**Files:**
- Modify: `GuanDanFront-V2.0/src/views/AdminView.vue`

- [ ] **Step 1: 增加前端状态和 computed**

新增 `selectedMatchTurn`，默认使用当前轮次，没有当前轮次时用 `1`。新增 `visibleMatches` 过滤 `matches` 中指定轮次的数据，`matchCount` 显示当前轮条数。

- [ ] **Step 2: 修改对阵列表模板**

在对阵列表面板标题右侧增加 1、2、3 轮按钮；表格 `v-for` 改为 `visibleMatches`；空态按当前轮显示。

- [ ] **Step 3: 修改样式**

新增 `.round-tabs` 和 `.round-tab`，放在面板标题右侧；表格区域继续使用现有 `.list-table-wrap` 滚动。

---

### Task 5: 验证

**Files:**
- No additional files.

- [ ] **Step 1: 后端测试**

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_store tests.test_runtime_views tests.test_admin_workflow tests.test_admin_score_api -v
```

Expected: PASS。

- [ ] **Step 2: 前端 helper 测试**

```powershell
cd GuanDanFront-V2.0
node --input-type=module -e "import { sliceRotatingPage } from './src/utils/rankingRotation.js'; const rows = Array.from({length: 13}, (_, i) => i + 1); const cases = [[0,[1,2,3,4,5,6]],[5000,[7,8,9,10,11,12]],[10000,[13]],[15000,[1,2,3,4,5,6]]]; for (const [now, expected] of cases) { const actual = sliceRotatingPage(rows, 6, 5000, now); if (JSON.stringify(actual) !== JSON.stringify(expected)) { console.error(actual, expected); process.exit(1); } }"
```

Expected: PASS。

- [ ] **Step 3: 前端构建**

```powershell
cd GuanDanFront-V2.0
npm run build
```

Expected: PASS；允许保留既有 Vite warning。
