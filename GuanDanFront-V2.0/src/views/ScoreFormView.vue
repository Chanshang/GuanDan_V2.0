<script setup>
defineProps({
  turn: {
    type: String,
    required: true,
  },
  table: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <main class="score-page">
    <h1>第 {{ turn }} 轮 {{ table }} 桌录分</h1>
  </main>
</template>
