<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { toast } from '../stores/toast'
import Card from '../components/ui/Card.vue'
import Input from '../components/ui/Input.vue'
import Button from '../components/ui/Button.vue'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({ id: '', password: '' })
const loading = ref(false)

async function handleLogin() {
  if (!form.id || !form.password) {
    toast('请输入用户 id 与密码', 'warning')
    return
  }
  loading.value = true
  try {
    await auth.adminLogin(form.id, form.password)
    toast('管理员登录成功', 'success')
    router.push('/admin')
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="admin-login-page">
    <div class="admin-login-wrap">
      <router-link to="/" class="login-back">← 返回首页</router-link>

      <Card class="admin-login-card">
        <h2 class="title">系统管理员登录</h2>
        <p class="desc">仅限系统管理员使用，请输入你的用户 id 与密码。</p>

        <form class="form" @submit.prevent="handleLogin">
          <Input v-model="form.id" label="用户 id" placeholder="请输入用户 id" required />
          <Input
            v-model="form.password"
            label="密码"
            placeholder="请输入密码"
            type="password"
            required
            autocomplete="current-password"
          />
          <Button type="submit" :loading="loading" block size="lg">登录</Button>
        </form>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.admin-login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
}
.admin-login-wrap {
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
.admin-login-card {
  padding: 32px;
}
.title {
  margin-bottom: 8px;
}
.desc {
  color: var(--text-secondary);
  font-size: 19px;
  margin-bottom: 24px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
