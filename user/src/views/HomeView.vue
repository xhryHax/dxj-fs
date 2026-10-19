<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import logoBig from '../assets/logo-big.svg'
import logoSmall from '../assets/logo-small.svg'

const router = useRouter()
const auth = useAuthStore()

const greeting = computed(() => {
  if (auth.user) {
    return `欢迎回来，${auth.user.userName || auth.user.email}`
  }
  return '登录以进入你的个人空间'
})

function go(target) {
  if (auth.isSystemAdmin && target === '/admin') {
    router.push('/admin')
    return
  }
  router.push(target)
}
</script>

<template>
  <div class="home">
    <header class="home-nav">
      <img :src="logoSmall" alt="云存储协作平台" class="nav-logo" />
      <span class="nav-brand">云存储协作平台</span>
    </header>

    <main class="home-main">
      <img :src="logoBig" alt="云存储协作平台" class="hero-logo" />
      <img :src="logoSmall" alt="云存储协作平台" class="nav-logo" />
      <p></p>
      <p></p>
      <h1 class="home-title">云文件协作平台</h1>
      <p class="home-desc">
        为团队协作打造的云端文件协作空间，上传、分享、按页面展示，一切井井有条。
      </p>

      <div class="home-entries">
        <div class="entry-card" @click="go('/login')">
          <img src="/img/userLogic.png" alt="用户登录、注册" class="entry-icon" />
          <h3>用户登录、注册</h3>
          <p>{{ greeting }}</p>
          <span class="entry-action">进入 →</span>
        </div>

        <div class="entry-card" @click="go('/admin/login')">
          <img src="/img/sysAdminLogic.png" alt="系统管理员登录" class="entry-icon" />
          <h3>系统管理员登录</h3>
          <p>管理在线用户、可访问域与组类</p>
          <span class="entry-action">进入 →</span>
        </div>
      </div>

      <p v-if="auth.user" class="home-back">
        <router-link :to="auth.isSystemAdmin ? '/admin' : '/profile'">
          {{ auth.isSystemAdmin ? '返回系统管理' : '返回个人中心' }}
        </router-link>
      </p>
    </main>
  </div>
</template>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.home-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 24px;
}
.nav-logo {
  height: 28px;
  width: auto;
}
.nav-brand {
  font-weight: 600;
  font-size: 19px;
}
.home-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 24px 80px;
}
.hero-logo {
  max-width: 320px;
  width: 80%;
  height: auto;
  margin-bottom: 32px;
}
.home-title {
  margin-bottom: 12px;
}
.home-desc {
  max-width: 480px;
  color: var(--text-secondary);
  margin-bottom: 40px;
}
.home-entries {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
  width: 100%;
  max-width: 680px;
}
.entry-card {
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-md);
  padding: 28px 24px;
  text-align: left;
  cursor: pointer;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.entry-card:hover {
  box-shadow: var(--shadow-focus);
  transform: translateY(-2px);
}
.entry-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
}
.entry-card h3 {
  margin: 12px 0 8px;
}
.entry-card p {
  margin: 0 0 16px;
  color: var(--text-secondary);
  font-size: 19px;
  min-height: 42px;
}
.entry-action {
  font-weight: 600;
  font-size: 19px;
}
.home-back {
  margin-top: 32px;
  font-size: 19px;
}
.home-back a {
  text-decoration: underline;
  text-underline-offset: 4px;
}
</style>
