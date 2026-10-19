<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { toast } from '../stores/toast'
import Card from '../components/ui/Card.vue'
import Input from '../components/ui/Input.vue'
import Button from '../components/ui/Button.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const mode = ref('login') // login | register
const loading = ref(false)

const loginForm = reactive({ email: '', password: '' })
const registerForm = reactive({ userName: '', email: '', password: '' })

function switchMode(m) {
  mode.value = m
}

async function handleLogin() {
  if (!loginForm.email || !loginForm.password) {
    toast('请输入用户名与密码', 'warning')
    return
  }
  loading.value = true
  try {
    await auth.login(loginForm.email, loginForm.password)
    toast('登录成功', 'success')
    const redirect = route.query.redirect
    router.push(typeof redirect === 'string' ? redirect : '/profile')
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!registerForm.userName || !registerForm.email || !registerForm.password) {
    toast('请填写完整的注册信息', 'warning')
    return
  }
  if (registerForm.password.length < 6) {
    toast('密码长度至少为 6 位', 'warning')
    return
  }
  loading.value = true
  try {
    await auth.register(registerForm)
    toast('注册成功，已自动登录', 'success')
    router.push('/profile')
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-wrap">
      <router-link to="/" class="login-back">← 返回首页</router-link>

      <Card class="login-card">
        <h2 class="login-title">{{ mode === 'login' ? '用户登录' : '注册账户' }}</h2>

        <div class="login-tabs">
          <button
            class="tab"
            :class="{ 'tab--active': mode === 'login' }"
            @click="switchMode('login')"
          >
            登录
          </button>
          <button
            class="tab"
            :class="{ 'tab--active': mode === 'register' }"
            @click="switchMode('register')"
          >
            注册
          </button>
        </div>

        <form v-if="mode === 'login'" class="login-form" @submit.prevent="handleLogin">
          <Input
            v-model="loginForm.email"
            label="用户名（邮箱）"
            placeholder="请输入登录邮箱"
            type="email"
            required
            autocomplete="username"
          />
          <Input
            v-model="loginForm.password"
            label="密码"
            placeholder="请输入密码"
            type="password"
            required
            autocomplete="current-password"
          />
          <Button type="submit" :loading="loading" block size="lg">登录</Button>
        </form>

        <form v-else class="login-form" @submit.prevent="handleRegister">
          <Input
            v-model="registerForm.userName"
            label="用户名"
            placeholder="你的展示名称"
            required
          />
          <Input
            v-model="registerForm.email"
            label="邮箱"
            placeholder="用于登录的邮箱地址"
            type="email"
            required
            autocomplete="username"
          />
          <Input
            v-model="registerForm.password"
            label="密码"
            placeholder="至少 6 位"
            type="password"
            required
            autocomplete="new-password"
          />
          <Button type="submit" :loading="loading" block size="lg">注册并登录</Button>
        </form>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
}
.login-wrap {
  width: 100%;
  max-width: 420px;
}
.login-back {
  display: inline-block;
  margin-bottom: 16px;
  font-size: 19px;
  color: var(--text-secondary);
}
.login-back:hover {
  color: var(--text-primary);
}
.login-card {
  padding: 32px;
}
.login-title {
  margin-bottom: 20px;
}
.login-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  background: rgba(28, 28, 28, 0.04);
  border-radius: var(--radius-sm);
  padding: 4px;
}
.tab {
  flex: 1;
  padding: 8px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 19px;
  cursor: pointer;
  color: var(--text-secondary);
}
.tab--active {
  background: var(--bg-offwhite);
  color: var(--text-primary);
  box-shadow: var(--shadow-focus);
}
.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
