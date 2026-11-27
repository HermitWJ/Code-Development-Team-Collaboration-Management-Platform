// 平台级导航唯一数据源，按「能力域」分组，不是围绕需求单组织。
// 加功能：把 enabled 改 true + 加一条路由 + 加一个 view，SideNav 不用改。
export default [
  { key: 'dashboard', title: '工作看板', path: 'dashboard', group: '工作台', enabled: true },

  { key: 'team-settings', title: '团队设置', path: 'settings', group: '团队与项目管理', enabled: true },
  { key: 'projects', title: '项目管理', path: 'projects', group: '团队与项目管理', enabled: true },

  { key: 'story', title: '需求单', path: 'stories', group: '项目管理', enabled: true },
  { key: 'iteration', title: '迭代', path: 'iterations', group: '项目管理', enabled: false },
  { key: 'bug', title: '缺陷', path: 'bugs', group: '项目管理', enabled: false },

  { key: 'branch', title: '分支查看', path: 'code/branches', group: '代码工程', enabled: true },
  { key: 'commit', title: '代码提交', path: 'code/commits', group: '代码工程', enabled: true },
  { key: 'review', title: '代码评审', path: 'reviews', group: '代码工程', enabled: false },

  { key: 'pipeline', title: '流水线', path: 'pipelines', group: '交付部署', enabled: false },
  { key: 'deploy', title: '部署记录', path: 'deployments', group: '交付部署', enabled: false },
  { key: 'env', title: '环境配置', path: 'environments', group: '交付部署', enabled: false },

  { key: 'report', title: '数据报表', path: 'reports', group: '洞察', enabled: false },
]
