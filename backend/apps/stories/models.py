from django.conf import settings
from django.db import models


class Project(models.Model):
    """团队下的项目：一个项目对应一个代码仓库与一条 main 基线分支。"""

    team = models.ForeignKey(
        "teams.Team", on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=64)
    slug = models.CharField(max_length=32)
    repo_url = models.CharField(max_length=255, blank=True, default="")
    main_branch = models.CharField(max_length=128, default="main")
    # 可选：本地已 clone 的仓库根目录，用于按 main..branch 同步 commit
    local_repo_path = models.CharField(max_length=255, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "slug"], name="uk_team_project_slug"
            )
        ]

    def __str__(self):
        return f"{self.slug} {self.name}"


class Story(models.Model):
    STATUS_PLANNING = "planning"
    STATUS_DEVELOPING = "developing"
    STATUS_PENDING_TEST = "pending_test"
    STATUS_PENDING_ACCEPT = "pending_accept"
    STATUS_RELEASED = "released"
    STATUS_CANCELLED = "cancelled"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_PLANNING, "规划中"),
        (STATUS_DEVELOPING, "开发中"),
        (STATUS_PENDING_TEST, "待测试"),
        (STATUS_PENDING_ACCEPT, "待验收"),
        (STATUS_RELEASED, "已发布"),
        (STATUS_CANCELLED, "已取消"),
        (STATUS_SUSPENDED, "已挂起"),
    ]

    PRIORITY_CHOICES = [
        ("low", "低"),
        ("medium", "中"),
        ("high", "高"),
        ("urgent", "紧急"),
    ]

    team = models.ForeignKey(
        "teams.Team", on_delete=models.CASCADE, related_name="stories"
    )
    project = models.ForeignKey(
        "stories.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stories",
    )
    story_no = models.CharField(max_length=32)
    no_seq = models.PositiveIntegerField()
    type = models.CharField(max_length=16, default="feat")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=24, choices=STATUS_CHOICES, default=STATUS_PLANNING
    )
    priority = models.CharField(
        max_length=16, choices=PRIORITY_CHOICES, default="medium"
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_stories",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_stories",
    )
    # 需求单绑定的开发分支；base_branch 在绑定时从项目的 main 分支快照下来
    branch_name = models.CharField(max_length=128, blank=True, default="")
    base_branch = models.CharField(max_length=128, blank=True, default="")
    # 乐观锁：每次编辑或状态流转 +1
    version = models.PositiveIntegerField(default=1)
    # 软删除：保留历史流水，所有查询入口统一过滤
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deleted_stories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "story"
        ordering = ["-no_seq"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "story_no"], name="uk_team_story_no"
            )
        ]
        indexes = [
            models.Index(fields=["team", "status"], name="idx_story_team_status"),
            models.Index(fields=["team", "assignee"], name="idx_story_team_assignee"),
            models.Index(fields=["team", "is_deleted"], name="idx_story_team_deleted"),
        ]

    def __str__(self):
        return f"{self.story_no} {self.title}"


class StoryTransition(models.Model):
    """状态流转流水：只追加，不修改、不删除。"""

    story = models.ForeignKey(
        Story, on_delete=models.CASCADE, related_name="transitions"
    )
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="story_transitions",
    )
    remark = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_transition"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["story", "created_at"], name="idx_transition_story_time")
        ]

    def __str__(self):
        return f"{self.story_id} {self.from_status} -> {self.to_status}"


class BranchCommit(models.Model):
    """开发分支相对 main 基线的新增 commit；可关联到具体需求单。"""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="commits"
    )
    story = models.ForeignKey(
        Story,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commits",
    )
    branch_name = models.CharField(max_length=128)
    base_branch = models.CharField(max_length=128, default="main")
    sha = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, default="")
    author = models.CharField(max_length=64, blank=True, default="")
    committed_at = models.DateTimeField(null=True, blank=True)
    url = models.CharField(max_length=500, blank=True, default="")
    additions = models.PositiveIntegerField(default=0)
    deletions = models.PositiveIntegerField(default=0)
    files_changed = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "branch_commit"
        ordering = ["-committed_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "branch_name", "sha"],
                name="uk_project_branch_sha",
            )
        ]
        indexes = [
            models.Index(fields=["project", "branch_name"], name="idx_commit_branch"),
            models.Index(fields=["story"], name="idx_commit_story"),
        ]

    def __str__(self):
        return f"{self.branch_name} {self.sha[:8]}"
