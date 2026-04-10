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
  position: absolute;
  top: 10px;
  right: 10px;
  font-size: 48px;
  color: #fff;
  background-color: rgba(0, 0, 0, 0.5);
  padding: 5px;
  border-radius: 5px;
}
</style>
