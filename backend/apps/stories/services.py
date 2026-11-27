import re
import shutil
import subprocess
from collections import Counter
from datetime import timedelta
from pathlib import Path

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.common.exceptions import ApiError
from apps.stories.models import BranchCommit, Project, Story, StoryTransition
from apps.stories.numbering import allocate_number
from apps.stories.serializers import BranchCommitSerializer
from apps.stories.state_machine import resolve_action
from apps.teams.models import TeamMember

EDITABLE_FIELDS = {
    "type", "title", "description", "assignee_id", "priority",
    "project_id", "branch_name", "base_branch",
}
DOING_STATUSES = {
    Story.STATUS_DEVELOPING,
    Story.STATUS_PENDING_TEST,
    Story.STATUS_PENDING_ACCEPT,
}
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/\-]+$")
SHORTSTAT_PATTERN = re.compile(
    r"(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?"
)


@transaction.atomic
def create_story(team, user, data):
    """取号与落库在同一事务；回滚不会留下半截编号。"""
    story_no, no_seq = allocate_number(team)
    return Story.objects.create(
        team=team,
        story_no=story_no,
        no_seq=no_seq,
        type=data["type"],
        title=data["title"],
        description=data.get("description", ""),
        status=Story.STATUS_PLANNING,
        priority=data.get("priority", "medium"),
        creator=user,
        assignee_id=data.get("assignee_id"),
        project_id=data.get("project_id"),
        branch_name=data.get("branch_name", ""),
        base_branch=data.get("base_branch", ""),
        version=1,
    )


@transaction.atomic
def update_story(story, data):
    version = data["version"]
    fields = {key: value for key, value in data.items() if key in EDITABLE_FIELDS}
    fields["version"] = F("version") + 1
    fields["updated_at"] = timezone.now()
    updated = Story.objects.filter(
        id=story.id, team_id=story.team_id, version=version
    ).update(**fields)
    if not updated:
        raise ApiError(409, "VERSION_CONFLICT", "内容已被别人改过，请刷新后重试")
    story.refresh_from_db()
    return story


@transaction.atomic
def perform_transition(story, user, role, action, version, remark):
    """状态与流水在同一事务；影响行数为 0 时绝不写一条孤立流水。"""
    # 版本先于规则判定：重复提交与并发覆盖都归为「请刷新」，错误码保持一致
    if story.version != version:
        raise ApiError(409, "VERSION_CONFLICT", "状态已被别人改过，请刷新后重试")

    to_status, error = resolve_action(story, action, role, user.id, remark)
    if error:
        code, message = error
        http_status = 403 if code in ("ROLE_NOT_ALLOWED", "NOT_ASSIGNEE") else (
            400 if code == "INVALID_PARAM" else 409
        )
        raise ApiError(http_status, code, message)

    from_status = story.status
    updated = Story.objects.filter(
        id=story.id,
        team_id=story.team_id,
        version=version,
        status=from_status,
    ).update(
        status=to_status,
        version=F("version") + 1,
        updated_at=timezone.now(),
    )
    if not updated:
        raise ApiError(409, "VERSION_CONFLICT", "状态已被别人改过，请刷新后重试")

    StoryTransition.objects.create(
        story=story,
        from_status=from_status,
        to_status=to_status,
        operator=user,
        remark=remark or "",
    )
    story.refresh_from_db()
    return story, from_status, to_status


@transaction.atomic
def delete_story(story, user):
    """软删除：保留需求单与历史流水，所有查询入口统一过滤 is_deleted。"""
    now = timezone.now()
    updated = Story.objects.filter(
        id=story.id, team_id=story.team_id, is_deleted=False
    ).update(
        is_deleted=True,
        deleted_at=now,
        deleted_by=user,
        version=F("version") + 1,
        updated_at=now,
    )
    if not updated:
        raise ApiError(404, "STORY_NOT_FOUND", "需求单不存在")
    return updated


def project_brief(project):
    if project is None:
        return None
    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "repo_url": project.repo_url,
        "main_branch": project.main_branch,
        "local_repo_path": project.local_repo_path,
    }


def repo_web_url(repo_url):
    """把 git@ / .git 形式的仓库地址规整成可点击的网页地址。"""
    url = (repo_url or "").strip()
    if not url:
        return ""
    if url.startswith("git@"):
        url = "https://" + url[4:].replace(":", "/", 1)
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return ""
    if url.endswith(".git"):
        url = url[:-4]
    return url.rstrip("/")


def build_repo_links(repo_url, branch="", base_branch="", sha=""):
    base = repo_web_url(repo_url)
    if not base:
        return {"repo": "", "branch": "", "compare": "", "commit": ""}
    return {
        "repo": base,
        "branch": f"{base}/tree/{branch}" if branch else "",
        "compare": f"{base}/compare/{base_branch}...{branch}" if base_branch and branch else "",
        "commit": f"{base}/commit/{sha}" if sha else "",
    }


def base_branch_for(project, fallback=""):
    if project and project.main_branch:
        return project.main_branch
    return fallback or "main"


def resolve_branch_fields(team, data, current=None):
    """绑定开发分支时把项目 main 分支快照到 base_branch；解绑时清空。"""
    branch = (data.get("branch_name") or "").strip()
    project_id = data.get("project_id", current.project_id if current else None)
    project = Project.objects.filter(id=project_id, team_id=team.id).first() if project_id else None
    if branch:
        data["base_branch"] = base_branch_for(project, current.base_branch if current else "")
    else:
        data["base_branch"] = ""
    return data


@transaction.atomic
def import_commits(project, branch_name, base_branch, rows, story=None):
    """按 (项目, 分支, sha) 去重导入；同一 sha 再次导入不会重复计数。"""
    created = 0
    for row in rows:
        sha = str(row.get("sha") or "").strip()
        if not sha:
            continue
        link = build_repo_links(project.repo_url, sha=sha)["commit"]
        committed_at = row.get("committed_at")
        if isinstance(committed_at, str):
            committed_at = parse_datetime(committed_at)
        _, was_created = BranchCommit.objects.get_or_create(
            project=project,
            branch_name=branch_name,
            sha=sha,
            defaults={
                "story": story,
                "base_branch": base_branch or project.main_branch,
                "title": str(row.get("title") or sha[:8])[:255],
                "message": row.get("message") or "",
                "author": str(row.get("author") or "")[:64],
                "committed_at": committed_at,
                "url": (row.get("url") or "").strip() or link,
                "additions": int(row.get("additions") or 0),
                "deletions": int(row.get("deletions") or 0),
                "files_changed": int(row.get("files_changed") or 0),
            },
        )
        if was_created:
            created += 1
        elif story is not None:
            BranchCommit.objects.filter(
                project=project, branch_name=branch_name, sha=sha, story__isnull=True
            ).update(story=story)
    return {
        "created": created,
        "total": len(rows),
        "repo_links": build_repo_links(
            project.repo_url, branch_name, base_branch or project.main_branch
        ),
    }


def sync_branch_commits(project, story, branch_name):
    """从项目配置的本地仓库按 main..branch 读取新增 commit（不访问远程、不需要凭据）。"""
    path = (project.local_repo_path or "").strip()
    if not path or not Path(path, ".git").exists():
        raise ApiError(
            400, "LOCAL_REPO_MISSING", "项目未配置本地仓库路径，或该路径不是 Git 仓库"
        )
    if not BRANCH_PATTERN.fullmatch(branch_name) or not BRANCH_PATTERN.fullmatch(project.main_branch):
        raise ApiError(400, "INVALID_PARAM", "分支名包含非法字符")
    git = shutil.which("git")
    if not git:
        raise ApiError(400, "GIT_UNAVAILABLE", "本机未找到 git 命令")

    spec = f"{project.main_branch}..{branch_name}"
    try:
        result = subprocess.run(
            [
                git, "-C", path, "log", spec, "--date=iso-strict",
                "--format=%H%x1f%an%x1f%aI%x1f%s%x1f%b%x1e",
            ],
            capture_output=True, text=True, timeout=30, check=False,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ApiError(400, "GIT_SYNC_FAILED", "读取本地仓库失败或超时")
    if result.returncode != 0:
        raise ApiError(400, "GIT_SYNC_FAILED", "分支或基线不存在，无法计算新增 commit")

    rows = []
    for block in result.stdout.split("\x1e"):
        block = block.strip("\n")
        if not block.strip():
            continue
        parts = block.strip().split("\x1f")
        if len(parts) < 4:
            continue
        sha, author, when, title = parts[0], parts[1], parts[2], parts[3]
        message = parts[4] if len(parts) > 4 else ""
        additions, deletions, files_changed = 0, 0, 0
        stat = subprocess.run(
            [git, "-C", path, "show", "--shortstat", "--format=", sha.strip()],
            capture_output=True, text=True, timeout=15, check=False,
            encoding="utf-8", errors="replace",
        )
        if stat.returncode == 0:
            match = SHORTSTAT_PATTERN.search(stat.stdout)
            if match:
                files_changed = int(match.group(1) or 0)
                additions = int(match.group(2) or 0)
                deletions = int(match.group(3) or 0)
        rows.append({
            "sha": sha.strip(),
            "title": title.strip()[:255],
            "message": message.strip(),
            "author": author.strip()[:64],
            "committed_at": parse_datetime(when.strip()) if when.strip() else None,
            "additions": additions,
            "deletions": deletions,
            "files_changed": files_changed,
        })
    return import_commits(project, branch_name, project.main_branch, rows, story)


def build_branch_summary(story):
    """需求单详情用：绑定分支、基线、相对基线的新增 commit 与总信息。"""
    project = story.project
    rows = list(BranchCommit.objects.filter(story=story)) if story.id else []
    if not rows and story.branch_name and project:
        rows = list(
            BranchCommit.objects.filter(project=project, branch_name=story.branch_name)
        )
    base = story.base_branch or base_branch_for(project)
    authors = sorted({row.author for row in rows if row.author})
    latest = max((row.committed_at for row in rows if row.committed_at), default=None)
    return {
        "project": project_brief(project),
        "branch_name": story.branch_name,
        "base_branch": base,
        "repo_links": build_repo_links(
            project.repo_url if project else "", story.branch_name, base
        ),
        "total": len(rows),
        "additions": sum(row.additions for row in rows),
        "deletions": sum(row.deletions for row in rows),
        "files_changed": sum(row.files_changed for row in rows),
        "authors": authors,
        "author_count": len(authors),
        "latest_commit_at": latest.isoformat() if latest else None,
        "commits": BranchCommitSerializer(rows, many=True).data,
    }


def _brief(user):
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.get_full_name() or user.username,
    }


def build_dashboard_stats(team, user, project=None):
    """团队与个人指标一次算齐；传入项目时只统计该项目下的需求与提交。"""
    story_qs = Story.objects.filter(
        team_id=team.id, is_deleted=False
    ).select_related("creator", "assignee")
    if project is not None:
        story_qs = story_qs.filter(project_id=project.id)
    stories = list(story_qs)
    transition_qs = StoryTransition.objects.filter(
        story__team_id=team.id, story__is_deleted=False
    )
    if project is not None:
        transition_qs = transition_qs.filter(story__project_id=project.id)
    transitions = list(
        transition_qs.values_list("to_status", "operator_id", "created_at")
    )

    total = len(stories)
    status_counts = Counter(story.status for story in stories)
    priority_counts = Counter(story.priority for story in stories)
    type_counts = Counter(story.type for story in stories)
    released = status_counts.get(Story.STATUS_RELEASED, 0)
    in_progress = sum(status_counts.get(code, 0) for code in DOING_STATUSES)

    load = {}
    for story in stories:
        if story.assignee_id is None:
            continue
        row = load.setdefault(
            story.assignee_id, {"total": 0, "doing": 0, "released": 0}
        )
        row["total"] += 1
        if story.status in DOING_STATUSES:
            row["doing"] += 1
        if story.status == Story.STATUS_RELEASED:
            row["released"] += 1
    member_load = []
    for membership in TeamMember.objects.filter(team=team).select_related("user"):
        row = load.get(membership.user_id, {"total": 0, "doing": 0, "released": 0})
        member_load.append({"user": _brief(membership.user), **row})
    member_load.sort(key=lambda row: (-row["total"], row["user"]["username"]))

    today = timezone.localdate()
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    created_series = Counter(
        timezone.localtime(story.created_at).date() for story in stories
    )
    released_series = Counter(
        timezone.localtime(created_at).date()
        for to_status, _, created_at in transitions
        if to_status == Story.STATUS_RELEASED
    )
    trend = [
        {
            "date": day.isoformat(),
            "created": created_series.get(day, 0),
            "released": released_series.get(day, 0),
        }
        for day in days
    ]

    mine_assigned = [story for story in stories if story.assignee_id == user.id]
    mine_status = Counter(story.status for story in mine_assigned)
    mine_recent = [
        {
            "id": story.id,
            "story_no": story.story_no,
            "title": story.title,
            "status": story.status,
            "status_label": story.get_status_display(),
            "updated_at": story.updated_at.isoformat(),
        }
        for story in sorted(
            mine_assigned, key=lambda story: story.updated_at, reverse=True
        )[:5]
    ]

    return {
        "team": {"id": team.id, "name": team.name, "slug": team.slug},
        "project": project_brief(project),
        "total": total,
        "released": released,
        "in_progress": in_progress,
        "pending_accept": status_counts.get(Story.STATUS_PENDING_ACCEPT, 0),
        "completion_rate": round(released / total, 4) if total else 0.0,
        "unassigned": sum(1 for story in stories if story.assignee_id is None),
        "status_distribution": [
            {"status": code, "label": label, "count": status_counts.get(code, 0)}
            for code, label in Story.STATUS_CHOICES
        ],
        "priority_distribution": [
            {"priority": code, "label": label, "count": priority_counts.get(code, 0)}
            for code, label in Story.PRIORITY_CHOICES
        ],
        "type_distribution": [
            {"type": code, "count": count}
            for code, count in sorted(
                type_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "member_load": member_load,
        "trend": trend,
        "mine": {
            "user": _brief(user),
            "created": sum(
                1 for story in stories if story.creator_id == user.id
            ),
            "assigned": len(mine_assigned),
            "released": mine_status.get(Story.STATUS_RELEASED, 0),
            "in_progress": sum(mine_status.get(code, 0) for code in DOING_STATUSES),
            "status_distribution": [
                {"status": code, "label": label, "count": mine_status.get(code, 0)}
                for code, label in Story.STATUS_CHOICES
            ],
            "transitions": sum(1 for _, operator_id, _ in transitions if operator_id == user.id),
            "recent": mine_recent,
        },
    }
