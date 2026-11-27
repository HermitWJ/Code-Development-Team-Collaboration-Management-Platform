from rest_framework.permissions import BasePermission

from apps.common.exceptions import ApiError


def get_membership(user, team_id):
    """服务端权威判定：角色只从成员表反查，绝不读请求体里的角色声明。"""
    from apps.teams.models import TeamMember

    if not user or not user.is_authenticated:
        return None
    return (
        TeamMember.objects.filter(team_id=team_id, user_id=user.id)
        .select_related("team")
        .first()
    )


class IsTeamMember(BasePermission):
    """挂在所有 /teams/{team_id}/... 接口上；查不到成员关系直接 403。"""

    def has_permission(self, request, view):
        team_id = view.kwargs.get("team_id")
        membership = get_membership(request.user, team_id)
        request.team_membership = membership
        if membership is None:
            # 直接抛业务异常，避免 DRF 默认的 403 被泛化映射成 ROLE_NOT_ALLOWED
            raise ApiError(
                403, "NOT_TEAM_MEMBER", "你不在该团队中", {"team_id": team_id}
            )
        return True
