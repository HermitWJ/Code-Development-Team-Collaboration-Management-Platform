"""无评审状态机：转移矩阵只在服务端这一份，前端可用动作由接口返回。"""

from apps.teams.models import TeamMember

MANAGER_ROLES = {TeamMember.ROLE_OWNER, TeamMember.ROLE_ADMIN}
# 验收负责人只负责「待验收」的通过与打回；owner/admin 保留兜底能力
ACCEPT_ROLES = MANAGER_ROLES | {TeamMember.ROLE_ACCEPTOR}
TERMINAL_STATUSES = {"released", "cancelled"}
MAIN_STATUSES = [
    "planning", "developing", "pending_test", "pending_accept", "released"
]

TRANSITIONS = {
    "start": {
        "from": ["planning"],
        "to": "developing",
        "roles": MANAGER_ROLES,
        "require_assignee": True,
        "label": "开始开发",
    },
    "cancel": {
        "from": ["planning"],
        "to": "cancelled",
        "roles": MANAGER_ROLES,
        "require_remark": True,
        "label": "暂停 / 不做了",
    },
    "suspend": {
        "from": ["planning", "developing"],
        "to": "suspended",
        "roles": MANAGER_ROLES,
        "require_remark": True,
        "label": "暂缓",
    },
    "submit_test": {
        "from": ["developing"],
        "to": "pending_test",
        "roles": MANAGER_ROLES,
        "allow_assignee": True,
        "label": "提交测试",
    },
    "reopen": {
        "from": ["pending_test"],
        "to": "developing",
        "roles": MANAGER_ROLES,
        "allow_assignee": True,
        "label": "测试打回",
    },
    "submit_accept": {
        "from": ["pending_test"],
        "to": "pending_accept",
        "roles": MANAGER_ROLES,
        "allow_assignee": True,
        "label": "测试通过·提交验收",
    },
    "release": {
        "from": ["pending_accept"],
        "to": "released",
        "roles": ACCEPT_ROLES,
        "label": "验收通过·发布",
    },
    "accept_reject": {
        "from": ["pending_accept"],
        "to": "developing",
        "roles": ACCEPT_ROLES,
        "require_remark": True,
        "label": "验收不通过·打回开发",
    },
    "resume_plan": {
        "from": ["suspended"],
        "to": "planning",
        "roles": MANAGER_ROLES,
        "label": "回到规划",
    },
    "resume_dev": {
        "from": ["suspended"],
        "to": "developing",
        "roles": MANAGER_ROLES,
        "require_assignee": True,
        "label": "直接开发",
    },
}


def _role_allowed(rule, story, role, user_id):
    if role in rule["roles"]:
        return True, None
    if rule.get("allow_assignee") and story.assignee_id == user_id:
        return True, None
    if rule.get("allow_assignee"):
        return False, ("NOT_ASSIGNEE", "只能轮转自己负责的需求单")
    return False, ("ROLE_NOT_ALLOWED", "当前角色不能执行该操作")


def available_actions(story, role, user_id):
    """给前端渲染按钮用；前端不写死矩阵，减少前后端规则漂移。"""
    result = []
    if story.status in TERMINAL_STATUSES:
        return result
    for action, rule in TRANSITIONS.items():
        if story.status not in rule["from"]:
            continue
        allowed, _ = _role_allowed(rule, story, role, user_id)
        if not allowed:
            continue
        if rule.get("require_assignee") and story.assignee_id is None:
            continue
        result.append({
            "action": action,
            "label": rule["label"],
            "to_status": rule["to"],
            "require_remark": bool(rule.get("require_remark")),
        })
    return result


def resolve_action(story, action, role, user_id, remark):
    """返回 (目标状态, 错误)；错误为 (业务码, 提示) 或 None。"""
    rule = TRANSITIONS.get(action)
    if rule is None:
        return None, ("TRANSITION_NOT_ALLOWED", "不支持的操作")
    if story.status in TERMINAL_STATUSES:
        return None, ("TRANSITION_NOT_ALLOWED", "终态不可再流转")
    if story.status not in rule["from"]:
        return None, ("TRANSITION_NOT_ALLOWED", "当前状态不能执行该操作")

    allowed, err = _role_allowed(rule, story, role, user_id)
    if not allowed:
        return None, err
    if rule.get("require_assignee") and story.assignee_id is None:
        return None, ("TRANSITION_NOT_ALLOWED", "请先指定负责人")
    if rule.get("require_remark") and not (remark or "").strip():
        return None, ("INVALID_PARAM", "请填写说明或原因")
    return rule["to"], None
