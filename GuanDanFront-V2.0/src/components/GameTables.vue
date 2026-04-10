<template>
  <div v-if="matchDatas && matchDatas.length > 0" class="tables">
    <div class="tables-title">{{ UI_TEXT.GAME_TITLE }}</div>
    <div class="table-card" v-for="(match, index) in matchDatas" :key="index">
      <div class="table-id">{{ match[0] }}</div>
      <div class="two-team">
        <div class="team-score">
          <p class="team-name">{{ match[1] }}</p>
          <p class="team-members">{{ formatTeamMembers(match[2]) }}</p>
          <p class="team-total-score">
            {{ scores[match[1]] }}
          </p>
        </div>
        <div class="team-score">
          <p class="team-name">{{ match[3] }}</p>
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
  display: flex;
  flex-wrap: wrap;
  float: left;
  width: 74%;
  height: 80%;
  align-items: center;
}

.tables-title {
  width: 100%;
  text-align: center;
  font-size: 60px;
  font-weight: bold;
  color: #fff;
  text-shadow: 2px 2px 1px #2b4180;
}

.table-card {
  height: 160px;
  width: 160px;
  background-color: rgba(255, 254, 245, 0.95);
  border: 0.5px solid rgb(255, 255, 255); /* rgb(255, 248, 173) */
  border-radius: 20%;
  box-shadow: 0 0 20px rgb(255, 255, 255); /* rgb(255, 244, 128) */
  margin: 20px;
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
  height: 10%;
  width: 100%;
  margin-top: 0%;
  font-family: Impact, Haettenschweiler, "Arial Narrow Bold", sans-serif;
  font-size: 20px;
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
  margin-bottom: 10px;
  font-size: 16px;
  white-space: pre-line;
  font-weight: bold;
}

.team-members {
  text-align: center;
  font-size: 18px;
  /* 减小字号 */
  margin: 0;
  /* 垂直显示 */
  white-space: pre-line;
  /* 保留换行符 */
  font-weight: bold;
}

.team-total-score {
  text-align: center;
  font-size: 16px;
}
</style>
