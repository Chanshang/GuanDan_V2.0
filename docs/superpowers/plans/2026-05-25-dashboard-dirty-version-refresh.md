# Dashboard Dirty Version Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将大屏快照刷新从单纯 dirty set 改造成“Redis 原始比分立即写入 + dirty/version 防丢 + 后台合并刷新”的最终一致方案，避免高并发录分时新 dirty 标记被刷新线程误清掉。

**Architecture:** 用户提交比分仍然同步写 Redis 原始分数并立即返回；快照刷新任务只通过 `gd:dirty:dashboard` 和 `gd:dashboard:version` 表达“需要重建”。后台刷新线程每 300ms/500ms 取出当前 dirty 轮次，先消费 dirty，再重建快照；若重建期间 version 变化，说明又有新录分进入，刷新器会重新标记受影响轮次，下一轮继续补建，保证不丢刷新通知。

**Tech Stack:** Flask、Redis、unittest、Redis fake、Vue 3 + Vite、PowerShell、Conda 环境 `flask_app_env`。

---

## 背景与问题

当前高并发录分链路已经从“提交比分时同步重建大屏快照”改为：

```text
用户提交比分
-> runtime_store.apply_score_result 写 Redis 原始比分
-> runtime_store.mark_dashboard_dirty 标记 dirty turn
-> 接口立即返回
-> runtime_view_refresh_service 后台重建 dashboard/admin 快照
```

这个方向是对的，但当前 dirty 清理顺序存在竞态：

```text
刷新线程读取 dirty = {2, 3}
刷新线程 rebuild_dashboard_view(2)
用户此时提交新比分，再次 SADD dirty {2, 3}
刷新线程 rebuild_dashboard_view(3)
刷新线程 clear dirty {2, 3}
```

最后一步可能把新提交比分产生的 dirty 标记一起清掉。比分本身不会丢，因为已经写入 Redis 原始数据；丢的是“需要重新生成 dashboard_snapshot”的通知，表现为某些大屏短时间读到旧快照。

本计划不引入 Redis Stream，也不把用户比分写入改成队列。原因是录分业务需要提交后立即确定写入成功；队列化应放在“快照重建任务”层，而不是拦截“原始比分写 Redis”层。

---

## 文件结构

- Modify: `GuanDan_backend-V2.0/services/runtime_store.py`
  - 新增 `DASHBOARD_VERSION_KEY = "gd:dashboard:version"`。
  - `mark_dashboard_dirty(from_turn)` 同时 `INCR` version。
  - 新增 `get_dashboard_version()`、`consume_dashboard_dirty_turns()`、`restore_dashboard_dirty_turns()`。
- Modify: `GuanDan_backend-V2.0/services/runtime_view_refresh_service.py`
  - 改为“先消费 dirty，再 rebuild，失败恢复 dirty”。
  - 重建前后比较 version；如果 version 变化，重新标记本次处理轮次。
- Modify: `GuanDan_backend-V2.0/tests/fakes.py`
  - 给 `FakeRedis` 增加 `incr()`，支持 version 测试。
- Modify: `GuanDan_backend-V2.0/tests/test_runtime_store.py`
  - 覆盖 dirty 标记会递增 version。
  - 覆盖 consume/restore 的原子语义近似。
- Modify: `GuanDan_backend-V2.0/tests/test_runtime_view_refresh_service.py`
  - 覆盖刷新期间新 version 到来时不会丢 dirty。
  - 覆盖重建失败时 dirty 会恢复。

不删除任何文件或目录，不使用批量删除命令。

---

### Task 1: 给 Redis fake 增加 version 所需命令

**Files:**
- Modify: `GuanDan_backend-V2.0/tests/fakes.py`
- Test: `GuanDan_backend-V2.0/tests/test_runtime_store.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_runtime_store.py` 增加测试，先描述目标行为：每次标记 dashboard dirty 都会递增 version。

```python
def test_mark_dashboard_dirty_increments_dashboard_version(self):
    runtime_store.initialize_empty_state()

    first_dirty = runtime_store.mark_dashboard_dirty(2)
    first_version = runtime_store.get_dashboard_version()
    second_dirty = runtime_store.mark_dashboard_dirty(3)
    second_version = runtime_store.get_dashboard_version()

    self.assertEqual(["2", "3"], first_dirty)
    self.assertEqual(["3"], second_dirty)
    self.assertEqual(1, first_version)
    self.assertEqual(2, second_version)
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
C:\Users\Administrator\miniconda3\envs\flask_app_env\python.exe -m unittest tests.test_runtime_store.RuntimeStoreTestCase.test_mark_dashboard_dirty_increments_dashboard_version -v
```

Expected: FAIL，原因是 `get_dashboard_version` 或 `FakeRedis.incr` 尚不存在。

- [ ] **Step 3: 修改 FakeRedis**

在 `tests/fakes.py` 的 `FakeRedis` 类中加入：

```python
def incr(self, key):
    value = int(self.values.get(key) or 0) + 1
    self.values[key] = str(value)
    return value
```

- [ ] **Step 4: 只运行当前测试**

Run 同 Step 2。

Expected: 仍可能 FAIL，因为生产代码还没实现 version；如果错误从 `FakeRedis` 缺方法变为 `runtime_store` 缺函数，说明 fake 层已准备好。

---

### Task 2: 在 runtime_store 中实现 dirty version

**Files:**
- Modify: `GuanDan_backend-V2.0/services/runtime_store.py`
- Test: `GuanDan_backend-V2.0/tests/test_runtime_store.py`

- [ ] **Step 1: 增加 version key 与初始化清理**

在 `runtime_store.py` 常量区加入：

```python
DASHBOARD_VERSION_KEY = "gd:dashboard:version"
```

在 `initialize_empty_state()` 的 dirty 清理处，把 version key 一起删除：

```python
client.delete(
    DIRTY_SCORE_KEY,
    DIRTY_MATCHES_KEY,
    DIRTY_TEAMS_KEY,
    DIRTY_DASHBOARD_KEY,
    DASHBOARD_VERSION_KEY,
)
```

- [ ] **Step 2: 增加读取 version 函数**

在 `runtime_store.py` 中加入：

```python
def get_dashboard_version():
    client = require_redis()
    _require_initialized(client)
    raw_version = client.get(DASHBOARD_VERSION_KEY)
    if raw_version is None or raw_version == "":
        return 0
    if isinstance(raw_version, bytes):
        raw_version = raw_version.decode("utf-8")
    return int(raw_version)
```

- [ ] **Step 3: 修改 mark_dashboard_dirty**

让 `mark_dashboard_dirty(from_turn)` 在 `SADD` dirty 后递增 version：

```python
def mark_dashboard_dirty(from_turn):
    client = require_redis()
    _require_initialized(client)
    start_turn = int(from_turn)
    if start_turn not in (1, 2, 3):
        raise ValueError("invalid_turn")
    dirty_turns = [str(turn) for turn in range(start_turn, 4)]
    client.sadd(DIRTY_DASHBOARD_KEY, *dirty_turns)
    client.incr(DASHBOARD_VERSION_KEY)
    return dirty_turns
```

- [ ] **Step 4: 运行 Task 1 测试确认通过**

Run:

```powershell
cd GuanDan_backend-V2.0
C:\Users\Administrator\miniconda3\envs\flask_app_env\python.exe -m unittest tests.test_runtime_store.RuntimeStoreTestCase.test_mark_dashboard_dirty_increments_dashboard_version -v
```

Expected: PASS。

---

### Task 3: 实现 dirty 消费与失败恢复

**Files:**
- Modify: `GuanDan_backend-V2.0/services/runtime_store.py`
- Test: `GuanDan_backend-V2.0/tests/test_runtime_store.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_runtime_store.py` 增加测试：消费 dirty 会返回当前 dirty 并从 Redis 删除；恢复 dirty 会重新写回。

```python
def test_consume_and_restore_dashboard_dirty_turns(self):
    runtime_store.initialize_empty_state()
    runtime_store.mark_dashboard_dirty(2)

    consumed = runtime_store.consume_dashboard_dirty_turns()

    self.assertEqual(
        {"valid_turns": [2, 3], "malformed_turns": []},
        consumed,
    )
    self.assertEqual(set(), self.redis.smembers(runtime_store.DIRTY_DASHBOARD_KEY))

    runtime_store.restore_dashboard_dirty_turns(consumed)

    self.assertEqual(
        {"2", "3"},
        self.redis.smembers(runtime_store.DIRTY_DASHBOARD_KEY),
    )
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
C:\Users\Administrator\miniconda3\envs\flask_app_env\python.exe -m unittest tests.test_runtime_store.RuntimeStoreTestCase.test_consume_and_restore_dashboard_dirty_turns -v
```

Expected: FAIL，原因是 `consume_dashboard_dirty_turns` 尚不存在。

- [ ] **Step 3: 实现 consume**

在 `runtime_store.py` 中加入：

```python
def consume_dashboard_dirty_turns():
    dirty = read_dashboard_dirty_turns()
    clear_dashboard_dirty_turns(
        [*dirty["valid_turns"], *dirty["malformed_turns"]]
    )
    return dirty
```

说明：这里用“读后删”模拟消费语义。Redis 单线程保证单条命令串行，但这里不是 Lua 原子块；后续用 version 检测补偿重建期间的新写入。

- [ ] **Step 4: 实现 restore**

在 `runtime_store.py` 中加入：

```python
def restore_dashboard_dirty_turns(dirty):
    client = require_redis()
    _require_initialized(client)
    members = [
        str(turn)
        for turn in [
            *dirty.get("valid_turns", []),
            *dirty.get("malformed_turns", []),
        ]
    ]
    if members:
        client.sadd(DIRTY_DASHBOARD_KEY, *members)
```

- [ ] **Step 5: 运行测试确认通过**

Run 同 Step 2。

Expected: PASS。

---

### Task 4: 改造快照刷新器的消费顺序

**Files:**
- Modify: `GuanDan_backend-V2.0/services/runtime_view_refresh_service.py`
- Test: `GuanDan_backend-V2.0/tests/test_runtime_view_refresh_service.py`

- [ ] **Step 1: 写失败测试：重建失败恢复 dirty**

在 `tests/test_runtime_view_refresh_service.py` 保留或改写失败恢复测试，明确要求重建失败后 dirty 仍存在。

```python
def test_refresh_dirty_views_once_restores_dirty_turns_when_rebuild_fails(self):
    runtime_store.mark_dashboard_dirty(1)

    def fail_rebuild(turn):
        raise RuntimeError("refresh failed")

    runtime_views.rebuild_dashboard_view = fail_rebuild

    result = runtime_view_refresh_service.refresh_dirty_views_once()

    self.assertFalse(result["ok"])
    self.assertEqual(
        {"1", "2", "3"},
        self.redis.smembers(runtime_store.DIRTY_DASHBOARD_KEY),
    )
```

- [ ] **Step 2: 写失败测试：正常成功后 dirty 被消费**

```python
def test_refresh_dirty_views_once_consumes_dirty_before_rebuild(self):
    calls = []
    runtime_store.mark_dashboard_dirty(2)

    def rebuild_dashboard(turn):
        calls.append(("dashboard", turn, set(self.redis.smembers(runtime_store.DIRTY_DASHBOARD_KEY))))

    runtime_views.rebuild_dashboard_view = rebuild_dashboard
    runtime_views.rebuild_admin_matches_view = lambda: calls.append("matches")
    runtime_views.rebuild_admin_overview_view = lambda: calls.append("overview")

    result = runtime_view_refresh_service.refresh_dirty_views_once()

    self.assertTrue(result["ok"])
    self.assertEqual(
        [
            ("dashboard", 2, set()),
            ("dashboard", 3, set()),
            "matches",
            "overview",
        ],
        calls,
    )
    self.assertEqual(set(), self.redis.smembers(runtime_store.DIRTY_DASHBOARD_KEY))
```

- [ ] **Step 3: 运行测试确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
C:\Users\Administrator\miniconda3\envs\flask_app_env\python.exe -m unittest tests.test_runtime_view_refresh_service -v
```

Expected: 至少 `test_refresh_dirty_views_once_consumes_dirty_before_rebuild` FAIL，因为当前实现是在 rebuild 后清 dirty。

- [ ] **Step 4: 修改 refresh_dirty_views_once 消费顺序**

在 `runtime_view_refresh_service.py` 中，把读取 dirty 改为消费 dirty：

```python
dirty = runtime_store.consume_dashboard_dirty_turns()
dirty_turns = dirty["valid_turns"]
malformed_turns = dirty["malformed_turns"]
```

在 `except` 分支里恢复 dirty：

```python
except Exception as exc:
    runtime_store.restore_dashboard_dirty_turns(dirty)
    try:
        runtime_store.update_state(
            flush_status="failed",
            flush_error=f"view refresh failed: {exc}",
        )
    except Exception:
        pass
    return {"ok": False, "dirty_count": dirty_count, "error": str(exc)}
```

正常成功时不再调用 `clear_dashboard_dirty_turns()`，因为 dirty 已经在开头被消费。

- [ ] **Step 5: 运行测试确认通过**

Run 同 Step 3。

Expected: PASS。

---

### Task 5: 用 version 检测刷新期间的新比分

**Files:**
- Modify: `GuanDan_backend-V2.0/services/runtime_view_refresh_service.py`
- Test: `GuanDan_backend-V2.0/tests/test_runtime_view_refresh_service.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_runtime_view_refresh_service.py` 增加测试：重建过程中如果又发生 `mark_dashboard_dirty(2)`，本轮刷新结束后 dirty 不应为空。

```python
def test_refresh_dirty_views_once_keeps_dirty_when_version_changes_during_rebuild(self):
    calls = []
    runtime_store.mark_dashboard_dirty(2)

    def rebuild_dashboard(turn):
        calls.append(("dashboard", turn))
        if turn == 2:
            runtime_store.mark_dashboard_dirty(2)

    runtime_views.rebuild_dashboard_view = rebuild_dashboard
    runtime_views.rebuild_admin_matches_view = lambda: calls.append("matches")
    runtime_views.rebuild_admin_overview_view = lambda: calls.append("overview")

    result = runtime_view_refresh_service.refresh_dirty_views_once()

    self.assertTrue(result["ok"])
    self.assertEqual([("dashboard", 2), ("dashboard", 3), "matches", "overview"], calls)
    self.assertEqual(
        {"2", "3"},
        self.redis.smembers(runtime_store.DIRTY_DASHBOARD_KEY),
    )
    self.assertEqual("version_changed", result["pending_reason"])
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
C:\Users\Administrator\miniconda3\envs\flask_app_env\python.exe -m unittest tests.test_runtime_view_refresh_service.RuntimeViewRefreshServiceTestCase.test_refresh_dirty_views_once_keeps_dirty_when_version_changes_during_rebuild -v
```

Expected: FAIL，当前刷新器不会比较 version，可能清掉新 dirty。

- [ ] **Step 3: 在刷新器中记录 version_before/version_after**

在 `refresh_dirty_views_once()` 中，成功拿到锁后、消费 dirty 前读取版本：

```python
version_before = runtime_store.get_dashboard_version()
dirty = runtime_store.consume_dashboard_dirty_turns()
```

重建完成后读取版本：

```python
version_after = runtime_store.get_dashboard_version()
```

- [ ] **Step 4: version 变化时恢复本次处理轮次**

在成功 rebuild 后加入：

```python
pending_reason = None
if version_after != version_before:
    runtime_store.restore_dashboard_dirty_turns(
        {
            "valid_turns": dirty_turns,
            "malformed_turns": [],
        }
    )
    pending_reason = "version_changed"
```

返回值包含调试信息：

```python
return {
    "ok": True,
    "dirty_count": dirty_count,
    "rebuilt_dashboard_turns": dirty_turns,
    "version_before": version_before,
    "version_after": version_after,
    "pending_reason": pending_reason,
}
```

- [ ] **Step 5: 运行测试确认通过**

Run 同 Step 2。

Expected: PASS。

---

### Task 6: 调整刷新频率为可配置并确认默认值

**Files:**
- Modify: `GuanDan_backend-V2.0/services/runtime_view_refresh_service.py`
- Test: `GuanDan_backend-V2.0/tests/test_runtime_view_refresh_service.py`

- [ ] **Step 1: 检查默认值**

确认 `VIEW_REFRESH_INTERVAL_SECONDS` 当前使用：

```python
VIEW_REFRESH_INTERVAL_SECONDS = float(os.getenv("RUNTIME_VIEW_REFRESH_INTERVAL_SECONDS", "0.5"))
```

保留默认 `0.5` 秒。如果现场希望更快，可通过环境变量改为：

```powershell
$env:RUNTIME_VIEW_REFRESH_INTERVAL_SECONDS="0.3"
```

- [ ] **Step 2: 增加服务说明注释**

在 `runtime_view_refresh_service.py` 顶部常量附近加入中文注释：

```python
# 快照刷新线程只合并重建读模型，不负责写 MySQL。
# 用户录分请求已经同步写入 Redis 原始分数；这里通过 dirty/version 防止刷新通知丢失。
```

- [ ] **Step 3: 运行刷新服务测试**

Run:

```powershell
cd GuanDan_backend-V2.0
C:\Users\Administrator\miniconda3\envs\flask_app_env\python.exe -m unittest tests.test_runtime_view_refresh_service -v
```

Expected: PASS。

---

### Task 7: 集成验证

**Files:**
- No additional code files.

- [ ] **Step 1: 运行聚焦后端测试**

```powershell
cd GuanDan_backend-V2.0
C:\Users\Administrator\miniconda3\envs\flask_app_env\python.exe -m unittest tests.test_runtime_store tests.test_runtime_view_refresh_service tests.test_admin_workflow tests.test_admin_score_api tests.test_runtime_api_integration -v
```

Expected: PASS。

- [ ] **Step 2: 运行全量后端测试**

```powershell
cd GuanDan_backend-V2.0
C:\Users\Administrator\miniconda3\envs\flask_app_env\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Expected: PASS，允许保留已有显式 skipped 的大规模 smoke 测试。

- [ ] **Step 3: 运行前端构建**

```powershell
cd GuanDanFront-V2.0
npm run build
```

Expected: PASS。若仍出现现有图片路径 warning，仅记录，不作为本次计划阻塞项。

- [ ] **Step 4: 手工并发复核**

启动后端和前端后，执行一轮人工验证：

```powershell
Invoke-RestMethod -Uri 'http://localhost:5000/dashboard_snapshot'
```

然后在多个录分页面连续提交同一轮不同桌的比分，观察：

- `/score` 提交响应仍快速返回。
- 大屏比分最终刷新。
- 倒计时和小队排名轮播不因快照请求短暂失败而停止。
- Redis 中 `gd:dirty:dashboard` 在稳定后会被消费为空。
- Redis 中 `gd:dashboard:version` 会随每次录分递增。

---

## 风险与边界

- 本计划保证的是 dashboard 快照“最终一致”，不是每一次提交后立即同步出现在所有大屏上。
- 如果 `rebuild_dashboard_view()` 持续失败，dirty 会被恢复，刷新线程会持续重试；这时应通过 `flush_status/flush_error` 或日志定位根因。
- 本计划不改 DB 写回策略。Redis -> MySQL 仍由 `runtime_flush_service.py` 负责，默认约 10 秒写回。
- 本计划不实现 MySQL -> Redis 自动同步。手动修改数据库后，Redis 不会自动更新，这仍需要显式 reload/import 或未来新增管理接口。
- 本计划不引入 Redis Stream。当前用 dirty set + version 已能覆盖现场高并发录分下的刷新通知防丢问题。

---

## 自检清单

- [ ] dirty 通知不会在重建期间被误清掉。
- [ ] 用户比分写 Redis 仍然是同步立即写，不被队列延迟。
- [ ] 快照刷新合并执行，避免高并发下重复重建。
- [ ] 重建失败会恢复 dirty，下一轮继续重试。
- [ ] version 变化会留下 pending dirty，下一轮补建。
- [ ] 不使用批量删除命令。
- [ ] 不使用 `git add .`。
