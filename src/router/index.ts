import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/pages/HomePage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/v2', redirect: '/' },
    {
      path: '/studio',
      name: 'studio',
      component: () => import('@/pages/StudioPage.vue'),
    },
    {
      path: '/works',
      name: 'works',
      component: () => import('@/pages/WorksPage.vue'),
    },
    {
      path: '/template-import',
      name: 'template-import',
      component: () => import('@/pages/TemplateImportPage.vue'),
    },
    {
      path: '/template-generate',
      name: 'template-generate',
      component: () => import('@/pages/TemplateGeneratePage.vue'),
    },
  ],
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition ?? { top: 0 }
  },
})

export default router
