import { reactive, computed } from 'vue'
import { getDashboardSnapshot } from '@/api.js'
import { TURN_CONFIG, TEAM_DATA_CONFIG, TIME_MESSAGES } from '@/constants/index.js'

function isInvalidTurn(payload) {
  return payload?.error === TURN_CONFIG.INVALID_TURN_ERROR
}

function toArray(value) {
  return Array.isArray(value) ? value : []
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
  })

  const activityStarted = computed(() => state.turn !== TURN_CONFIG.INITIAL_TURN)
  const isLoading = computed(() => guandanDatas.matchDatas.length === 0)

  async function fetchAllData() {
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
        return false
      }

      state.turn = String(snapshot.TURN ?? TURN_CONFIG.INITIAL_TURN)
      state.timeinfo = snapshot.time_message ?? TIME_MESSAGES.NOT_STARTED

      const officeData = snapshot.officescore || {}
      const teamData = snapshot.sumteaminfo || {}

      guandanDatas.cur_officeScores = toArray(officeData.current_turn)
      guandanDatas.sum_officeScores = toArray(officeData.total_until_turn)
      guandanDatas.cur_teamScores = toArray(teamData.current_turn).slice(0, TEAM_DATA_CONFIG.MAX_TEAMS)
      guandanDatas.sum_teamScores = toArray(teamData.total_until_turn).slice(0, TEAM_DATA_CONFIG.MAX_TEAMS)
      guandanDatas.matchDatas = toArray(snapshot.matchesinfo)
      guandanDatas.scores = normalizeScores(snapshot.scoresinfo)

      return true
    } catch (error) {
      console.error('请求出错:', error)
      return false
    }
  }

  return {
    guandanDatas,
    state,
    activityStarted,
    isLoading,
    fetchAllData,
  }
}
