<!-- filepath: d:\project\GuanDan\src\components\DynamicGroupingResult.vue -->
<template>
  <div class="dynamic-grouping-container">
    <div class="header">
      <h2>掼蛋比赛动态分组系统</h2>
      <div class="controls">
        <input
          type="file"
          ref="fileInput"
          @change="handleFileUpload"
          accept=".xlsx,.xls"
          class="file-input"
          id="excel-file"
        />
        <label for="excel-file" class="file-label"> 📁 选择Excel文件 </label>
        <button @click="useDefaultFile" class="default-btn" :disabled="loading">
          使用默认文件
        </button>
        <button
          @click="regenerateGroups"
          class="regenerate-btn"
          :disabled="!groupingResult || loading"
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

    <!-- 数据验证信息 -->
    <div
      v-if="groupingResult && groupingResult.validation"
      class="validation-info"
    >
      <h3>📊 数据信息</h3>
      <div class="validation-grid">
        <div class="validation-item">
          <span class="label">总队伍数:</span>
          <span class="value">{{
            groupingResult.validation.statistics.totalTeams
          }}</span>
        </div>
        <div class="validation-item">
          <span class="label">有效队伍数:</span>
          <span class="value">{{ groupingResult.teams.length }}</span>
        </div>
        <div class="validation-item">
          <span class="label">办公室数:</span>
          <span class="value">{{
            groupingResult.validation.statistics.officeCount
          }}</span>
        </div>
        <div class="validation-item">
          <span class="label">等级分布:</span>
          <span class="value">{{
            formatLevelDistribution(
              groupingResult.validation.statistics.levelDistribution
            )
          }}</span>
        </div>
      </div>

      <div
        v-if="groupingResult.validation.warnings.length > 0"
        class="warnings"
      >
        <h4>⚠️ 警告信息</h4>
        <ul>
          <li
            v-for="warning in groupingResult.validation.warnings"
            :key="warning"
          >
            {{ warning }}
          </li>
        </ul>
      </div>
    </div>

    <!-- 队伍列表 -->
    <div v-if="groupingResult && !loading" class="teams-overview">
      <h3>📋 参赛队伍一览</h3>
      <div class="teams-by-office">
        <div
          v-for="(officeTeams, office) in teamsByOffice"
          :key="office"
          class="office-section"
        >
          <h4 class="office-title">
            🏢 办公室{{ office }} ({{ officeTeams.length }}支队伍)
          </h4>
          <div class="office-teams">
            <div
              v-for="team in officeTeams"
              :key="team.id"
              class="team-card"
              :class="`level-${team.level.toLowerCase()}`"
            >
              <div class="team-header">
                <span class="team-id">{{ team.id }}</span>
                <span
                  class="team-level"
                  :class="`level-${team.level.toLowerCase()}`"
                >
                  {{ team.level }}级
                </span>
              </div>
              <div class="team-name">{{ team.teamName }}</div>
              <div class="team-members">
                <span
                  v-for="(member, index) in team.members"
                  :key="member"
                  class="member"
                >
                  {{ member }}
                  <span v-if="index < team.members.length - 1" class="separator"
                    >·</span
                  >
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分组结果 -->
    <div v-if="groupingResult && !loading" class="content">
      <!-- 统计信息 -->
      <div class="statistics">
        <h3>📈 分组统计</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="label">总比赛数:</span>
            <span class="value">{{
              groupingResult.statistics.totalMatches
            }}</span>
          </div>
          <div
            class="stat-item"
            :class="{
              error: groupingResult.statistics.violationCount.sameOffice > 0,
            }"
          >
            <span class="label">同办公室对战:</span>
            <span class="value"
              >{{ groupingResult.statistics.violationCount.sameOffice }}次</span
            >
          </div>
          <div
            class="stat-item"
            :class="{
              error: groupingResult.statistics.violationCount.repeatedMatch > 0,
            }"
          >
            <span class="label">重复对战:</span>
            <span class="value"
              >{{
                groupingResult.statistics.violationCount.repeatedMatch
              }}次</span
            >
          </div>
          <div
            class="stat-item"
            :class="{
              warning:
                groupingResult.statistics.violationCount.missingLevels > 0,
            }"
          >
            <span class="label">未完成等级要求:</span>
            <span class="value"
              >{{
                groupingResult.statistics.violationCount.missingLevels
              }}个队伍</span
            >
          </div>
        </div>
      </div>

      <!-- 分组结果 -->
      <div class="rounds">
        <div
          v-for="(round, roundIndex) in groupingResult.rounds"
          :key="roundIndex"
          class="round"
        >
          <h3>🏆 第{{ roundIndex + 1 }}轮比赛 ({{ round.length }}场)</h3>
          <div class="matches">
            <div
              v-for="(match, matchIndex) in round"
              :key="matchIndex"
              class="match-card"
            >
              <div class="table-number">{{ match[0] }}</div>
              <div class="teams">
                <div class="team">
                  <div class="team-header-match">
                    <div class="team-id">{{ match[1] }}</div>
                    <div
                      class="team-level-badge"
                      :class="`level-${getTeamLevel(match[1]).toLowerCase()}`"
                    >
                      {{ getTeamLevel(match[1]) }}
                    </div>
                  </div>
                  <div class="team-members">
                    {{ formatTeamMembers(match[2]) }}
                  </div>
                  <div class="team-info">
                    {{ getTeamOffice(match[1]) }}办公室
                  </div>
                </div>
                <div class="vs">VS</div>
                <div class="team">
                  <div class="team-header-match">
                    <div class="team-id">{{ match[3] }}</div>
                    <div
                      class="team-level-badge"
                      :class="`level-${getTeamLevel(match[3]).toLowerCase()}`"
                    >
                      {{ getTeamLevel(match[3]) }}
                    </div>
                  </div>
                  <div class="team-members">
                    {{ formatTeamMembers(match[4]) }}
                  </div>
                  <div class="team-info">
                    {{ getTeamOffice(match[3]) }}办公室
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 队伍对战统计 -->
      <div
        v-if="groupingResult.statistics.teamStatistics"
        class="team-statistics"
      >
        <h3>📊 队伍对战详情</h3>
        <div class="statistics-grid">
          <div
            v-for="(stats, teamId) in groupingResult.statistics.teamStatistics"
            :key="teamId"
            class="team-stat-card"
            :class="{ incomplete: stats.missingLevels.length > 0 }"
          >
            <div class="team-stat-header">
              <span class="team-name">{{ teamId }}</span>
              <span
                class="team-level-badge"
                :class="`level-${getTeamLevel(teamId).toLowerCase()}`"
              >
                {{ getTeamLevel(teamId) }}
              </span>
            </div>
            <div class="stat-details">
              <div class="stat-row">
                <span class="label">对战次数:</span>
                <span class="value">{{ stats.matchCount }}</span>
              </div>
              <div class="stat-row">
                <span class="label">对战等级:</span>
                <span class="value">
                  <span
                    v-for="level in stats.levelsPlayed"
                    :key="level"
                    class="level-tag"
                    :class="`level-${level.toLowerCase()}`"
                  >
                    {{ level }}
                  </span>
                  <span v-if="stats.levelsPlayed.length === 0" class="no-data"
                    >无</span
                  >
                </span>
              </div>
              <div
                v-if="stats.missingLevels.length > 0"
                class="stat-row missing"
              >
                <span class="label">未对战等级:</span>
                <span class="value">
                  <span
                    v-for="level in stats.missingLevels"
                    :key="level"
                    class="level-tag missing"
                  >
                    {{ level }}
                  </span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 导出功能 -->
      <div class="export-section">
        <h3>📤 导出结果</h3>
        <div class="export-buttons">
          <button @click="exportToJson" class="export-btn">导出JSON</button>
          <button @click="exportToText" class="export-btn">导出文本</button>
          <button @click="printResult" class="export-btn">打印结果</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import {
  generateGuandanGroupsFromFile,
  generateGuandanGroupsFromExcel,
  printGroupingResult,
} from "@/composables/dynamicGroupingAlgorithm.js";
import { formatTeamMembers } from "@/utils/formatters.js";

const groupingResult = ref(null);
const loading = ref(false);
const loadingMessage = ref("");
const error = ref("");
const fileInput = ref(null);

// 计算属性：按办公室分组的队伍
const teamsByOffice = computed(() => {
  if (!groupingResult.value) return {};

  const teams = groupingResult.value.teams;
  const grouped = {};

  teams.forEach((team) => {
    if (!grouped[team.office]) {
      grouped[team.office] = [];
    }
    grouped[team.office].push(team);
  });

  // 按办公室编号排序
  const sortedOffices = Object.keys(grouped).sort(
    (a, b) => parseInt(a) - parseInt(b)
  );
  const result = {};
  sortedOffices.forEach((office) => {
    // 按等级排序队伍
    result[office] = grouped[office].sort((a, b) =>
      a.level.localeCompare(b.level)
    );
  });

  return result;
});

// 处理文件上传
const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  try {
    loading.value = true;
    loadingMessage.value = "正在读取Excel文件...";
    error.value = "";

    const result = await generateGuandanGroupsFromFile(file);
    groupingResult.value = result;

    loadingMessage.value = "分组完成！";

    // 短暂显示完成消息后隐藏加载状态
    setTimeout(() => {
      loading.value = false;
    }, 500);
  } catch (err) {
    console.error("文件处理失败:", err);
    error.value = err.message || "文件处理失败，请检查文件格式";
    loading.value = false;
  }
};

// 使用默认文件
const useDefaultFile = async () => {
  try {
    loading.value = true;
    loadingMessage.value = "正在读取默认Excel文件...";
    error.value = "";

    // 使用项目中的默认Excel文件
    const defaultFilePath =
      "/src/assets/2025迎新吃月饼 × VCC第四届掼蛋大赛报名表.xlsx";
    const result = await generateGuandanGroupsFromExcel(defaultFilePath);
    groupingResult.value = result;

    loadingMessage.value = "分组完成！";

    setTimeout(() => {
      loading.value = false;
    }, 500);
  } catch (err) {
    console.error("使用默认文件失败:", err);
    error.value = "无法读取默认文件，请手动上传Excel文件";
    loading.value = false;
  }
};

// 重新生成分组
const regenerateGroups = async () => {
  if (!fileInput.value?.files[0] && !groupingResult.value) return;

  if (fileInput.value?.files[0]) {
    await handleFileUpload({ target: fileInput.value });
  } else {
    await useDefaultFile();
  }
};

// 获取队伍信息
const getTeamInfo = (teamId) => {
  if (!groupingResult.value) return "";

  const team = groupingResult.value.teams.find((t) => t.id === teamId);
  return team ? `${team.office}-${team.level}` : "";
};

// 获取队伍等级
const getTeamLevel = (teamId) => {
  if (!groupingResult.value) return "";

  const team = groupingResult.value.teams.find((t) => t.id === teamId);
  return team ? team.level : "";
};

// 获取队伍办公室
const getTeamOffice = (teamId) => {
  if (!groupingResult.value) return "";

  const team = groupingResult.value.teams.find((t) => t.id === teamId);
  return team ? team.office : "";
};

// 格式化等级分布
const formatLevelDistribution = (distribution) => {
  return Object.entries(distribution)
    .map(([level, count]) => `${level}:${count}`)
    .join(", ");
};

// 导出为JSON
const exportToJson = () => {
  if (!groupingResult.value) return;

  const dataStr = JSON.stringify(groupingResult.value, null, 2);
  const blob = new Blob([dataStr], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = `掼蛋比赛分组结果_${new Date().toISOString().slice(0, 10)}.json`;
  a.click();

  URL.revokeObjectURL(url);
};

// 导出为文本
const exportToText = () => {
  if (!groupingResult.value) return;

  let text = "掼蛋比赛分组结果\n";
  text += "=".repeat(50) + "\n\n";

  groupingResult.value.rounds.forEach((round, index) => {
    text += `第${index + 1}轮比赛 (${round.length}场):\n`;
    text += "-".repeat(30) + "\n";

    round.forEach((match) => {
      const [table, team1Id, team1Members, team2Id, team2Members] = match;
      text += `${table}: ${team1Id} vs ${team2Id}\n`;
      text += `      ${team1Members} vs ${team2Members}\n`;
    });
    text += "\n";
  });

  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = `掼蛋比赛分组结果_${new Date().toISOString().slice(0, 10)}.txt`;
  a.click();

  URL.revokeObjectURL(url);
};

// 打印结果到控制台
const printResult = () => {
  if (!groupingResult.value) return;

  printGroupingResult(groupingResult.value);
  alert("结果已打印到浏览器控制台，请按F12查看");
};
</script>

<style scoped>
.dynamic-grouping-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.header {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #eee;
}

.header h2 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 28px;
}

.controls {
  display: flex;
  gap: 15px;
  align-items: center;
  flex-wrap: wrap;
}

.file-input {
  display: none;
}

.file-label {
  padding: 10px 20px;
  background-color: #28a745;
  color: white;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.file-label:hover {
  background-color: #218838;
}

.default-btn,
.regenerate-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.default-btn {
  background-color: #007bff;
  color: white;
}

.default-btn:hover:not(:disabled) {
  background-color: #0056b3;
}

.regenerate-btn {
  background-color: #6c757d;
  color: white;
}

.regenerate-btn:hover:not(:disabled) {
  background-color: #545b62;
}

.default-btn:disabled,
.regenerate-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.loading {
  text-align: center;
  padding: 50px;
  color: #666;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 20px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
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
  background-color: #fff5f5;
  border: 1px solid #fed7d7;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.error h3 {
  margin: 0 0 10px 0;
  color: #e53e3e;
}

.error p {
  margin: 0;
  color: #c53030;
}

.validation-info {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #007bff;
}

.validation-info h3 {
  margin: 0 0 15px 0;
  color: #333;
}

.validation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.validation-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: white;
  border-radius: 5px;
}

.validation-item .label {
  font-weight: 500;
  color: #666;
}

.validation-item .value {
  font-weight: bold;
  color: #333;
}

.warnings {
  background: #fffbf0;
  border: 1px solid #ffd60a;
  border-radius: 5px;
  padding: 15px;
  margin-top: 15px;
}

.warnings h4 {
  margin: 0 0 10px 0;
  color: #b45309;
}

.warnings ul {
  margin: 0;
  padding-left: 20px;
}

.warnings li {
  color: #92400e;
  margin-bottom: 5px;
}

/* 队伍一览样式 */
.teams-overview {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.teams-overview h3 {
  margin: 0 0 20px 0;
  color: #333;
}

.office-section {
  margin-bottom: 25px;
}

.office-title {
  color: #495057;
  margin: 0 0 15px 0;
  padding: 10px 15px;
  background: #e9ecef;
  border-radius: 5px;
  border-left: 4px solid #007bff;
}

.office-teams {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.team-card {
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  padding: 15px;
  transition: all 0.3s ease;
}

.team-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.team-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.team-id {
  font-weight: bold;
  color: #333;
  font-size: 16px;
}

.team-name {
  color: #666;
  font-size: 14px;
  margin-bottom: 8px;
}

.team-members {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.member {
  color: #495057;
  font-weight: 500;
}

.separator {
  color: #adb5bd;
  margin: 0 2px;
}

/* 等级徽章样式 */
.team-level,
.team-level-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
}

.level-a {
  background-color: #d4edda;
  color: #155724;
  border-color: #c3e6cb;
}

.level-b {
  background-color: #cce7ff;
  color: #004085;
  border-color: #b3d7ff;
}

.level-c {
  background-color: #fff3cd;
  color: #856404;
  border-color: #ffeaa7;
}

.level-d {
  background-color: #f8d7da;
  color: #721c24;
  border-color: #f5c6cb;
}

.team-card.level-a {
  border-color: #28a745;
}

.team-card.level-b {
  border-color: #007bff;
}

.team-card.level-c {
  border-color: #ffc107;
}

.team-card.level-d {
  border-color: #dc3545;
}

.statistics {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.statistics h3 {
  margin: 0 0 15px 0;
  color: #333;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 10px;
  background: white;
  border-radius: 5px;
  border-left: 4px solid #007bff;
}

.stat-item.error {
  border-left-color: #dc3545;
  background-color: #fff5f5;
}

.stat-item.warning {
  border-left-color: #ffc107;
  background-color: #fffbf0;
}

.rounds {
  margin-bottom: 30px;
}

.round {
  margin-bottom: 40px;
}

.round h3 {
  color: #333;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ddd;
}

.matches {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
}

.match-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.table-number {
  text-align: center;
  font-weight: bold;
  font-size: 18px;
  color: #007bff;
  margin-bottom: 15px;
}

.teams {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.team {
  flex: 1;
  text-align: center;
}

.team-header-match {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  margin-bottom: 8px;
}

.team-id {
  font-weight: bold;
  color: #333;
}

.team-members {
  font-size: 14px;
  color: #666;
  white-space: pre-line;
  margin-bottom: 5px;
}

.team-info {
  font-size: 12px;
  color: #888;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 3px;
  display: inline-block;
}

.vs {
  font-weight: bold;
  color: #007bff;
  margin: 0 15px;
  font-size: 16px;
}

/* 队伍统计样式 */
.team-statistics {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.team-statistics h3 {
  margin: 0 0 20px 0;
  color: #333;
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 15px;
}

.team-stat-card {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 15px;
  border-left: 4px solid #28a745;
}

.team-stat-card.incomplete {
  border-left-color: #ffc107;
  background-color: #fffbf0;
}

.team-stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e9ecef;
}

.team-name {
  font-weight: bold;
  color: #333;
}

.stat-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-row.missing {
  color: #dc3545;
  font-weight: 500;
}

.stat-row .label {
  font-size: 14px;
  color: #666;
}

.stat-row .value {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.level-tag {
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: bold;
  text-transform: uppercase;
}

.level-tag.missing {
  background-color: #f8d7da;
  color: #721c24;
}

.no-data {
  color: #adb5bd;
  font-style: italic;
}

.export-section {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.export-section h3 {
  margin: 0 0 15px 0;
  color: #333;
}

.export-buttons {
  display: flex;
  gap: 15px;
  justify-content: center;
  flex-wrap: wrap;
}

.export-btn {
  padding: 10px 20px;
  background-color: #17a2b8;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.export-btn:hover {
  background-color: #138496;
}

@media (max-width: 768px) {
  .controls {
    flex-direction: column;
    align-items: stretch;
  }

  .file-label,
  .default-btn,
  .regenerate-btn {
    text-align: center;
  }

  .matches {
    grid-template-columns: 1fr;
  }

  .export-buttons {
    flex-direction: column;
  }

  .office-teams {
    grid-template-columns: 1fr;
  }

  .statistics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
