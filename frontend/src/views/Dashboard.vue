<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { storyApi } from '../api/story'
import {
  PRIORITY_LABELS,
  STATUS_GLYPHS,
  STATUS_LABELS,
  STATUS_TONES,
  formatTime,
} from '../config/constants'
import { useProjectStore } from '../stores/project'
import { useTeamStore } from '../stores/team'
import { useToastStore } from '../stores/toast'

const route = useRoute()
const router = useRouter()
const team = useTeamStore()
const project = useProjectStore()
const toast = useToastStore()

const stats = ref(null)
const loading = ref(false)
const error = ref('')

const teamId = computed(() => Number(route.params.teamId) || 0)
const CIRCUMFERENCE = 2 * Math.PI * 54

const TONE_VARS = {
  planning: '--status-planning',
  developing: '--status-developing',
  pending_test: '--status-pending-test',
  pending_accept: '--status-pending-accept',
  released: '--status-released',
  cancelled: '--status-branch',
  suspended: '--status-branch',
}

function toneVar(status) {
  return `var(${TONE_VARS[status] || '--status-planning'})`
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

function percent(value) {
  return `${Math.round((value || 0) * 100)}%`
}

async function load() {
  // 没有当前项目时不请求全团队数据，避免看板跨项目混杂
  if (!teamId.value || !project.currentProjectId) {
    stats.value = null
    error.value = ''
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    stats.value = await storyApi.stats(teamId.value, {
      project_id: project.currentProjectId,
    })
  } catch (err) {
    error.value = err.message
    toast.notify(err.message, { tone: 'error' })
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => team.epoch, load)
watch(() => project.epoch, load)
watch(teamId, load)

const kpis = computed(() => {
  const data = stats.value || {}
  return [
    { key: 'total', label: '需求总数', value: data.total ?? '—', color: 'var(--ink)' },
    { key: 'in_progress', label: '进行中', value: data.in_progress ?? '—', color: 'var(--status-developing)' },
    { key: 'pending_accept', label: '待验收', value: data.pending_accept ?? '—', color: 'var(--status-pending-accept)' },
    { key: 'released', label: '已发布', value: data.released ?? '—', color: 'var(--status-released)' },
    { key: 'rate', label: '完成率', value: percent(data.completion_rate), color: 'var(--accent)' },
  ]
})

const donutSegments = computed(() => {
  const rows = stats.value?.status_distribution || []
  const total = rows.reduce((sum, row) => sum + row.count, 0)
  let offset = 0
  return rows
    .filter((row) => row.count > 0)
    .map((row) => {
      const length = total ? (row.count / total) * CIRCUMFERENCE : 0
      const segment = { ...row, length, offset, color: toneVar(row.status) }
      offset += length
      return segment
    })
})

const trend = computed(() => stats.value?.trend || [])
const trendMax = computed(() =>
  Math.max(1, ...trend.value.flatMap((day) => [day.created, day.released]))
)
const memberMax = computed(() =>
  Math.max(1, ...(stats.value?.member_load || []).map((row) => row.total))
)
const priorityMax = computed(() =>
  Math.max(1, ...(stats.value?.priority_distribution || []).map((row) => row.count))
)
const mine = computed(() => stats.value?.mine || null)
const mineTotal = computed(() =>
  Math.max(1, ...(mine.value?.status_distribution || []).map((row) => row.count))
)
const mineSegments = computed(() =>
  (mine.value?.status_distribution || []).filter((row) => row.count > 0)
)
</script>

<template>
  <div class="board">
    <div class="board__head">
      <div>
        <nav class="u-label board__crumb">协作平台 / 工作台 / 工作看板</nav>
        <h1 class="display">工作看板</h1>
        <p class="u-muted board__lead">当前项目下，整个团队在做什么、我做完了什么，一屏看清。</p>
      </div>
      <div class="board__head-right">
        <div class="board__scope">
          <span class="u-label">团队</span>
          <span>{{ team.currentTeam?.name || '—' }}</span>
        </div>
        <div class="board__scope">
          <span class="u-label">项目</span>
          <span class="board__project">{{ project.currentProject?.name || '未选择' }}</span>
        </div>
        <button class="btn btn--sm" :disabled="loading" @click="load">
          {{ loading ? '刷新中…' : '刷新数据' }}
        </button>
      </div>
    </div>
    <div class="board__rule"></div>

    <div v-if="error" class="state-block">
      <div class="state-block__title">看板没能加载</div>
      <div class="state-block__desc">{{ error }}</div>
      <button class="btn" @click="load">重试加载</button>
    </div>

    <div v-else-if="!project.currentProjectId" class="state-block">
      <div class="state-block__title">还没有选择项目</div>
      <div class="state-block__desc">
        看板按当前项目隔离。请在顶部下拉选择项目，或到「团队与项目管理 / 项目管理」创建。
      </div>
      <button
        class="btn btn--primary"
        @click="router.push({ name: 'projects', params: { teamId } })"
      >
        前往项目管理
      </button>
    </div>

    <div v-else-if="!stats && loading" class="state-block">
      <div class="state-block__desc">正在汇总当前项目与个人的指标…</div>
    </div>

    <template v-else-if="stats">
      <!-- 团队 KPI -->
      <div class="kpi-grid">
        <div v-for="item in kpis" :key="item.key" class="kpi">
          <div class="kpi__label u-label">{{ item.label }}</div>
          <div class="kpi__value u-num" :style="{ color: item.color }">{{ item.value }}</div>
        </div>
      </div>

      <div class="board__grid">
        <!-- 状态分布 -->
        <section class="card">
          <div class="card__head">
            <h2 class="card__title">01 / 状态分布</h2>
            <span class="u-label">主线五态 · 旁路两态</span>
          </div>
          <div class="donut-wrap">
            <svg class="donut" viewBox="0 0 140 140" role="img" aria-label="需求状态分布环形图">
              <circle cx="70" cy="70" r="54" fill="none" stroke="var(--line-hair)" stroke-width="16" />
              <circle
                v-for="segment in donutSegments"
                :key="segment.status"
                cx="70" cy="70" r="54"
                fill="none"
                :stroke="segment.color"
                stroke-width="16"
                :stroke-dasharray="`${segment.length} ${CIRCUMFERENCE - segment.length}`"
                :stroke-dashoffset="`-${segment.offset}`"
                transform="rotate(-90 70 70)"
              />
              <text x="70" y="68" text-anchor="middle" class="donut__num">{{ stats.total }}</text>
              <text x="70" y="88" text-anchor="middle" class="donut__label">需求总数</text>
            </svg>
            <div class="legend">
              <div
                v-for="row in stats.status_distribution"
                :key="row.status"
                class="legend__row"
              >
                <span class="legend__dot" :style="{ background: toneVar(row.status) }"></span>
                <span class="status-chip" :data-tone="STATUS_TONES[row.status]">
                  <span class="status-chip__glyph">{{ STATUS_GLYPHS[row.status] }}</span>
                  {{ statusLabel(row.status) }}
                </span>
                <span class="legend__num u-num">{{ row.count }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 近 7 天趋势 -->
        <section class="card">
          <div class="card__head">
            <h2 class="card__title">02 / 近 7 天趋势</h2>
            <span class="u-label">
              <span class="legend__dot legend__dot--inline" style="background: var(--status-developing)"></span>
              新建
              <span class="legend__dot legend__dot--inline" style="background: var(--status-released)"></span>
              发布
            </span>
          </div>
          <svg class="trend" viewBox="0 0 420 170" role="img" aria-label="近七天新建与发布趋势">
            <line v-for="n in 4" :key="`grid-${n}`" x1="16" :y1="20 + (n - 1) * 34" x2="410"
              :y2="20 + (n - 1) * 34" stroke="var(--line-hair)" stroke-width="1" />
            <g v-for="(day, index) in trend" :key="day.date">
              <rect
                :x="24 + index * 56" :y="136 - (day.created / trendMax) * 110"
                width="16" :height="(day.created / trendMax) * 110"
                fill="var(--status-developing)" rx="1"
              />
              <rect
                :x="44 + index * 56" :y="136 - (day.released / trendMax) * 110"
                width="16" :height="(day.released / trendMax) * 110"
                fill="var(--status-released)" rx="1"
              />
              <text :x="42 + index * 56" y="154" text-anchor="middle" class="trend__label">
                {{ day.date.slice(5) }}
              </text>
            </g>
          </svg>
          <div class="card__foot">
            新建合计 {{ trend.reduce((sum, day) => sum + day.created, 0) }} 条 · 发布合计
            {{ trend.reduce((sum, day) => sum + day.released, 0) }} 条
          </div>
        </section>

        <!-- 成员负载 -->
        <section class="card">
          <div class="card__head">
            <h2 class="card__title">03 / 成员负载</h2>
            <span class="u-label">未分配 {{ stats.unassigned }} 条</span>
          </div>
          <div v-if="stats.member_load.length" class="bars">
            <div v-for="row in stats.member_load" :key="row.user.id" class="bar-row">
              <div class="bar-row__name">{{ row.user.display_name }}</div>
              <div class="bar-row__track">
                <span
                  class="bar-row__fill"
                  :style="{
                    width: `${(row.total / memberMax) * 100}%`,
                    background: 'var(--status-developing)',
                  }"
                ></span>
              </div>
              <div class="bar-row__meta u-mono">
                {{ row.total }} / 在做 {{ row.doing }} / 完成 {{ row.released }}
              </div>
            </div>
          </div>
          <div v-else class="field__hint">还没有分配需求单。</div>
        </section>

        <!-- 优先级 / 类型 -->
        <section class="card">
          <div class="card__head">
            <h2 class="card__title">04 / 优先级与类型</h2>
            <span class="u-label">当前项目</span>
          </div>
          <div class="bars">
            <div
              v-for="row in stats.priority_distribution"
              :key="row.priority"
              class="bar-row"
            >
              <div class="bar-row__name">{{ PRIORITY_LABELS[row.priority] || row.priority }}</div>
              <div class="bar-row__track">
                <span
                  class="bar-row__fill"
                  :style="{
                    width: `${(row.count / priorityMax) * 100}%`,
                    background: 'var(--status-pending-accept)',
                  }"
                ></span>
              </div>
              <div class="bar-row__meta u-mono">{{ row.count }}</div>
            </div>
          </div>
          <div class="type-row">
            <span
              v-for="row in stats.type_distribution"
              :key="row.type"
              class="type-pill u-mono"
            >
              {{ row.type }} · {{ row.count }}
            </span>
          </div>
        </section>
      </div>

      <!-- 个人指标 -->
      <section class="card mine">
        <div class="card__head">
          <h2 class="card__title">05 / 我的指标</h2>
          <span class="u-label">{{ mine.user.display_name }} · 当前项目内</span>
        </div>
        <div class="mine__kpis">
          <div class="mine__kpi">
            <div class="u-label">我创建</div>
            <div class="mine__num u-num">{{ mine.created }}</div>
          </div>
          <div class="mine__kpi">
            <div class="u-label">我负责</div>
            <div class="mine__num u-num">{{ mine.assigned }}</div>
          </div>
          <div class="mine__kpi">
            <div class="u-label">进行中</div>
            <div class="mine__num u-num" style="color: var(--status-developing)">
              {{ mine.in_progress }}
            </div>
          </div>
          <div class="mine__kpi">
            <div class="u-label">已发布</div>
            <div class="mine__num u-num" style="color: var(--status-released)">
              {{ mine.released }}
            </div>
          </div>
          <div class="mine__kpi">
            <div class="u-label">我操作的流转</div>
            <div class="mine__num u-num">{{ mine.transitions }}</div>
          </div>
        </div>

        <div class="mine__split">
          <div>
            <div class="u-label mine__sub">我负责的需求 · 状态分布</div>
            <div class="stack">
              <span
                v-for="row in mineSegments"
                :key="row.status"
                class="stack__seg"
                :style="{
                  width: `${(row.count / mineTotal) * 100}%`,
                  background: toneVar(row.status),
                }"
                :title="`${statusLabel(row.status)} ${row.count}`"
              ></span>
            </div>
            <div class="mine__legend">
              <span v-for="row in mineSegments" :key="row.status" class="mine__legend-item">
                <span class="legend__dot" :style="{ background: toneVar(row.status) }"></span>
                {{ statusLabel(row.status) }} {{ row.count }}
              </span>
            </div>
          </div>
          <div>
            <div class="u-label mine__sub">最近更新 · 我负责的</div>
            <div v-if="mine.recent.length" class="recent">
              <div v-for="row in mine.recent" :key="row.id" class="recent__row">
                <span class="u-mono recent__no">{{ row.story_no }}</span>
                <span class="recent__title">{{ row.title }}</span>
                <span class="status-chip" :data-tone="STATUS_TONES[row.status]">
                  {{ statusLabel(row.status) }}
                </span>
                <span class="u-mono recent__time">{{ formatTime(row.updated_at) }}</span>
              </div>
            </div>
            <div v-else class="field__hint">还没有分配给你的需求单。</div>
          </div>
        </div>
        <div class="mine__foot">
          <button
            class="btn btn--sm"
            @click="router.push({ name: 'stories', params: { teamId: teamId } })"
          >
            去需求单列表 →
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.board {
  max-width: var(--maxw);
  margin: 0 auto;
  padding: var(--space-12) var(--margin) var(--space-16);
}
.board__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--gutter);
  padding-bottom: var(--space-8);
}
.board__crumb { margin-bottom: var(--space-4); }
.board__lead { margin-top: var(--space-2); }
.board__head-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
.board__scope {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  text-align: right;
}
.board__project { font-weight: 600; }
.board__rule {
  height: 2px;
  background: var(--line-base);
  margin-bottom: var(--space-8);
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  border: 1px solid var(--line-base);
  margin-bottom: var(--space-8);
}
.kpi {
  padding: var(--space-4) var(--space-6);
  border-right: 1px solid var(--line-hair);
}
.kpi:last-child { border-right: 0; }
.kpi__value {
  font-size: 32px;
  line-height: 40px;
  font-weight: 600;
  margin-top: var(--space-1);
}
.board__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}
.card {
  border: 1px solid var(--line-base);
  background: var(--bg-surface);
  padding: var(--space-6);
}
.card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--line-hair);
  margin-bottom: var(--space-6);
}
.card__title {
  font-size: var(--fs-h2);
  line-height: var(--lh-h2);
  font-weight: 600;
}
.card__foot {
  margin-top: var(--space-3);
  font-size: var(--fs-label);
  color: var(--ink-3);
}
.donut-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-8);
}
.donut { width: 160px; height: 160px; flex: 0 0 160px; }
.donut__num {
  fill: var(--ink);
  font-size: 26px;
  font-weight: 600;
  font-family: var(--font-ui);
}
.donut__label { fill: var(--ink-3); font-size: 10px; }
.legend { flex: 1; min-width: 0; }
.legend__row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 3px 0;
}
.legend__dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: 0 0 8px;
}
.legend__dot--inline { margin: 0 4px 0 8px; vertical-align: 0; }
.legend__num { margin-left: auto; font-variant-numeric: tabular-nums; }
.trend { width: 100%; height: auto; }
.trend__label { fill: var(--ink-3); font-size: 10px; }
.bars { display: flex; flex-direction: column; gap: var(--space-3); }
.bar-row {
  display: grid;
  grid-template-columns: 72px 1fr auto;
  align-items: center;
  gap: var(--space-3);
}
.bar-row__name { font-size: var(--fs-body); }
.bar-row__track {
  height: 8px;
  background: var(--bg-sunken);
  overflow: hidden;
}
.bar-row__fill { display: block; height: 100%; min-width: 2px; }
.bar-row__meta { font-size: 11px; color: var(--ink-3); white-space: nowrap; }
.type-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid var(--line-hair);
}
.type-pill {
  padding: 2px 8px;
  border: 1px solid var(--line-base);
  color: var(--ink-2);
  font-size: 11px;
}
.mine { margin-top: var(--space-6); }
.mine__kpis {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-8);
}
.mine__kpi {
  padding: var(--space-3) var(--space-4);
  background: var(--bg-sunken);
  border-left: 2px solid var(--line-base);
}
.mine__num { font-size: 24px; line-height: 32px; font-weight: 600; }
.mine__split {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: var(--space-8);
}
.mine__sub { margin-bottom: var(--space-3); }
.stack {
  display: flex;
  height: 14px;
  background: var(--bg-sunken);
  overflow: hidden;
}
.stack__seg { display: block; height: 100%; }
.mine__legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-3);
  font-size: var(--fs-label);
  color: var(--ink-2);
}
.mine__legend-item { display: inline-flex; align-items: center; gap: 4px; }
.recent__row {
  display: grid;
  grid-template-columns: 88px 1fr auto auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--line-hair);
  font-size: var(--fs-label);
}
.recent__no { color: var(--ink-3); }
.recent__title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recent__time { color: var(--ink-3); font-size: 11px; }
.mine__foot {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-6);
}
@media (max-width: 992px) {
  .board__grid, .mine__split { grid-template-columns: 1fr; }
  .kpi-grid, .mine__kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kpi { border-bottom: 1px solid var(--line-hair); }
  .board__head { flex-direction: column; align-items: flex-start; }
  .board__scope { text-align: left; }
}
</style>
