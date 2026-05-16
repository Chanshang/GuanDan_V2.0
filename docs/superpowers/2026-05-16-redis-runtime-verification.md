# 2026-05-16 Redis 运行态缓存验证记录

## 验证范围

- Redis 运行态事实数据
- 大屏读模型
- 后台概览和对阵列表
- 录分加载与提交
- 10 秒 MySQL 写回服务
- 旧 Flask 页面运行态读模型接入
- 前端后台 Redis / 写回状态展示

## 自动化验证

- `tests.test_redis_runtime`：通过，5 tests OK。
- `tests.test_runtime_store`：通过，11 tests OK。
- `tests.test_runtime_views`：通过，7 tests OK。
- `tests.test_runtime_flush_service`：通过，10 tests OK。
- `tests.test_runtime_api_integration`：通过，7 tests OK。
- `tests.test_admin_workflow`：通过，21 tests OK。
- `tests.test_admin_score_api`：通过，3 tests OK。
- Targeted backend suites：通过，64 tests OK。
- `npm run build`：通过。

## 全量测试结果

执行：

```powershell
cd GuanDan_backend-V2.0
conda run -n flask_app_env python -m unittest discover -s tests -p "test_*.py" -v
```

结果：

- 共运行 78 个测试，1 个 skipped。
- 新增 Redis runtime 相关测试均通过。
- 仍有 1 个既有失败：`tests/test_scoring.py::test_build_score_update_tie_requires_winner`。
- 失败原因仍是 `services/scoring.py` 返回乱码错误文本，而测试期望 `winner_required_when_tied`；该问题在本阶段前已记录为遗留问题，本阶段未修改 scoring 行为。

## 前端构建结果

执行：

```powershell
cd GuanDanFront-V2.0
npm run build
```

结果：构建通过。

构建仍提示两个既有 warning：

- `ScreenView.vue` 中 `src/assets/2025中秋背景.jpg` 构建期未解析，会保留到运行时解析。
- `excelReader.js` 同时被动态和静态导入，Vite 提示不会拆分到独立 chunk。

## 手工时延观察

本轮完成了代码级接入、单元测试和前端构建验证；未在当前回合启动 Redis、后端和前端进行现场手工点击压测。

待手工验证路径：

- `/admin` 首次加载：确认概览和对阵列表来自 Redis runtime view。
- 生成对阵：确认 Redis `gd:fights:turn:*` 更新，后台对阵列表立即变化。
- 后台改分入口：确认按 runtime 对阵读取，不再查 MySQL 对阵存在性。
- 提交比分：确认 Redis `gd:mini_teams:turn:*` 立即变化，dirty score 标记产生。
- `/dashboard_snapshot`：确认返回 Redis dashboard view，不触发进程内 snapshot 刷新。
- Redis 停止后的错误返回：确认接口快速返回 `redis_unavailable`。
- MySQL 写回：确认 10 秒 worker 写回后 dirty 标记清理，失败时保留 dirty 并显示 `flush_status=failed`。

## 残留问题

- 数据库索引、SQL 重写、批量插入优化未纳入本阶段。
- 旧模板仍保留为兼容入口，后续可在 Vue 流程稳定后再讨论下线。
- 全量测试仍有既有 scoring 失败：`test_build_score_update_tie_requires_winner`。
- `run.py` 当前工作区仍保留任务前已有的未暂存配置改动，本阶段提交已避免混入该配置 hunk。
