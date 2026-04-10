<template>
  <div class="loading-container">
    <div class="spinner"></div>
    <h1 class="loading-title">数据加载中，请稍候…</h1>
  </div>
</template>

<script setup>
// 加载界面组件
</script>

<style scoped>
/* Loading 动画居中容器 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  color: #333;
}

.loading-title {
  font-size: 108px;
  font-weight: bold;
  color: #fff;
  text-shadow: 12px 12px 8px #2b4180;
  /* 文字阴影效果 */
}

.spinner {
  width: 250px;
  height: 250px;
  border: 25px solid rgba(0, 0, 0, 0.5);
  border-top-color: #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
