// 展示用常量。状态/类型的「可用取值」由后端接口与枚举决定，这里只负责中文标签。
export const STATUS_LABELS = {
  planning: '规划中',
  developing: '开发中',
  pending_test: '待测试',
  pending_accept: '待验收',
  released: '已发布',
  cancelled: '已取消',
  suspended: '已挂起',
}

// 主线五态各占一个色相，取消/挂起共用「旁路」斜纹态。
// 不只靠颜色：每态另有图标/形状差异，色弱与灰度打印下也能区分。
export const STATUS_TONES = {
  planning: 'planning',
  developing: 'developing',
  pending_test: 'pending_test',
  pending_accept: 'pending_accept',
  released: 'released',
  cancelled: 'branch',
  suspended: 'branch',
}

export const STATUS_GLYPHS = {
  planning: '○',
  developing: '◐',
  pending_test: '◇',
  pending_accept: '◆',
  released: '✓',
  cancelled: '×',
  suspended: '∥',
}

export const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  ...Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label })),
]

// 状态主线：五步五色；已取消 / 已挂起走旁路，不塞进主线
export const STATUS_STEPS = [
  { key: 'planning', label: '规划中', tone: 'planning' },
  { key: 'developing', label: '开发中', tone: 'developing' },
  { key: 'pending_test', label: '待测试', tone: 'pending_test' },
  { key: 'pending_accept', label: '待验收', tone: 'pending_accept' },
  { key: 'released', label: '已发布', tone: 'released' },
]

export const BRANCH_STATUSES = ['cancelled', 'suspended']

export const PRIORITY_LABELS = {
  low: '低',
  medium: '中',
  high: '高',
  urgent: '紧急',
}

export const PRIORITY_TONES = {
  low: 'low',
  medium: 'medium',
  high: 'high',
  urgent: 'urgent',
}

export const ROLE_LABELS = {
  owner: '创建者',
  admin: '管理员',
  acceptor: '验收负责人',
  member: '成员',
}

export const ASSIGNABLE_ROLES = [
  { value: 'member', label: '成员' },
  { value: 'acceptor', label: '验收负责人' },
  { value: 'admin', label: '管理员' },
]

export const STORY_TYPES = [
  { value: 'feat', label: 'feat · 新功能' },
  { value: 'fix', label: 'fix · 缺陷修复' },
  { value: 'docs', label: 'docs · 文档' },
  { value: 'refactor', label: 'refactor · 重构' },
  { value: 'perf', label: 'perf · 性能' },
  { value: 'test', label: 'test · 测试' },
  { value: 'chore', label: 'chore · 杂务' },
]

/** 把 git@ / .git 形式的仓库地址规整成网页地址，供外链跳转用。 */
export function repoWebUrl(url) {
  let value = (url || '').trim()
  if (!value) return ''
  if (value.startsWith('git@')) {
    value = 'https://' + value.slice(4).replace(':', '/')
  }
  if (!/^https?:\/\//i.test(value)) return ''
  if (value.endsWith('.git')) value = value.slice(0, -4)
  return value.replace(/\/$/, '')
}

export function repoLinks(repoUrl, branch = '', baseBranch = '', sha = '') {
  const base = repoWebUrl(repoUrl)
  if (!base) return { repo: '', branch: '', compare: '', commit: '' }
  return {
    repo: base,
    branch: branch ? `${base}/tree/${branch}` : '',
    compare: baseBranch && branch ? `${base}/compare/${baseBranch}...${branch}` : '',
    commit: sha ? `${base}/commit/${sha}` : '',
  }
}

export function formatTime(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}
