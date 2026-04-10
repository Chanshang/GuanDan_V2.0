# 掼蛋后端前端接口规范（基于当前 `run.py`）

## 1. 文档目标

本文档用于指导前端开发与现有后端联调，并为后续前后端分离提供统一接口规范。  
范围基于当前代码：
- `run.py`
- `services/*.py`

说明：
- 当前系统是 Flask 模板页 + 部分 JSON 接口混合模式。
- 很多操作接口返回 `redirect + flash`，不是纯 JSON。
- 前端若要单页化，建议按本文“第 4 节：分离版 v1 规范”实现。

---

## 2. 全局约定（现状）

### 2.1 基础信息
- Base URL：`http://<host>:5000`
- 鉴权：当前无登录态校验（默认开放）
- CORS：已全局开启（`CORS(app, supports_credentials=True)`）

### 2.2 当前有效轮次
- 全局变量 `TURN` 允许值：`"1" | "2" | "3" | "null"`
- 大部分统计接口要求 `TURN` 为 `1~3`，否则返回：

```json
{"error": "invalid turn"}
```

### 2.3 录分约束
- 桌号范围：`1~22`
- 牌级输入（`score_x`, `score_y`）：`2~32` 的整数
- 若双方小分相等，`winner` 必填（用于判定大分归属）

---

## 3. 当前后端接口（可直接联调）

## 3.1 展示与状态接口（JSON）

### 3.1.1 获取当前轮次
- Method：`GET`
- Path：`/TURNsinfo`
- Response:

```json
{"TURN": "1"}
```

### 3.1.2 获取倒计时
- Method：`GET`
- Path：`/timesinfo`
- Response（未开始）：

```json
{"time_message": "倒计时未开始"}
```

- Response（进行中）：

```json
{"time_message": "58:13"}
```

### 3.1.3 获取当前轮次对阵
- Method：`GET`
- Path：`/matchesinfo`
- Response（成功）：

```json
{
  "matchesinfo": [
    [1, "A队", "张三,李四", "B队", "王五,赵六", 1, 2, 3]
  ]
}
```

字段顺序来自 `fight_info`（当前实现 `SELECT *`）。

### 3.1.4 获取当前轮次小分
- Method：`GET`
- Path：`/scoresinfo`
- Response：

```json
{
  "scoresinfo": [
    ["A队", "张三", 5],
    ["A队", "李四", 5]
  ]
}
```

### 3.1.5 获取队伍维度排名（当前轮 + 累计）
- Method：`GET`
- Path：`/sumteaminfo`
- Response：

```json
{
  "current_turn": [
    [1, "A队", 3, 20]
  ],
  "total_until_turn": [
    [1, "A队", 6, 35]
  ]
}
```

字段说明：
- `rank_id`
- `team_name`
- `total_big_score`
- `total_small_score`

备注：计时开始后，当前实现会对返回做轮播切片（每 5 秒切一段，每段最多 6 条）。

### 3.1.6 获取办公室维度排名（当前轮 + 累计）
- Method：`GET`
- Path：`/officescore`
- Response：

```json
{
  "current_turn": [
    [1, "技术部", 12, 85]
  ],
  "total_until_turn": [
    [1, "技术部", 20, 140]
  ]
}
```

字段说明：
- `rank_id`
- `office`
- `total_big_score`
- `total_small_score`

---

## 3.2 页面路由与操作接口（模板 + 重定向）

这部分接口是服务端渲染模式，前端分离时建议改造为 JSON API。

### 3.2.1 首页与导入
- `GET /`：渲染 `index.html`，展示 `team_info` 数据
- `POST /`：上传 `.xlsx` 并导入
  - FormData：`file`
  - 成功：重定向回 `/`
  - 失败：重定向回 `/`（通过 flash 显示错误）

### 3.2.2 清空业务表
- `POST /clear_tables`
- 成功/失败：重定向 `/`（flash 提示）

### 3.2.3 设置轮次
- `POST /set_turn`
- form 字段：`turn`（`null|1|2|3`）
- 返回：重定向 `/create_table`

### 3.2.4 创建展示页
- `GET /create_table`
- 渲染 `create_table.html`
- 模板参数：
  - `mini_team_info`
  - `current_turn`

### 3.2.5 生成对阵
- `GET /generate_matches`：渲染 `generate_matches.html`（含当前对阵）
- `POST /generate_matches`：执行对阵生成并覆盖 `fight_info`，完成后重定向回本页

### 3.2.6 录分入口（按当前轮）
- `GET /select_table`：渲染输入桌号页面
- `POST /select_table`
  - form：`table_num`
  - 校验：当前轮次有效 + 桌号范围 1~22
  - 成功：重定向  
    `/input_scores/<table_num>/<turn_num>/0`

### 3.2.7 修改比分入口（按轮次+桌号）
- `GET /modify_select_table`：渲染页面
- `POST /modify_select_table`
  - form：`table_num`, `turn_num`
  - 校验：轮次合法 + 对局存在
  - 成功：重定向  
    `/input_scores/<table_num>/<turn_num>/1`

### 3.2.8 录分与写分
- `GET /input_scores/<int:table_num>/<int:turn_num>/<int:modify_type>`
  - 渲染 `input_scores.html`
  - 展示该桌双方队伍与成员
- `POST /input_scores/<int:table_num>/<int:turn_num>/<int:modify_type>`
  - form：`score_x`, `score_y`, `winner`
  - 内部逻辑：
    - 调用 `build_score_update` 解析大小分
    - 调用 `apply_score_update` 落库
    - 调用 `save_score_log` 写日志
  - 成功跳转：
    - `modify_type=1` -> `/modify_select_table`
    - `modify_type=0` -> `/select_table`

---

## 4. 前后端分离建议规范（v1，推荐前端按此开发）

为避免前端处理重定向与 flash，建议新增 `/api/v1/*` JSON 接口。  
以下是建议规范（可逐步兼容现有逻辑）。

### 4.1 统一返回格式

成功：

```json
{
  "ok": true,
  "data": {},
  "message": "ok"
}
```

失败：

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_TURN",
    "message": "轮次不合法"
  }
}
```

### 4.2 建议接口清单

1. 比赛状态
- `GET /api/v1/state/turn`
- `PUT /api/v1/state/turn`
- `GET /api/v1/state/timer`
- `POST /api/v1/state/timer/start`
- `POST /api/v1/state/timer/stop`

2. 排名与展示
- `GET /api/v1/stats/matches?turn=1`
- `GET /api/v1/stats/scores?turn=1`
- `GET /api/v1/stats/team-rankings?turn=1`
- `GET /api/v1/stats/office-rankings?turn=1`

3. 对阵管理
- `POST /api/v1/matches/generate`
- `GET /api/v1/matches?turn=1`
- `GET /api/v1/matches/{turn}/{table_num}`

4. 录分管理
- `POST /api/v1/scores`
- `PUT /api/v1/scores`（用于后台改分）

5. 数据管理
- `POST /api/v1/import/excel`
- `POST /api/v1/admin/clear-tables`

### 4.3 关键请求示例

设置轮次：

```http
PUT /api/v1/state/turn
Content-Type: application/json

{"turn": 2}
```

提交比分：

```http
POST /api/v1/scores
Content-Type: application/json

{
  "turn_num": 2,
  "table_num": 5,
  "score_x": 10,
  "score_y": 8,
  "winner": "x",
  "modify_type": 0
}
```

响应：

```json
{
  "ok": true,
  "data": {
    "turn_num": 2,
    "table_num": 5
  },
  "message": "score updated"
}
```

---

## 5. 前端联调建议流程

1. 页面初始化先请求：
- `/TURNsinfo`
- `/timesinfo`
- `/sumteaminfo`
- `/officescore`

2. 若是大屏轮播展示页，可每 3~5 秒轮询：
- `/matchesinfo`
- `/scoresinfo`
- `/sumteaminfo`
- `/officescore`

3. 后台管理流程：
- 先 `POST /set_turn`
- 再 `POST /generate_matches`
- 录分时调用 `/input_scores/...`（当前模式）  
-  分离后改为 `/api/v1/scores`

---

## 6. 已知兼容性注意点

1. 当前很多接口返回的是“数组元组结构”，不是具名 JSON 字段，前端需要按位置解构。  
建议分离改造后改为对象结构（如 `{"team_name":"A队"}`）。

2. 当前导入、清空、生成对阵、录分等接口主要依赖 `flash + redirect`，不适合纯前端直接消费。  
建议新增 JSON 接口并保留旧页面路由一段时间。

3. `TURN` 和计时器在当前实现是进程内全局变量。  
多实例部署时会出现状态不一致，建议后续迁移到 Redis/DB。

