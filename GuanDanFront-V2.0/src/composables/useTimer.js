import { ref, onMounted, onUnmounted } from 'vue'

export function useTimer(callback, interval = 2000) {
  const timerId = ref(null)

  // 启动定时器
  const startTimer = () => {
    if (timerId.value) return // 防止重复启动
    
    // 立即执行一次
    callback()
    
    // 设置定时器
    timerId.value = setInterval(callback, interval)
  }

  // 停止定时器
  const stopTimer = () => {
    if (timerId.value) {
      clearInterval(timerId.value)
      timerId.value = null
    }
  }

  // 重启定时器
  const restartTimer = () => {
    stopTimer()
    startTimer()
  }

  // 组件挂载时自动启动
  onMounted(() => {
    startTimer()
  })

  // 组件卸载时自动清理
  onUnmounted(() => {
    stopTimer()
  })

  return {
    timerId,
    startTimer,
    stopTimer,
    restartTimer,
  }
}
