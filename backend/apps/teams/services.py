from django.contrib.auth import get_user_model
from django.db import transaction

from apps.common.exceptions import ApiError
from apps.teams.models import Team, TeamCounter, TeamMember


@transaction.atomic
def create_team(user, name, slug, git_repo_url=""):
    """建团、写入 owner、初始化计数器，三件事在一个事务里。"""
    team = Team.objects.create(
        name=name, slug=slug, owner=user, git_repo_url=git_repo_url
    )
    TeamMember.objects.create(team=team, user=user, role=TeamMember.ROLE_OWNER)
    TeamCounter.objects.create(team=team, last_no=0)
    return team


@transaction.atomic
def add_member(team, user_id, role):
    User = get_user_model()
    if not User.objects.filter(id=user_id).exists():
        raise ApiError(404, "USER_NOT_FOUND", "找不到该用户", {"user_id": user_id})
    _, created = TeamMember.objects.get_or_create(
        team=team, user_id=user_id, defaults={"role": role}
    )
    if not created:
        raise ApiError(409, "MEMBER_EXISTS", "该用户已在团队中")
    return TeamMember.objects.select_related("user").get(team=team, user_id=user_id)


@transaction.atomic
def remove_member(team, user_id):
    membership = TeamMember.objects.filter(team=team, user_id=user_id).first()
    if membership is None:
        raise ApiError(404, "MEMBER_NOT_FOUND", "该用户不在团队中")
    if membership.role == TeamMember.ROLE_OWNER:
        raise ApiError(409, "CANNOT_REMOVE_OWNER", "不能移除团队创建者")
    membership.delete()
