from django.conf import settings
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=64)
    # 单号前缀：大写字母数字，创建后不可改，否则历史单号与已复制的 commit 标题对不上
    slug = models.CharField(max_length=16, unique=True)
    # 团队绑定的 Git 仓库地址；只存地址，不连 Git、不记录凭证
    git_repo_url = models.CharField(max_length=255, blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_teams",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "team"
        ordering = ["id"]

    def __str__(self):
        return f"{self.slug} {self.name}"


class TeamMember(models.Model):
    ROLE_OWNER = "owner"
    ROLE_ADMIN = "admin"
    ROLE_ACCEPTOR = "acceptor"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [
        (ROLE_OWNER, "创建者"),
        (ROLE_ADMIN, "管理员"),
        (ROLE_ACCEPTOR, "验收负责人"),
        (ROLE_MEMBER, "成员"),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "team_member"
        constraints = [
            models.UniqueConstraint(fields=["team", "user"], name="uk_team_user")
        ]
        indexes = [models.Index(fields=["user"], name="idx_team_member_user")]

    def __str__(self):
        return f"{self.team_id}:{self.user_id}:{self.role}"


class TeamCounter(models.Model):
    """每个团队一行；取号时用行锁，保证团队内编号不撞。"""

    team = models.OneToOneField(
        Team, primary_key=True, on_delete=models.CASCADE, related_name="counter"
    )
    last_no = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "team_counter"

    def __str__(self):
        return f"{self.team_id}:{self.last_no}"
