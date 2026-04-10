<template>
  <div class="extra-info">
    <p class="extra-title">扫我计分</p>
    <img src="/src/assets/深色二维码.png" alt="计分二维码" />
  </div>
</template>

<script setup>
// QR码组件
</script>

<style scoped>
/* 扫码计分移动到右下角 */
.extra-info {
  position: absolute;
  bottom: 35px;
  right: 655px;
  width: 20%;
}

.extra-info img {
  width: 75%;
  display: block;
  margin: auto;
}

.extra-title {
  text-align: center;
  font-size: 25px;
  font-weight: bold;
  color: #fff;
  text-shadow: 12px 12px 8px #2b4180;
  margin-bottom: 0px;
}
/* .extra-info {
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.extra-title {
  font-size: 1.2rem;
  font-weight: bold;
  color: #333;
  margin-bottom: 15px;
}

.extra-info img {
  max-width: 200px;
  height: auto;
  border-radius: 8px;
} */
</style>
