<template>
  <div class="seating-arrangement">
    <div class="header">
      <h2>2025中秋 × VCC第四届掼蛋大赛 - 座位安排</h2>
      <div class="controls">
        <input
          type="file"
          ref="fileInput"
          @change="handleFileUpload"
          accept=".xlsx,.xls"
          class="file-input"
          id="seating-excel-file"
        />
        <label for="seating-excel-file" class="file-label">📁 导入Excel</label>
        <button @click="useDefaultFile" class="default-btn" :disabled="loading">
          使用默认数据
        </button>
        <select
          v-model="currentRound"
          class="round-selector"
          v-if="groupingResult"
        >
          <option v-for="round in availableRounds" :key="round" :value="round">
            第{{ round }}轮
          </option>
        </select>
        <button
          v-if="groupingResult"
          @click="regenerateGroups"
          class="regenerate-btn"
          :disabled="loading"
        >
          重新分组
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>{{ loadingMessage }}</p>
    </div>

    <!-- 错误信息 -->
    <div v-if="error" class="error">
      <h3>❌ 错误</h3>
      <p>{{ error }}</p>
    </div>

    <!-- 教室布局容器 -->
    <div v-if="!loading && !error" class="classrooms-container">
      <!-- 703教室 -->
      <div class="classroom classroom-703">
        <div class="classroom-header">
          <h3>703桌位安排</h3>
          <span class="table-count">{{ getTables703().length }}桌</span>
        </div>
        <div class="classroom-layout">
          <!-- 大屏幕 -->
          <div class="screen-area">
            <div class="screen">大屏幕</div>
          </div>

          <!-- 桌位布局 -->
          <div class="tables-grid grid-703">
            <div
              class="table-position"
              v-for="table in getTables703()"
              :key="table.id"
            >
              <div class="table-card" :class="{ 'has-match': table.match }">
                <div class="table-number">{{ table.number }}号桌</div>
                <div v-if="table.match" class="match-info">
                  <div class="team team1">
                    <div class="team-name">{{ table.match.team1Id }}</div>
                    <div class="team-members">
                      {{ table.match.team1Members }}
                    </div>
                    <div class="team-meta">
                      {{ table.match.team1Office }}-{{ table.match.team1Level }}
                    </div>
                  </div>
                  <div class="vs">VS</div>
                  <div class="team team2">
                    <div class="team-name">{{ table.match.team2Id }}</div>
                    <div class="team-members">
                      {{ table.match.team2Members }}
                    </div>
                    <div class="team-meta">
                      {{ table.match.team2Office }}-{{ table.match.team2Level }}
                    </div>
                  </div>
                </div>
                <div v-else class="empty-table">
                  <span>空桌</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 窗户区域 -->
          <div class="window-area">
            <div class="window-label">窗户</div>
          </div>
        </div>
      </div>

      <!-- 704教室 -->
      <div class="classroom classroom-704">
        <div class="classroom-header">
          <h3>704飞机座桌位表</h3>
          <span class="table-count">{{ getTables704().length }}桌</span>
        </div>
        <div class="classroom-layout">
          <!-- 玻璃门 -->
          <div class="door-area">
            <div class="door">玻璃门</div>
          </div>

          <!-- 桌位布局 -->
          <div class="tables-grid grid-704">
            <div
              class="table-position"
              v-for="table in getTables704()"
              :key="table.id"
            >
              <div class="table-card" :class="{ 'has-match': table.match }">
                <div class="table-number">{{ table.number }}号桌</div>
                <div v-if="table.match" class="match-info">
                  <div class="team team1">
                    <div class="team-name">{{ table.match.team1Id }}</div>
                    <div class="team-members">
                      {{ table.match.team1Members }}
                    </div>
                    <div class="team-meta">
                      {{ table.match.team1Office }}-{{ table.match.team1Level }}
                    </div>
                  </div>
                  <div class="vs">VS</div>
                  <div class="team team2">
                    <div class="team-name">{{ table.match.team2Id }}</div>
                    <div class="team-members">
                      {{ table.match.team2Members }}
                    </div>
                    <div class="team-meta">
                      {{ table.match.team2Office }}-{{ table.match.team2Level }}
                    </div>
                  </div>
                </div>
                <div v-else class="empty-table">
                  <span>空桌</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 7楼体闲区 -->
      <div class="classroom classroom-rest-area">
        <div class="classroom-header">
          <h3>7楼体闲区桌位表</h3>
          <span class="table-count">{{ getTablesRest().length }}桌</span>
        </div>
        <div class="classroom-layout">
          <!-- 点心开群 -->
          <div class="snack-area">
            <div class="snack-label">点心月饼</div>
          </div>

          <!-- 桌位布局 -->
          <div class="tables-grid grid-rest">
            <div
              class="table-position"
              v-for="table in getTablesRest()"
              :key="table.id"
            >
              <div class="table-card" :class="{ 'has-match': table.match }">
                <div class="table-number">{{ table.number }}号桌</div>
                <div v-if="table.match" class="match-info">
                  <div class="team team1">
                    <div class="team-name">{{ table.match.team1Id }}</div>
                    <div class="team-members">
                      {{ table.match.team1Members }}
                    </div>
                    <div class="team-meta">
                      {{ table.match.team1Office }}-{{ table.match.team1Level }}
                    </div>
                  </div>
                  <div class="vs">VS</div>
                  <div class="team team2">
                    <div class="team-name">{{ table.match.team2Id }}</div>
                    <div class="team-members">
                      {{ table.match.team2Members }}
                    </div>
                    <div class="team-meta">
                      {{ table.match.team2Office }}-{{ table.match.team2Level }}
                    </div>
                  </div>
                </div>
                <div v-else class="empty-table">
                  <span>空桌</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 排行榜区域 -->
          <!-- <div class="ranking-area">
            <div class="ranking-label">排行榜</div>
          </div> -->
        </div>
      </div>
    </div>

    <!-- 统计信息 -->
    <!-- <div v-if="groupingResult && !loading" class="statistics-panel">
      <h3>📊 分组统计</h3>
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-label">总队伍数:</span>
          <span class="stat-value">{{
            groupingResult.statistics.totalTeams
          }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">总比赛数:</span>
          <span class="stat-value">{{ getCurrentRoundMatches().length }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">空桌数:</span>
          <span class="stat-value">{{ getEmptyTablesCount() }}</span>
        </div>
      </div>
    </div> -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import {
  generateGuandanGroupsFromFile,
  generateGuandanGroupsFromExcel,
} from "@/composables/dynamicGroupingAlgorithm.js";

// 响应式数据
const fileInput = ref();
const groupingResult = ref(null);
const loading = ref(false);
const error = ref("");
const loadingMessage = ref("正在处理数据...");
const currentRound = ref(1);

// 桌位分配规则
const CLASSROOM_TABLES = {
  703: { start: 1, count: 10 }, // 1-10号桌
  704: { start: 11, count: 4 }, // 11-14号桌
  rest: { start: 15, count: 8 }, // 15-22号桌
};

// 计算属性
const availableRounds = computed(() => {
  if (!groupingResult.value) return [];
  return Array.from(
    { length: groupingResult.value.rounds.length },
    (_, i) => i + 1
  );
});

// 获取当前轮次的比赛数据
const getCurrentRoundMatches = () => {
  if (
    !groupingResult.value ||
    !groupingResult.value.rounds[currentRound.value - 1]
  ) {
    return [];
  }
  return groupingResult.value.rounds[currentRound.value - 1];
};

// 将比赛数据转换为包含队伍详细信息的格式
const getMatchWithTeamDetails = (match) => {
  if (!match || !groupingResult.value) return null;

  const [tableName, team1Id, team1Members, team2Id, team2Members] = match;
  const teams = groupingResult.value.teams;

  const team1 = teams.find((t) => t.id === team1Id);
  const team2 = teams.find((t) => t.id === team2Id);

  if (!team1 || !team2) return null;

  return {
    tableName,
    team1Id,
    team1Members,
    team1Office: team1.office,
    team1Level: team1.level,
    team2Id,
    team2Members,
    team2Office: team2.office,
    team2Level: team2.level,
  };
};

// 获取指定教室的桌位数据
const getClassroomTables = (classroom) => {
  const config = CLASSROOM_TABLES[classroom];
  const tables = [];
  const matches = getCurrentRoundMatches();

  for (let i = 0; i < config.count; i++) {
    const tableNumber = config.start + i;
    const tableId = `桌${tableNumber}`;

    // 查找对应的比赛
    const match = matches.find((m) => {
      const matchTableNumber = parseInt(m[0].replace("桌", ""));
      return matchTableNumber === tableNumber;
    });

    tables.push({
      id: tableNumber,
      number: tableNumber,
      match: match ? getMatchWithTeamDetails(match) : null,
    });
  }

  return tables;
};

// 各教室桌位获取函数
const getTables703 = () => getClassroomTables("703");
const getTables704 = () => getClassroomTables("704");
const getTablesRest = () => getClassroomTables("rest");

// 计算空桌数量
const getEmptyTablesCount = () => {
  const allTables = [...getTables703(), ...getTables704(), ...getTablesRest()];
  return allTables.filter((table) => !table.match).length;
};

// 文件上传处理
const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  try {
    loading.value = true;
    loadingMessage.value = "正在读取Excel文件...";
    error.value = "";

    const result = await generateGuandanGroupsFromFile(file);
    groupingResult.value = result;
    currentRound.value = 1;

    console.log("分组结果:", result);
  } catch (err) {
    console.error("处理文件失败:", err);
    error.value = err.message;
  } finally {
    loading.value = false;
  }
};

// 使用默认文件
const useDefaultFile = async () => {
  try {
    loading.value = true;
    loadingMessage.value = "正在加载默认数据...";
    error.value = "";

    // 使用默认的Excel文件路径
    const defaultFilePath =
      "/src/assets/2025迎新吃月饼 × VCC第四届掼蛋大赛报名表.xlsx";
    const result = await generateGuandanGroupsFromExcel(defaultFilePath);
    groupingResult.value = result;
    currentRound.value = 1;

    console.log("默认分组结果:", result);
  } catch (err) {
    console.error("加载默认数据失败:", err);
    error.value = err.message;
  } finally {
    loading.value = false;
  }
};

// 重新生成分组
const regenerateGroups = async () => {
  if (!groupingResult.value) return;

  try {
    loading.value = true;
    loadingMessage.value = "正在重新生成分组...";
    error.value = "";

    // 重新运行分组算法
    const teams = groupingResult.value.teams;
    const result = await generateGuandanGroupsFromExcel(
      "/src/assets/2025迎新吃月饼 × VCC第四届掼蛋大赛报名表.xlsx"
    );
    groupingResult.value = result;

    console.log("重新分组结果:", result);
  } catch (err) {
    console.error("重新分组失败:", err);
    error.value = err.message;
  } finally {
    loading.value = false;
  }
};

// 组件挂载时自动加载默认数据
onMounted(() => {
  useDefaultFile();
});
</script>

<style scoped>
.seating-arrangement {
  width: 100%;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  box-sizing: border-box;
  overflow-y: auto;
}

.header {
  text-align: center;
  margin-bottom: 20px;
}

.header h2 {
  color: white;
  font-size: 24px;
  font-weight: bold;
  margin: 0 0 15px 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.controls {
  display: flex;
  gap: 10px;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
}

.file-input {
  display: none;
}

.file-label,
.default-btn,
.regenerate-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.9);
  border: none;
  border-radius: 20px;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #2c3e50;
}

.file-label:hover,
.default-btn:hover,
.regenerate-btn:hover {
  background: white;
  transform: translateY(-1px);
}

.round-selector {
  padding: 8px 12px;
  border: none;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.9);
  font-weight: bold;
  color: #2c3e50;
}

.loading {
  text-align: center;
  color: white;
  padding: 40px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top: 4px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.error {
  background: rgba(255, 107, 107, 0.9);
  color: white;
  padding: 20px;
  border-radius: 10px;
  margin: 20px;
  text-align: center;
}

.classrooms-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: center;
  align-items: flex-start;
}

.classroom {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 15px;
  padding: 15px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  min-width: 400px;
  max-width: 600px;
  flex: 1;
}

.classroom-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #4a90e2;
}

.classroom-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 18px;
  font-weight: bold;
}

.table-count {
  background: #4a90e2;
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

.classroom-layout {
  position: relative;
  min-height: 400px;
}

/* 网格布局样式 */
.grid-703 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 20px 0;
}

.grid-703 .table-position:nth-child(1) {
  grid-column: 1;
  grid-row: 1;
}
.grid-703 .table-position:nth-child(2) {
  grid-column: 1;
  grid-row: 3;
}
.grid-703 .table-position:nth-child(3) {
  grid-column: 2;
  grid-row: 1;
}
.grid-703 .table-position:nth-child(4) {
  grid-column: 2;
  grid-row: 2;
}
.grid-703 .table-position:nth-child(5) {
  grid-column: 2;
  grid-row: 3;
}
.grid-703 .table-position:nth-child(6) {
  grid-column: 3;
  grid-row: 1;
}
.grid-703 .table-position:nth-child(7) {
  grid-column: 3;
  grid-row: 2;
}
.grid-703 .table-position:nth-child(8) {
  grid-column: 2;
  grid-row: 4;
}
.grid-703 .table-position:nth-child(9) {
  grid-column: 3;
  grid-row: 3;
}
.grid-703 .table-position:nth-child(10) {
  grid-column: 3;
  grid-row: 4;
}

.grid-704 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  padding: 20px 0;
  justify-items: center;
}

.grid-rest {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 20px 0;
}

.grid-rest .table-position:nth-child(1) {
  grid-column: 1;
  grid-row: 2;
}
.grid-rest .table-position:nth-child(2) {
  grid-column: 1;
  grid-row: 3;
}
.grid-rest .table-position:nth-child(3) {
  grid-column: 2;
  grid-row: 2;
}
.grid-rest .table-position:nth-child(4) {
  grid-column: 2;
  grid-row: 3;
}
.grid-rest .table-position:nth-child(5) {
  grid-column: 3;
  grid-row: 2;
}
.grid-rest .table-position:nth-child(6) {
  grid-column: 3;
  grid-row: 3;
}
.grid-rest .table-position:nth-child(7) {
  grid-column: 4;
  grid-row: 2;
}
.grid-rest .table-position:nth-child(8) {
  grid-column: 4;
  grid-row: 3;
}

.table-card {
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  padding: 8px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  background: white;
}

.table-card.has-match {
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  border-color: #f39c12;
}

.table-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.table-number {
  font-weight: bold;
  font-size: 12px;
  color: #2c3e50;
  margin-bottom: 8px;
  padding: 4px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 6px;
}

.match-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: 10px;
}

.team {
  padding: 4px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 6px;
  margin: 2px 0;
}

.team-name {
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 2px;
}

.team-members {
  color: #34495e;
  font-size: 9px;
  line-height: 1.2;
}

.team-meta {
  color: #7f8c8d;
  font-size: 8px;
  margin-top: 2px;
}

.vs {
  color: #e74c3c;
  font-weight: bold;
  font-size: 10px;
  margin: 4px 0;
}

.empty-table {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #95a5a6;
  font-style: italic;
}

/* 特殊区域样式 */
.screen-area,
.door-area,
.snack-area,
.ranking-area,
.window-area {
  position: absolute;
  background: rgba(255, 165, 0, 0.8);
  padding: 6px 12px;
  border-radius: 15px;
  font-weight: bold;
  color: white;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
  font-size: 10px;
  z-index: 10;
}

.screen-area {
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  width: 150px;
  text-align: center;
}

.door-area {
  top: 10px;
  right: 10px;
}

.snack-area {
  top: 10px;
  left: 10px;
  background: rgba(76, 175, 80, 0.8);
}

.ranking-area {
  bottom: 10px;
  right: 50%;
  transform: translateX(50%);
}

.window-area {
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  writing-mode: vertical-lr;
  background: rgba(33, 150, 243, 0.8);
}

/* 统计面板 */
.statistics-panel {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 10px;
  padding: 15px;
  margin-top: 20px;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

.statistics-panel h3 {
  margin: 0 0 15px 0;
  color: #2c3e50;
  text-align: center;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  background: rgba(74, 144, 226, 0.1);
  border-radius: 6px;
}

.stat-label {
  font-weight: bold;
  color: #2c3e50;
}

.stat-value {
  color: #4a90e2;
  font-weight: bold;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .classrooms-container {
    flex-direction: column;
    align-items: center;
  }

  .classroom {
    min-width: 350px;
    max-width: 90%;
  }

  .header h2 {
    font-size: 20px;
  }

  .controls {
    gap: 8px;
  }

  .file-label,
  .default-btn,
  .regenerate-btn {
    padding: 6px 12px;
    font-size: 11px;
  }
}

@media (max-width: 480px) {
  .classroom {
    min-width: 300px;
  }

  .grid-703,
  .grid-rest {
    grid-template-columns: repeat(2, 1fr);
  }

  .table-card {
    min-height: 100px;
  }

  .match-info {
    font-size: 9px;
  }
}
</style>
