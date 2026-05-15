# Redis 运行态缓存统一设计

## 目标

本设计用于解决 GuanDan V2.0 当前前后端在后台管理、生成对阵、录分改分和大屏刷新时出现的卡顿问题。核心方向是把 Redis 升级为运行期事实源，统一承接现场高频读写；MySQL 退回为持久化落盘层和冷启动恢复来源。

第一阶段只处理 Redis 运行态统一，先观察时延效果。数据库索引、SQL 重写、`executemany()` 批量插入等数据库侧优化不纳入本阶段。

## 当前背景

当前项目已经存在多套缓存/读取路径：

- `api/dashboard_cache.py` 使用进程内 `_dashboard_snapshot` 和后台线程每 5 秒刷新大屏快照。
- `services/redis_cache_service.py` 只缓存某轮对阵信息。
- `services/score_writeback_service.py` 使用 Redis 队列异步写回比分。
- `/api/admin/overview`、`/api/admin/matches`、旧 Flask 页面和部分录分校验仍直接查询 MySQL。

这些路径职责不统一，导致现场请求可能同时触发 Redis 探测、进程内快照刷新、MySQL 聚合查询和后台动作后的重复刷新。Redis 不可用时当前代码还会返回 `None` 并尝试走降级逻辑，容易隐藏真实故障，也会带来反复连接和 `ping()` 的固定延迟。

## 选定方案

采用“Redis 运行态事实源 + 10 秒批量写回 MySQL”方案。

运行期接口优先读写 Redis：

- 前端大屏读 Redis 读模型。
- Vue 后台概览和对阵列表读 Redis 读模型。
- 录分加载桌号从 Redis 对阵事实数据读取。
- 录分提交先原子更新 Redis 中的比分事实数据，再重建相关读模型。
- 写回 worker 每 10 秒把 Redis 中的脏数据批量写回 MySQL。

Redis 是现场运行强依赖。Redis 不可用时，后台和录分接口返回明确错误，不自动降级为 MySQL 直读直写。Redis 不可用需要优先修复，而不是通过降级忽视问题。

## 非目标

本阶段不做以下事项：

- 不优化 MySQL 索引。
- 不重写旧 `/create_table` 的 `OR JOIN` SQL。
- 不优化 `replace_fight_info()` 的逐条插入。
- 不调整数据库表结构。
- 不新增登录、权限或二维码动态生成。
- 不删除旧 Flask 模板路由。
- 不把系统改造成完整事件溯源架构。

## 总体架构

系统运行态分为三层：

1. Redis 运行态事实源
   保存比赛状态、报名队伍、队伍等级、三轮得分、三轮对阵、读模型和脏数据标记。现场请求以 Redis 数据为准。

2. MySQL 持久化层
   用于报名导入后的持久化、Redis 冷启动恢复和 10 秒批量落盘。MySQL 不再服务高频展示和录分读取。

3. Flask API 层
   `/api/admin/*`、`/api/score/*` 和 `/dashboard_snapshot` 通过新的 Redis 运行态服务读写数据。旧 Flask 页面第一阶段继续保留，但读取路径也应改为 Redis 读模型，避免绕过新架构。

## Redis Key 设计

Redis 数据分为事实数据、读模型和写回状态三类。

### 事实数据

`gd:state`

Hash，保存比赛运行状态：

```text
current_turn
timer_started_at
timer_total_seconds
schema_version
last_loaded_at
last_flush_at
flush_status
flush_error
```

`gd:teams`

JSON 字符串，保存 `team_info` 的报名原始信息快照。

`gd:team_levels`

JSON 字符串，保存 `team_level` 的队伍等级快照。

`gd:mini_teams:turn:{turn}`

JSON 字符串，保存某轮 `mini_team_info` 得分事实数据。录分提交时更新这一份数据中对应双方队伍的 `big_score` 和 `small_score`。

`gd:fights:turn:{turn}`

JSON 字符串，保存某轮 `fight_info` 对阵事实数据。

第一阶段采用 JSON 快照格式，而不是拆成大量 Redis hash/index。当前项目数据量可控，JSON 更容易兼容现有 tuple/list/dict 结构，也能更快统一缓存边界。后续如果数据量扩大，再把热点结构拆细。

### 读模型

`gd:view:dashboard:{turn}`

大屏聚合视图，替代进程内 `_dashboard_snapshot`。内容覆盖当前 `/dashboard_snapshot` 返回所需字段：

- `TURN`
- `time_message`
- `matchesinfo`
- `scoresinfo`
- `sumteaminfo`
- `officescore`
- `snapshot_updated_at`

`gd:view:admin:overview`

Vue 后台概览视图，覆盖 `/api/admin/overview` 所需数据：

- 当前轮次
- 倒计时文案
- 队伍列表
- 是否已有对阵
- Redis 初始化状态
- MySQL 写回状态

`gd:view:admin:matches`

Vue 后台对阵列表视图，覆盖 `/api/admin/matches` 所需数据。该视图基于 Redis 中的对阵事实数据和得分事实数据构建，不再通过 `fight_info LEFT JOIN mini_team_info` 查询 MySQL。

`gd:view:create_table`

旧 Flask `/create_table` 页面使用的队伍与桌号展示视图。第一阶段保留旧页面，但其数据来源改为 Redis，避免旧页面继续触发慢 SQL。

### 写回状态

`gd:dirty:score_updates`

Set，保存待写回比分的标识。成员格式：

```text
{turn}:{team_name}
```

同一队伍 10 秒内多次改分时，集合只保留一个标识。写回时从 Redis 当前事实数据读取最新值，因此 MySQL 只落最终值。

`gd:dirty:matches`

String 或 Set，用于标记对阵事实数据已变更，需要写回 MySQL。

`gd:dirty:teams`

String 或 Set，用于标记报名/队伍相关事实数据已变更，需要写回 MySQL。

`gd:flush:lock`

写回 worker 的分布式锁，防止多进程或 Flask debug reload 场景下重复写库。

## 数据流设计

### Redis 初始化

启动后需要保证 Redis 中存在运行态数据。初始化来源有两类：

1. 报名导入后初始化
   报名导入是低频动作，仍先按现有流程解析 Excel，并写入 MySQL。成功后调用 Redis 初始化服务，从 MySQL 加载 `team_info`、`team_level`、`mini_team_info` 和 `fight_info` 到 Redis，重建所有读模型。

2. 服务重启后的冷启动恢复
   如果 Redis 可用但没有 `gd:state` 或 `schema_version` 不匹配，后台接口返回 `redis_not_initialized`。管理员可以通过初始化动作从 MySQL 加载运行态数据。第一阶段可以在后端启动时尝试加载一次，但接口仍要能明确区分 Redis 不可用和 Redis 未初始化。

### 设置轮次与倒计时

设置轮次只更新 `gd:state.current_turn`，随后重建：

- `gd:view:admin:overview`
- 当前轮 `gd:view:dashboard:{turn}`

倒计时开始时写入 `timer_started_at` 和 `timer_total_seconds`。倒计时文案可以在接口返回时根据 Redis state 实时计算，也可以在读模型重建时写入。第一阶段建议接口返回时实时计算，避免为了倒计时每秒重建读模型。

### 生成对阵

生成对阵仍使用现有对阵算法。算法需要的基础数据从 Redis 或 MySQL 读取都可以，但本阶段推荐从 Redis 的 `gd:mini_teams:turn:1` 和 `gd:team_levels` 读取，减少运行期查库。

算法完成后：

1. 写入 `gd:fights:turn:1`、`gd:fights:turn:2`、`gd:fights:turn:3`。
2. 标记 `gd:dirty:matches`。
3. 重建 `gd:view:admin:matches`、各轮 `gd:view:dashboard:{turn}` 和 `gd:view:create_table`。
4. 返回成功。

MySQL 中的 `fight_info` 由 10 秒写回 worker 持久化。本阶段不优化原有 `replace_fight_info()` 的 SQL 实现。

### 录分加载

扫码录分和后台改分都从 Redis 读取对阵：

```text
/api/score/table GET
/api/admin/score-match GET
```

读取流程：

1. 校验 Redis 可用。
2. 读取当前轮次或请求中的显式轮次。
3. 从 `gd:fights:turn:{turn}` 查找桌号。
4. 找不到返回 `match_not_found`。
5. 找到则返回双方队伍和成员。

该流程不再调用 `check_match_exists()` 查 MySQL。

### 录分提交

录分提交是本阶段最核心的高并发写路径：

1. 校验 Redis 可用和 Redis 已初始化。
2. 从 `gd:fights:turn:{turn}` 读取该桌双方队伍。
3. 使用现有 `build_score_update()` 计算大小分。
4. 原子更新 `gd:mini_teams:turn:{turn}` 中双方队伍得分。
5. 标记 `gd:dirty:score_updates` 中双方队伍。
6. 重建当前轮 `gd:view:dashboard:{turn}`、`gd:view:admin:matches` 和 `gd:view:admin:overview`。
7. 记录比分日志。
8. 返回成功。

原子性可以通过 Redis pipeline 或 Lua 脚本实现。第一阶段优先选择 pipeline；如果测试发现并发覆盖风险，再把“读取 JSON、修改、写回、标记 dirty”收敛到 Lua 或使用 Redis 锁保护单轮比分数据。

### 大屏读取

`/dashboard_snapshot` 路由保留，内部改为读取 Redis：

1. 校验 Redis 可用。
2. 读取 `gd:state.current_turn`。
3. 当前轮次无效时返回空结构。
4. 当前轮次有效时读取 `gd:view:dashboard:{turn}`。
5. 返回时补充实时倒计时文案。

`api/dashboard_cache.py` 中的后台刷新线程、`_dashboard_snapshot` 和 `ensure_dashboard_snapshot_fresh()` 不再作为运行时数据来源。第一阶段可保留兼容函数名，但内部转调 Redis 读模型，降低一次性迁移风险。

### MySQL 写回

新增写回 worker，每 10 秒执行一次：

1. 获取 `gd:flush:lock`。
2. 读取 `gd:dirty:score_updates`、`gd:dirty:matches`、`gd:dirty:teams`。
3. 从 Redis 事实数据读取最新数据。
4. 批量写回 MySQL。
5. 成功后清理已写回 dirty 标记。
6. 更新 `gd:state.last_flush_at`、`flush_status=ok`、`flush_error=""`。
7. 失败时保留 dirty 标记，更新 `flush_status=failed` 和 `flush_error`，下一轮继续尝试。

MySQL 写回失败不影响 Redis 实时展示，但后台概览必须能看到写回失败状态。

## 后端模块设计

### `services/redis_runtime.py`

统一 Redis 强依赖入口。

职责：

- 创建 Redis client。
- 提供 `require_redis()`。
- Redis 不可用时抛出统一异常。
- 不返回 `None`，避免调用方静默降级。

### `services/runtime_store.py`

Redis 事实数据仓库。

职责：

- 读写 `gd:state`。
- 读写队伍、等级、三轮得分和三轮对阵事实数据。
- 提供 `load_from_mysql()` 冷启动/初始化方法。
- 提供 `get_match()`、`submit_score()`、`mark_score_dirty()` 等语义化方法。

### `services/runtime_views.py`

Redis 读模型构建模块。

职责：

- 从事实数据构建 dashboard、admin overview、admin matches 和 create table 视图。
- 提供重建单个视图和重建全部视图的方法。
- 保持现有前端响应字段兼容，避免前端大面积改动。

### `services/runtime_flush_service.py`

MySQL 写回 worker。

职责：

- 每 10 秒扫描 dirty 标记。
- 合并同一队伍多次修改。
- 写回 MySQL。
- 维护写回状态。
- 失败时保留 dirty 标记并暴露错误。

### `services/perf_logger.py`

轻量性能日志模块。

职责：

- 在 `PERF_LOG_ENABLED=1` 时记录接口和关键 Redis 操作耗时。
- 默认不影响业务逻辑。
- 用于比较 Redis 统一前后的时延效果。

## API 调整

### 管理后台接口

`GET /api/admin/overview`

改为读取 `gd:view:admin:overview`。返回中增加 Redis/写回状态字段：

```text
runtime_status
flush_status
last_flush_at
flush_error
```

`GET /api/admin/matches`

改为读取 `gd:view:admin:matches`。

`POST /api/admin/matches/generate`

生成对阵后先写 Redis，标记 dirty，重建读模型。MySQL 写回交给 worker。

`GET /api/admin/score-match`

改为从 `gd:fights:turn:{turn}` 读取。

`POST /api/admin/scores`

改为先写 Redis 并标记 dirty，不再进入旧 Redis 队列或直接写 MySQL。

### 录分接口

`GET /api/score/current-turn`

从 `gd:state.current_turn` 读取。

`GET /api/score/table`

从 Redis 当前轮对阵中读取桌号。

`POST /api/score/table`

先写 Redis，重建读模型，标记 dirty，返回成功。

### 大屏接口

`GET /dashboard_snapshot`

从 `gd:view:dashboard:{turn}` 读取。该接口保持原响应结构，避免前端大屏改动过多。

旧的 `/matchesinfo`、`/scoresinfo`、`/sumteaminfo` 和 `/officescore` 可以继续保留，但内部也从 Redis 读模型拆分返回。

## 错误处理

统一错误码：

- `redis_unavailable`：Redis 不可用，现场运行故障，需要检查 Redis 服务。
- `redis_not_initialized`：Redis 可用但没有运行态数据，需要从 MySQL 初始化。
- `flush_failed`：MySQL 写回失败，Redis 实时数据仍可用，但需要处理落盘故障。
- `invalid_turn`：轮次非法或未设置。
- `match_not_found`：指定轮次/桌号不存在。
- `score_invalid`：比分非法。
- `winner_required_when_tied`：同等级结算缺少最后一局赢家。

Redis 不可用时不自动查 MySQL。接口应快速返回错误，避免 Redis 重试和 MySQL 降级叠加造成新的卡顿。

## 性能日志与验收

新增 `PERF_LOG_ENABLED=1` 控制轻量耗时日志。

建议记录接口：

- `/api/admin/overview`
- `/api/admin/matches`
- `/api/admin/matches/generate`
- `/api/admin/score-match`
- `/api/admin/scores`
- `/api/score/table GET`
- `/api/score/table POST`
- `/dashboard_snapshot`

日志字段：

```text
接口名
总耗时 ms
Redis 耗时 ms
是否命中 Redis
是否触发读模型重建
dirty 数量
flush_status
异常摘要
```

验收标准：

- 打开 `/admin` 时，概览和对阵列表不再并发查询 MySQL。
- 提交比分后，大屏和后台列表立即读取 Redis 最新分数，不等待 MySQL。
- 10 秒内连续修改同一队伍比分，MySQL 只落最终值。
- Redis 停止时接口快速返回 `redis_unavailable`。
- `/dashboard_snapshot` 不再由后台线程每 5 秒无条件查库刷新。
- 后台概览能显示 MySQL 写回状态。

## 测试策略

第一阶段测试重点是防止架构回退。

后端单元测试应覆盖：

- Redis 不可用时，后台和录分接口返回 `redis_unavailable`，不调用 MySQL 查询兜底。
- Redis 未初始化时返回 `redis_not_initialized`。
- 录分成功后，Redis 中比分事实数据立即变化。
- 录分成功后，dashboard 和 admin matches 读模型立即变化。
- 写回 worker 合并同一队伍多次修改，只写最新值。
- 写回失败时 dirty 标记保留，下一轮可以重试。
- `/dashboard_snapshot` 从 Redis 读模型返回，不触发原进程内 snapshot 刷新。

前端验证应覆盖：

- `/admin` 能正常加载 Redis 读模型。
- 后台改分成功后返回 `/admin` 能看到最新分数。
- `/score` 和 `/score/:turn/:table` 能完成录分。
- Redis 不可用时页面展示明确错误，不长时间卡住。

## 分阶段实施建议

### 阶段一：运行态 Redis 基础

- 新增 Redis 强依赖入口。
- 新增运行态事实数据仓库。
- 支持从 MySQL 初始化 Redis。
- 增加 Redis 未初始化和 Redis 不可用错误。

### 阶段二：读模型替换 snapshot

- 新增 dashboard/admin/create_table 读模型构建。
- `/dashboard_snapshot` 改读 Redis。
- `/api/admin/overview` 和 `/api/admin/matches` 改读 Redis。
- 停用进程内 snapshot 后台刷新线程。

### 阶段三：录分写 Redis 与 10 秒写回

- 录分加载和提交改为 Redis 事实数据。
- 标记 dirty score。
- 新增 10 秒写回 worker。
- 后台概览展示写回状态。

### 阶段四：旧页面接入 Redis 读模型

- `/create_table` 改读 `gd:view:create_table`。
- `/generate_matches` GET 改读 Redis 对阵视图。
- `/input_scores` GET/POST 复用 Redis 录分链路。
- 旧模板继续保留作为入口，不删除文件。

## 风险与控制

### Redis JSON 快照并发覆盖

风险：多个录分请求同时修改同一轮 JSON，可能出现后写覆盖先写。

控制：第一版使用 Redis pipeline 和按轮次锁保护写入；如果现场并发验证发现风险，再将比分更新改为 Lua 脚本或把 `mini_teams` 拆成 Redis hash。

### Redis 与 MySQL 短时间不一致

风险：10 秒写回窗口内，MySQL 不是最新状态。

控制：这是设计预期。现场展示和后台操作以 Redis 为准，MySQL 只做持久化。后台显示 `last_flush_at` 和 `flush_status`。

### 写回失败

风险：MySQL 落盘失败会导致 Redis 正常、MySQL 滞后。

控制：保留 dirty 标记，持续重试；后台概览显示失败状态和错误摘要，现场人员优先处理数据库写回问题。

### 旧页面绕过 Redis

风险：旧 Flask 页面仍查 MySQL 会让卡顿链路残留。

控制：第一阶段保留旧页面入口，但数据来源改为 Redis 读模型。后续确认 Vue 页面稳定后，再讨论是否下线旧模板。

## 实施边界确认

本设计第一版只解决 Redis 运行态统一和时延观测。数据库层优化延后处理。完成后先通过性能日志和现场操作观察 `/admin`、录分提交、大屏刷新和旧页面访问的时延变化，再决定是否进入数据库索引与 SQL 优化阶段。
