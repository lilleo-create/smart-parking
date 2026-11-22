import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { hasSession } from './data/session'
import App from './App.vue'
import Start from './pages/Start.vue'
import Auth from './pages/Auth.vue'
import ParkingPage from './pages/ParkingPage.vue'
import './styles/main.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'start', component: Start },
    { path: '/login', name: 'login', component: Auth },
    { path: '/register', name: 'register', component: Auth },
    {
      path: '/map',
      name: 'map',
      component: () => import('./pages/MapPage.vue'),
      meta: { auth: true },
    },
    { path: '/parkings/:id', name: 'parking', component: ParkingPage, meta: { auth: true } },
    {
      path: '/parkings/:id/:legacy(route|drive)',
      redirect: (to) => ({ name: 'parking', params: { id: to.params.id } }),
    },
    {
      path: '/parkings/:old(island|khodynka|krasnoselskaya|danilovsky)/:tail(drive|route)?',
      redirect: '/map',
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
router.beforeEach((to) => {
  if (to.meta.auth && !hasSession()) return { name: 'login', query: { next: to.fullPath } }
  if (hasSession() && ['start', 'login', 'register'].includes(String(to.name)))
    return { name: 'map' }
})
createApp(App).use(router).mount('#app')
