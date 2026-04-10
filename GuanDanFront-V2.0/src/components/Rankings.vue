<template>
  <div class="ranks-container">
    <!-- 当前轮次排行榜 -->
    <div class="ranks current-ranks">
      <div class="rank-item">
        <p class="rank-title">
          <span v-if="turn === '4'">全部轮次统计得分</span>
          <span v-else>第 {{ turn }} 轮当前得分</span>
        </p>
      </div>

      <div class="rank-item header">
        <p class="rank-id">排名</p>
        <p class="rank-office">办公室</p>
        <p class="rank-big-score">大分</p>
        <p class="rank-small-score">小分</p>
      </div>

      <div
        v-for="(office, index) in currentOfficeScores"
        :key="index"
        class="rank-item"
      >
        <p class="rank-id">{{ office[0] }}</p>
        <p class="rank-office">{{ office[1] }}</p>
        <p class="rank-big-score">{{ office[2] }}</p>
        <p class="rank-small-score">{{ office[3] }}</p>
      </div>

      <div class="rank-item header">
        <p class="rank-id">排名</p>
        <p class="rank-team">小队</p>
        <p class="rank-big-score">大分</p>
        <p class="rank-small-score">小分</p>
      </div>

      <div
        v-for="(team, index) in currentTeamScores"
        :key="index"
        class="rank-item"
      >
        <p class="rank-id">{{ team[0] }}</p>
        <p class="rank-team">{{ team[1] }}</p>
        <p class="rank-big-score">{{ team[2] }}</p>
        <p class="rank-small-score">{{ team[3] }}</p>
      </div>
    </div>

    <!-- 累计轮次排行榜 -->
    <div class="ranks total-ranks">
      <div class="rank-item">
        <p class="rank-title">累计轮次得分</p>
      </div>

      <div class="rank-item header">
        <p class="rank-id">排名</p>
        <p class="rank-office">办公室</p>
        <p class="rank-big-score">大分</p>
        <p class="rank-small-score">小分</p>
      </div>

      <div
        v-for="(office, index) in totalOfficeScores"
        :key="index"
        class="rank-item"
      >
        <p class="rank-id">{{ office[0] }}</p>
        <p class="rank-office">{{ office[1] }}</p>
        <p class="rank-big-score">{{ office[2] }}</p>
        <p class="rank-small-score">{{ office[3] }}</p>
      </div>

      <div class="rank-item header">
        <p class="rank-id">排名</p>
        <p class="rank-team">小队</p>
        <p class="rank-big-score">大分</p>
        <p class="rank-small-score">小分</p>
      </div>

      <div
        v-for="(team, index) in totalTeamScores"
        :key="index"
        class="rank-item"
      >
        <p class="rank-id">{{ team[0] }}</p>
        <p class="rank-team">{{ team[1] }}</p>
        <p class="rank-big-score">{{ team[2] }}</p>
        <p class="rank-small-score">{{ team[3] }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  turn: {
    type: String,
    required: true,
  },
  currentOfficeScores: {
    type: Array,
    required: true,
  },
  currentTeamScores: {
    type: Array,
    required: true,
  },
  totalOfficeScores: {
    type: Array,
    required: true,
  },
  totalTeamScores: {
    type: Array,
    required: true,
  },
});
</script>

<style scoped>
/* 排行榜容器 */

.ranks-container {
  position: fixed;
  top: 100px; /* 置顶显示，可根据需要调整 */
  right: 40px; /* 靠右显示 */
  display: flex;
  flex-direction: row;
  gap: 40px;
  z-index: 10;
}

.ranks {
  width: 280px;
  background: rgba(20, 30, 60, 0.7);
  border-radius: 16px;
  padding: 0px 0px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: -20px;
}

.rank-item {
  color: #fff;
  font-size: 15px;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  font-weight: 800;
  text-align: center;
  line-height: 0.6;    /* 行高更紧凑 */
}

.rank-item.header {
  font-weight: bold;
  margin-bottom: -10px;
  display: flex;
  justify-content: space-between;
}

.rank-title {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 0px;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.rank-id,
.rank-office,
.rank-team,
.rank-big-score,
.rank-small-score {
  flex: 1;
  text-align: center;
}

.rank-office,
.rank-team {
  flex: 2;
}

/* 让内容不换行 */
.rank-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* .rank-item.header {
  background: none;
  color: #fff;
  font-size: 18px;
  border-bottom: 1px solid #fff2;
  padding-bottom: 4px;
  margin-bottom: 4px;
}
 */
/*
.ranks-container {
  position: absolute;
  top: 100px; // 根据实际页面调整
  right: 40px; // 靠右显示 //
  width: 420px; // 根据内容调整宽度 //
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 40px;
}
*/

/* 调整排行榜样式，可以根据需要修改 */
/* .ranks {
  width: 49%;
}

.ranks.current-ranks {
  margin: 100px 0 0 -40px;
}

.ranks.total-ranks {
  margin: 100px 0 0 0px;
}

.ranks {
  float: left;
  margin-top: 0%;
  height: 60%;
  width: auto;
}

.rank-item {
  color: #fff;
  font-size: 20px;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  font-weight: 800;
  text-align: center;
}

.rank-item p {
  text-shadow: 2px 2px 1px #000;
}

.rank-item.header {
  font-weight: bold;
  margin-bottom: 10px;
}
.rank-title {
  margin: 0 0 0 -40px;
}

.rank-id {
  width: 50px;
  float: left;
  margin: 5px 0 0 0;
}

.rank-office {
  width: 60px;
  float: left;
  margin: 5px 0 0 0;
}

.rank-big-score {
  width: 50px;
  float: left;
  margin: 5px 0 0 0;
}

.rank-small-score {
  width: 50px;
  float: left;
  margin: 5px 0 0 0;
}

.rank-team {
  width: 100px;
  float: left;
  margin: 5px 0 0 5px;
} */

/* .ranks-container {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.ranks {
  flex: 1;
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.rank-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.rank-item:last-child {
  border-bottom: none;
}

.rank-item.header {
  background: #f8f9fa;
  font-weight: bold;
  color: #333;
  margin: 10px -20px;
  padding: 10px 20px;
}

.rank-title {
  font-size: 1.2rem;
  font-weight: bold;
  color: #333;
  text-align: center;
  width: 100%;
}

.rank-id,
.rank-office,
.rank-team,
.rank-big-score,
.rank-small-score {
  flex: 1;
  text-align: center;
}

.rank-office,
.rank-team {
  flex: 2;
}

.rank-big-score,
.rank-small-score {
  font-weight: bold;
  color: #e74c3c;
} */
</style>
