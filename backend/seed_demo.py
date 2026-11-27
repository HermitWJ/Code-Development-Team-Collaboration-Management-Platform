"""本地演示数据：只用于把页面跑起来看效果，生产环境禁止执行。

用法（先 migrate）：
    DB_ENGINE=sqlite python seed_demo.py
演示账号口令可用 DEMO_PASSWORD 环境变量覆盖，默认仅本地演示值。
"""
import hashlib
import os
from datetime import timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.stories.models import Project, Story, StoryTransition  # noqa: E402
from apps.stories.services import import_commits  # noqa: E402
from apps.teams.models import Team, TeamCounter, TeamMember  # noqa: E402

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo12345")

USERS = [
    ("zhangsan", "张三"),
    ("lisi", "李四"),
    ("wangwu", "王五"),
]

# 团队下的多个项目，每个项目有自己的仓库与 main 基线
PROJECTS = [
    ("STAR-WEB", "星河前端", "https://github.com/example/star-web.git", "main", "前端控制台与工作看板"),
    ("STAR-API", "星河服务端", "https://github.com/example/star-api.git", "main", "Django REST 服务与状态机"),
]

# 单号 1016-1023 作为历史需求；计数器停在 1023，用户新建的第一条正好是 STAR-1024
STORIES = [
    (1016, "feat", "支持按季度归档审计日志", "planning", "medium", "zhangsan", "lisi",
     "每季度首月自动归档上一季度的审计日志，归档后只读。"),
    (1017, "fix", "修复导出月报时区偏移八小时", "developing", "high", "lisi", "lisi",
     "导出接口的起止时间按 UTC 计算，导致运营看到的月份少一天。"),
    (1018, "docs", "补齐团队邀请流程说明", "planning", "low", "zhangsan", None,
     "把建团、添加成员、角色边界写进团队上手文档。"),
    (1019, "feat", "需求单支持按负责人筛选", "pending_accept", "medium", "lisi", "zhangsan",
     "列表筛选栏增加负责人条件，并与关键字搜索叠加生效。"),
    (1020, "refactor", "拆分状态轮转与写流水逻辑", "developing", "medium", "zhangsan", "lisi",
     "把转移矩阵与乐观锁收进领域层，视图只负责参数与响应。"),
    (1021, "perf", "列表首屏查询减少一次连表", "released", "high", "lisi", "lisi",
     "创建人与负责人改为一次 select_related 取回。"),
    (1022, "fix", "旧版导入脚本兼容 MySQL 5.7", "cancelled", "low", "zhangsan", None,
     "目标库已统一 8.0，不再需要兼容分支。"),
    (1023, "chore", "统一本地开发环境变量模板", "suspended", "low", "zhangsan", "zhangsan",
     "等部署方案确定后再统一模板，避免反复改。"),
]


def ensure_pending_accept(team):
    """老演示库幂等补齐一条「待验收」单，方便首页看板展示新状态。"""
    if Story.objects.filter(
        team=team, status=Story.STATUS_PENDING_ACCEPT, is_deleted=False
    ).exists():
        return False
    candidate = (
        Story.objects.filter(
            team=team, status=Story.STATUS_PENDING_TEST, is_deleted=False
        )
        .order_by("no_seq")
        .first()
    )
    if candidate is None:
        return False
    StoryTransition.objects.create(
        story=candidate,
        from_status=Story.STATUS_PENDING_TEST,
        to_status=Story.STATUS_PENDING_ACCEPT,
        operator=candidate.assignee or candidate.creator,
        remark="测试通过，提交验收",
    )
    candidate.status = Story.STATUS_PENDING_ACCEPT
    candidate.version = candidate.version + 1
    candidate.save(update_fields=["status", "version", "updated_at"])
    return True


def ensure_codebase_demo(team, users):
    """幂等补齐：项目、需求单开发分支、相对 main 的新增 commit 记录。"""
    projects = {}
    for slug, name, repo, main, desc in PROJECTS:
        project, _ = Project.objects.get_or_create(
            team=team,
            slug=slug,
            defaults={
                "name": name,
                "repo_url": repo,
                "main_branch": main,
                "description": desc,
            },
        )
        projects[slug] = project

    linked = 0
    ordered = list(
        Story.objects.filter(team=team, is_deleted=False).order_by("no_seq")
    )
    for index, story in enumerate(ordered):
        if story.status in (Story.STATUS_PLANNING, Story.STATUS_CANCELLED):
            continue
        project = projects["STAR-WEB" if index % 2 == 0 else "STAR-API"]
        branch = f"feature/{story.story_no.lower()}"
        changed = False
        if story.project_id != project.id or story.branch_name != branch:
            story.project = project
            story.branch_name = branch
            story.base_branch = project.main_branch
            story.save(
                update_fields=["project", "branch_name", "base_branch", "updated_at"]
            )
            changed = True

        rows = []
        for i in range(2):
            sha = hashlib.sha1(
                f"{story.story_no}:{i}".encode("utf-8")
            ).hexdigest()
            author = users["zhangsan"] if i == 0 else users["lisi"]
            rows.append({
                "sha": sha,
                "title": (
                    f"{story.type}: {story.title} --story={story.no_seq}"
                    if i == 0
                    else f"test: 补充 {story.story_no} 自动化用例"
                ),
                "message": "演示数据：该开发分支相对 main 的新增提交",
                "author": author.username,
                "committed_at": timezone.now() - timedelta(days=6 - index, hours=i * 3),
                "additions": 48 + i * 17,
                "deletions": 7 + i * 4,
                "files_changed": 3 + i,
            })
        result = import_commits(project, branch, project.main_branch, rows, story)
        if changed or result["created"]:
            linked += 1
    return linked


@transaction.atomic
def run():
    User = get_user_model()
    users = {}
    for username, display_name in USERS:
        user, created = User.objects.get_or_create(
            username=username, defaults={"first_name": display_name}
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])
        users[username] = user

    team, _ = Team.objects.get_or_create(
        slug="STAR", defaults={"name": "星河项目组", "owner": users["zhangsan"]}
    )
    TeamMember.objects.get_or_create(
        team=team, user=users["zhangsan"], defaults={"role": TeamMember.ROLE_OWNER}
    )
    TeamMember.objects.get_or_create(
        team=team, user=users["lisi"], defaults={"role": TeamMember.ROLE_MEMBER}
    )
    counter, _ = TeamCounter.objects.get_or_create(team=team, defaults={"last_no": 0})

    if Story.objects.filter(team=team).exists():
        print("演示数据已存在，跳过导入")
        if ensure_pending_accept(team):
            print("已补齐一条「待验收」演示需求")
    else:
        for seq, kind, title, status, priority, creator, assignee, desc in STORIES:
            story = Story.objects.create(
                team=team,
                story_no=f"STAR-{seq}",
                no_seq=seq,
                type=kind,
                title=title,
                description=desc,
                status=status,
                priority=priority,
                creator=users[creator],
                assignee=users[assignee] if assignee else None,
                version=2 if status != "planning" else 1,
            )
            if status == "developing":
                StoryTransition.objects.create(
                    story=story, from_status="planning", to_status="developing",
                    operator=users["zhangsan"], remark="排期确定，开始开发",
                )
            elif status == "pending_test":
                StoryTransition.objects.create(
                    story=story, from_status="planning", to_status="developing",
                    operator=users["zhangsan"], remark="评审排期完成",
                )
                StoryTransition.objects.create(
                    story=story, from_status="developing", to_status="pending_test",
                    operator=users["lisi"], remark="已自测，提交测试",
                )
            elif status == "pending_accept":
                StoryTransition.objects.create(
                    story=story, from_status="planning", to_status="developing",
                    operator=users["zhangsan"], remark="排期确定",
                )
                StoryTransition.objects.create(
                    story=story, from_status="developing", to_status="pending_test",
                    operator=users["lisi"], remark="提测通过",
                )
                StoryTransition.objects.create(
                    story=story, from_status="pending_test", to_status="pending_accept",
                    operator=users["lisi"], remark="测试通过，提交验收",
                )
            elif status == "released":
                StoryTransition.objects.create(
                    story=story, from_status="planning", to_status="developing",
                    operator=users["zhangsan"], remark="排期确定",
                )
                StoryTransition.objects.create(
                    story=story, from_status="developing", to_status="pending_test",
                    operator=users["lisi"], remark="提测",
                )
                StoryTransition.objects.create(
                    story=story, from_status="pending_test", to_status="pending_accept",
                    operator=users["lisi"], remark="测试通过，提交验收",
                )
                StoryTransition.objects.create(
                    story=story, from_status="pending_accept", to_status="released",
                    operator=users["zhangsan"], remark="验收通过",
                )

        counter.last_no = 1023
        counter.save(update_fields=["last_no"])
        print(f"演示数据就绪：团队 {team.slug}，{len(STORIES)} 条需求，计数器 1023")
        print(f"演示账号：zhangsan / lisi / wangwu，口令见 DEMO_PASSWORD（默认 {DEMO_PASSWORD}）")

    linked = ensure_codebase_demo(team, users)
    if linked:
        print(f"代码工程演示数据就绪：{len(PROJECTS)} 个项目，{linked} 条需求绑定分支与 commit")


if __name__ == "__main__":
    run()
