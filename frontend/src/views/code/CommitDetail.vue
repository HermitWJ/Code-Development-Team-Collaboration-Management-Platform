<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { codeApi } from '../../api/code'
import { formatTime } from '../../config/constants'
import { useProjectStore } from '../../stores/project'

const route = useRoute()
const router = useRouter()
const project = useProjectStore()

const teamId = computed(() => Number(route.params.teamId) || 0)
const sha = computed(() => route.params.sha || '')
const detail = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  if (!teamId.value || !sha.value) return
  loading.value = true
  try {
    detail.value = await codeApi.commit(
      teamId.value,
      sha.value,
      project.currentProjectId
    )
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch([sha, () => project.epoch], load)

function openStory() {
  if (!detail.value?.story_brief?.id) return
  router.push({
    name: 'stories',
    params: { teamId: teamId.value },
    query: { story: detail.value.story_brief.id },
  })
}
</script>

<template>
  <div class="page">
    <div class="page__head">
      <div>
        <nav class="u-label page__crumb">协作平台 / 代码工程 / 代码提交 / commit 详情</nav>
        <h1 class="display">Commit 详情</h1>
        <p class="u-muted page__lead">
          {{ project.currentProject?.name || '当前项目' }} 下，开发分支相对 main 基线的一条新增提交。
        </p>
      </div>
      <button class="btn btn--sm" @click="router.push({ name: 'code-commits', params: { teamId } })">
        ← 返回提交列表
      </button>
    </div>
    <div class="page__rule"></div>

    <div v-if="error" class="state-block">
      <div class="state-block__title">commit 详情没能加载</div>
      <div class="state-block__desc">{{ error }}</div>
      <button class="btn" @click="load">重试加载</button>
    </div>
    <div v-else-if="loading && !detail" class="state-block">
      <div class="state-block__desc">正在读取 commit 详情…</div>
    </div>

    <template v-else-if="detail">
      <section class="card">
        <div class="card__head">
          <div>
            <span class="u-label">SHA</span>
            <div class="sha u-mono">{{ detail.sha }}</div>
          </div>
          <span class="u-mono chip">{{ detail.short_sha }}</span>
        </div>
        <h2 class="commit-title">{{ detail.title }}</h2>
        <pre v-if="detail.message" class="message">{{ detail.message }}</pre>

        <div class="meta-grid">
          <div>
            <div class="meta-grid__key">所属项目</div>
            <div class="meta-grid__value">{{ detail.project_name }}</div>
          </div>
          <div>
            <div class="meta-grid__key">开发分支 → 基线</div>
            <div class="meta-grid__value u-mono">{{ detail.branch_name }} ← {{ detail.base_branch }}</div>
          </div>
          <div>
            <div class="meta-grid__key">作者</div>
            <div class="meta-grid__value">{{ detail.author || '—' }}</div>
          </div>
          <div>
            <div class="meta-grid__key">提交时间</div>
            <div class="meta-grid__value u-mono">{{ formatTime(detail.committed_at) }}</div>
          </div>
          <div>
            <div class="meta-grid__key">关联需求单</div>
            <div class="meta-grid__value">
              <button v-if="detail.story_brief?.id" class="btn btn--quiet btn--sm u-mono" @click="openStory">
                {{ detail.story_brief.story_no }} · {{ detail.story_brief.title }} ↗
              </button>
              <span v-else>—</span>
            </div>
          </div>
          <div>
            <div class="meta-grid__key">变更统计</div>
            <div class="meta-grid__value u-mono">
              <span class="add">+{{ detail.additions }}</span> /
              <span class="del">−{{ detail.deletions }}</span> ·
              {{ detail.files_changed }} 个文件
            </div>
          </div>
        </div>

        <div class="card__actions">
          <a v-if="detail.repo_links?.repo" :href="detail.repo_links.repo" target="_blank" rel="noopener" class="btn btn--sm">
            打开仓库 ↗
          </a>
          <a v-if="detail.repo_links?.branch" :href="detail.repo_links.branch" target="_blank" rel="noopener" class="btn btn--sm">
            打开分支 ↗
          </a>
          <a v-if="detail.repo_links?.compare" :href="detail.repo_links.compare" target="_blank" rel="noopener" class="btn btn--sm">
            分支对比 ↗
          </a>
          <a v-if="detail.repo_links?.commit" :href="detail.repo_links.commit" target="_blank" rel="noopener" class="btn btn--primary btn--sm">
            在仓库中查看 commit ↗
          </a>
        </div>
      </section>

      <section class="card note">
        <div class="u-label">数据来源</div>
        <p class="u-muted">
          这里的记录来自当前项目下开发分支相对 main 基线的新增提交：可批量导入，或在项目配置本地仓库路径后按
          <span class="u-mono">git log main..分支</span> 同步。外链按项目仓库地址生成，不连接远程、不保存凭证。
        </p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: var(--maxw);
  margin: 0 auto;
  padding: var(--space-12) var(--margin) var(--space-16);
}
.page__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--gutter);
  padding-bottom: var(--space-8);
}
.page__crumb { margin-bottom: var(--space-4); }
.page__lead { margin-top: var(--space-2); }
.page__rule { height: 2px; background: var(--line-base); margin-bottom: var(--space-8); }
.card {
  border: 1px solid var(--line-base);
  background: var(--bg-surface);
  padding: var(--space-6);
  margin-bottom: var(--space-6);
}
.card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--line-hair);
  margin-bottom: var(--space-6);
}
.sha { font-size: var(--fs-h2); line-height: var(--lh-h2); word-break: break-all; }
.chip {
  padding: 2px 8px;
  border: 1px solid var(--accent);
  color: var(--accent);
}
.commit-title { font-size: var(--fs-h2); line-height: var(--lh-h2); margin-bottom: var(--space-4); }
.message {
  margin: 0 0 var(--space-6);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-sunken);
  font-family: var(--font-ui);
  font-size: var(--fs-body);
  white-space: pre-wrap;
  color: var(--ink-2);
}
.card__actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-8);
  padding-top: var(--space-4);
  border-top: 1px solid var(--line-hair);
}
.card__actions a { text-decoration: none; }
.add { color: var(--status-released); }
.del { color: var(--signal-error); }
.note p { margin-top: var(--space-2); line-height: 1.7; }
@media (max-width: 992px) {
  .page__head { flex-direction: column; align-items: flex-start; }
}
</style>
