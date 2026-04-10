<template>
  <div class="seating-img-only">
    <img src="@/assets/第四届新新座位表.png" alt="座位总览" class="big-seat-img" />
  </div>
</template>

<script setup>
// 无需逻辑
</script>

<style scoped>
.seating-img-only {
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden; /* 避免滚动条 */
}

.big-seat-img {
  width: 100%;
  height: 100%;
  object-fit: cover; /* 铺满屏幕，保持比例，可能裁剪 */
  display: block;
}
</style>