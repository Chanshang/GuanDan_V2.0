<script setup>
import { ref } from "vue"; // 添加 ref 导入
import { useGuandanData } from "@/composables/useGuandanData.js";
import { useAudio } from "@/composables/useAudio.js";
import { useTimer } from "@/composables/useTimer.js";
import { TIMER_INTERVAL } from "@/constants/index.js";

// 组件导入
import HomeScreen from "@/components/HomeScreen.vue";
import LoadingScreen from "@/components/LoadingScreen.vue";
import TimerDisplay from "@/components/TimerDisplay.vue";
import GameTables from "@/components/GameTables.vue";
import Rankings from "@/components/Rankings.vue";
import QRCode from "@/components/QRCode.vue";

import DynamicGroupingResult from "./components/DynamicGroupingResult.vue";
import SeatingArrangement from "./components/SeatingArrangement.vue";

import "./App.css";

// 添加分组显示控制变量
const showGrouping = ref(false);
const showSeating = ref(false);

// 使用 composables
const { guandanDatas, state, activityStarted, isLoading, fetchAllData } =
  useGuandanData();
const { checkAndPlayFiveMinuteWarning, testAudio } = useAudio();

// 设置定时器来获取数据
useTimer(async () => {
  const success = await fetchAllData();
  if (success) {
    // 检查并播放5分钟警告
    checkAndPlayFiveMinuteWarning(state.timeinfo, state.turn);
  }
  // 轮询每五秒钟获取一次数据，会卡顿
}, TIMER_INTERVAL);

// 处理定时器点击事件
const handleTimerClick = () => {
  testAudio();
};

// 切换显示模式
const toggleView = (viewType) => {
  if (viewType === "grouping") {
    showGrouping.value = !showGrouping.value;
    showSeating.value = false;
  } else if (viewType === "seating") {
    showSeating.value = !showSeating.value;
    showGrouping.value = false;
  }
};
</script>

<template>
  <div
    class="content-box"
    :class="{
      'grouping-mode': showGrouping,
      'seating-mode': showSeating,
    }"
  >
    <!-- 功能按钮组 - 固定在顶部 -->
    <div class="function-buttons">
      <!-- <button
        @click="toggleView('grouping')"
        class="function-toggle"
        :class="{ active: showGrouping }"
      >
        {{ showGrouping ? "返回比赛" : "分组管理" }}
      </button> -->

      <button
        @click="toggleView('seating')"
        class="function-toggle"
        :class="{ active: showSeating }"
      >
        {{ showSeating ? "返回比赛" : "座位安排" }}
      </button>
    </div>

    <!-- 分组组件 - 全屏显示 -->
    <div v-if="showGrouping" class="fullscreen-wrapper">
      <DynamicGroupingResult />
    </div>

    <!-- 座位安排组件 - 全屏显示 -->
    <div v-if="showSeating" class="fullscreen-wrapper">
      <SeatingArrangement />
    </div>

    <!-- <div class="content-box"> -->
    <!-- 在活动开始前显示 -->
    <HomeScreen v-if="!activityStarted" />

    <!-- 数据加载界面 -->
    <LoadingScreen v-else-if="isLoading" />
    <!-- 添加分组按钮 -->
    <!-- <button @click="showGrouping = !showGrouping" class="grouping-toggle">
      {{ showGrouping ? "隐藏分组" : "显示分组" }}
    </button> -->

    <!-- 分组组件 -->
    <!-- <DynamicGroupingResult v-if="showGrouping" /> -->

    <!-- 在活动开始后显示 -->
    <div v-else class="main-content">
      <!-- 倒计时显示 -->
      <TimerDisplay
        :timeinfo="state.timeinfo"
        @timer-click="handleTimerClick"
      />

      <!-- 桌子显示 -->
      <GameTables
        :match-datas="guandanDatas.matchDatas"
        :scores="guandanDatas.scores"
      />

      <!-- 排行榜容器 -->
      <Rankings
        :turn="state.turn"
        :current-office-scores="guandanDatas.cur_officeScores"
        :current-team-scores="guandanDatas.cur_teamScores"
        :total-office-scores="guandanDatas.sum_officeScores"
        :total-team-scores="guandanDatas.sum_teamScores"
      />

      <!-- 扫码计分 -->
      <QRCode />
    </div>
  </div>
</template>

<style scoped>
.content-box {
  /* padding: 0;
  margin: 0; */
  width: 100vw;
  height: 100vh;
  position: relative;
  /* overflow: hidden; */
  background-image: url("src/assets/2025中秋背景.jpg");
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center;
}

/* 功能按钮组 */
.function-buttons {
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 1000;
  display: flex;
  gap: 10px;
}

.function-toggle {
  padding: 12px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 25px;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
  border: 2px solid transparent;
}

.function-toggle:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
}

.function-toggle.active {
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
  border-color: #ffffff;
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.6);
}

/* 全屏包装器 */
.fullscreen-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 999;
}

/* 主要内容区域 */
.main-content {
  width: 100%;
  height: 100%;
  position: relative;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .function-buttons {
    top: 10px;
    left: 10px;
    flex-direction: column;
    gap: 8px;
  }

  .function-toggle {
    padding: 10px 16px;
    font-size: 12px;
  }
}

/* 主要内容区域 - 使用网格布局 */
.main-content {
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: auto auto 1fr auto;
  grid-template-areas:
    "timer"
    "rankings"
    "tables"
    "qr";
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  box-sizing: border-box;
  padding: 10px;
}
</style>
