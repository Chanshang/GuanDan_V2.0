# 2026-05-15 卡顿优化交接文档

## 当前状态

本轮仅做性能问题梳理与交接记录，未修改业务代码。

用户反馈的卡顿场景：

- Vue 管理页 `http://localhost:5001/admin` 中点击“生成/覆盖对阵”时卡顿。
- Vue 管理页进入“后台改分”或提交改分时卡顿。
- 旧 Flask 后台 `http://127.0.0.1:5000/` 及相关查询分数页面也有卡顿。

本轮已初步排查 snapshot、Redis、数据库查询和前端请求链路，结论是：卡顿大概率不是单一问题，而是 Redis 不可用时反复连接、snapshot 周期刷新、后台动作后的重复查询、旧查询 SQL 和逐条写入共同叠加。

## 需要继续遵守的项目规则

- 仓库根目录：`E:\Pycharm-pro\my_project\GuanDan\GuanDan_V2.0`
- 禁止批量删除文件或目录。
- 不要使用 `git add .`，只暂存当前任务相关文件。
- 后端测试使用 Conda 环境：

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
python -m unittest discover -s tests -p "test_*.py" -v
```

或：

```powershell
conda run -n flask_app_env python -m unittest tests.test_admin_workflow -v
conda run -n flask_app_env python -m unittest tests.test_admin_score_api -v
```

前端构建：

```powershell
cd GuanDanFront-V2.0
npm run build
```

## 相关文件地图

### Snapshot 聚合快照

- `GuanDan_backend-V2.0/api/dashboard_cache.py`
  - `SNAPSHOT_REFRESH_SECONDS = 5`
  - `SNAPSHOT_STALE_SECONDS = 8`
  - `_dashboard_snapshot`
  - `mark_snapshot_stale()`
  - `refresh_dashboard_snapshot_once()`
  - `ensure_dashboard_snapshot_fresh()`
  - `background_snapshot_worker()`
  - `ensure_snapshot_worker_started()`

- `GuanDan_backend-V2.0/api/frontend_api.py`
  - `/matchesinfo`
  - `/scoresinfo`
  - `/sumteaminfo`
  - `/officescore`
  - `/dashboard_snapshot`

Snapshot 逻辑：

1. 后端启动时 `run.py` 调用 `ensure_snapshot_worker_started()`。
2. 后台线程每 5 秒执行一次 `refresh_dashboard_snapshot_once()`。
3. 每次刷新会根据当前轮次查询：
   - `fetch_matches_by_turn`
   - `fetch_scores_by_turn`
   - `fetch_team_rankings`
   - `fetch_office_rankings`
4. 业务数据变化后调用 `mark_snapshot_stale()`，将 `updated_at` 置为 `0.0`。
5. 大屏相关接口请求时会调用 `ensure_dashboard_snapshot_fresh()`，如果快照过期，则在请求线程里同步刷新。

潜在问题：

- Snapshot 只服务大屏接口，不直接服务 `/admin` 后台列表。
- 快照过期时，请求线程会同步刷新，可能造成一次请求明显变慢。
- 后台线程每 5 秒无条件刷新，即使当前无人打开大屏也会查数据库。
- `ensure_dashboard_snapshot_fresh()` 没有刷新中的互斥标记，多请求同时过期时可能重复刷新。

### Redis 对阵缓存

- `GuanDan_backend-V2.0/services/redis_cache_service.py`
  - `get_redis_client()`
  - `read_fight_info_from_redis()`
  - `write_fight_info_to_redis()`
  - `clear_all_fight_cache_in_redis()`

- `GuanDan_backend-V2.0/run.py`
  - `_fight_cache`
  - `clear_fight_cache()`
  - `load_fight_info(turn_num)`

Redis 对阵缓存逻辑：

1. 录分页查某轮对阵时调用 `load_fight_info(turn_num)`。
2. 读取顺序为：本地 `_fight_cache` -> Redis -> MySQL。
3. MySQL 回源后会写回本地缓存和 Redis。
4. 导入、清空、生成对阵后会调用 `clear_fight_cache()`，清理本地缓存和 Redis 对阵缓存。

潜在问题：

- 如果 Redis 未启动或不可达，`get_redis_client()` 每次都会尝试 `_build_redis_client()` 和 `ping()`。
- 默认 `REDIS_TIMEOUT_SECONDS=0.5`，一次 Redis 探测可能最多等 0.5 秒。
- 多个路径会触发 Redis 探测，包括清缓存、读对阵、判断比分写回队列是否可用。
- 当前没有“Redis 已失败，短时间内不要重试”的熔断状态。

### Redis 比分写回队列

- `GuanDan_backend-V2.0/services/score_writeback_service.py`
  - `SCORE_WRITEBACK_ENABLED`
  - `is_writeback_enabled()`
  - `enqueue_score_update()`
  - `_writeback_worker()`
  - `ensure_writeback_worker_started()`

- `GuanDan_backend-V2.0/services/score_service.py`
  - `apply_score_update()`
  - `apply_score_updates_batch()`

比分写回逻辑：

1. `SCORE_WRITEBACK_ENABLED=1` 且 Redis 可用时，提交比分会进入 Redis 队列。
2. 后台线程从队列中批量读取，压缩同一批次内的重复更新。
3. 批量调用 `apply_score_updates_batch()` 写入 MySQL。
4. 如果 Redis 不可用，则会降级到直接调用 `apply_score_update()` 写 MySQL。

潜在问题：

- 如果 Redis 实际不可用，`is_writeback_enabled()` 会反复触发 `get_redis_client()`。
- 队列写回是异步的，管理页改分后立即刷新对阵列表时，可能读到旧分数或等待其它查询。
- 写回线程异常被吞掉，只 `sleep(0.3)`，没有明确日志，现场排查困难。

### 管理页与后台接口

- `GuanDanFront-V2.0/src/views/AdminView.vue`
  - `refreshAll()`
  - `runAction()`
  - `loadOverview()`
  - `loadMatches()`

- `GuanDan_backend-V2.0/api/admin_api.py`
  - `/api/admin/overview`
  - `/api/admin/matches`
  - `/api/admin/matches/generate`
  - `/api/admin/score-match`
  - `/api/admin/scores`

- `GuanDan_backend-V2.0/services/admin_workflow.py`
  - `get_overview()`
  - `generate_matches_workflow()`
  - `get_all_matches()`
  - `get_match_for_score()`
  - `submit_score()`

Vue 管理页动作逻辑：

1. 管理页打开时 `onMounted(refreshAll)`。
2. `refreshAll()` 并发请求：
   - `/api/admin/overview`
   - `/api/admin/matches`
3. 点击生成对阵后，先请求 `/api/admin/matches/generate`。
4. 生成成功后 `runAction()` 会再次调用 `refreshAll()`。
5. 后台改分成功后也会返回管理页或触发页面查询。

潜在问题：

- 一次操作后会立即发起多个查询，请求链路叠加。
- `/api/admin/overview` 当前会查队伍列表和 `fetch_all_fights()`，只是为了得到 `has_matches`。
- `/api/admin/matches` 当前为了展示比分，查询 `fight_info` 并两次 `LEFT JOIN mini_team_info`。
- 如果 `mini_team_info(team_name, turn)` 和 `fight_info(turn, id)` 没有索引，对阵列表会慢。

### 旧 Flask 查询分数页面

- `GuanDan_backend-V2.0/run.py`
  - `/`
  - `/create_table`
  - `/generate_matches`
  - `/input_scores/<table_num>/<turn_num>/<modify_type>`

- `GuanDan_backend-V2.0/services/stats_service.py`
  - `fetch_create_table_rows()`

旧后台查询逻辑：

- `/` 调用 `fetch_team_info_rows()`，直接查数据库，不走 snapshot/Redis。
- `/create_table` 调用 `fetch_create_table_rows()`，直接查 `mini_team_info LEFT JOIN fight_info`。
- `/generate_matches` 的 GET 调用 `fetch_all_fights()`。
- `/input_scores` 调用 `load_fight_info()`，这里会用本地缓存/Redis/MySQL。

高风险 SQL：

```sql
SELECT
    m.*,
    f.id AS fight_id
FROM mini_team_info m
LEFT JOIN fight_info f
  ON (f.members_1 = m.member_name OR f.members_2 = m.member_name)
 AND f.turn = m.turn
ORDER BY m.turn ASC, f.id ASC
```

问题点：

- `OR` 条件通常不利于索引。
- 用成员名做 join 可能比用队伍名更不稳定。
- 如果数据量增大，这条查询会成为旧后台分数页卡顿的重点嫌疑。

## 当前优先怀疑点

1. **Redis 不可用时反复连接/`ping()`**
   - 高概率造成固定 0.5 秒级延迟。
   - 影响录分、改分、生成对阵后的清缓存、写回队列判断。

2. **旧后台 `/create_table` 的 `OR JOIN` 查询**
   - 直接影响 `http://127.0.0.1:5000/` 后端旧页面相关查询体验。

3. **管理页操作后的重复刷新**
   - `runAction()` 成功后立即 `refreshAll()`，同时查概览和对阵列表。
   - 概览和列表存在重复读取。

4. **对阵列表比分查询需要索引支撑**
   - `fetch_all_fights_with_scores()` 依赖 `fight_info` 与 `mini_team_info` join。
   - 建议检查或增加索引：`mini_team_info(team_name, turn)`、`fight_info(turn, id)`。

5. **生成对阵写入是逐条 INSERT**
   - `replace_fight_info()` 先 `DELETE FROM fight_info`，再循环逐条插入。
   - 队伍多时建议改成 `executemany()`。

6. **Snapshot 可能给数据库增加背景压力**
   - 每 5 秒无条件刷新。
   - 过期后请求线程同步刷新。
   - 缺少“刷新中”保护和耗时日志。

## 下一步建议

### 第一步：先加耗时诊断日志，不急着优化

建议新增一个轻量性能计时 helper，例如：

- `services/perf_logger.py`
- 或先局部加 `time.perf_counter()` 日志。

需要打点的位置：

- `redis_cache_service.get_redis_client()`
- `redis_cache_service.clear_all_fight_cache_in_redis()`
- `dashboard_cache.refresh_dashboard_snapshot_once()`
- `admin_workflow.generate_matches_workflow()`
- `admin_workflow.submit_score()`
- `match_service.fetch_all_fights_with_scores()`
- `stats_service.fetch_create_table_rows()`
- `match_service.replace_fight_info()`

日志内容至少包括：

- 函数名
- 总耗时毫秒
- Redis 是否可用
- 数据行数
- 当前 turn
- 异常摘要

### 第二步：用一次真实操作复现

建议分别执行：

1. 打开 `/admin`
2. 点击“生成/覆盖对阵”
3. 进入后台改分
4. 提交一次分数
5. 打开旧后台 `/create_table`
6. 打开大屏 `/screen`

根据日志判断瓶颈在 Redis、SQL、算法、写入还是前端重复请求。

### 第三步：按证据选择优化方案

可能优化方向：

- Redis 熔断：连接失败后 10 到 30 秒内不重复 ping。
- Snapshot 刷新锁：避免多个请求同时同步刷新。
- Snapshot 懒刷新：无人访问大屏时不频繁查库。
- SQL 索引：`mini_team_info(team_name, turn)`、`mini_team_info(turn)`、`fight_info(turn, id)`。
- `/create_table` 查询重写，避免 `OR JOIN`。
- `replace_fight_info()` 改 `executemany()`。
- 管理页刷新瘦身：生成对阵后只刷新必要数据，概览的 `has_matches` 改成轻量 `EXISTS`。

## 下一会话可直接粘贴的提示词

```text
你正在接手 GuanDan V2.0 的卡顿性能排查与优化任务。

项目路径：
E:\Pycharm-pro\my_project\GuanDan\GuanDan_V2.0

当前分支：
codex/admin-score-migration

必须先阅读并遵守：
1. AGENTS.md
2. docs/superpowers/2026-05-15-performance-handoff.md
3. docs/superpowers/2026-05-14-admin-score-migration-usage.md

当前问题：
- Vue 管理页 http://localhost:5001/admin 点击生成对阵卡顿。
- Vue 管理页后台改分或提交改分卡顿。
- 旧 Flask 后台 http://127.0.0.1:5000/ 及旧查询分数页面也有卡顿。

本轮不要先猜测修复。请使用 Superpowers 的 systematic-debugging 流程，先完成根因调查。

请重点检查：
- GuanDan_backend-V2.0/api/dashboard_cache.py
- GuanDan_backend-V2.0/api/frontend_api.py
- GuanDan_backend-V2.0/services/redis_cache_service.py
- GuanDan_backend-V2.0/services/score_writeback_service.py
- GuanDan_backend-V2.0/services/admin_workflow.py
- GuanDan_backend-V2.0/services/match_service.py
- GuanDan_backend-V2.0/services/stats_service.py
- GuanDan_backend-V2.0/run.py
- GuanDanFront-V2.0/src/views/AdminView.vue

我的目标：
1. 先用最小代码改动加入性能耗时诊断日志，定位卡顿到底来自 Redis、MySQL 查询、对阵算法、逐条写入、snapshot 刷新，还是前端重复请求。
2. 用真实路径复现并记录证据。
3. 基于证据给出优化方案，然后再实施。

注意：
- 禁止批量删除文件或目录。
- 不要使用 git add .。
- 当前仓库已有未提交本地改动和生成物，避免误提交。
- 后端测试使用 conda 环境 flask_app_env。
- 如果需要提交，只暂存当前任务相关文件。
```

## 提交建议

如果下一会话先做诊断日志，建议提交拆成两步：

1. `chore: add performance diagnostics for admin flows`
2. `perf: optimize admin score and snapshot paths`

诊断日志确认无用后，再决定是否保留为可控 debug 开关，或移除临时日志。
