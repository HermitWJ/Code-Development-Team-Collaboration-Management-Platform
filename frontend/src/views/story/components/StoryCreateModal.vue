<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import { codeApi } from '../../../api/code'
import { storyApi } from '../../../api/story'
import { STORY_TYPES } from '../../../config/constants'
import { useProjectStore } from '../../../stores/project'
import { useTeamStore } from '../../../stores/team'
import RichTextEditor from './RichTextEditor.vue'

const props = defineProps({ teamId: { type: Number, default: 0 } })
const emit = defineEmits(['close', 'created'])

const team = useTeamStore()
const project = useProjectStore()
const members = computed(() => team.members.map((row) => row.user))
const projects = ref([])

const form = ref({
  type: 'feat',
  title: '',
  description: '',
  assignee_id: '',
  priority: 'medium',
  project_id: project.currentProjectId || '',
  branch_name: '',
})
const saving = ref(false)
const error = ref('')

onMounted(async () => {
  form.value.project_id = project.currentProjectId || ''
  if (!props.teamId) return
  try {
    projects.value = await codeApi.projects(props.teamId)
  } catch {
    projects.value = []
  }
})

watch(
  () => project.epoch,
  () => {
    form.value.project_id = project.currentProjectId || ''
  }
)

async function submit() {
  if (!form.value.title.trim()) {
    error.value = '请填写需求标题'
    return
  }
  if (!props.teamId) {
    error.value = '请先创建或选择一个团队'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const payload = {
      type: form.value.type,
      title: form.value.title.trim(),
      description: form.value.description,
      assignee_id: form.value.assignee_id || null,
      priority: form.value.priority,
      project_id: form.value.project_id || null,
      branch_name: form.value.branch_name.trim(),
    }
    const created = await storyApi.create(props.teamId, payload)
    emit('created', created)
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Transition name="panel" appear>
    <div class="overlay overlay--modal" @click.self="emit('close')">
      <div class="modal">
        <div class="modal__head">
          <div>
            <div class="u-label">新建需求单</div>
            <div class="modal__title">写下要做的事</div>
          </div>
          <button class="btn btn--quiet btn--sm" @click="emit('close')">关闭 ×</button>
        </div>

        <p class="u-muted" style="margin-bottom: var(--space-8)">
          默认归属当前项目；说明栏支持图文与视频，需求单可绑定开发分支。
        </p>

        <form @submit.prevent="submit">
          <div class="field">
            <label class="field__label" for="create-type">需求类型 <em>*</em></label>
            <select id="create-type" v-model="form.type" class="underline-select">
              <option v-for="item in STORY_TYPES" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
            <div class="field__hint">类型决定 commit 标题前缀，如 feat / fix</div>
          </div>

          <div class="field">
            <label class="field__label" for="create-title">需求标题 <em>*</em></label>
            <input
              id="create-title"
              v-model="form.title"
              class="underline-input"
              placeholder="例如：支持导出月报"
              maxlength="200"
            />
          </div>

          <div class="field">
            <div class="field__label">说明</div>
            <RichTextEditor v-model="form.description" :team-id="teamId" />
            <div class="field__hint">像 Word 一样排版，可插入图片与视频；服务端会过滤危险内容</div>
          </div>

          <div class="field">
            <label class="field__label" for="create-project">所属项目</label>
            <select id="create-project" v-model="form.project_id" class="underline-select">
              <option value="">未指定</option>
              <option v-for="item in projects" :key="item.id" :value="item.id">
                {{ item.name }} ({{ item.slug }}) · {{ item.main_branch }}
              </option>
            </select>
            <div class="field__hint">默认当前项目；项目在「团队与项目管理 / 项目管理」维护</div>
          </div>

          <div class="field">
            <label class="field__label" for="create-branch">开发分支（可选）</label>
            <input
              id="create-branch"
              v-model="form.branch_name"
              class="underline-input u-mono"
              placeholder="feature/STAR-1024"
            />
            <div class="field__hint">绑定时自动把所选项目的 main 分支记录为基线</div>
          </div>

          <div class="meta-grid" style="margin-bottom: var(--space-6)">
            <div>
              <div class="field">
                <label class="field__label" for="create-assignee">负责人</label>
                <select
                  id="create-assignee"
                  v-model="form.assignee_id"
                  class="underline-select"
                >
                  <option value="">未指定</option>
                  <option v-for="user in members" :key="user.id" :value="user.id">
                    {{ user.display_name }}
                  </option>
                </select>
              </div>
            </div>
            <div>
              <div class="field">
                <label class="field__label" for="create-priority">优先级</label>
                <select
                  id="create-priority"
                  v-model="form.priority"
                  class="underline-select"
                >
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                  <option value="urgent">紧急</option>
                </select>
              </div>
            </div>
          </div>

          <div v-if="error" class="field__error" style="margin-bottom: var(--space-4)">
            {{ error }}
          </div>

          <div class="create-actions">
            <button type="button" class="btn btn--quiet" @click="emit('close')">取消</button>
            <button type="submit" class="btn btn--primary" :disabled="saving">
              {{ saving ? '保存中…' : '创建需求单' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.create-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding-top: var(--space-4);
  border-top: 1px solid var(--line-hair);
}
</style>
