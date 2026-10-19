import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGroupStore } from '../stores/group'

const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue'), meta: { title: '首页' } },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { title: '登录 / 注册' } },
  { path: '/admin/login', name: 'admin-login', component: () => import('../views/AdminLoginView.vue'), meta: { title: '系统管理员登录' } },
  { path: '/profile', name: 'profile', component: () => import('../views/ProfileView.vue'), meta: { requiresAuth: true, title: '个人中心' } },
  { path: '/public-pages', name: 'public-pages', component: () => import('../views/PublicPagesView.vue'), meta: { requiresAuth: true, title: '访问公开页' } },
  { path: '/specific-pages', name: 'specific-pages', component: () => import('../views/SpecificPagesView.vue'), meta: { requiresAuth: true, title: '访问指定页' } },
  { path: '/group-space', name: 'group-space', component: () => import('../views/GroupSpaceView.vue'), meta: { requiresAuth: true, requiresGroup: true, title: '组空间' } },
  { path: '/group-space/public-control', name: 'public-control', component: () => import('../views/PublicControlView.vue'), meta: { requiresAuth: true, requiresGroup: true, requiresGroupAdmin: true, title: '公开页控制' } },
  { path: '/group-space/specific-control', name: 'specific-control', component: () => import('../views/SpecificControlView.vue'), meta: { requiresAuth: true, requiresGroup: true, requiresGroupAdmin: true, title: '指定页控制' } },
  { path: '/group-space/approvals', name: 'approvals', component: () => import('../views/ApprovalsView.vue'), meta: { requiresAuth: true, requiresGroup: true, requiresGroupAdmin: true, title: '审批加入请求' } },
  { path: '/admin', name: 'admin', component: () => import('../views/AdminDashboardView.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: '系统管理员' } },
  { path: '/admin/domains', name: 'admin-domains', component: () => import('../views/AdminDomainsView.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: '可访问域' } },
  { path: '/admin/groups', name: 'admin-groups', component: () => import('../views/AdminGroupsView.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: '组类' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  document.title = to.meta.title ? `${to.meta.title} · 云存储协作平台` : '云存储协作平台'

  // 需登录：未登录跳登录页，携带回跳地址
  if (to.meta.requiresAuth && !auth.user) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  // 系统管理员专属页面
  if (to.meta.requiresAdmin && !auth.isSystemAdmin) {
    return { name: 'admin-login' }
  }
  // 需已加入组
  if (to.meta.requiresGroup && !auth.user?.groupId) {
    return { name: 'profile' }
  }
  // 组管理员专属页面：先确保组管理员状态已加载
  if (to.meta.requiresGroupAdmin) {
    const group = useGroupStore()
    if (!group.groupId) await group.initGroup().catch(() => null)
    if (!group.isGroupAdmin) return { name: 'group-space' }
  }
  return true
})

export default router
