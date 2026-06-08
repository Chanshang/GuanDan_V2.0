import { reactive, computed, onMounted, onUnmounted } from 'vue'
import { getDashboardSnapshot } from '@/api.js'
import { TURN_CONFIG, TEAM_DATA_CONFIG, TIME_MESSAGES } from '@/constants/index.js'
import { sliceRotatingPage } from '@/utils/rankingRotation.js'

function isInvalidTurn(payload) {
  return payload?.error === TURN_CONFIG.INVALID_TURN_ERROR
}

function toArray(value) {
  return Array.isArray(value) ? value : []
}

function clearDashboardData(guandanDatas) {
  guandanDatas.matchDatas = []
  guandanDatas.scores = {}
  guandanDatas.cur_officeScores = []
  guandanDatas.sum_officeScores = []
  guandanDatas.cur_teamScores = []
  guandanDatas.sum_teamScores = []
}

function clearRankingData(rankingState) {
  rankingState.currentTeams = []
  rankingState.totalTeams = []
}

function normalizeScores(scoresinfo) {
  // 兼容后端返回数组结构：[[teamId, _, score], ...]
  if (Array.isArray(scoresinfo)) {
    return scoresinfo.reduce((acc, item) => {
      if (Array.isArray(item) && item.length >= 3) {
        const [group, , score] = item
        acc[group] = score
      }
      return acc
    }, {})
  }

  // 兼容后端直接返回对象映射：{ teamId: score }
  if (scoresinfo && typeof scoresinfo === 'object') {
    return scoresinfo
  }

  return {}
}

function parseNumber(value) {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
}

function formatCountdown(seconds) {
  const safeSeconds = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(safeSeconds / 60)
  const remainSeconds = safeSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(remainSeconds).padStart(2, '0')}`
}

export function useGuandanData() {
  const guandanDatas = reactive({
    matchDatas: [],
    scores: {},
    cur_officeScores: [],
    sum_officeScores: [],
    cur_teamScores: [],
    sum_teamScores: [],
  })

  const state = reactive({
    turn: TURN_CONFIG.INITIAL_TURN,
    timeinfo: TIME_MESSAGES.NOT_STARTED,
    hasFetchedSnapshot: false,
    lastError: '',
  })

  const timerState = reactive({
    startedAt: null,
    totalSeconds: 3600,
    serverTime: null,
    receivedAtMs: 0,
  })

  const rankingState = reactive({
    currentTeams: [],
    totalTeams: [],
  })

  const hasValidTurn = computed(() => state.turn !== TURN_CONFIG.INITIAL_TURN)
  const activityStarted = computed(
    () => state.hasFetchedSnapshot && hasValidTurn.value && guandanDatas.matchDatas.length > 0,
  )
  const isLoading = computed(() => !state.hasFetchedSnapshot)
  let requestInFlight = false
  let localTimerId = null

  function syncTimerState(snapshot) {
    const startedAt = parseNumber(snapshot.timer_started_at)
    const totalSeconds = parseNumber(snapshot.timer_total_seconds)
    const serverTime = parseNumber(snapshot.server_time)

    timerState.startedAt = startedAt
    timerState.totalSeconds = totalSeconds ?? 3600
    timerState.serverTime = serverTime ?? Date.now() / 1000
    timerState.receivedAtMs = Date.now()
  }

  function updateLocalCountdown() {
    if (!timerState.startedAt || !timerState.serverTime || !timerState.receivedAtMs) {
      return
    }

    const elapsedAfterFetch = (Date.now() - timerState.receivedAtMs) / 1000
    const estimatedServerNow = timerState.serverTime + elapsedAfterFetch
    const remainingSeconds = timerState.totalSeconds - (estimatedServerNow - timerState.startedAt)
    state.timeinfo = formatCountdown(remainingSeconds)
  }

  function updateLocalRankingPages(nowMs = Date.now()) {
    guandanDatas.cur_teamScores = sliceRotatingPage(
      rankingState.currentTeams,
      TEAM_DATA_CONFIG.MAX_TEAMS,
      TEAM_DATA_CONFIG.ROTATION_INTERVAL_MS,
      nowMs,
    )
    guandanDatas.sum_teamScores = sliceRotatingPage(
      rankingState.totalTeams,
      TEAM_DATA_CONFIG.MAX_TEAMS,
      TEAM_DATA_CONFIG.ROTATION_INTERVAL_MS,
      nowMs,
    )
  }

  async function fetchAllData() {
    if (requestInFlight) {
      return false
    }

    requestInFlight = true
    try {
      const snapshot = await getDashboardSnapshot()

      if (!snapshot || typeof snapshot !== 'object') {
        console.error('获取数据失败：dashboard_snapshot 返回结构无效')
        return false
      }

      if (
        isInvalidTurn(snapshot) ||
        isInvalidTurn(snapshot.officescore) ||
        isInvalidTurn(snapshot.sumteaminfo)
      ) {
        console.error('获取数据失败：当前轮次无效')
        state.hasFetchedSnapshot = true
        state.lastError = ''
        state.turn = TURN_CONFIG.INITIAL_TURN
        state.timeinfo = snapshot.time_message ?? TIME_MESSAGES.NOT_STARTED
        timerState.startedAt = null
        timerState.serverTime = null
        timerState.receivedAtMs = 0
        clearRankingData(rankingState)
        clearDashboardData(guandanDatas)
        return true
      }

      state.hasFetchedSnapshot = true
      state.lastError = ''
      state.turn = String(snapshot.TURN ?? TURN_CONFIG.INITIAL_TURN)
      state.timeinfo = snapshot.time_message ?? TIME_MESSAGES.NOT_STARTED
      syncTimerState(snapshot)
      updateLocalCountdown()

      const officeData = snapshot.officescore || {}
      const teamData = snapshot.sumteaminfo || {}
      rankingState.currentTeams = toArray(teamData.current_turn)
      rankingState.totalTeams = toArray(teamData.total_until_turn)

      guandanDatas.cur_officeScores = toArray(officeData.current_turn)
      guandanDatas.sum_officeScores = toArray(officeData.total_until_turn)
      updateLocalRankingPages()
      guandanDatas.matchDatas = toArray(snapshot.matchesinfo)
      guandanDatas.scores = normalizeScores(snapshot.scoresinfo)

      return true
    } catch (error) {
      console.error('请求出错:', error)
      state.lastError = error?.message || 'dashboard_snapshot 请求失败'
      return false
    } finally {
      requestInFlight = false
    }
  }

  onMounted(() => {
    localTimerId = window.setInterval(() => {
      updateLocalCountdown()
      updateLocalRankingPages()
    }, 1000)
  })

  onUnmounted(() => {
    if (localTimerId) {
      window.clearInterval(localTimerId)
      localTimerId = null
    }
  })

  return {
    guandanDatas,
    state,
    activityStarted,
    isLoading,
    fetchAllData,
  }
}
