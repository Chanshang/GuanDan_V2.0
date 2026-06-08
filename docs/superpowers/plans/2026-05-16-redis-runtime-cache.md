# Redis 运行态缓存统一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后台、大屏和录分的高频读写统一到 Redis 运行态事实源，并通过 10 秒写回 worker 持久化到 MySQL。

**Architecture:** 新增 Redis 强依赖入口、运行态事实仓库、读模型构建和写回服务；现有 `/api/admin/*`、`/api/score/*`、`/dashboard_snapshot` 和旧 Flask 页面逐步改为读取 Redis。Redis 不可用时接口明确失败，不自动降级到 MySQL；数据库索引、SQL 重写和批量插入优化不属于本计划。

**Tech Stack:** Flask、unittest、Redis、MySQL、Vue 3、Vite、PowerShell、Conda 环境 `flask_app_env`。

---

## 文件结构

后端新增：

- Create: `GuanDan_backend-V2.0/services/redis_runtime.py`
  - Redis 强依赖入口，提供统一异常和 `require_redis()`。
- Create: `GuanDan_backend-V2.0/services/runtime_store.py`
  - Redis 事实数据仓库，管理 state、teams、team_levels、mini_teams、fights 和 dirty 标记。
- Create: `GuanDan_backend-V2.0/services/runtime_views.py`
  - 基于 Redis 事实数据构建 dashboard、admin overview、admin matches 和 create table 读模型。
- Create: `GuanDan_backend-V2.0/services/runtime_flush_service.py`
  - 10 秒写回 worker 和可单测的 `flush_once()`。
- Create: `GuanDan_backend-V2.0/services/perf_logger.py`
  - 轻量耗时日志 helper。
- Create: `GuanDan_backend-V2.0/tests/fakes.py`
  - 单元测试使用的 FakeRedis 和 fake DB connection。
- Create: `GuanDan_backend-V2.0/tests/test_redis_runtime.py`
  - Redis 强依赖行为测试。
- Create: `GuanDan_backend-V2.0/tests/test_runtime_store.py`
  - 运行态事实数据读写和录分更新测试。
- Create: `GuanDan_backend-V2.0/tests/test_runtime_views.py`
  - 读模型构建测试。
- Create: `GuanDan_backend-V2.0/tests/test_runtime_flush_service.py`
  - 10 秒写回合并、失败保留 dirty 测试。
- Create: `GuanDan_backend-V2.0/tests/test_runtime_api_integration.py`
  - API 不降级查 MySQL、Redis 错误返回测试。

后端修改：

- Modify: `GuanDan_backend-V2.0/services/admin_workflow.py`
  - 后台概览、对阵列表、生成对阵、录分加载和录分提交改用 Redis 运行态服务。
- Modify: `GuanDan_backend-V2.0/api/frontend_api.py`
  - `/dashboard_snapshot` 和拆分展示接口改为读取 Redis 读模型。
- Modify: `GuanDan_backend-V2.0/api/dashboard_cache.py`
  - 停用进程内 snapshot 后台刷新；保留轮次/倒计时兼容函数或转调 Redis。
- Modify: `GuanDan_backend-V2.0/run.py`
  - 注入 runtime dependencies，启动写回 worker，旧模板页面改读 Redis 读模型。
- Modify: `GuanDan_backend-V2.0/tests/test_admin_workflow.py`
  - 更新测试期望，覆盖 Redis 读模型和写 Redis 分支。
- Modify: `GuanDan_backend-V2.0/tests/test_admin_score_api.py`
  - 更新 API 测试，覆盖 Redis 错误和当前轮次读取。

前端修改：

- Modify: `GuanDanFront-V2.0/src/views/AdminView.vue`
  - 显示 Redis/写回状态字段，Redis 错误时给出明确提示。

不修改：

- 不修改数据库表结构。
- 不新增数据库索引。
- 不重写 `/create_table` 的旧 SQL。
- 不优化 `replace_fight_info()` 的逐条插入。
- 不删除旧模板、旧路由或任何目录。

提交约束：

- 不使用 `git add .`。
- 不提交 `__pycache__`、日志、上传文件、`node_modules`、Dockerfile 或本任务无关文件。
- 每个任务只暂存当前任务相关文件。
- 仓库内禁止批量删除文件或目录。

---

### Task 1: Redis 强依赖入口与性能日志

**Files:**
- Create: `GuanDan_backend-V2.0/services/redis_runtime.py`
- Create: `GuanDan_backend-V2.0/services/perf_logger.py`
- Create: `GuanDan_backend-V2.0/tests/test_redis_runtime.py`

- [ ] **Step 1: 编写 Redis 强依赖失败测试**

Create `GuanDan_backend-V2.0/tests/test_redis_runtime.py`:

```python
import unittest
from unittest.mock import patch

from services import redis_runtime


class TestRedisRuntime(unittest.TestCase):
    def setUp(self):
        redis_runtime.reset_redis_client_for_tests()

    def tearDown(self):
        redis_runtime.reset_redis_client_for_tests()

    def test_require_redis_raises_clear_error_when_package_missing(self):
        with patch.object(redis_runtime, "redis", None):
            with self.assertRaises(redis_runtime.RedisRuntimeError) as cm:
                redis_runtime.require_redis()

        self.assertEqual(cm.exception.code, "redis_unavailable")
        self.assertIn("Redis", str(cm.exception))

    def test_require_redis_raises_clear_error_when_ping_fails(self):
        class BrokenRedis:
            def ping(self):
                raise RuntimeError("connection refused")

        with patch.object(redis_runtime, "_build_redis_client", return_value=BrokenRedis()):
            with self.assertRaises(redis_runtime.RedisRuntimeError) as cm:
                redis_runtime.require_redis()

        self.assertEqual(cm.exception.code, "redis_unavailable")
        self.assertIn("connection refused", cm.exception.message)

    def test_require_redis_returns_cached_client(self):
        class WorkingRedis:
            ping_count = 0

            def ping(self):
                self.ping_count += 1
                return True

        client = WorkingRedis()
        with patch.object(redis_runtime, "_build_redis_client", return_value=client):
            self.assertIs(redis_runtime.require_redis(), client)
            self.assertIs(redis_runtime.require_redis(), client)

        self.assertEqual(client.ping_count, 1)

    def test_runtime_error_to_api_payload(self):
        exc = redis_runtime.RedisRuntimeError("redis_not_initialized", "Redis 未初始化")
        self.assertEqual(
            redis_runtime.runtime_error_to_api_payload(exc),
            {
                "ok": False,
                "error": "redis_not_initialized",
                "message": "Redis 未初始化",
                "data": {},
            },
        )
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_redis_runtime -v
```

Expected: FAIL，错误包含 `cannot import name 'redis_runtime'` 或 `AttributeError`。

- [ ] **Step 3: 实现 `redis_runtime.py`**

Create `GuanDan_backend-V2.0/services/redis_runtime.py`:

```python
import os

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


class RedisRuntimeError(Exception):
    """Redis 运行态错误，用于明确阻断静默降级。"""

    def __init__(self, code, message, original_error=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.original_error = original_error


_redis_client = None


def _build_redis_client():
    if redis is None:
        raise RedisRuntimeError("redis_unavailable", "Redis 依赖未安装")

    client = redis.Redis(
        host=os.getenv("REDIS_HOST", "127.0.0.1"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD") or None,
        socket_timeout=float(os.getenv("REDIS_TIMEOUT_SECONDS", "0.5")),
        decode_responses=True,
    )
    return client


def require_redis():
    """获取 Redis 客户端；不可用时抛错，不返回 None。"""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        client = _build_redis_client()
        client.ping()
    except RedisRuntimeError:
        raise
    except Exception as exc:
        raise RedisRuntimeError("redis_unavailable", f"Redis 不可用：{exc}", exc)

    _redis_client = client
    return _redis_client


def reset_redis_client_for_tests():
    global _redis_client
    _redis_client = None


def runtime_error_to_api_payload(exc):
    return {
        "ok": False,
        "error": exc.code,
        "message": exc.message,
        "data": {},
    }
```

- [ ] **Step 4: 实现 `perf_logger.py`**

Create `GuanDan_backend-V2.0/services/perf_logger.py`:

```python
import os
import time
from contextlib import contextmanager


def is_perf_log_enabled():
    return os.getenv("PERF_LOG_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


@contextmanager
def perf_timer(name, **fields):
    start = time.perf_counter()
    try:
        yield
    finally:
        if is_perf_log_enabled():
            elapsed_ms = (time.perf_counter() - start) * 1000
            parts = [f"{key}={value}" for key, value in fields.items()]
            suffix = " ".join(parts)
            print(f"[perf] {name} elapsed_ms={elapsed_ms:.2f} {suffix}".rstrip())
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_redis_runtime -v
```

Expected: PASS，4 tests OK。

- [ ] **Step 6: 提交**

```powershell
git add -- GuanDan_backend-V2.0/services/redis_runtime.py GuanDan_backend-V2.0/services/perf_logger.py GuanDan_backend-V2.0/tests/test_redis_runtime.py
git commit -m "feat: add redis runtime dependency guard"
```

Expected: commit succeeds；不要暂存其他文件。

---

### Task 2: 运行态事实仓库

**Files:**
- Create: `GuanDan_backend-V2.0/tests/fakes.py`
- Create: `GuanDan_backend-V2.0/services/runtime_store.py`
- Create: `GuanDan_backend-V2.0/tests/test_runtime_store.py`

- [ ] **Step 1: 创建测试 FakeRedis**

Create `GuanDan_backend-V2.0/tests/fakes.py`:

```python
import fnmatch


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.hashes = {}
        self.sets = {}

    def ping(self):
        return True

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value
        return True

    def setex(self, key, ttl_seconds, value):
        self.values[key] = value
        return True

    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self.values:
                del self.values[key]
                count += 1
            if key in self.hashes:
                del self.hashes[key]
                count += 1
            if key in self.sets:
                del self.sets[key]
                count += 1
        return count

    def hset(self, key, mapping=None, field=None, value=None):
        bucket = self.hashes.setdefault(key, {})
        if mapping is not None:
            bucket.update(mapping)
        elif field is not None:
            bucket[field] = value
        return True

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def sadd(self, key, *values):
        bucket = self.sets.setdefault(key, set())
        before = len(bucket)
        bucket.update(values)
        return len(bucket) - before

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def srem(self, key, *values):
        bucket = self.sets.setdefault(key, set())
        before = len(bucket)
        for value in values:
            bucket.discard(value)
        return before - len(bucket)

    def scan_iter(self, match=None, count=None):
        keys = set(self.values) | set(self.hashes) | set(self.sets)
        for key in sorted(keys):
            if match is None or fnmatch.fnmatch(key, match):
                yield key

    def setnx(self, key, value):
        if key in self.values:
            return False
        self.values[key] = value
        return True

    def expire(self, key, seconds):
        return True
```

- [ ] **Step 2: 编写事实仓库失败测试**

Create `GuanDan_backend-V2.0/tests/test_runtime_store.py`:

```python
import unittest
from unittest.mock import patch

from services import runtime_store
from services.redis_runtime import RedisRuntimeError
from tests.fakes import FakeRedis


class TestRuntimeStore(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()

    def patch_redis(self):
        return patch("services.runtime_store.require_redis", return_value=self.redis)

    def test_get_current_turn_requires_initialized_state(self):
        with self.patch_redis():
            with self.assertRaises(RedisRuntimeError) as cm:
                runtime_store.get_current_turn()

        self.assertEqual(cm.exception.code, "redis_not_initialized")

    def test_set_and_get_current_turn(self):
        with self.patch_redis():
            runtime_store.initialize_empty_state()
            runtime_store.set_current_turn("2")
            self.assertEqual(runtime_store.get_current_turn(), "2")

    def test_store_and_find_match(self):
        fights = [
            (1, "A队", "张三-李四", "B队", "王五-赵六"),
            (2, "C队", "甲-乙", "D队", "丙-丁"),
        ]
        with self.patch_redis():
            runtime_store.initialize_empty_state()
            runtime_store.write_fights(1, fights)
            match = runtime_store.get_match(1, 2)

        self.assertEqual(match["team1_name"], "C队")
        self.assertEqual(match["team2_members"], "丙-丁")

    def test_submit_score_updates_redis_and_marks_dirty(self):
        mini_teams = [
            {"team_name": "A队", "turn": 1, "big_score": 0, "small_score": 0},
            {"team_name": "B队", "turn": 1, "big_score": 0, "small_score": 0},
        ]
        fights = [(1, "A队", "张三-李四", "B队", "王五-赵六")]

        with self.patch_redis():
            runtime_store.initialize_empty_state()
            runtime_store.write_mini_teams(1, mini_teams)
            runtime_store.write_fights(1, fights)
            runtime_store.apply_score_result(
                1,
                {"A队": 4, "B队": -4},
                {"A队": 2, "B队": 0},
            )
            rows = runtime_store.read_mini_teams(1)
            dirty = self.redis.smembers(runtime_store.DIRTY_SCORE_KEY)

        by_name = {row["team_name"]: row for row in rows}
        self.assertEqual(by_name["A队"]["small_score"], 4)
        self.assertEqual(by_name["A队"]["big_score"], 2)
        self.assertEqual(by_name["B队"]["small_score"], -4)
        self.assertEqual(dirty, {"1:A队", "1:B队"})
```

- [ ] **Step 3: 运行测试并确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_store -v
```

Expected: FAIL，错误包含 `cannot import name 'runtime_store'`。

- [ ] **Step 4: 实现事实仓库**

Create `GuanDan_backend-V2.0/services/runtime_store.py`:

```python
import json
import time

from services.redis_runtime import RedisRuntimeError, require_redis


STATE_KEY = "gd:state"
TEAMS_KEY = "gd:teams"
TEAM_LEVELS_KEY = "gd:team_levels"
DIRTY_SCORE_KEY = "gd:dirty:score_updates"
DIRTY_MATCHES_KEY = "gd:dirty:matches"
DIRTY_TEAMS_KEY = "gd:dirty:teams"
SCHEMA_VERSION = "1"
VALID_TURNS = {"1", "2", "3"}


def _json_default(value):
    return str(value)


def _dumps(value):
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _loads(raw, default):
    if raw in (None, ""):
        return default
    return json.loads(raw)


def _mini_teams_key(turn):
    return f"gd:mini_teams:turn:{int(turn)}"


def _fights_key(turn):
    return f"gd:fights:turn:{int(turn)}"


def _normalize_row(row, columns=None):
    if isinstance(row, dict):
        return dict(row)
    if columns:
        return dict(zip(columns, row))
    return list(row)


def _require_initialized(client):
    state = client.hgetall(STATE_KEY)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise RedisRuntimeError("redis_not_initialized", "Redis 运行态数据未初始化")
    return state


def initialize_empty_state():
    client = require_redis()
    now = str(time.time())
    client.hset(
        STATE_KEY,
        mapping={
            "current_turn": "null",
            "timer_started_at": "",
            "timer_total_seconds": "3600",
            "schema_version": SCHEMA_VERSION,
            "last_loaded_at": now,
            "last_flush_at": "",
            "flush_status": "ok",
            "flush_error": "",
        },
    )


def get_state():
    client = require_redis()
    return _require_initialized(client)


def update_state(**fields):
    client = require_redis()
    _require_initialized(client)
    client.hset(STATE_KEY, mapping={key: "" if value is None else str(value) for key, value in fields.items()})


def get_current_turn():
    return get_state().get("current_turn", "null")


def set_current_turn(turn):
    value = str(turn).strip() if turn not in (None, "") else "null"
    if value != "null" and value not in VALID_TURNS:
        raise ValueError("invalid_turn")
    update_state(current_turn=value)
    return value


def write_teams(rows, columns=None, mark_dirty=False):
    client = require_redis()
    _require_initialized(client)
    client.set(TEAMS_KEY, _dumps([_normalize_row(row, columns) for row in rows]))
    if mark_dirty:
        client.sadd(DIRTY_TEAMS_KEY, "teams")


def read_teams():
    client = require_redis()
    _require_initialized(client)
    return _loads(client.get(TEAMS_KEY), [])


def write_team_levels(rows, columns=None, mark_dirty=False):
    client = require_redis()
    _require_initialized(client)
    client.set(TEAM_LEVELS_KEY, _dumps([_normalize_row(row, columns) for row in rows]))
    if mark_dirty:
        client.sadd(DIRTY_TEAMS_KEY, "team_levels")


def read_team_levels():
    client = require_redis()
    _require_initialized(client)
    return _loads(client.get(TEAM_LEVELS_KEY), [])


def write_mini_teams(turn, rows, columns=None):
    client = require_redis()
    _require_initialized(client)
    client.set(_mini_teams_key(turn), _dumps([_normalize_row(row, columns) for row in rows]))


def read_mini_teams(turn):
    client = require_redis()
    _require_initialized(client)
    return _loads(client.get(_mini_teams_key(turn)), [])


def write_fights(turn, rows, columns=None, mark_dirty=True):
    client = require_redis()
    _require_initialized(client)
    client.set(_fights_key(turn), _dumps([_normalize_row(row, columns) for row in rows]))
    if mark_dirty:
        client.sadd(DIRTY_MATCHES_KEY, str(int(turn)))


def read_fights(turn):
    client = require_redis()
    _require_initialized(client)
    return _loads(client.get(_fights_key(turn)), [])


def _value_from_row(row, key, index=None):
    if isinstance(row, dict):
        return row.get(key)
    if isinstance(row, list) and index is not None and index < len(row):
        return row[index]
    return None


def get_match(turn, table_num):
    table = int(table_num)
    for row in read_fights(turn):
        row_table = _value_from_row(row, "id", 0)
        if int(row_table) != table:
            continue
        return {
            "table_num": table,
            "team1_name": _value_from_row(row, "team_name_1", 1),
            "team1_members": _value_from_row(row, "members_1", 2),
            "team2_name": _value_from_row(row, "team_name_2", 3),
            "team2_members": _value_from_row(row, "members_2", 4),
            "turn_num": int(turn),
        }
    return None


def apply_score_result(turn, small_scores, big_scores):
    client = require_redis()
    _require_initialized(client)
    rows = read_mini_teams(turn)
    turn_int = int(turn)
    for row in rows:
        team_name = row.get("team_name") if isinstance(row, dict) else None
        if team_name in small_scores:
            row["small_score"] = small_scores[team_name]
            client.sadd(DIRTY_SCORE_KEY, f"{turn_int}:{team_name}")
        if team_name in big_scores:
            row["big_score"] = big_scores[team_name]
            client.sadd(DIRTY_SCORE_KEY, f"{turn_int}:{team_name}")
    client.set(_mini_teams_key(turn), _dumps(rows))
    return rows
```

- [ ] **Step 5: 运行事实仓库测试**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_store -v
```

Expected: PASS，4 tests OK。

- [ ] **Step 6: 提交**

```powershell
git add -- GuanDan_backend-V2.0/tests/fakes.py GuanDan_backend-V2.0/services/runtime_store.py GuanDan_backend-V2.0/tests/test_runtime_store.py
git commit -m "feat: add redis runtime store"
```

Expected: commit succeeds；不要暂存其他文件。

---

### Task 3: Redis 读模型构建

**Files:**
- Create: `GuanDan_backend-V2.0/services/runtime_views.py`
- Create: `GuanDan_backend-V2.0/tests/test_runtime_views.py`

- [ ] **Step 1: 编写读模型失败测试**

Create `GuanDan_backend-V2.0/tests/test_runtime_views.py`:

```python
import unittest
from unittest.mock import patch

from services import runtime_store, runtime_views
from tests.fakes import FakeRedis


class TestRuntimeViews(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        patcher = patch("services.runtime_store.require_redis", return_value=self.redis)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher_views = patch("services.runtime_views.require_redis", return_value=self.redis)
        patcher_views.start()
        self.addCleanup(patcher_views.stop)
        runtime_store.initialize_empty_state()
        runtime_store.set_current_turn("1")
        runtime_store.write_teams([{"id": 1, "office": "研发部", "team_name_1": "A队"}])
        runtime_store.write_team_levels([{"team_name": "A队", "level": "A"}])
        runtime_store.write_mini_teams(
            1,
            [
                {"office": "研发部", "team_name": "A队", "member_name": "张三-李四", "big_score": 2, "small_score": 4, "turn": 1},
                {"office": "研发部", "team_name": "B队", "member_name": "王五-赵六", "big_score": 0, "small_score": -4, "turn": 1},
            ],
        )
        runtime_store.write_fights(1, [(1, "A队", "张三-李四", "B队", "王五-赵六")])

    def test_build_dashboard_view(self):
        view = runtime_views.rebuild_dashboard_view(1)

        self.assertEqual(view["TURN"], "1")
        self.assertEqual(len(view["matchesinfo"]), 1)
        self.assertEqual(view["scoresinfo"][0][0], "A队")
        self.assertEqual(view["sumteaminfo"]["current_turn"][0][1], "A队")

    def test_build_admin_matches_view_includes_scores(self):
        view = runtime_views.rebuild_admin_matches_view()

        self.assertEqual(view["matches"][0]["team_name_1"], "A队")
        self.assertEqual(view["matches"][0]["team1_big_score"], 2)
        self.assertEqual(view["matches"][0]["team2_small_score"], -4)

    def test_rebuild_all_views_writes_to_redis(self):
        runtime_views.rebuild_all_views()

        self.assertIsNotNone(self.redis.get(runtime_views.DASHBOARD_VIEW_KEY.format(turn=1)))
        self.assertIsNotNone(self.redis.get(runtime_views.ADMIN_OVERVIEW_KEY))
        self.assertIsNotNone(self.redis.get(runtime_views.ADMIN_MATCHES_KEY))
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_views -v
```

Expected: FAIL，错误包含 `cannot import name 'runtime_views'`。

- [ ] **Step 3: 实现读模型构建模块**

Create `GuanDan_backend-V2.0/services/runtime_views.py`:

```python
import json
import time

from services.redis_runtime import require_redis
from services import runtime_store


DASHBOARD_VIEW_KEY = "gd:view:dashboard:{turn}"
ADMIN_OVERVIEW_KEY = "gd:view:admin:overview"
ADMIN_MATCHES_KEY = "gd:view:admin:matches"
CREATE_TABLE_VIEW_KEY = "gd:view:create_table"


def _dumps(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def _loads(raw, default):
    if raw in (None, ""):
        return default
    return json.loads(raw)


def _row_value(row, key, index=None, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    if isinstance(row, list) and index is not None and index < len(row):
        return row[index]
    return default


def _timer_message(state):
    started_at = state.get("timer_started_at")
    if not started_at:
        return "倒计时未开始"
    total_seconds = int(float(state.get("timer_total_seconds") or 3600))
    elapsed = int(time.time() - float(started_at))
    remaining = max(0, total_seconds - elapsed)
    return f"{remaining // 60:02d}:{remaining % 60:02d}"


def _rank_team_rows(rows, turn):
    current = []
    total = []
    by_team = {}
    for row in rows:
        team = row.get("team_name")
        item = by_team.setdefault(team, {"big": 0, "small": 0})
        item["big"] += int(row.get("big_score") or 0)
        item["small"] += int(row.get("small_score") or 0)

    ranked = sorted(by_team.items(), key=lambda item: (-item[1]["big"], -item[1]["small"], item[0]))
    for idx, (team, score) in enumerate(ranked, start=1):
        current.append((idx, team, score["big"], score["small"]))
        total.append((idx, team, score["big"], score["small"]))
    return current, total


def _rank_office_rows(rows):
    by_office = {}
    for row in rows:
        office = row.get("office")
        item = by_office.setdefault(office, {"big": 0, "small": 0})
        item["big"] += int(row.get("big_score") or 0)
        item["small"] += int(row.get("small_score") or 0)
    ranked = sorted(by_office.items(), key=lambda item: (-item[1]["big"], -item[1]["small"], item[0]))
    rows = [(idx, office, score["big"], score["small"]) for idx, (office, score) in enumerate(ranked, start=1)]
    return rows, list(rows)


def rebuild_dashboard_view(turn):
    client = require_redis()
    state = runtime_store.get_state()
    fights = runtime_store.read_fights(turn)
    mini_teams = runtime_store.read_mini_teams(turn)
    team_current, team_total = _rank_team_rows(mini_teams, turn)
    office_current, office_total = _rank_office_rows(mini_teams)
    scores = [
        (
            row.get("team_name"),
            row.get("member_name"),
            row.get("small_score"),
        )
        for row in mini_teams
    ]
    view = {
        "TURN": str(turn),
        "time_message": _timer_message(state),
        "matchesinfo": fights,
        "scoresinfo": scores,
        "sumteaminfo": {"current_turn": team_current, "total_until_turn": team_total},
        "officescore": {"current_turn": office_current, "total_until_turn": office_total},
        "snapshot_updated_at": time.time(),
    }
    client.set(DASHBOARD_VIEW_KEY.format(turn=int(turn)), _dumps(view))
    return view


def rebuild_admin_overview_view():
    client = require_redis()
    state = runtime_store.get_state()
    current_turn = state.get("current_turn", "null")
    teams = runtime_store.read_teams()
    has_matches = any(runtime_store.read_fights(turn) for turn in (1, 2, 3))
    view = {
        "turn": current_turn,
        "time_message": _timer_message(state),
        "teams": teams,
        "has_matches": has_matches,
        "runtime_status": "ok",
        "flush_status": state.get("flush_status", "ok"),
        "last_flush_at": state.get("last_flush_at", ""),
        "flush_error": state.get("flush_error", ""),
        "snapshot_updated_at": time.time(),
    }
    client.set(ADMIN_OVERVIEW_KEY, _dumps(view))
    return view


def rebuild_admin_matches_view():
    client = require_redis()
    matches = []
    for turn in (1, 2, 3):
        score_by_team = {
            row.get("team_name"): row
            for row in runtime_store.read_mini_teams(turn)
            if isinstance(row, dict)
        }
        for fight in runtime_store.read_fights(turn):
            table_no = _row_value(fight, "id", 0)
            team1 = _row_value(fight, "team_name_1", 1)
            team2 = _row_value(fight, "team_name_2", 3)
            team1_score = score_by_team.get(team1, {})
            team2_score = score_by_team.get(team2, {})
            matches.append(
                {
                    "table_no": table_no,
                    "team_name_1": team1,
                    "members_1": _row_value(fight, "members_1", 2),
                    "team_name_2": team2,
                    "members_2": _row_value(fight, "members_2", 4),
                    "turn": turn,
                    "team_level_1": _row_value(fight, "team_level_1", 6),
                    "team_level_2": _row_value(fight, "team_level_2", 7),
                    "team1_big_score": team1_score.get("big_score"),
                    "team1_small_score": team1_score.get("small_score"),
                    "team2_big_score": team2_score.get("big_score"),
                    "team2_small_score": team2_score.get("small_score"),
                }
            )
    view = {"matches": matches}
    client.set(ADMIN_MATCHES_KEY, _dumps(view))
    return view


def rebuild_create_table_view():
    client = require_redis()
    rows = []
    for turn in (1, 2, 3):
        table_by_team = {}
        for fight in runtime_store.read_fights(turn):
            table_by_team[_row_value(fight, "team_name_1", 1)] = _row_value(fight, "id", 0)
            table_by_team[_row_value(fight, "team_name_2", 3)] = _row_value(fight, "id", 0)
        for row in runtime_store.read_mini_teams(turn):
            rows.append({"team": row, "fight_id": table_by_team.get(row.get("team_name"))})
    view = {"rows": rows}
    client.set(CREATE_TABLE_VIEW_KEY, _dumps(view))
    return view


def read_view(key, default=None):
    return _loads(require_redis().get(key), default or {})


def read_dashboard_view(turn):
    return read_view(DASHBOARD_VIEW_KEY.format(turn=int(turn)), {})


def read_admin_overview_view():
    return read_view(ADMIN_OVERVIEW_KEY, {})


def read_admin_matches_view():
    return read_view(ADMIN_MATCHES_KEY, {"matches": []})


def read_create_table_view():
    return read_view(CREATE_TABLE_VIEW_KEY, {"rows": []})


def rebuild_all_views():
    for turn in (1, 2, 3):
        rebuild_dashboard_view(turn)
    rebuild_admin_overview_view()
    rebuild_admin_matches_view()
    rebuild_create_table_view()
```

- [ ] **Step 4: 运行读模型测试**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_views -v
```

Expected: PASS，3 tests OK。

- [ ] **Step 5: 提交**

```powershell
git add -- GuanDan_backend-V2.0/services/runtime_views.py GuanDan_backend-V2.0/tests/test_runtime_views.py
git commit -m "feat: build redis runtime views"
```

Expected: commit succeeds；不要暂存其他文件。

---

### Task 4: MySQL 写回服务

**Files:**
- Create: `GuanDan_backend-V2.0/services/runtime_flush_service.py`
- Create: `GuanDan_backend-V2.0/tests/test_runtime_flush_service.py`

- [ ] **Step 1: 编写写回失败测试**

Create `GuanDan_backend-V2.0/tests/test_runtime_flush_service.py`:

```python
import unittest
from unittest.mock import patch

from services import runtime_flush_service, runtime_store
from tests.fakes import FakeRedis


class FakeCursor:
    def __init__(self):
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params))

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class TestRuntimeFlushService(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        patcher = patch("services.runtime_store.require_redis", return_value=self.redis)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher_flush = patch("services.runtime_flush_service.require_redis", return_value=self.redis)
        patcher_flush.start()
        self.addCleanup(patcher_flush.stop)
        runtime_store.initialize_empty_state()
        runtime_store.write_mini_teams(
            1,
            [
                {"team_name": "A队", "turn": 1, "big_score": 2, "small_score": 4},
                {"team_name": "B队", "turn": 1, "big_score": 0, "small_score": -4},
            ],
        )
        self.redis.sadd(runtime_store.DIRTY_SCORE_KEY, "1:A队", "1:B队")

    def test_flush_once_writes_latest_scores_and_clears_dirty(self):
        conn = FakeConnection()

        result = runtime_flush_service.flush_once(lambda: conn)

        self.assertTrue(result["ok"])
        self.assertTrue(conn.committed)
        self.assertEqual(self.redis.smembers(runtime_store.DIRTY_SCORE_KEY), set())
        self.assertEqual(self.redis.hget(runtime_store.STATE_KEY, "flush_status"), "ok")
        self.assertEqual(len(conn.cursor_obj.statements), 4)

    def test_flush_once_keeps_dirty_when_db_write_fails(self):
        class BrokenCursor(FakeCursor):
            def execute(self, sql, params=None):
                raise RuntimeError("db down")

        class BrokenConnection(FakeConnection):
            def __init__(self):
                super().__init__()
                self.cursor_obj = BrokenCursor()

        conn = BrokenConnection()

        result = runtime_flush_service.flush_once(lambda: conn)

        self.assertFalse(result["ok"])
        self.assertTrue(conn.rolled_back)
        self.assertEqual(self.redis.smembers(runtime_store.DIRTY_SCORE_KEY), {"1:A队", "1:B队"})
        self.assertEqual(self.redis.hget(runtime_store.STATE_KEY, "flush_status"), "failed")
        self.assertIn("db down", self.redis.hget(runtime_store.STATE_KEY, "flush_error"))

    def test_flush_once_persists_dirty_matches(self):
        runtime_store.write_fights(
            1,
            [
                {
                    "id": 1,
                    "team_name_1": "A队",
                    "members_1": "张三-李四",
                    "team_name_2": "B队",
                    "members_2": "王五-赵六",
                    "turn": 1,
                    "team_level_1": "A",
                    "team_level_2": "B",
                }
            ],
        )
        conn = FakeConnection()

        result = runtime_flush_service.flush_once(lambda: conn)

        self.assertTrue(result["ok"])
        self.assertEqual(self.redis.smembers(runtime_store.DIRTY_MATCHES_KEY), set())
        joined_sql = "\n".join(sql for sql, _params in conn.cursor_obj.statements)
        self.assertIn("DELETE FROM fight_info", joined_sql)
        self.assertIn("INSERT INTO fight_info", joined_sql)
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_flush_service -v
```

Expected: FAIL，错误包含 `cannot import name 'runtime_flush_service'`。

- [ ] **Step 3: 实现写回服务**

Create `GuanDan_backend-V2.0/services/runtime_flush_service.py`:

第一阶段写回服务实现比分和对阵持久化；报名/队伍数据仍由导入流程先写 MySQL，再加载到 Redis。若发现 `gd:dirty:teams`，写回服务返回失败并保留标记，避免静默丢失未实现的数据写回。

```python
import os
import threading
import time

from services.redis_runtime import require_redis
from services import runtime_store


FLUSH_INTERVAL_SECONDS = float(os.getenv("RUNTIME_FLUSH_INTERVAL_SECONDS", "10"))
FLUSH_LOCK_KEY = "gd:flush:lock"
_worker_started = False
_worker_lock = threading.Lock()


def _score_by_team(turn):
    return {
        row.get("team_name"): row
        for row in runtime_store.read_mini_teams(turn)
        if isinstance(row, dict)
    }


def _flush_score_updates(cursor, dirty_members):
    grouped = {}
    for member in dirty_members:
        turn_raw, team_name = str(member).split(":", 1)
        grouped.setdefault(int(turn_raw), set()).add(team_name)

    for turn, team_names in grouped.items():
        scores = _score_by_team(turn)
        for team_name in team_names:
            row = scores.get(team_name)
            if row is None:
                continue
            cursor.execute(
                """
                UPDATE mini_team_info
                SET small_score = %s
                WHERE team_name = %s AND turn = %s
                """,
                (row.get("small_score", 0), team_name, turn),
            )
            cursor.execute(
                """
                UPDATE mini_team_info
                SET big_score = %s
                WHERE team_name = %s AND turn = %s
                """,
                (row.get("big_score", 0), team_name, turn),
            )


def _fight_value(row, key, default=None):
    return row.get(key, default) if isinstance(row, dict) else default


def _flush_matches(cursor, dirty_turns):
    for turn_raw in dirty_turns:
        turn = int(turn_raw)
        fights = runtime_store.read_fights(turn)
        cursor.execute("DELETE FROM fight_info WHERE turn = %s", (turn,))
        for fight in fights:
            cursor.execute(
                """
                INSERT INTO fight_info
                (id, team_name_1, members_1, team_name_2, members_2, turn, team_level_1, team_level_2)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    _fight_value(fight, "id"),
                    _fight_value(fight, "team_name_1"),
                    _fight_value(fight, "members_1"),
                    _fight_value(fight, "team_name_2"),
                    _fight_value(fight, "members_2"),
                    turn,
                    _fight_value(fight, "team_level_1"),
                    _fight_value(fight, "team_level_2"),
                ),
            )


def flush_once(get_db_connection):
    client = require_redis()
    dirty_scores = sorted(client.smembers(runtime_store.DIRTY_SCORE_KEY))
    dirty_matches = sorted(client.smembers(runtime_store.DIRTY_MATCHES_KEY))
    dirty_teams = sorted(client.smembers(runtime_store.DIRTY_TEAMS_KEY))
    if dirty_teams:
        message = "team dirty writeback is not enabled in this phase"
        runtime_store.update_state(flush_status="failed", flush_error=message)
        return {"ok": False, "dirty_count": len(dirty_teams), "error": message}
    if not dirty_scores and not dirty_matches and not dirty_teams:
        runtime_store.update_state(flush_status="ok", flush_error="")
        return {"ok": True, "dirty_count": 0}

    if not client.setnx(FLUSH_LOCK_KEY, str(time.time())):
        return {"ok": True, "skipped": "locked", "dirty_count": len(dirty_scores)}
    client.expire(FLUSH_LOCK_KEY, max(5, int(FLUSH_INTERVAL_SECONDS * 2)))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        _flush_score_updates(cursor, dirty_scores)
        _flush_matches(cursor, dirty_matches)
        conn.commit()
        if dirty_scores:
            client.srem(runtime_store.DIRTY_SCORE_KEY, *dirty_scores)
        if dirty_matches:
            client.srem(runtime_store.DIRTY_MATCHES_KEY, *dirty_matches)
        runtime_store.update_state(last_flush_at=time.time(), flush_status="ok", flush_error="")
        return {"ok": True, "dirty_count": len(dirty_scores) + len(dirty_matches)}
    except Exception as exc:
        conn.rollback()
        runtime_store.update_state(flush_status="failed", flush_error=str(exc))
        return {"ok": False, "dirty_count": len(dirty_scores), "error": str(exc)}
    finally:
        cursor.close()
        conn.close()
        client.delete(FLUSH_LOCK_KEY)


def _worker(get_db_connection):
    while True:
        try:
            flush_once(get_db_connection)
        except Exception as exc:
            try:
                runtime_store.update_state(flush_status="failed", flush_error=str(exc))
            except Exception:
                pass
        time.sleep(FLUSH_INTERVAL_SECONDS)


def ensure_runtime_flush_worker_started(get_db_connection):
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if _worker_started:
            return
        worker = threading.Thread(target=_worker, args=(get_db_connection,), daemon=True)
        worker.start()
        _worker_started = True
```

- [ ] **Step 4: 运行写回测试**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_flush_service -v
```

Expected: PASS，3 tests OK。

- [ ] **Step 5: 提交**

```powershell
git add -- GuanDan_backend-V2.0/services/runtime_flush_service.py GuanDan_backend-V2.0/tests/test_runtime_flush_service.py
git commit -m "feat: add redis runtime flush service"
```

Expected: commit succeeds；不要暂存其他文件。

---

### Task 5: 后台 workflow 接入 Redis 运行态

**Files:**
- Modify: `GuanDan_backend-V2.0/services/admin_workflow.py`
- Modify: `GuanDan_backend-V2.0/tests/test_admin_workflow.py`

- [ ] **Step 1: 编写 workflow 行为测试**

Append to `GuanDan_backend-V2.0/tests/test_admin_workflow.py`:

```python
    def test_get_overview_reads_runtime_view(self):
        self.patch_workflow("read_admin_overview_view", lambda: {"turn": "1", "teams": [], "flush_status": "ok"})

        result = admin_workflow.get_overview(object())

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["turn"], "1")
        self.assertEqual(result["data"]["flush_status"], "ok")

    def test_get_all_matches_reads_runtime_view(self):
        self.patch_workflow("read_admin_matches_view", lambda: {"matches": [{"table_no": 1}]})

        result = admin_workflow.get_all_matches(object())

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], {"matches": [{"table_no": 1}]})

    def test_get_match_for_score_uses_runtime_store_without_mysql_check(self):
        def fail_db_call(*args, **kwargs):
            raise AssertionError("should not query mysql")

        self.patch_workflow("runtime_get_match", lambda turn, table: {"turn_num": 1, "table_num": 2})
        self.patch_workflow("check_match_exists", fail_db_call)

        result = admin_workflow.get_match_for_score(object(), None, "1", "2")

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["table_num"], 2)
```

If the existing test class does not have `patch_workflow()`, add this helper inside the class:

```python
    def patch_workflow(self, name, value):
        original = getattr(admin_workflow, name, None)
        setattr(admin_workflow, name, value)
        self.addCleanup(lambda: setattr(admin_workflow, name, original))
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_admin_workflow -v
```

Expected: FAIL，错误包含缺少 `read_admin_overview_view`、`read_admin_matches_view` 或 `runtime_get_match`。

- [ ] **Step 3: 修改 `admin_workflow.py` 的 lazy imports**

In `GuanDan_backend-V2.0/services/admin_workflow.py`, add globals near existing globals:

```python
read_admin_overview_view = None
read_admin_matches_view = None
rebuild_all_views = None
rebuild_admin_matches_view = None
rebuild_admin_overview_view = None
runtime_get_match = None
runtime_apply_score_result = None
runtime_set_current_turn = None
runtime_get_current_turn = None
runtime_write_fights = None
runtime_read_mini_teams = None
runtime_read_team_levels = None
```

Add loader:

```python
def _load_runtime(required=None):
    global read_admin_overview_view, read_admin_matches_view
    global rebuild_all_views, rebuild_admin_matches_view, rebuild_admin_overview_view
    global runtime_get_match, runtime_apply_score_result, runtime_set_current_turn
    global runtime_get_current_turn, runtime_write_fights, runtime_read_mini_teams, runtime_read_team_levels
    required = required or ()
    if required and all(globals()[name] is not None for name in required):
        return

    from services.runtime_views import (
        read_admin_overview_view as _read_admin_overview_view,
        read_admin_matches_view as _read_admin_matches_view,
        rebuild_all_views as _rebuild_all_views,
        rebuild_admin_matches_view as _rebuild_admin_matches_view,
        rebuild_admin_overview_view as _rebuild_admin_overview_view,
    )
    from services.runtime_store import (
        get_match as _runtime_get_match,
        apply_score_result as _runtime_apply_score_result,
        set_current_turn as _runtime_set_current_turn,
        get_current_turn as _runtime_get_current_turn,
        write_fights as _runtime_write_fights,
        read_mini_teams as _runtime_read_mini_teams,
        read_team_levels as _runtime_read_team_levels,
    )

    read_admin_overview_view = _read_admin_overview_view
    read_admin_matches_view = _read_admin_matches_view
    rebuild_all_views = _rebuild_all_views
    rebuild_admin_matches_view = _rebuild_admin_matches_view
    rebuild_admin_overview_view = _rebuild_admin_overview_view
    runtime_get_match = _runtime_get_match
    runtime_apply_score_result = _runtime_apply_score_result
    runtime_set_current_turn = _runtime_set_current_turn
    runtime_get_current_turn = _runtime_get_current_turn
    runtime_write_fights = _runtime_write_fights
    runtime_read_mini_teams = _runtime_read_mini_teams
    runtime_read_team_levels = _runtime_read_team_levels
```

- [ ] **Step 4: 修改 overview 和 matches**

Replace `get_overview()`:

```python
def get_overview(get_db_connection):
    _load_runtime(("read_admin_overview_view",))
    return api_success("后台概览已获取", read_admin_overview_view())
```

Replace `get_all_matches()`:

```python
def get_all_matches(get_db_connection):
    _load_runtime(("read_admin_matches_view",))
    return api_success("对阵列表已获取", read_admin_matches_view())
```

- [ ] **Step 5: 修改轮次设置**

In `set_turn_value()`, replace dashboard-cache state mutation with runtime store:

```python
def set_turn_value(value):
    _load_runtime(("runtime_set_current_turn", "rebuild_admin_overview_view"))
    turn = str(value).strip() if value is not None else ""
    try:
        saved_turn = runtime_set_current_turn(turn or "null")
    except ValueError:
        return api_error("invalid_turn", "轮次值无效")

    rebuild_admin_overview_view()
    return api_success("当前轮次已更新", {"turn": saved_turn})
```

- [ ] **Step 6: 修改录分加载和提交**

Replace `get_match_for_score()`:

```python
def get_match_for_score(get_db_connection, load_fight_info, turn_num, table_num):
    _load_dashboard_cache(("is_valid_turn",))
    _load_runtime(("runtime_get_match",))
    turn = str(turn_num).strip() if turn_num is not None else ""
    if not turn.isdigit() or not is_valid_turn(turn):
        return api_error("invalid_turn", "轮次值无效")

    table = parse_table_number(table_num)
    if table is None:
        return api_error("invalid_table", "桌号无效")

    match_info = runtime_get_match(int(turn), table)
    if match_info is None:
        return api_error("match_not_found", "未找到该桌对阵")
    return api_success("录分对阵已获取", match_info)
```

In `submit_score()`, replace the `is_writeback_enabled()` / `enqueue_score_update()` / `apply_score_update()` block with:

```python
    _load_runtime(("runtime_apply_score_result", "rebuild_admin_matches_view", "rebuild_admin_overview_view"))
    runtime_apply_score_result(
        int(match_info["turn_num"]),
        update_payload["small_scores"],
        update_payload["big_scores"],
    )
    rebuild_admin_matches_view()
    rebuild_admin_overview_view()
    queued = True
```

Keep existing `save_score_log()` and API response shape.

- [ ] **Step 7: 运行 workflow 测试**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_admin_workflow -v
```

Expected: PASS。If the known pre-existing scoring test is not part of this command, do not adjust scoring behavior here.

- [ ] **Step 8: 提交**

```powershell
git add -- GuanDan_backend-V2.0/services/admin_workflow.py GuanDan_backend-V2.0/tests/test_admin_workflow.py
git commit -m "refactor: route admin workflow through redis runtime"
```

Expected: commit succeeds；不要暂存其他文件。

---

### Task 6: 大屏接口替换进程内 snapshot

**Files:**
- Modify: `GuanDan_backend-V2.0/api/frontend_api.py`
- Modify: `GuanDan_backend-V2.0/api/dashboard_cache.py`
- Create: `GuanDan_backend-V2.0/tests/test_runtime_api_integration.py`

- [ ] **Step 1: 编写 API 测试**

Create `GuanDan_backend-V2.0/tests/test_runtime_api_integration.py`:

```python
import unittest
from unittest.mock import patch

from flask import Flask

from api.frontend_api import frontend_api_bp
from services.redis_runtime import RedisRuntimeError


class TestRuntimeFrontendApi(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(frontend_api_bp)
        self.client = app.test_client()

    def test_dashboard_snapshot_returns_runtime_redis_error(self):
        with patch("api.frontend_api.get_runtime_dashboard_snapshot", side_effect=RedisRuntimeError("redis_unavailable", "Redis 不可用")):
            response = self.client.get("/dashboard_snapshot")

        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "redis_unavailable")

    def test_dashboard_snapshot_reads_runtime_view(self):
        with patch(
            "api.frontend_api.get_runtime_dashboard_snapshot",
            return_value={
                "TURN": "1",
                "time_message": "倒计时未开始",
                "matchesinfo": [],
                "scoresinfo": [],
                "sumteaminfo": {"current_turn": [], "total_until_turn": []},
                "officescore": {"current_turn": [], "total_until_turn": []},
                "snapshot_updated_at": 123,
            },
        ):
            response = self.client.get("/dashboard_snapshot")

        payload = response.get_json()
        self.assertEqual(payload["TURN"], "1")
        self.assertEqual(payload["snapshot_updated_at"], 123)
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_api_integration -v
```

Expected: FAIL，错误包含缺少 `get_runtime_dashboard_snapshot`。

- [ ] **Step 3: 在 `frontend_api.py` 增加 Redis dashboard helper**

In `GuanDan_backend-V2.0/api/frontend_api.py`, add imports:

```python
from services.redis_runtime import RedisRuntimeError, runtime_error_to_api_payload
from services.runtime_store import get_current_turn
from services.runtime_views import read_dashboard_view
```

Add helper:

```python
def get_runtime_dashboard_snapshot():
    turn = get_current_turn()
    if not is_valid_turn(turn):
        return {
            "TURN": turn,
            "time_message": build_time_message(),
            "error": "invalid turn",
            "matchesinfo": [],
            "scoresinfo": [],
            "sumteaminfo": {"current_turn": [], "total_until_turn": []},
            "officescore": {"current_turn": [], "total_until_turn": []},
        }
    snapshot = read_dashboard_view(turn)
    snapshot["time_message"] = build_time_message()
    return snapshot
```

- [ ] **Step 4: 修改 `/dashboard_snapshot`**

Replace route body:

```python
@frontend_api_bp.route('/dashboard_snapshot', methods=['GET'])
def dashboard_snapshot():
    """聚合接口：从 Redis 运行态读模型读取展示数据。"""
    try:
        return jsonify(get_runtime_dashboard_snapshot())
    except RedisRuntimeError as exc:
        return jsonify(runtime_error_to_api_payload(exc))
```

- [ ] **Step 5: 修改拆分展示接口**

For `/matchesinfo`, `/scoresinfo`, `/sumteaminfo`, `/officescore`, replace snapshot refresh logic with:

```python
    try:
        snapshot = get_runtime_dashboard_snapshot()
    except RedisRuntimeError as exc:
        return jsonify(runtime_error_to_api_payload(exc))
```

Then return the existing field from `snapshot`.

- [ ] **Step 6: 停用 `dashboard_cache.py` 后台刷新**

In `GuanDan_backend-V2.0/api/dashboard_cache.py`, keep compatibility functions but make worker startup no-op:

```python
def mark_snapshot_stale():
    """兼容旧调用；Redis 读模型由写操作主动重建。"""
    return


def ensure_dashboard_snapshot_fresh(force_refresh=False):
    """兼容旧调用；不再触发 MySQL 同步刷新。"""
    return


def background_snapshot_worker():
    """Redis 运行态接管后不再后台轮询 MySQL。"""
    return


def ensure_snapshot_worker_started():
    """兼容旧调用；不再启动 snapshot 线程。"""
    return
```

Do not delete the file. Do not remove `get_turn()` or timer helper functions until runtime store fully replaces them.

- [ ] **Step 7: 运行 API 测试**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_api_integration -v
```

Expected: PASS，2 tests OK。

- [ ] **Step 8: 提交**

```powershell
git add -- GuanDan_backend-V2.0/api/frontend_api.py GuanDan_backend-V2.0/api/dashboard_cache.py GuanDan_backend-V2.0/tests/test_runtime_api_integration.py
git commit -m "refactor: serve dashboard from redis runtime views"
```

Expected: commit succeeds；不要暂存其他文件。

---

### Task 7: 应用启动、Redis 初始化和旧页面接入

**Files:**
- Modify: `GuanDan_backend-V2.0/run.py`
- Modify: `GuanDan_backend-V2.0/services/runtime_store.py`
- Modify: `GuanDan_backend-V2.0/services/admin_workflow.py`

- [ ] **Step 1: 在 `runtime_store.py` 增加 MySQL 初始化方法**

Append:

```python
def _fetch_all(cursor, sql, params=None):
    cursor.execute(sql, params or ())
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    return [_normalize_row(row, columns) for row in rows]


def load_from_mysql(get_db_connection):
    """从 MySQL 加载运行态数据到 Redis，用于导入后初始化和冷启动恢复。"""
    initialize_empty_state()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        write_teams(_fetch_all(cursor, "SELECT * FROM team_info"), mark_dirty=False)
        write_team_levels(_fetch_all(cursor, "SELECT * FROM team_level"), mark_dirty=False)
        for turn in (1, 2, 3):
            write_mini_teams(turn, _fetch_all(cursor, "SELECT * FROM mini_team_info WHERE turn = %s", (turn,)))
            write_fights(turn, _fetch_all(cursor, "SELECT * FROM fight_info WHERE turn = %s", (turn,)), mark_dirty=False)
        update_state(last_loaded_at=time.time(), flush_status="ok", flush_error="")
    finally:
        cursor.close()
        conn.close()
```

- [ ] **Step 2: 在导入、清空、生成对阵后重建 Redis**

In `admin_workflow.import_registration_file()`, after successful MySQL import:

```python
    _load_runtime(("rebuild_all_views",))
    from services.runtime_store import load_from_mysql
    load_from_mysql(get_db_connection)
    rebuild_all_views()
```

In `admin_workflow.clear_business_data()`, after successful MySQL clear:

```python
    from services.runtime_store import initialize_empty_state
    initialize_empty_state()
    _load_runtime(("rebuild_all_views",))
    rebuild_all_views()
```

In `admin_workflow.generate_matches_workflow()`, after `match_result` succeeds but before return, replace the direct MySQL save as follows for phase one:

```python
    _load_runtime(("runtime_write_fights", "rebuild_all_views"))
    total_tables = len(match_result["team_members"]) // 2
    for turn in (1, 2, 3):
        start = (turn - 1) * total_tables
        end = turn * total_tables
        rows = []
        for idx, (team_name_1, team_name_2) in enumerate(match_result["pairs"][start:end], start=1):
            rows.append(
                {
                    "id": idx,
                    "team_name_1": team_name_1,
                    "members_1": match_result["team_members"][team_name_1],
                    "team_name_2": team_name_2,
                    "members_2": match_result["team_members"][team_name_2],
                    "turn": turn,
                    "team_level_1": match_result["team_levels"][team_name_1],
                    "team_level_2": match_result["team_levels"][team_name_2],
                }
            )
        runtime_write_fights(turn, rows)
    rebuild_all_views()
```

Keep the old `replace_fight_info()` call only if the team decides generation must synchronously persist to MySQL. The preferred first Redis version is Redis-first with writer persistence.

- [ ] **Step 3: 启动写回 worker**

In `GuanDan_backend-V2.0/run.py`, replace `ensure_writeback_worker_started` import/use with:

```python
from services.runtime_flush_service import ensure_runtime_flush_worker_started
```

At app startup:

```python
if __name__ == '__main__':
    ensure_runtime_flush_worker_started(get_db_connection)
    app.run(host=app_config.HOST, port=app_config.PORT, debug=app_config.DEBUG)
```

Do not call `ensure_snapshot_worker_started()`.

- [ ] **Step 4: 旧页面读取 Redis 读模型**

In `run.py`, import:

```python
from services.runtime_views import read_create_table_view, read_admin_matches_view
```

Change `/create_table` GET:

```python
@app.route('/create_table', methods=['GET'])
def create_table():
    view = read_create_table_view()
    rows = view.get("rows", [])
    mini_team_info_with_rank = [(i + 1, row) for i, row in enumerate(rows)]
    return render_template(
        'create_table.html',
        mini_team_info=mini_team_info_with_rank,
        current_turn=get_turn(),
    )
```

Change `/generate_matches` GET:

```python
    view = read_admin_matches_view()
    return render_template('generate_matches.html', fights=view.get("matches", []))
```

If templates expect tuple shape and render breaks, add a small adapter in `run.py` to transform dict rows into the original tuple order. Keep the adapter local to `run.py`.

- [ ] **Step 5: 运行 targeted tests**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_runtime_store tests.test_runtime_views tests.test_runtime_flush_service tests.test_admin_workflow tests.test_runtime_api_integration -v
```

Expected: PASS for the listed suites. Do not run full discovery yet if local Redis/MySQL services are not ready.

- [ ] **Step 6: 提交**

```powershell
git add -- GuanDan_backend-V2.0/run.py GuanDan_backend-V2.0/services/runtime_store.py GuanDan_backend-V2.0/services/admin_workflow.py
git commit -m "feat: initialize redis runtime and wire legacy pages"
```

Expected: commit succeeds；不要暂存其他文件。

---

### Task 8: 前端后台显示 Redis/写回状态

**Files:**
- Modify: `GuanDanFront-V2.0/src/views/AdminView.vue`

- [ ] **Step 1: 增加 overview 字段**

In `AdminView.vue`, extend initial `overview`:

```javascript
const overview = ref({
  turn: '',
  time_message: '',
  teams: [],
  has_matches: false,
  snapshot_updated_at: '',
  runtime_status: '',
  flush_status: '',
  last_flush_at: '',
  flush_error: '',
})
```

- [ ] **Step 2: 在 `loadOverview()` 保存字段**

Inside `overview.value = { ... }`, add:

```javascript
      runtime_status: data.runtime_status ?? '',
      flush_status: data.flush_status ?? '',
      last_flush_at: data.last_flush_at ?? '',
      flush_error: data.flush_error ?? '',
```

- [ ] **Step 3: 增加状态卡**

In the summary grid, after 对阵状态 card, add:

```vue
      <article class="summary-card">
        <span>运行状态</span>
        <strong>{{ overview.runtime_status || '未知' }}</strong>
      </article>
      <article class="summary-card">
        <span>写回状态</span>
        <strong>{{ overview.flush_status || '未知' }}</strong>
      </article>
```

- [ ] **Step 4: 增加写回错误提示**

After the existing status messages:

```vue
    <p v-if="overview.flush_error" class="status error">
      MySQL 写回异常：{{ overview.flush_error }}
    </p>
```

- [ ] **Step 5: 构建前端**

Run:

```powershell
cd GuanDanFront-V2.0
npm run build
```

Expected: build succeeds。

- [ ] **Step 6: 提交**

```powershell
git add -- GuanDanFront-V2.0/src/views/AdminView.vue
git commit -m "feat: show redis runtime status in admin"
```

Expected: commit succeeds；不要暂存其他文件。

---

### Task 9: 验证与时延观测

**Files:**
- Modify only if needed: `docs/superpowers/2026-05-15-performance-handoff.md`
- Create if useful: `docs/superpowers/2026-05-16-redis-runtime-verification.md`

- [ ] **Step 1: 运行后端 targeted tests**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest tests.test_redis_runtime tests.test_runtime_store tests.test_runtime_views tests.test_runtime_flush_service tests.test_runtime_api_integration tests.test_admin_workflow tests.test_admin_score_api -v
```

Expected: PASS for all listed suites.

- [ ] **Step 2: 运行后端 discovery**

Run:

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: known residual `tests/test_scoring.py::test_build_score_update_tie_requires_winner` may still fail if not fixed in this task. Do not silently change scoring behavior unless the failure is caused by Redis runtime edits.

- [ ] **Step 3: 运行前端构建**

Run:

```powershell
cd GuanDanFront-V2.0
npm run build
```

Expected: build succeeds。

- [ ] **Step 4: 手工时延验证**

Start Redis, backend and frontend using existing project commands:

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
$env:PERF_LOG_ENABLED="1"
python run.py
```

In another shell:

```powershell
cd GuanDanFront-V2.0
npm run dev
```

Exercise:

```text
1. 打开 http://localhost:5001/admin
2. 点击生成/覆盖对阵
3. 打开后台改分入口
4. 提交一次比分
5. 打开 http://localhost:5001/screen
6. 停止 Redis 后再次请求 /admin 或 /score，确认快速显示 Redis 错误
```

Expected:

```text
/admin 概览和对阵列表不再触发 MySQL 聚合查询
/dashboard_snapshot 不再由后台线程每 5 秒刷新 MySQL
比分提交后 Redis 读模型立即变化
Redis 停止时返回 redis_unavailable
```

- [ ] **Step 5: 记录验证结果**

Create `docs/superpowers/2026-05-16-redis-runtime-verification.md`:

```markdown
# 2026-05-16 Redis 运行态缓存验证记录

## 验证范围

- Redis 运行态事实数据
- 大屏读模型
- 后台概览和对阵列表
- 录分提交
- 10 秒 MySQL 写回

## 自动化验证

- `tests.test_redis_runtime`：
- `tests.test_runtime_store`：
- `tests.test_runtime_views`：
- `tests.test_runtime_flush_service`：
- `tests.test_runtime_api_integration`：
- `tests.test_admin_workflow`：
- `tests.test_admin_score_api`：
- `npm run build`：

## 手工时延观察

- `/admin` 首次加载：
- 生成对阵：
- 后台改分入口：
- 提交比分：
- `/dashboard_snapshot`：
- Redis 停止后的错误返回：

## 残留问题

- 数据库索引和 SQL 优化未纳入本阶段。
- 旧模板仅保留兼容，后续可在 Vue 流程稳定后再讨论下线。
```

- [ ] **Step 6: 提交验证记录**

```powershell
git add -- docs/superpowers/2026-05-16-redis-runtime-verification.md
git commit -m "docs: record redis runtime verification"
```

Expected: commit succeeds；不要暂存其他文件。

---

## 自检清单

- [ ] 所有高频读路径从 Redis 读模型读取：`/admin`、`/score`、`/dashboard_snapshot`。
- [ ] Redis 不可用时返回 `redis_unavailable`，不自动查 MySQL。
- [ ] Redis 未初始化时返回 `redis_not_initialized`。
- [ ] 录分提交先更新 Redis，再异步写回 MySQL。
- [ ] 写回失败保留 dirty 标记。
- [ ] 进程内 snapshot 后台线程不再轮询 MySQL。
- [ ] 第一阶段没有加入数据库索引、SQL 重写或批量插入优化。
- [ ] 没有删除旧模板和旧路由。
- [ ] 没有使用 `git add .`。

## 执行建议

推荐使用 Subagent-Driven 实施：

- Task 1 到 Task 4 可以按后端模块独立执行。
- Task 5 到 Task 7 需要主代理做集成 review，避免多个 worker 同时修改 `admin_workflow.py` 或 `run.py`。
- Task 8 是独立前端小任务。
- Task 9 由主代理执行验证并写记录。
