# 后台管理与录分页面迁移设计

## 目标

将当前基于 Flask 模板的后台管理页面和录分页面迁移到 Vue 前端，同时保持现有 Flask + Vue 架构不变，保留既有业务行为，并在第一阶段继续保留旧模板路由作为回滚兜底。

## 当前背景

项目当前由 Vue 3 + Vite 前端负责现场大屏展示，Flask 后端仍承担多个操作型 HTML 页面：

- `/`：上传报名 Excel，并展示队伍数据。
- `/create_table`：展示队伍得分/排名数据，并控制当前轮次和倒计时。
- `/generate_matches`：查看和重新生成对阵列表。
- `/modify_select_table`：管理员按轮次和桌号进入改分。
- `/select_table`：录分人员基于当前轮次查询桌号。
- `/input_scores/<table>/<turn>/<type>`：具体比分录入表单。

后端已经提供面向大屏展示的 JSON 接口，尤其是 `/dashboard_snapshot` 聚合快照接口，但后台管理动作仍然耦合在 `run.py` 中，依赖表单提交、页面重定向和 Flask `flash` 消息。

## 选定方案

采用分阶段迁移：

1. 为现有后台管理流程抽取可复用的后端 helper 函数。
2. 新增 `/api/admin/*` 和 `/api/score/*` JSON 接口。
3. 引入 Vue Router，并将当前大屏页面迁移到 `/screen`。
4. 新增 `/admin`、`/score`、`/score/:turn/:table` Vue 页面。
5. 第一版继续保留旧 Flask 模板路由，作为现场使用时的兜底方案。

这个方案风险适中。Vue 页面可以获得清晰的 API 契约；如果现场流程出现异常，旧页面仍可临时使用，便于回滚和对照。

## 路由设计

前端路由：

- `/`：重定向到 `/screen`，保持当前默认访问大屏的习惯。
- `/screen`：现有现场大屏展示。
- `/admin`：管理员后台控制台，用于报名导入、轮次/计时控制、对阵生成、队伍预览和后台改分。
- `/score`：扫码录分入口页。第一版不做登录和身份校验。
- `/score/:turn/:table`：某一轮某一桌的比分录入表单。

后端模板路由：

- 第一阶段保留现有模板路由。
- 只在必要时调整旧模板路由，让它们复用新抽取的 helper 函数。
- 本阶段不删除模板文件和旧路由。

## 后端 API 设计

新增 `GuanDan_backend-V2.0/api/admin_api.py`。

接口：

- `GET /api/admin/overview`
  - 返回后台首页所需聚合信息：当前轮次、倒计时文本、队伍列表、是否已有对阵、快照更新时间等。
- `POST /api/admin/import`
  - 接收一个 `.xlsx` 文件。
  - 复用 `import_registration_excel`。
  - 导入成功后清理对阵缓存、重置当前轮次，并标记大屏快照过期。
- `POST /api/admin/clear`
  - 复用 `clear_all_tables`。
  - 清理对阵缓存、重置当前轮次，并标记大屏快照过期。
- `POST /api/admin/turn`
  - 接收 `turn`，合法值为 `1`、`2`、`3` 或 `null`。
  - 更新当前轮次，并标记大屏快照过期。
- `POST /api/admin/timer/start`
  - 启动当前轮次倒计时。
- `POST /api/admin/timer/stop`
  - 暂停当前轮次倒计时。
- `GET /api/admin/matches`
  - 返回 `fight_info` 中的全部对阵行。
- `POST /api/admin/matches/generate`
  - 生成并覆盖三轮对阵。
  - 清理对阵缓存，并标记大屏快照过期。
- `GET /api/admin/score-match?turn=<turn>&table=<table>`
  - 校验指定轮次和桌号，并返回双方队伍与成员信息。
- `POST /api/admin/scores`
  - 按显式指定的轮次和桌号提交或修改比分。

新增 `GuanDan_backend-V2.0/api/score_api.py`。

接口：

- `GET /api/score/current-turn`
  - 返回当前轮次，供录分入口页展示。
- `GET /api/score/table?table=<table>`
  - 使用当前轮次和请求中的桌号，返回双方队伍与成员信息。
- `POST /api/score/table`
  - 使用当前轮次和请求中的桌号提交比分。

统一响应格式：

```json
{
  "ok": true,
  "message": "操作成功",
  "data": {}
}
```

失败响应格式：

```json
{
  "ok": false,
  "message": "当前轮次未设置",
  "error": "invalid_turn"
}
```

`message` 面向用户展示，可以使用中文；接口稳定性主要依赖 `ok` 布尔值和 `error` 错误码。

## 后端 Helper 设计

新增小型业务编排层，避免把逻辑复制到新 API 中：

- 导入流程 helper：
  - 校验文件是否存在、扩展名是否为 `.xlsx`、文件名是否安全。
  - 保存上传文件。
  - 执行导入服务。
  - 清理对阵缓存、重置当前轮次、标记快照过期。
- 对阵生成 helper：
  - 读取对阵生成所需源数据。
  - 生成三轮对阵。
  - 覆盖写入 `fight_info`。
  - 清理对阵缓存，并标记快照过期。
- 对阵查询 helper：
  - 校验轮次和桌号。
  - 读取对应轮次的对阵信息。
  - 返回双方队名和成员。
- 比分提交 helper：
  - 读取对阵信息。
  - 构建比分更新 payload。
  - 如果启用 Redis 写回队列，则写入队列；否则直接写入 MySQL。
  - 标记快照过期。
  - 保存比分日志。

现有 HTML 路由在 helper 存在后也应调用同一套 helper。这样可以避免 Vue 页面和旧 Flask 页面出现两套行为。

## 前端设计

新增 `vue-router`。

文件规划：

- `GuanDanFront-V2.0/src/router/index.js`
  - 定义 `/`、`/screen`、`/admin`、`/score`、`/score/:turn/:table`。
- `GuanDanFront-V2.0/src/views/ScreenView.vue`
  - 承接当前 `App.vue` 中的大屏展示逻辑。
- `GuanDanFront-V2.0/src/views/AdminView.vue`
  - 管理员后台控制台外壳。
- `GuanDanFront-V2.0/src/views/ScoreEntryView.vue`
  - 当前轮次展示和桌号输入入口。
- `GuanDanFront-V2.0/src/views/ScoreFormView.vue`
  - 队伍信息展示和比分提交表单。
- `GuanDanFront-V2.0/src/api/admin.js`
  - 后台管理 API 封装。
- `GuanDanFront-V2.0/src/api/score.js`
  - 录分 API 封装。
- `GuanDanFront-V2.0/src/components/admin/*`
  - 如果 `AdminView.vue` 过大，将后台功能拆成多个聚焦组件。

后台页面分区：

- 赛事初始化：
  - 上传 Excel。
  - 清空业务数据，并进行二次确认。
  - 预览已导入队伍。
- 轮次与计时控制：
  - 展示当前轮次和倒计时文本。
  - 设置轮次为 `1`、`2`、`3` 或未设置。
  - 启动/暂停倒计时。
- 对阵管理：
  - 展示全部对阵行。
  - 重新生成对阵，并进行二次确认。
- 后台改分：
  - 输入轮次和桌号。
  - 复用 `/score/:turn/:table` 的表单行为。
- 大屏状态：
  - 如果后端可提供，展示快照更新时间。
  - 提供跳转 `/screen` 的入口。

录分页面行为：

- `/score` 加载当前轮次。
- 如果当前轮次无效，展示明确提示，并禁用桌号查询。
- 如果当前轮次有效，用户输入桌号后跳转到 `/score/<turn>/<table>`。
- `/score/:turn/:table` 加载对阵信息，展示双方队伍和成员，然后提交比分。
- 如果双方最终等级相同，必须选择最后一局赢家。
- 二维码登录、身份校验和权限控制不属于第一版迁移范围。

## 错误处理

后端：

- 统一返回 `ok/message/error/data` JSON。
- 使用稳定错误码：
  - `invalid_turn`
  - `invalid_table`
  - `match_not_found`
  - `invalid_file`
  - `import_failed`
  - `match_generation_failed`
  - `score_invalid`
  - `winner_required_when_tied`
  - `score_write_failed`
- 对危险操作保持显式和收敛。

前端：

- 在页面内展示错误，不再依赖 `alert`。
- 清空业务数据和重新生成对阵必须有二次确认。
- `/score` 保持移动端可读、操作简单，为后续二维码扫码入口预留空间。
- 比分提交后提示“已进入更新队列”或“已直接更新”。

## 测试与验证

后端运行环境：

- Conda 环境名：`flask_app_env`
- Conda 环境路径：`C:\Users\Administrator\miniconda3\envs\flask_app_env`
- 该环境已经配置完毕，后续后端运行和测试应优先使用该环境，避免误报缺少依赖。

后端测试：

- 为比分解析和比分提交 helper 增加测试；涉及数据库的部分尽量 mock。
- 可行时使用 Flask test client 增加 API 测试。
- 覆盖：
  - 当前轮次未设置时返回 `invalid_turn`。
  - 桌号非法或不存在时返回 `invalid_table` 或 `match_not_found`。
  - 同等级未选择赢家时返回 `winner_required_when_tied`。
  - 比分提交成功后会标记快照过期。
  - 对阵生成失败时管理员接口返回明确错误。

运行：

```powershell
cd GuanDan_backend-V2.0
conda activate flask_app_env
python -m unittest discover -s tests -p "test_*.py" -v
```

前端验证：

```powershell
cd GuanDanFront-V2.0
npm run build
```

手工验证：

- `/screen` 仍能渲染大屏展示。
- `/admin` 能导入数据、设置轮次、控制计时、生成对阵，并进入后台改分。
- `/score` 能加载当前轮次、输入桌号并提交比分。
- 数据变更后，大屏在下一次轮询时能刷新比分和排名。

## Git 策略

使用小提交：

1. `docs: add admin migration design`
2. `feat: add admin and score json APIs`
3. `feat: route frontend screen admin score pages`

如果前端路由迁移改动较大，将第三个提交拆成：

- `feat: move screen display behind vue router`
- `feat: add admin and score vue pages`

每一步只暂存当前步骤相关文件。仓库中已经存在其他本地改动和生成文件，因此提交时避免使用宽泛的 `git add .`。

## 非目标范围

- 二维码录分用户登录。
- 细粒度权限控制。
- 删除旧 Flask 模板。
- 超出功能可用性的视觉美化。
- 替换 Flask、Vue、MySQL 或 Redis。
- 批量删除文件或目录。
