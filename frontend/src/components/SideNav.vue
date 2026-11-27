<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import menuConfig from '../config/menuConfig'

const route = useRoute()

const groups = computed(() => {
  const map = new Map()
  menuConfig.forEach((item) => {
    if (!map.has(item.group)) map.set(item.group, [])
    map.get(item.group).push(item)
  })
  return Array.from(map, ([name, items]) => ({ name, items }))
})

const teamId = computed(() => route.params.teamId || 0)

function isActive(item) {
  return item.enabled && route.path.endsWith(`/${item.path}`)
}
</script>

<template>
  <aside class="side">
    <!-- 平台品牌区：只显示平台名，禁止写当前页名称 -->
    <div class="side__brand">
      <div class="side__brand-row">
        <span class="side__brand-mark"></span>
        <span class="side__brand-title">协作平台</span>
      </div>
      <div class="side__brand-sub">workspace / v0.1.0</div>
    </div>

    <div v-for="group in groups" :key="group.name" class="side__group">
      <div class="side__group-label">{{ group.name }}</div>
      <template v-for="item in group.items" :key="item.key">
        <router-link
          v-if="item.enabled"
          :to="`/teams/${teamId}/${item.path}`"
          class="side__item"
          :class="{ 'is-active': isActive(item) }"
        >
          <span class="side__mark"></span>
          <span>{{ item.title }}</span>
        </router-link>
        <div v-else class="side__item is-disabled">
          <span class="side__mark"></span>
          <span>{{ item.title }}</span>
          <span class="side__soon">待开放</span>
        </div>
      </template>
    </div>

    <div class="side__foot u-mono">local / engineering console</div>
  </aside>
</template>

<style scoped>
.side {
  width: var(--sidebar-w);
  flex: 0 0 var(--sidebar-w);
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  background: var(--bg-paper);
  border-right: 1px solid var(--line-base);
  display: flex;
  flex-direction: column;
}
.side__brand {
  height: var(--topbar-h);
  flex: 0 0 var(--topbar-h);
  padding: 0 var(--space-6);
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-bottom: 1px solid var(--line-hair);
}
.side__brand-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.side__brand-mark {
  position: relative;
  width: 12px;
  height: 12px;
  border: 1px solid var(--accent);
  border-radius: 1px;
  flex: 0 0 12px;
}
.side__brand-mark::after {
  content: '';
  position: absolute;
  inset: 3px;
  background: var(--accent);
}
.side__brand-title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.01em;
}
.side__brand-sub {
  margin: 2px 0 0 24px;
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 14px;
  color: var(--ink-3);
}
.side__group {
  padding: var(--space-6) 0 var(--space-2);
  border-bottom: 1px solid var(--line-hair);
}
.side__group-label {
  padding: 0 var(--space-6) var(--space-3);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--ink-3);
}
.side__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 36px;
  padding: 0 var(--space-6);
  font-size: var(--fs-body);
  color: var(--ink-2);
  transition: background-color var(--t-fast) var(--ease-standard),
    color var(--t-fast) var(--ease-standard);
}
.side__mark {
  width: 2px;
  height: 14px;
  background: transparent;
  flex: 0 0 2px;
}
.side__item:not(.is-disabled):hover {
  background: var(--bg-sunken);
  color: var(--ink);
}
.side__item.is-active {
  color: var(--ink);
  font-weight: 600;
}
.side__item.is-active .side__mark {
  background: var(--accent);
}
.side__item.is-disabled {
  color: var(--ink-3);
  cursor: default;
}
.side__soon {
  margin-left: auto;
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--ink-3);
}
.side__foot {
  margin-top: auto;
  padding: var(--space-6);
  font-size: 11px;
  color: var(--ink-3);
}
@media (max-width: 992px) {
  .side__brand-sub,
  .side__soon,
  .side__foot,
  .side__group-label {
    display: none;
  }
  .side__brand-row {
    justify-content: center;
  }
  .side__brand-title {
    display: none;
  }
  .side__item {
    justify-content: center;
    padding: 0;
  }
  .side__item > span:not(.side__mark) {
    display: none;
  }
}
</style>
