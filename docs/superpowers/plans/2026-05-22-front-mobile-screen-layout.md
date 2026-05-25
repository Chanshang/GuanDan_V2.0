# 前端移动端与主屏布局调整实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `/admin` 手机端滚动/缩放体验，避免 `/screen` 桌位、排行榜、二维码在缩放和窄屏下重叠，并更新赛事标题与小队排行榜轮播数量。

**Architecture:** 保持现有 Vue 3 + Vite 结构，不引入新框架。移动端后台通过路由级 body class 放开全局滚动约束；主屏通过父级 CSS Grid 约束桌位区、排行榜区和二维码区，不再依赖固定坐标互相避让。

**Tech Stack:** Vue 3 SFC、Vite、CSS Grid、现有 `useGuandanData` 与 `rankingRotation` 工具。

---

## 问题拆解与解决流程

### 1. `/admin` 手机端无法缩放或操作不顺

根因分析：
- `src/App.css` 对 `html`、`body`、`#app` 设置了 `height: 100%`、`100vh` 和 `overflow: hidden`。
- 这对大屏页合理，但后台页内容很长，手机端需要页面滚动和浏览器缩放。

解决流程：
- 在 `src/views/AdminView.vue` 进入页面时给 `document.body` 添加 `admin-route-active` class，离开页面时移除。
- 在后台样式中用全局选择器只对该 class 放开 `overflow` 与高度限制。
- 保留后台表格自身横向滚动，避免手机端压缩表格导致文字互相覆盖。

验证方式：
- 构建通过。
- 用移动端宽度打开 `/admin`，确认页面可纵向滚动，表格区域可横向滚动，顶部按钮不被挤出屏幕。

### 2. `/screen` 主屏桌位、得分、二维码缩放时重叠

根因分析：
- `GameTables.vue` 使用 `float: left` 和百分比宽高。
- `Rankings.vue` 使用 `position: fixed`。
- `QRCode.vue` 使用 `position: absolute` 且 `right: 655px`。
- 这些定位方式互相不知道彼此尺寸，窗口缩放或设备宽度变化时容易叠在一起。

解决流程：
- 在 `ScreenView.vue` 的 `.main-content` 建立三列两行 grid：顶部倒计时，左侧桌位，中右侧排行榜，右下二维码。
- 给 `TimerDisplay`、`GameTables`、`Rankings`、`QRCode` 的根节点分配 grid area。
- `GameTables.vue` 改为响应式卡片网格，桌位卡片使用 `clamp()` 控制尺寸。
- `Rankings.vue` 移除 fixed 定位，使用可收缩宽度和内部滚动，保证在固定区域内显示。
- `QRCode.vue` 移除绝对定位，二维码在 grid 单元内自适应显示。
- 窄屏时改为单列纵向布局，让桌位、排行榜、二维码按顺序显示，避免硬挤。

验证方式：
- 构建通过。
- 用桌面宽屏、平板宽度、手机宽度检查 `/screen`，确认三个区域不重叠且主要内容可见。

### 3. 主屏赛事标题替换

根因分析：
- 标题集中在 `src/constants/index.js` 的 `UI_TEXT.GAME_TITLE`。

解决流程：
- 将 `VCC 2025 中秋迎新暨第四届掼蛋大赛` 替换为 `VCC2026毕业趴第五届掼蛋大赛`。

验证方式：
- 构建通过。
- `/screen` 桌位标题显示新赛事名。

### 4. 小队得分轮播从 6 组改为 8 组

根因分析：
- 轮播切片数量来自 `src/constants/index.js` 的 `TEAM_DATA_CONFIG.MAX_TEAMS`，当前值为 `6`。
- `useGuandanData.js` 已统一通过该常量切片当前轮次和累计小队得分。

解决流程：
- 将 `TEAM_DATA_CONFIG.MAX_TEAMS` 从 `6` 改为 `8`。
- 排行榜区域同步压缩行距和滚动约束，避免 8 组数据撑出布局。

验证方式：
- 使用现有构建检查编译。
- 浏览器检查排行榜可显示 8 组小队数据区域，内容不足 8 组时按实际数量显示。

## 实施步骤

- [x] 读取 `ScreenView.vue`、`AdminView.vue`、`GameTables.vue`、`Rankings.vue`、`QRCode.vue`、`useGuandanData.js` 和 `constants/index.js`，确认当前布局和轮播实现。
- [x] 修改 `AdminView.vue`，增加后台页面 body class 生命周期，并补充移动端全局滚动样式。
- [x] 修改 `ScreenView.vue`，定义主屏 grid 布局和窄屏降级布局。
- [x] 修改 `GameTables.vue`，改为响应式桌位卡片网格。
- [x] 修改 `Rankings.vue`，移除固定定位并适配 8 组小队滚动显示。
- [x] 修改 `QRCode.vue`，移除固定坐标，改为 grid 区域内自适应。
- [x] 修改 `constants/index.js`，更新赛事标题和 `MAX_TEAMS`。
- [x] 运行 `npm run build`。
- [x] 启动或复用 Vite 服务，用浏览器检查 `/admin` 和 `/screen` 的桌面/移动视图。
