# 后台管理与录分迁移使用说明

## 完成状态

后台管理与录分迁移实现工作已经按计划完成，并已提交到当前分支
`codex/admin-score-migration`。

本轮完成内容包括：

- 后端新增 `services/admin_workflow.py` 业务编排层。
- 后端新增 `/api/admin/*` 管理接口和 `/api/score/*` 录分接口。
- 旧 Flask 模板路由已复用新的 `admin_workflow` helper，旧页面仍保留作为回滚入口。
- 前端引入 `vue-router`，原大屏迁移到 `/screen`。
- 前端新增 `/admin` 管理后台。
- 前端新增 `/score` 录分入口和 `/score/:turn/:table` 录分表单。
- 大屏二维码区域新增 `/score` 录分入口链接。

相关提交：

- `34e46eb feat: add admin workflow helpers`
- `35be021 feat: add admin and score json apis`
- `c000cb2 refactor: share backend workflow helpers`
- `a23ae3e feat: move screen display behind vue router`
- `2416e8e feat: add frontend admin score api clients`
- `7c38738 feat: add vue score entry pages`
- `6c56948 feat: add vue admin console`

## 启动方式

### 后端

```powershell
cd E:\Pycharm-pro\my_project\GuanDan\GuanDan_V2.0\GuanDan_backend-V2.0
conda activate flask_app_env
python run.py
```

默认后端地址为：

```text
http://localhost:5000
```

### 前端

```powershell
cd E:\Pycharm-pro\my_project\GuanDan\GuanDan_V2.0\GuanDanFront-V2.0
npm install
npm run dev
```

默认前端地址为：

```text
http://localhost:5001
```

## 页面入口

### 大屏展示

```text
http://localhost:5001/screen
```

`/` 会重定向到 `/screen`。

### 管理后台

```text
http://localhost:5001/admin
```

管理后台可执行：

- 上传 `.xlsx` 报名文件并导入。
- 清空业务数据，需要二次确认。
- 设置当前轮次为空、1、2、3。
- 启动或暂停倒计时。
- 生成或覆盖三轮对阵，需要二次确认。
- 查看队伍列表和对阵列表。
- 从对阵列表进入后台改分。
- 跳转打开大屏。

### 录分入口

```text
http://localhost:5001/score
```

录分入口会读取当前轮次。当前轮次未设置时，桌号入口会禁用。

录分人员输入桌号后，会进入：

```text
http://localhost:5001/score/<turn>/<table>
```

### 后台改分入口

管理后台会跳转到：

```text
http://localhost:5001/score/<turn>/<table>?mode=admin
```

该模式会使用 `/api/admin/score-match` 和 `/api/admin/scores`，按显式轮次和桌号改分。

## 后端接口概览

管理后台接口：

- `GET /api/admin/overview`
- `POST /api/admin/import`
- `POST /api/admin/clear`
- `POST /api/admin/turn`
- `POST /api/admin/timer/start`
- `POST /api/admin/timer/stop`
- `GET /api/admin/matches`
- `POST /api/admin/matches/generate`
- `GET /api/admin/score-match?turn=<turn>&table=<table>`
- `POST /api/admin/scores`

录分接口：

- `GET /api/score/current-turn`
- `GET /api/score/table?table=<table>`
- `POST /api/score/table`

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
  "error": "invalid_turn",
  "message": "当前轮次未设置",
  "data": {}
}
```

## 验证命令

### 后端新增测试

```powershell
cd E:\Pycharm-pro\my_project\GuanDan\GuanDan_V2.0\GuanDan_backend-V2.0
conda activate flask_app_env
python -m unittest tests.test_admin_workflow -v
python -m unittest tests.test_admin_score_api -v
```

当前结果：

- `tests.test_admin_workflow`：通过，11 tests OK。
- `tests.test_admin_score_api`：通过，3 tests OK。

### 前端构建

```powershell
cd E:\Pycharm-pro\my_project\GuanDan\GuanDan_V2.0\GuanDanFront-V2.0
npm run build
```

当前结果：构建通过。

构建时存在两个非阻断提示：

- `ScreenView.vue` 中背景图路径在构建期未解析，会保留到运行时解析。
- `excelReader.js` 同时被动态和静态导入，Vite 提示不会单独拆分 chunk。

## 已知遗留问题

后端全量测试：

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

当前仍有 1 个既有失败：

- `tests/test_scoring.py::test_build_score_update_tie_requires_winner`

失败原因是 `services/scoring.py` 当前返回中文或乱码错误文本，而测试期望
`winner_required_when_tied`。该问题在本轮迁移前已经存在，本轮迁移代码通过
`admin_workflow.build_score_error()` 对该错误做了兼容映射，因此不影响新增
JSON API 的错误码输出。

## 当前工作区提醒

当前仓库仍有未提交的本地改动和生成物，例如：

- `AGENTS.md`
- `GuanDan_backend-V2.0/app/config.py`
- `GuanDan_backend-V2.0/run.py`
- `__pycache__`
- `doc_render_check/`
- 项目说明 `.docx` / PDF 渲染产物

本轮迁移提交均使用窄暂存，没有把这些既有改动和生成物混入迁移提交。
