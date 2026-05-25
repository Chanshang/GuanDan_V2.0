# AGENTS.md

本文件用于指导 Codex / 自动化代理在本仓库内工作。项目细节参考
`doc_render_check/掼蛋项目功能说明_word.pdf`。

## 必须遵守的删除规则

禁止批量删除文件或目录。

不要使用：

- `del /s`
- `rd /s`
- `rmdir /s`
- `Remove-Item -Recurse`
- `rm -rf`

需要删除文件时，只能一次删除一个明确路径的文件。

正确示例：

```powershell
Remove-Item "C:\path\to\file.txt"
```

如果需要批量删除文件，应停止操作，并询问用户，让用户手动删除。

## 项目定位

GuanDan V2.0 是面向线下掼蛋赛事的管理与大屏展示系统，覆盖报名 Excel
导入、队伍与等级初始化、三轮对阵生成、轮次与倒计时控制、成绩录入、排名统计
和现场大屏展示。

系统采用“后台管理 + 前端大屏展示”形态：

- 后端 Flask 提供模板管理页面、JSON 接口、聚合快照接口和业务服务。
- 前端 Vue 3 + Vite 通过 `/dashboard_snapshot` 等接口轮询展示比赛状态。
- MySQL 保存业务数据，Redis 用于对阵缓存、仪表盘快照辅助和可选成绩写回队列。

## 目录结构

- `GuanDanFront-V2.0/`：Vue 3 + Vite 前端大屏。
- `GuanDanFront-V2.0/src/api.js`：前端接口基础地址读取与请求封装。
- `GuanDanFront-V2.0/src/composables/useGuandanData.js`：大屏数据轮询与规范化。
- `GuanDanFront-V2.0/src/components/`：计时、桌位、排名、二维码、座位图等展示组件。
- `GuanDan_backend-V2.0/`：Flask 后端。
- `GuanDan_backend-V2.0/run.py`：后端入口，包含模板页面路由和主要业务流程。
- `GuanDan_backend-V2.0/api/frontend_api.py`：前端展示用 JSON / 聚合快照接口。
- `GuanDan_backend-V2.0/services/`：导入、对阵、录分、统计、缓存、日志和写回服务。
- `GuanDan_backend-V2.0/tests/`：不依赖数据库的 unittest 测试骨架。
- `doc_render_check/`：项目功能说明 PDF 及渲染检查图片。

## 常用命令

后端：

```powershell
cd GuanDan_backend-V2.0
# pip install -r requirements.txt
# 后端通过conda进行环境管理，已经配置好了环境
conda activate flask_app_env   # C:\Users\Administrator\miniconda3\envs\flask_app_env
python run.py
python -m unittest discover -s tests -p "test_*.py" -v
```

前端：

```powershell
cd GuanDanFront-V2.0
npm install
npm run dev
npm run build
```

## 运行配置

后端默认配置来自 `GuanDan_backend-V2.0/app/config.py`：

- `APP_HOST` 默认 `0.0.0.0`
- `APP_PORT` 默认 `5000`
- `DB_HOST` / `DB_PORT` 默认 `127.0.0.1` / `3306`
- `DB_NAME` 默认 `guan_egg_game`
- `REDIS_HOST` / `REDIS_PORT` 默认 `127.0.0.1` / `6379`
- `SCORE_WRITEBACK_ENABLED` 控制 Redis 成绩写回队列

前端 `.env`：

- `VITE_BASE_API=http://localhost`
- `VITE_BASE_PORT=5000`

前端 Vite 开发服务器当前配置在 `GuanDanFront-V2.0/vite.config.js`，默认监听
`0.0.0.0:5001`。

## 业务要点

- 报名导入只接受 `.xlsx`，导入后初始化队伍、等级、办公室、三轮成绩等数据。
- 对阵生成默认三轮，目标是每轮每队只出现一次、同办公室不互打、尽量避免重复对阵并兼顾等级组合。
- 当前轮次合法值为 `1`、`2`、`3` 或空状态；倒计时默认 60 分钟。
- 录分入口按轮次和桌号读取双方队伍，最终等级范围为 2 到 32。
- 同等级结算需要额外指定最后一局赢家，用于判定大分。
- `/dashboard_snapshot` 是前端大屏主接口，聚合轮次、倒计时、对阵、比分、队伍排名、办公室排名和快照时间。
- 数据变化后需要标记快照过期，避免大屏读取旧排名或旧比分。

## 开发注意事项

- 开发代码过程中，遇到环境配置问题，优先向我提问和我尝试沟通，而不是反复思考。
- 优先保持现有 Flask + Vue 结构，不要在没有明确需求时更换框架。
- 修改后端业务逻辑时，优先在 `services/` 中扩展可测试函数，避免继续把逻辑堆进 `run.py`。
- 涉及导入、对阵、录分、统计排名时，应补充或运行 `GuanDan_backend-V2.0/tests/` 下相关 unittest。
- 涉及前端大屏展示时，检查 `useGuandanData.js` 的数据规范化逻辑和组件空数据状态。
- 注意中文源码、模板和说明文档的编码一致性；发现乱码时先确认文件真实编码，不要盲目批量重写。
- 后端 README 当前显示为乱码，项目说明以 PDF、代码和测试为准。
- 不要提交或依赖 `__pycache__`、运行日志、临时上传文件、`node_modules` 等生成物。
## 中文文档与编码规范

- 除代码片段、命令、接口名、字段名、文件路径等需要保持英文或原始标识的内容外，项目设计文档、实施计划、评审说明、交接说明等面向项目审查的文档应默认使用中文编写，方便业务侧和项目对接审查。
- 新增或修改函数时，如果注释用于解释业务意图、边界条件、异常分支或非显而易见的实现原因，应优先使用中文注释；不要为显而易见的代码添加空洞注释。
- 涉及中文 Markdown、Vue、Python、HTML 模板或配置说明时，应保持 UTF-8 兼容。新增文本文件优先使用 UTF-8 无 BOM，除非既有文件或工具链明确要求其他编码。
- 发现中文显示乱码时，先确认文件真实编码和读取方式，不要盲目批量重写；确需编码恢复时，应小范围处理并说明原因。

