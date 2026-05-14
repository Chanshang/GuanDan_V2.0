<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  clearBusinessData,
  generateAdminMatches,
  getAdminMatches,
  getAdminOverview,
  importRegistration,
  setAdminTurn,
  startAdminTimer,
  stopAdminTimer,
} from '@/api/admin.js'

const router = useRouter()

const overview = ref({
  turn: '',
  time_message: '',
  teams: [],
  has_matches: false,
  snapshot_updated_at: '',
})
const matches = ref([])
const selectedTurn = ref('')
const selectedFile = ref(null)
const fileInput = ref(null)
const loadingOverview = ref(false)
const loadingMatches = ref(false)
const working = ref('')
const error = ref('')
const message = ref('')

const teams = computed(() => Array.isArray(overview.value.teams) ? overview.value.teams : [])
const hasMatches = computed(() => Boolean(overview.value.has_matches))
const matchCount = computed(() => Array.isArray(matches.value) ? matches.value.length : 0)
const isBusy = computed(() => Boolean(working.value) || loadingOverview.value || loadingMatches.value)
const currentTurnText = computed(() => formatTurn(overview.value.turn))
const selectedFileName = computed(() => selectedFile.value?.name || '未选择文件')
const hasArrayTeamRows = computed(() => teams.value.some((team) => Array.isArray(team)))
const teamColumnCount = computed(() => {
  const rowLengths = teams.value.map((team) => {
    if (Array.isArray(team)) {
      return team.length
    }
    return 4
  })

  return Math.max(4, ...rowLengths)
})

const turnOptions = [
  { label: '空', value: '' },
  { label: '第 1 轮', value: '1' },
  { label: '第 2 轮', value: '2' },
  { label: '第 3 轮', value: '3' },
]

const normalizeResponse = (result, fallbackMessage) => {
  if (!result?.ok) {
    throw new Error(result?.message || result?.error || fallbackMessage)
  }

  return result.data || {}
}

const normalizeTurn = (turn) => {
  if (turn === null || turn === undefined || turn === '' || turn === 'null') {
    return ''
  }
  return turn
}

const formatTurn = (turn) => {
  const normalizedTurn = normalizeTurn(turn)
  if (normalizedTurn === '') {
    return '未设置'
  }
  return `第 ${normalizedTurn} 轮`
}

const isPresent = (value) => value !== null && value !== undefined && value !== ''

const displayCell = (value) => {
  if (!isPresent(value)) {
    return '-'
  }
  if (Array.isArray(value)) {
    return value.join('、')
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return value
}

const fieldValue = (item, keys, fallback = '-', indexFallbacks = []) => {
  if (!item || typeof item !== 'object') {
    return fallback
  }

  if (!Array.isArray(item)) {
    for (const key of keys) {
      const value = item[key]
      if (isPresent(value)) {
        return value
      }
    }
  }

  if (Array.isArray(item)) {
    for (const index of indexFallbacks) {
      const value = item[index]
      if (isPresent(value)) {
        return value
      }
    }
  }

  return fallback
}

const teamArrayPadding = (team) => {
  if (!Array.isArray(team)) {
    return 0
  }
  return Math.max(0, teamColumnCount.value - team.length)
}

const matchTurn = (match, fallback = overview.value.turn) => normalizeTurn(fieldValue(
  match,
  ['turn', 'round', 'current_turn'],
  normalizeTurn(fallback),
  [5],
))

const matchTable = (match, fallback = '-') => fieldValue(
  match,
  ['table', 'table_no', 'table_number', 'desk', 'desk_no', 'id'],
  fallback,
  [0],
)

const matchTeamOne = (match) => fieldValue(
  match,
  ['team1_name', 'team_a_name', 'team_x_name', 'team1', 'team_a', 'team_name_1'],
  '-',
  [1],
)

const matchTeamTwo = (match) => fieldValue(
  match,
  ['team2_name', 'team_b_name', 'team_y_name', 'team2', 'team_b', 'team_name_2'],
  '-',
  [3],
)

const loadOverview = async () => {
  loadingOverview.value = true
  error.value = ''

  try {
    const data = normalizeResponse(await getAdminOverview(), '后台概览加载失败')
    const normalizedTurn = normalizeTurn(data.turn)
    overview.value = {
      turn: normalizedTurn,
      time_message: data.time_message ?? '',
      teams: Array.isArray(data.teams) ? data.teams : [],
      has_matches: Boolean(data.has_matches),
      snapshot_updated_at: data.snapshot_updated_at ?? '',
    }
    selectedTurn.value = normalizedTurn === '' ? '' : String(normalizedTurn)
  } catch (err) {
    error.value = err.message || '后台概览加载失败'
  } finally {
    loadingOverview.value = false
  }
}

const loadMatches = async () => {
  loadingMatches.value = true

  try {
    const data = normalizeResponse(await getAdminMatches(), '对阵列表加载失败')
    matches.value = Array.isArray(data.matches) ? data.matches : []
  } catch (err) {
    error.value = err.message || '对阵列表加载失败'
  } finally {
    loadingMatches.value = false
  }
}

const refreshAll = async () => {
  message.value = ''
  await Promise.all([loadOverview(), loadMatches()])
}

const runAction = async (actionName, action, successMessage) => {
  working.value = actionName
  error.value = ''
  message.value = ''

  try {
    const result = await action()
    normalizeResponse(result, successMessage)
    message.value = result.message || successMessage
    await refreshAll()
  } catch (err) {
    error.value = err.message || `${actionName}失败`
  } finally {
    working.value = ''
  }
}

const handleFileChange = (event) => {
  const [file] = event.target.files || []
  selectedFile.value = file || null
  message.value = ''
  error.value = ''
}

const handleImport = async () => {
  if (!selectedFile.value) {
    error.value = '请先选择报名 Excel 文件'
    return
  }

  await runAction(
    '导入报名',
    () => importRegistration(selectedFile.value),
    '报名数据导入完成',
  )

  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const handleClear = async () => {
  if (!window.confirm('确认清空所有业务数据吗？')) {
    return
  }

  await runAction('清空业务数据', clearBusinessData, '业务数据已清空')
}

const handleSetTurn = async () => {
  await runAction(
    '设置轮次',
    () => setAdminTurn(selectedTurn.value),
    '当前轮次已更新',
  )
}

const handleStartTimer = async () => {
  await runAction('启动倒计时', startAdminTimer, '倒计时已启动')
}

const handleStopTimer = async () => {
  await runAction('暂停倒计时', stopAdminTimer, '倒计时已暂停')
}

const handleGenerateMatches = async () => {
  if (!window.confirm('确认重新生成并覆盖对阵吗？')) {
    return
  }

  await runAction('生成对阵', generateAdminMatches, '对阵已生成')
}

const goScore = (match) => {
  const turn = matchTurn(match)
  const table = matchTable(match)

  if (turn === '' || turn === '-' || table === '-') {
    error.value = '该对阵缺少轮次或桌号，无法打开改分入口'
    return
  }

  router.push(`/score/${turn}/${table}?mode=admin`)
}

const goScreen = () => {
  router.push('/screen')
}

onMounted(refreshAll)
</script>

<template>
  <main class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">赛事管理后台</p>
        <h1>掼蛋赛事后台管理</h1>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" :disabled="isBusy" @click="refreshAll">
          刷新
        </button>
        <button class="primary-button" type="button" @click="goScreen">
          打开大屏
        </button>
      </div>
    </header>

    <p v-if="error" class="status error">{{ error }}</p>
    <p v-else-if="message" class="status success">{{ message }}</p>

    <section class="summary-grid" aria-label="后台概览">
      <article class="summary-card">
        <span>当前轮次</span>
        <strong>{{ currentTurnText }}</strong>
      </article>
      <article class="summary-card">
        <span>倒计时</span>
        <strong>{{ overview.time_message || '未启动' }}</strong>
      </article>
      <article class="summary-card">
        <span>队伍数量</span>
        <strong>{{ teams.length }}</strong>
      </article>
      <article class="summary-card">
        <span>对阵状态</span>
        <strong>{{ hasMatches ? '已有对阵' : '未生成' }}</strong>
      </article>
    </section>

    <p v-if="overview.snapshot_updated_at" class="snapshot-time">
      快照更新时间：{{ overview.snapshot_updated_at }}
    </p>

    <section class="tool-grid">
      <article class="panel">
        <div class="panel-title">
          <h2>报名导入</h2>
          <span>仅支持 .xlsx</span>
        </div>
        <div class="upload-row">
          <label class="file-picker">
            <input ref="fileInput" type="file" accept=".xlsx" @change="handleFileChange" />
            选择 Excel
          </label>
          <span class="file-name">{{ selectedFileName }}</span>
        </div>
        <button class="primary-button full" type="button" :disabled="isBusy" @click="handleImport">
          {{ working === '导入报名' ? '正在导入...' : '上传并导入' }}
        </button>
      </article>

      <article class="panel">
        <div class="panel-title">
          <h2>轮次与倒计时</h2>
          <span>{{ loadingOverview ? '正在加载...' : currentTurnText }}</span>
        </div>
        <div class="turn-row">
          <select v-model="selectedTurn" :disabled="isBusy">
            <option v-for="option in turnOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
          <button class="secondary-button" type="button" :disabled="isBusy" @click="handleSetTurn">
            设置轮次
          </button>
        </div>
        <div class="button-row">
          <button class="primary-button" type="button" :disabled="isBusy" @click="handleStartTimer">
            启动倒计时
          </button>
          <button class="secondary-button" type="button" :disabled="isBusy" @click="handleStopTimer">
            暂停倒计时
          </button>
        </div>
      </article>

      <article class="panel danger-panel">
        <div class="panel-title">
          <h2>业务数据</h2>
          <span>谨慎操作</span>
        </div>
        <button class="danger-button full" type="button" :disabled="isBusy" @click="handleClear">
          清空业务数据
        </button>
      </article>

      <article class="panel">
        <div class="panel-title">
          <h2>对阵生成</h2>
          <span>{{ matchCount }} 条对阵</span>
        </div>
        <button class="primary-button full" type="button" :disabled="isBusy" @click="handleGenerateMatches">
          生成/覆盖对阵
        </button>
      </article>
    </section>

    <section class="content-grid">
      <article class="panel teams-panel">
        <div class="panel-title">
          <h2>队伍列表</h2>
          <span>{{ teams.length }} 队</span>
        </div>
        <p v-if="loadingOverview" class="empty-text">正在加载队伍...</p>
        <p v-else-if="!teams.length" class="empty-text">暂无队伍数据</p>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr v-if="hasArrayTeamRows">
                <th v-for="index in teamColumnCount" :key="index">字段 {{ index }}</th>
              </tr>
              <tr v-else>
                <th>队伍</th>
                <th>成员</th>
                <th>办公室</th>
                <th>等级</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(team, index) in teams" :key="fieldValue(team, ['id', 'team_id', 'name', 'team_name'], index)">
                <template v-if="Array.isArray(team)">
                  <td v-for="(cell, cellIndex) in team" :key="cellIndex">{{ displayCell(cell) }}</td>
                  <td v-for="padIndex in teamArrayPadding(team)" :key="`pad-${padIndex}`">-</td>
                </template>
                <template v-else>
                  <td>{{ fieldValue(team, ['name', 'team_name', 'team']) }}</td>
                  <td>{{ fieldValue(team, ['members', 'member_names', 'players']) }}</td>
                  <td>{{ fieldValue(team, ['office', 'office_name', 'department']) }}</td>
                  <td>{{ fieldValue(team, ['level', 'score', 'rank']) }}</td>
                  <td v-for="padIndex in Math.max(0, teamColumnCount - 4)" :key="`object-pad-${padIndex}`">-</td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <article class="panel matches-panel">
        <div class="panel-title">
          <h2>对阵列表</h2>
          <span>{{ loadingMatches ? '正在加载...' : `${matchCount} 桌` }}</span>
        </div>
        <p v-if="loadingMatches" class="empty-text">正在加载对阵...</p>
        <p v-else-if="!matches.length" class="empty-text">暂无对阵数据</p>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>轮次</th>
                <th>桌号</th>
                <th>甲方队伍</th>
                <th>乙方队伍</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(match, index) in matches"
                :key="`${matchTurn(match)}-${matchTable(match, index)}`"
              >
                <td>{{ formatTurn(matchTurn(match)) }}</td>
                <td>{{ matchTable(match) }}</td>
                <td>{{ matchTeamOne(match) }}</td>
                <td>{{ matchTeamTwo(match) }}</td>
                <td>
                  <button class="link-button" type="button" @click="goScore(match)">
                    后台改分
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </section>
  </main>
</template>

<style scoped>
.admin-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 28px;
  background: #f4f6f8;
  color: #172033;
}

.page-header,
.panel-title,
.header-actions,
.button-row,
.turn-row,
.upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-header {
  justify-content: space-between;
  margin-bottom: 20px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #5b6b82;
  font-size: 14px;
}

h1,
h2 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: 30px;
  line-height: 1.2;
}

h2 {
  font-size: 18px;
  line-height: 1.35;
}

.summary-grid,
.tool-grid,
.content-grid {
  display: grid;
  gap: 14px;
}

.summary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 12px;
}

.tool-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 18px 0;
}

.content-grid {
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.4fr);
  align-items: start;
}

.summary-card,
.panel {
  border: 1px solid #d9e1ec;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(23, 32, 51, 0.06);
}

.summary-card {
  padding: 16px;
}

.summary-card span,
.panel-title span,
.snapshot-time,
.file-name,
.empty-text {
  color: #5b6b82;
}

.summary-card span {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
}

.summary-card strong {
  display: block;
  font-size: 24px;
  line-height: 1.25;
}

.panel {
  padding: 18px;
}

.panel-title {
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel-title span {
  font-size: 13px;
}

.status {
  margin: 0 0 16px;
  padding: 12px 14px;
  border-radius: 8px;
  font-weight: 700;
}

.success {
  background: #e9f8ef;
  color: #1b7648;
}

.error {
  background: #fff0ee;
  color: #b42318;
}

.snapshot-time {
  margin: 0;
  font-size: 13px;
}

button,
select,
.file-picker {
  min-height: 40px;
  border-radius: 8px;
  font: inherit;
}

button,
.file-picker {
  border: 0;
  font-weight: 700;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.primary-button,
.secondary-button,
.danger-button,
.file-picker {
  padding: 0 14px;
}

.primary-button {
  background: #1f5fbf;
  color: #fff;
}

.secondary-button {
  background: #e8edf5;
  color: #1f3556;
}

.danger-button {
  background: #b42318;
  color: #fff;
}

.link-button {
  min-height: 32px;
  padding: 0 10px;
  background: #e8f0ff;
  color: #1f5fbf;
}

.full {
  width: 100%;
}

.file-picker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #e8edf5;
  color: #1f3556;
}

.file-picker input {
  display: none;
}

.file-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-row,
.button-row {
  margin-bottom: 12px;
}

.turn-row {
  margin-bottom: 12px;
}

select {
  flex: 1;
  min-width: 0;
  padding: 0 12px;
  border: 1px solid #c8d3e4;
  background: #fff;
}

.table-wrap {
  overflow: auto;
  border: 1px solid #e1e7f0;
  border-radius: 8px;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 560px;
}

th,
td {
  padding: 11px 12px;
  border-bottom: 1px solid #e8edf5;
  text-align: left;
  vertical-align: top;
}

th {
  background: #f7f9fc;
  color: #45556f;
  font-size: 13px;
  white-space: nowrap;
}

tr:last-child td {
  border-bottom: 0;
}

.empty-text {
  margin: 0;
  padding: 16px 0;
}

@media (max-width: 1100px) {
  .summary-grid,
  .tool-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .admin-page {
    padding: 18px;
  }

  .page-header,
  .header-actions,
  .turn-row,
  .upload-row {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-grid,
  .tool-grid {
    grid-template-columns: 1fr;
  }

  .header-actions,
  .button-row {
    width: 100%;
  }

  .header-actions button,
  .button-row button,
  .turn-row button {
    width: 100%;
  }
}
</style>
