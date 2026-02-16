import { createRouter, createWebHistory } from 'vue-router'

import AppShell from '../components/layout/AppShell.vue'
import { useAuthStore } from '../stores/auth'
import DashboardView from '../views/DashboardView.vue'
import GiftCreateView from '../views/GiftCreateView.vue'
import GiftEditView from '../views/GiftEditView.vue'
import GiftView from '../views/GiftView.vue'
import JumpPageManageView from '../views/JumpPageManageView.vue'
import LoginView from '../views/LoginView.vue'
import LogsView from '../views/LogsView.vue'
import RedPacketStyleManageView from '../views/RedPacketStyleManageView.vue'
import RedPacketImportView from '../views/RedPacketImportView.vue'
import RedPacketView from '../views/RedPacketView.vue'
import SecurityView from '../views/SecurityView.vue'
import SystemConfigView from '../views/SystemConfigView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true },
    },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', name: 'dashboard', component: DashboardView },
        { path: 'gifts', name: 'gifts', component: GiftView },
        { path: 'gifts/create', name: 'giftCreate', component: GiftCreateView },
        { path: 'gifts/:id/edit', name: 'giftEdit', component: GiftEditView },
        { path: 'red-packets', name: 'redPackets', component: RedPacketView },
        { path: 'red-packets/import', name: 'redPacketImport', component: RedPacketImportView },
        { path: 'jump-pages', name: 'jumpPages', component: JumpPageManageView },
        {
          path: 'red-packet-styles',
          name: 'redPacketStyles',
          component: RedPacketStyleManageView,
        },
        { path: 'security', name: 'security', component: SecurityView },
        { path: 'logs', name: 'logs', component: LogsView },
        { path: 'system-config', name: 'systemConfig', component: SystemConfigView },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  if (to.meta.public) {
    if (to.path === '/login' && authStore.isAuthed) {
      return '/'
    }
    return true
  }

  if (!authStore.isAuthed) {
    return '/login'
  }

  return true
})

export default router
