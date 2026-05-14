<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getAdminScoreMatch, submitAdminScore } from '@/api/admin.js'
import { getScoreTable, submitScoreTable } from '@/api/score.js'

const props = defineProps({
  turn: {
    type: String,
    required: true,
  },
  table: {
    type: String,
    required: true,
  },
})

const router = useRouter()
const isAdminMode = computed(() => router.currentRoute.value.query.mode === 'admin')

const loading = ref(false)
const submitting = ref(false)
const message = ref('')
const error = ref('')
const match = ref(null)
const form = reactive({
  scoreX: '',
  scoreY: '',
  winner: '',
})

const hasTieScore = computed(() => {
  const scoreX = Number(form.scoreX)
  const scoreY = Number(form.scoreY)
  return isValidScore(scoreX) && isValidScore(scoreY) && scoreX === scoreY
})

const pageTitle = computed(() => {
  const prefix = isAdminMode.value ? '后台改分' : '扫码录分'
  return `${prefix}：第 ${props.turn} 轮 ${props.table} 桌`
})

const isValidScore = (value) => Number.isInteger(value) && value >= 2 && value <= 32

const loadMatch = async () => {
  loading.value = true
  error.value = ''
  message.value = ''
  match.value = null

  try {
    const result = isAdminMode.value
      ? await getAdminScoreMatch({ turn: props.turn, table: props.table })
      : await getScoreTable(props.table)

    if (!result.ok) {
      error.value = result.message || result.error || '录分对阵加载失败'
      return
    }

    match.value = result.data || null
    message.value = result.message || '录分对阵已加载'
  } catch (err) {
    error.value = err.message || '录分对阵加载失败'
  } finally {
    loading.value = false
  }
}

const validateForm = () => {
  const scoreX = Number(form.scoreX)
  const scoreY = Number(form.scoreY)

  if (!isValidScore(scoreX) || !isValidScore(scoreY)) {
    return '请输入 2 到 32 之间的最终等级'
  }

  if (scoreX === scoreY && !form.winner) {
    return '双方最终等级相同，请选择最后一局赢家'
  }

  return ''
}

const submitScore = async () => {
  error.value = ''
  message.value = ''

  const validationError = validateForm()
  if (validationError) {
    error.value = validationError
    return
  }

  const payload = {
    table: props.table,
    score_x: Number(form.scoreX),
    score_y: Number(form.scoreY),
    winner: form.winner,
  }

  if (isAdminMode.value) {
    payload.turn = props.turn
  }

  submitting.value = true
  try {
    const result = isAdminMode.value
      ? await submitAdminScore(payload)
      : await submitScoreTable(payload)

    if (!result.ok) {
      error.value = result.message || result.error || '得分提交失败'
      return
    }

    message.value = result.message || '得分已提交'
  } catch (err) {
    error.value = err.message || '得分提交失败'
  } finally {
    submitting.value = false
  }
}

onMounted(loadMatch)
</script>

<template>
  <main class="score-page">
    <section class="score-panel">
      <div class="title-row">
        <div>
          <p class="eyebrow">{{ isAdminMode ? '后台管理' : '移动端录分' }}</p>
          <h1>{{ pageTitle }}</h1>
        </div>
        <button class="ghost-button" type="button" @click="router.push('/score')">
          返回入口
        </button>
      </div>

      <p v-if="loading" class="status muted">正在加载对阵信息...</p>
      <p v-else-if="error && !match" class="status error">{{ error }}</p>

      <form v-if="match" class="score-form" @submit.prevent="submitScore">
        <div class="match-grid">
          <article class="team-card">
            <span>甲方队伍</span>
            <strong>{{ match.team1_name }}</strong>
            <p>{{ match.team1_members }}</p>
          </article>
          <article class="team-card">
            <span>乙方队伍</span>
            <strong>{{ match.team2_name }}</strong>
            <p>{{ match.team2_members }}</p>
          </article>
        </div>

        <div class="score-grid">
          <label>
            <span>{{ match.team1_name }} 最终等级</span>
            <input
              v-model="form.scoreX"
              type="number"
              min="2"
              max="32"
              step="1"
              inputmode="numeric"
              placeholder="2~32"
            />
          </label>
          <label>
            <span>{{ match.team2_name }} 最终等级</span>
            <input
              v-model="form.scoreY"
              type="number"
              min="2"
              max="32"
              step="1"
              inputmode="numeric"
              placeholder="2~32"
            />
          </label>
        </div>

        <fieldset v-if="hasTieScore" class="winner-box">
          <legend>最后一局赢家</legend>
          <label>
            <input v-model="form.winner" type="radio" :value="match.team1_name" />
            <span>{{ match.team1_name }}</span>
          </label>
          <label>
            <input v-model="form.winner" type="radio" :value="match.team2_name" />
            <span>{{ match.team2_name }}</span>
          </label>
        </fieldset>

        <button class="submit-button" type="submit" :disabled="submitting">
          {{ submitting ? '提交中...' : '提交得分' }}
        </button>
      </form>

      <p v-if="error && match" class="status error">{{ error }}</p>
      <p v-else-if="message" class="status success">{{ message }}</p>
    </section>
  </main>
</template>

<style scoped>
.score-page {
  min-height: 100vh;
  padding: 32px 16px;
  background: linear-gradient(135deg, #f5f7fb 0%, #e8eef8 100%);
  color: #172033;
}

.score-panel {
  width: min(100%, 760px);
  margin: 0 auto;
  padding: 28px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 18px 45px rgba(23, 32, 51, 0.14);
}

.title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 14px;
  color: #53647f;
}

h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.25;
}

.ghost-button,
.submit-button {
  min-height: 44px;
  border: 0;
  border-radius: 8px;
  font-weight: 700;
  cursor: pointer;
}

.ghost-button {
  flex: 0 0 auto;
  padding: 0 16px;
  background: #edf2fa;
  color: #1f3556;
}

.submit-button {
  width: 100%;
  margin-top: 8px;
  background: #1f5fbf;
  color: #fff;
  font-size: 17px;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.score-form {
  display: grid;
  gap: 18px;
}

.match-grid,
.score-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.team-card {
  padding: 16px;
  border: 1px solid #d9e1ef;
  border-radius: 8px;
  background: #f8fbff;
}

.team-card span {
  display: block;
  margin-bottom: 8px;
  color: #53647f;
}

.team-card strong {
  display: block;
  margin-bottom: 8px;
  font-size: 22px;
}

.team-card p {
  margin: 0;
  line-height: 1.6;
  color: #33425c;
}

label {
  display: grid;
  gap: 8px;
  font-weight: 700;
}

input[type='number'] {
  width: 100%;
  box-sizing: border-box;
  padding: 13px 14px;
  border: 1px solid #c8d3e4;
  border-radius: 8px;
  font-size: 18px;
}

.winner-box {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid #d9e1ef;
  border-radius: 8px;
}

.winner-box legend {
  padding: 0 8px;
  font-weight: 700;
}

.winner-box label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
}

.status {
  margin: 16px 0 0;
  line-height: 1.5;
}

.muted {
  color: #53647f;
}

.success {
  color: #1f7a4d;
}

.error {
  color: #b42318;
}

@media (max-width: 640px) {
  .score-panel {
    padding: 22px;
  }

  .title-row,
  .match-grid,
  .score-grid {
    grid-template-columns: 1fr;
  }

  .title-row {
    display: grid;
  }

  .ghost-button {
    width: 100%;
  }
}
</style>
