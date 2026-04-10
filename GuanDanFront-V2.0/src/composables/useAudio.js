import { ref } from 'vue'
import { AUDIO_PATHS, TIME_MESSAGES } from '@/constants/index.js'

export function useAudio() {
  const audioContext = ref(null)
  const fiveMinuteWarningPlayed = ref({}) // 标记是否播放过5分钟提醒

  // 初始化 AudioContext
  const initAudioContext = () => {
    audioContext.value = new AudioContext()
  }

  // 使用 Web Audio API 播放声音
  const playSoundWebAudio = async (soundFile) => {
    if (!audioContext.value) {
      initAudioContext()
    }
    try {
      // 检查 AudioContext 的状态，如果 suspended 则恢复
      if (audioContext.value.state === "suspended") {
        await audioContext.value.resume()
      }

      const response = await fetch(soundFile)
      const arrayBuffer = await response.arrayBuffer()
      const audioBuffer = await audioContext.value.decodeAudioData(arrayBuffer)
      const source = audioContext.value.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioContext.value.destination)
      source.start()
    } catch (error) {
      console.error("Error playing sound with Web Audio API:", error)
    }
  }

  // 语音合成
  const speak = (text) => {
    const synth = window.speechSynthesis
    const utterance = new SpeechSynthesisUtterance(text)
    synth.speak(utterance)
  }

  // 检查并播放5分钟警告
  const checkAndPlayFiveMinuteWarning = (timeinfo, turn) => {
    if (timeinfo === TIME_MESSAGES.FIVE_MINUTE_WARNING && !fiveMinuteWarningPlayed.value[turn]) {
      playSoundWebAudio(AUDIO_PATHS.FIVE_MINUTE_WARNING)
      fiveMinuteWarningPlayed.value[turn] = true
    }
  }

  // 测试音频播放
  const testAudio = async () => {
    await playSoundWebAudio(AUDIO_PATHS.FIVE_MINUTE_WARNING)
  }

  return {
    audioContext,
    fiveMinuteWarningPlayed,
    playSoundWebAudio,
    speak,
    checkAndPlayFiveMinuteWarning,
    testAudio,
  }
}
