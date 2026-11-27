<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useProjectStore } from '../stores/project'

const route = useRoute()
const router = useRouter()
const project = useProjectStore()
const open = ref(false)

function pick(row) {
  open.value = false
  project.switchProject(row.id)
}

function manage() {
  open.value = false
  router.push({
    name: 'projects',
    params: { teamId: Number(route.params.teamId) || 0 },
  })
}
</script>

<template>
  <div class="switcher">
    <button class="switcher__trigger" @click="open = !open" :aria-expanded="open">
      <span class="u-label">项目</span>
      <span class="switcher__name">{{ project.currentProject?.name || '选择项目' }}</span>
      <span class="switcher__slug u-mono">{{ project.currentProject?.slug || '—' }}</span>
      <span class="switcher__caret">⌄</span>
    </button>

    <div v-if="open" class="switcher__menu">
      <div class="switcher__menu-label u-label">当前团队的项目</div>
      <button
        v-for="row in project.projects"
        :key="row.id"
        class="switcher__row"
        :class="{ 'is-current': row.id === project.currentProjectId }"
        @click="pick(row)"
      >
        <span>{{ row.name }}</span>
        <span class="u-mono">{{ row.slug }}</span>
      </button>
      <div v-if="!project.projects.length" class="switcher__empty u-label">还没有项目</div>
      <button class="switcher__create" @click="manage">项目管理 ＋</button>
    </div>
  </div>
</template>

<style scoped>
.switcher {
  position: relative;
}
.switcher__trigger {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  border: 0;
  background: transparent;
  padding: 0;
  height: var(--topbar-h);
}
.switcher__name {
  border-bottom: 1px solid var(--line-base);
  padding-bottom: 2px;
  font-size: var(--fs-body);
}
.switcher__trigger:hover .switcher__name {
  border-bottom-color: var(--ink);
}
.switcher__slug {
  color: var(--ink-3);
}
.switcher__caret {
  color: var(--ink-2);
  font-size: 16px;
}
.switcher__menu {
  position: absolute;
  top: calc(var(--topbar-h) - 4px);
  left: 0;
  z-index: 30;
  width: 260px;
  background: var(--bg-surface);
  border: 1px solid var(--line-base);
  border-radius: var(--radius-sm);
  padding: var(--space-3) 0;
}
.switcher__menu-label {
  padding: 0 var(--space-4) var(--space-2);
}
.switcher__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  border: 0;
  background: transparent;
  padding: var(--space-2) var(--space-4);
  text-align: left;
  font-size: var(--fs-body);
}
.switcher__row:hover {
  background: var(--bg-sunken);
}
.switcher__row.is-current {
  box-shadow: inset 2px 0 0 var(--accent);
}
.switcher__row .u-mono {
  color: var(--ink-3);
}
.switcher__empty {
  padding: var(--space-2) var(--space-4);
}
.switcher__create {
  width: 100%;
  border: 0;
  border-top: 1px solid var(--line-hair);
  background: transparent;
  padding: var(--space-3) var(--space-4);
  margin-top: var(--space-2);
  text-align: left;
  font-size: var(--fs-body);
  color: var(--ink-2);
}
.switcher__create:hover {
  color: var(--ink);
  background: var(--bg-sunken);
}
</style>
