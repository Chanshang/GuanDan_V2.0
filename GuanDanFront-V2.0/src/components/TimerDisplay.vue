<template>
  <div class="timer" @click="onTimerClick" style="cursor: pointer">
    <span v-if="timeinfo === TIME_MESSAGES.NOT_STARTED">
      {{ TIME_MESSAGES.NOT_STARTED }}
    </span>
    <span v-else> {{ UI_TEXT.TIME_REMAINING }}{{ timeinfo }} </span>
  </div>
</template>

<script setup>
import { TIME_MESSAGES, UI_TEXT } from "@/constants/index.js";

defineProps({
  timeinfo: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["timer-click"]);

const onTimerClick = () => {
  emit("timer-click");
};
</script>

<style scoped>
.timer {
  justify-self: end;
  max-width: 100%;
  font-size: clamp(24px, 3vw, 48px);
  line-height: 1.2;
  color: #fff;
  background-color: rgba(0, 0, 0, 0.5);
  padding: 6px 12px;
  border-radius: 8px;
  text-align: right;
  white-space: normal;
}
</style>
