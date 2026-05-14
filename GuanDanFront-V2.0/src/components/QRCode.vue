<script setup>
import qrCodeImage from '@/assets/深色二维码.png'
</script>

<template>
  <div class="extra-info">
    <p class="extra-title">扫码计分</p>
    <img :src="qrCodeImage" alt="计分二维码" />
    <a class="score-link" href="/score">扫码录分入口</a>
  </div>
</template>

<style scoped>
/* 扫码计分入口固定在大屏右下区域，保留原二维码展示。 */
.extra-info {
  position: absolute;
  bottom: 35px;
  right: 655px;
  width: 20%;
  text-align: center;
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
  margin-bottom: 0;
}

.score-link {
  display: inline-block;
  max-width: 88%;
  margin-top: 10px;
  padding: 7px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  color: #17305f;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.3;
  text-decoration: none;
  box-shadow: 0 4px 14px rgba(15, 28, 58, 0.22);
}

.score-link:hover,
.score-link:focus {
  background: #fff;
  color: #0b55b7;
}
</style>
