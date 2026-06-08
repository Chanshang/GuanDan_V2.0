<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCurrentScoreTurn } from '@/api/score.js'

const router = useRouter()

const loading = ref(false)
const entering = ref(false)
const message = ref('')
const error = ref('')
const currentTurn = ref('')
const table = ref('')

const canEnter = computed(() => currentTurn.value && table.value.trim())

const loadCurrentTurn = async () => {
  loading.value = true
  error.value = ''
  message.value = ''

  try {
    const result = await getCurrentScoreTurn()
    if (!result.ok) {
      error.value = result.message || result.error || '当前轮次加载失败'
      currentTurn.value = ''
      return
    }

    currentTurn.value = String(result.data?.turn || '')
    message.value = result.message || '当前轮次加载成功'
  } catch (err) {
    error.value = err.message || '当前轮次加载失败'
    currentTurn.value = ''
  } finally {
    loading.value = false
  }
}

const enterScoreForm = () => {
  error.value = ''
  const tableValue = table.value.trim()

  if (!currentTurn.value) {
    error.value = '当前轮次未设置，暂不能录分'
    return
  }

  if (!tableValue || !/^\d+$/.test(tableValue)) {
    error.value = '请输入有效桌号'
    return
  }

  entering.value = true
  router.push(`/score/${currentTurn.value}/${tableValue}`).finally(() => {
    entering.value = false
  })
}

onMounted(loadCurrentTurn)
</script>

<template>
  <main class="score-page">
    <section class="score-panel">
      <p class="eyebrow">赛事录分</p>
      <h1>扫码录分入口</h1>

      <div class="turn-card">
        <span>当前轮次</span>
        <strong v-if="currentTurn">第 {{ currentTurn }} 轮</strong>
        <strong v-else>未设置</strong>
      </div>

      <form class="entry-form" @submit.prevent="enterScoreForm">
        <label for="score-table">桌号</label>
        <input
          id="score-table"
          v-model="table"
          inputmode="numeric"
          autocomplete="off"
          placeholder="请输入桌号"
          :disabled="loading || entering"
        />

        <button type="submit" :disabled="loading || entering || !canEnter">
          {{ entering ? '进入中...' : '进入录分' }}
        </button>
      </form>

      <button class="secondary-button" type="button" :disabled="loading || entering" @click="loadCurrentTurn">
        重新加载轮次
      </button>

      <p v-if="loading" class="status muted">正在加载当前轮次...</p>
      <p v-else-if="error" class="status error">{{ error }}</p>
      <p v-else-if="message" class="status success">{{ message }}</p>
    </section>
  </main>
</template>

<style scoped>
.score-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 16px;
  background: linear-gradient(135deg, #f5f7fb 0%, #e8eef8 100%);
  color: #172033;
}

.score-panel {
  width: min(100%, 460px);
  padding: 28px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 18px 45px rgba(23, 32, 51, 0.14);
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 14px;
  color: #53647f;
}

h1 {
  margin: 0 0 24px;
  font-size: 30px;
  line-height: 1.2;
}

.turn-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  margin-bottom: 22px;
  border: 1px solid #d9e1ef;
  border-radius: 8px;
  background: #f8fbff;
}

.turn-card span {
  color: #53647f;
}

.turn-card strong {
  font-size: 22px;
}

.entry-form {
  display: grid;
  gap: 12px;
}

label {
  font-weight: 700;
}

input {
  width: 100%;
  box-sizing: border-box;
  padding: 13px 14px;
  border: 1px solid #c8d3e4;
  border-radius: 8px;
  font-size: 18px;
}

button {
  width: 100%;
  min-height: 46px;
  border: 0;
  border-radius: 8px;
  background: #1f5fbf;
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.secondary-button {
  margin-top: 12px;
  background: #edf2fa;
  color: #1f3556;
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
</style>
