<template>
  <div class="seating-img-only">
    <div class="seat-bg"></div>
    <img src="@/assets/VCC第五届掼蛋桌位图.png" alt="座位总览" class="big-seat-img" />
  </div>
</template>

<script setup>
// 无需逻辑
</script>

<style scoped>
.seating-img-only {
  position: relative;
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
  background: #101828;
}

.seat-bg {
  position: absolute;
  inset: 0;
  background-image: url("@/assets/VCC第五届掼蛋桌位图.png");
  background-size: cover;
  background-position: center;
  filter: blur(18px);
  opacity: 0.45;
  transform: scale(1.08);
}

.big-seat-img {
  position: relative;
  z-index: 1;
  width: calc(100% - 32px);
  height: calc(100% - 32px);
  margin: 16px;
  object-fit: contain;
  display: block;
}
</style>
