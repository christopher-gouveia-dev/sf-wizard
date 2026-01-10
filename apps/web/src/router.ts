import { createRouter, createWebHistory } from 'vue-router'
import QueryPage from './pages/QueryPage.vue'
import DeployPage from './pages/DeployPage.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/query' },
    { path: '/query', component: QueryPage },
    { path: '/deploy', component: DeployPage }
  ]
})
