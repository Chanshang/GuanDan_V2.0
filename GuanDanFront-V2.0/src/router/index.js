import { createRouter, createWebHistory } from 'vue-router'
import ScreenView from '@/views/ScreenView.vue'
import AdminView from '@/views/AdminView.vue'
import ScoreEntryView from '@/views/ScoreEntryView.vue'
import ScoreFormView from '@/views/ScoreFormView.vue'

const routes = [
  { path: '/', redirect: '/screen' },
  { path: '/screen', name: 'screen', component: ScreenView },
  { path: '/admin', name: 'admin', component: AdminView },
  { path: '/score', name: 'score-entry', component: ScoreEntryView },
  { path: '/score/:turn/:table', name: 'score-form', component: ScoreFormView, props: true },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
