<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { authApi } from '../api/auth'
import { useTeamStore } from '../stores/team'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const teamStore = useTeamStore()

const username = ref('')
const password = ref('')
const saving = ref(false)
const error = ref('')

async function submit() {
  if (!username.value.trim() || !password.value) {
    error.value = '请填写用户名与密码'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const payload = await authApi.login(username.value.trim(), password.value)
    userStore.signIn(payload)
    const teams = await teamStore.loadTeams()
    const next = route.query.next
    if (typeof next === 'string' && next.startsWith('/teams/')) {
      router.replace(next)
      return
    }
    const first = teams[0]
    if (first) {
      await teamStore.switchTeam(first.id, { reload: false })
      router.replace({ name: 'stories', params: { teamId: first.id } })
    } else {
      router.replace({ name: 'stories', params: { teamId: 0 } })
    }
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="login">
    <div class="login__intro">
      <div class="login__index u-mono">workspace / v0.1.0</div>
      <div class="login__mark"></div>
      <h1 class="display">协作平台</h1>
      <p class="login__lead">
        需求、代码与交付，在同一个工作区里协作。<br />
        组建团队、管理需求单、跟踪状态进展；分支查看、流水线与部署记录已在导航中留好位置。
      </p>
      <div class="login__note">
        <div class="u-label">关于演示数据</div>
        <p class="u-muted">
          本地演示账号由 seed_demo.py 生成，账号与口令见项目 README。<br />
          登录后可在顶部「团队与成员」里组建新团队。
        </p>
      </div>
    </div>

    <form class="login__form" @submit.prevent="submit">
      <div class="login__form-title heading-2">登录</div>
      <div class="field">
        <label class="field__label" for="login-user">用户名</label>
        <input
          id="login-user"
          v-model="username"
          class="underline-input"
          autocomplete="username"
          placeholder="用户名"
        />
      </div>
      <div class="field">
        <label class="field__label" for="login-pass">密码</label>
        <input
          id="login-pass"
          v-model="password"
          type="password"
          class="underline-input"
          autocomplete="current-password"
          placeholder="密码"
        />
      </div>
      <div v-if="error" class="field__error" style="margin-bottom: var(--space-4)">
        {{ error }}
      </div>
      <button class="btn btn--primary login__submit" type="submit" :disabled="saving">
        {{ saving ? '登录中…' : '进入工作区' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 7fr 5fr;
  gap: var(--gutter);
  padding: var(--space-16) var(--margin);
  max-width: var(--maxw);
  margin: 0 auto;
}
.login__intro {
  padding-top: var(--space-12);
  border-right: 1px solid var(--line-base);
  padding-right: var(--space-12);
}
.login__index {
  color: var(--ink-3);
  margin-bottom: var(--space-8);
}
.login__mark {
  width: 28px;
  height: 3px;
  background: var(--accent);
  margin-bottom: var(--space-6);
}
.login__lead {
  margin-top: var(--space-8);
  max-width: 40ch;
  line-height: 1.75;
  color: var(--ink-2);
}
.login__note {
  margin-top: var(--space-16);
  padding-top: var(--space-6);
  border-top: 1px solid var(--line-hair);
  max-width: 46ch;
}
.login__note p {
  margin-top: var(--space-2);
  font-size: var(--fs-body);
  line-height: 1.7;
}
.login__form {
  padding: var(--space-12) var(--space-8) 0;
  max-width: 380px;
}
.login__form-title {
  margin-bottom: var(--space-8);
}
.login__submit {
  width: 100%;
  min-height: 40px;
}
@media (max-width: 992px) {
  .login {
    grid-template-columns: 1fr;
    padding-top: var(--space-8);
  }
  .login__intro {
    border-right: 0;
    border-bottom: 1px solid var(--line-base);
    padding: 0 0 var(--space-8);
  }
  .login__note {
    margin-top: var(--space-8);
  }
  .login__form {
    padding: var(--space-8) 0 0;
    max-width: none;
  }
}
</style>
