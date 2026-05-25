# GuanDanFront V2.0

这是 GuanDan V2.0 的 Vue 3 + Vite 前端，主要服务于线下掼蛋比赛现场的大屏展示、扫码录分入口、后台管理页和座位图展示。项目通过后端 `/dashboard_snapshot` 聚合快照读取比赛运行态数据，并在前端本地维护倒计时与小队榜单轮播，减少公网或 frp 访问抖动对现场画面的影响。

## 主要页面

- `/screen`：现场大屏，展示当前轮次、倒计时、桌位对阵、排行榜和扫码入口。
- `/admin`：前端后台管理页，支持报名导入、生成对阵、设置轮次、计时控制、查看队伍和对阵列表。
- `/score`：扫码录分入口，按当前轮次和桌号进入录分表单。
- `/seat`：座位图展示页。

## 核心文件

- `src/api.js`：统一请求封装，读取 `.env` 中的后端地址并设置请求超时。
- `src/composables/useGuandanData.js`：大屏数据轮询、快照规范化、本地倒计时和榜单轮播。
- `src/components/GameTables.vue`：桌位对阵卡片。
- `src/components/Rankings.vue`：小队与办公室排行榜。
- `src/components/TimerDisplay.vue`：倒计时展示。
- `src/components/QRCode.vue`：扫码录分入口二维码。
- `src/views/AdminView.vue`：后台管理页。
- `src/views/ScoreEntryView.vue` / `src/views/ScoreFormView.vue`：录分入口和录分表单。
- `src/utils/rankingRotation.js`：按时间窗口切片小队榜单。

## 环境配置

`.env` 示例：

```env
VITE_BASE_API=http://localhost
VITE_BASE_PORT=5000
```

如果通过局域网、公网 IP 或 frp 访问后端，需要把 `VITE_BASE_API` 改为实际可访问地址。

## 开发与构建

```powershell
npm install
npm run dev
npm run build
```

Vite 开发服务器默认监听 `0.0.0.0:5001`。

## 验证

构建检查：

```powershell
npm run build
```

榜单轮播工具检查：

```powershell
node --input-type=module -e "import { sliceRotatingPage } from './src/utils/rankingRotation.js'; const rows = Array.from({length: 13}, (_, i) => i + 1); const page = sliceRotatingPage(rows, 8, 5000, 5000); if (JSON.stringify(page) !== JSON.stringify([9,10,11,12,13])) process.exit(1);"
```

## 现场使用注意

- 大屏页依赖后端 Redis runtime 快照，后端和 Redis 必须先启动。
- 录分提交后，前端不直接重算排名，而是等待后端刷新后的 `/dashboard_snapshot`。
- 当外部主机访问出现刷新延迟时，优先检查 `/dashboard_snapshot` 请求是否持续发出、后端是否返回新 `snapshot_updated_at`，再判断是网络/frp 问题还是前端轮询状态问题。
