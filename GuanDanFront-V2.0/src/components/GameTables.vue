<template>
  <div v-if="matchDatas && matchDatas.length > 0" class="tables">
    <div class="tables-title">{{ UI_TEXT.GAME_TITLE }}</div>
    <div class="table-card" v-for="(match, index) in matchDatas" :key="index">
      <div class="table-id">{{ match[0] }}</div>
      <div class="two-team">
        <div class="team-score">
          <p class="team-name">{{ match[1] }}</p>
          <p v-if="hasLevel(match[5])" class="team-level">
            Rank {{ displayLevel(match[5]) }}
          </p>
          <p class="team-members">{{ formatTeamMembers(match[2]) }}</p>
          <p class="team-total-score">
            {{ scores[match[1]] }}
          </p>
        </div>
        <div class="team-score">
          <p class="team-name">{{ match[3] }}</p>
          <p v-if="hasLevel(match[6])" class="team-level">
            Rank {{ displayLevel(match[6]) }}
          </p>
          <p class="team-members">{{ formatTeamMembers(match[4]) }}</p>
          <p class="team-total-score">
            {{ scores[match[3]] }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatTeamMembers } from "@/utils/formatters.js";
import { UI_TEXT } from "@/constants/index.js";

const hasLevel = (level) => level !== null && level !== undefined && level !== "";
const displayLevel = (level) => String(level);

defineProps({
  matchDatas: {
    type: Array,
    required: true,
  },
  scores: {
    type: Object,
    required: true,
  },
});
</script>

<style scoped>
.tables {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(clamp(128px, 12vw, 170px), 1fr));
  align-content: start;
  align-items: stretch;
  gap: clamp(10px, 1.2vw, 18px);
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: auto;
  padding: 0 6px 8px;
}

.tables-title {
  grid-column: 1 / -1;
  width: 100%;
  text-align: center;
  font-size: clamp(28px, 3.1vw, 58px);
  line-height: 1.15;
  font-weight: bold;
  color: #fff;
  text-shadow: 2px 2px 1px #2b4180;
}

.table-card {
  width: 100%;
  min-height: clamp(132px, 15vh, 172px);
  background-color: rgba(255, 254, 245, 0.95);
  border: 0.5px solid rgb(255, 255, 255); /* rgb(255, 248, 173) */
  border-radius: 18px;
  box-shadow: 0 0 20px rgb(255, 255, 255); /* rgb(255, 244, 128) */
  display: flex;
  /* 使用 Flexbox 布局 */
  flex-direction: column;
  /* 垂直排列 */
  justify-content: space-evenly;
  /* 垂直方向均匀分布 */
  align-items: center;
  /* 水平居中 */
  padding: 10px;
  /* 增加内边距 */
}

.table-id {
  width: 100%;
  margin-top: 0%;
  font-family: Impact, Haettenschweiler, "Arial Narrow Bold", sans-serif;
  font-size: clamp(16px, 1.2vw, 20px);
  text-align: center;
}

.two-team {
  display: flex;
  /* 水平方向均匀分布 */
  align-items: center;
  /* 垂直居中 */
  width: 100%;
}

.team-score {
  display: flex;
  /* 使用 Flexbox 布局 */
  flex-direction: column;
  /* 垂直排列 */
  align-items: center;
  /* 水平居中 */
  font-family: "Trebuchet MS", "Lucida Sans Unicode", "Lucida Grande",
    "Lucida Sans", Arial, sans-serif;
  width: 50%;
}

.team-name {
  text-align: center;
  margin: 0 0 8px;
  font-size: clamp(13px, 1vw, 16px);
  line-height: 1.25;
  white-space: pre-line;
  font-weight: bold;
  overflow-wrap: anywhere;
}

.team-members {
  text-align: center;
  font-size: clamp(13px, 1.1vw, 18px);
  line-height: 1.25;
  /* 减小字号 */
  margin: 0;
  /* 垂直显示 */
  white-space: pre-line;
  /* 保留换行符 */
  font-weight: bold;
}

.team-level {
  margin: 0 0 6px;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(43, 65, 128, 0.12);
  color: #2b4180;
  font-size: clamp(12px, 0.85vw, 14px);
  line-height: 1.2;
  font-weight: 800;
}

.team-total-score {
  text-align: center;
  font-size: clamp(13px, 1vw, 16px);
  margin: 6px 0 0;
}
</style>
