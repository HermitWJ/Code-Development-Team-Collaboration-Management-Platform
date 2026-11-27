from apps.common.exceptions import ApiError
from apps.common.permissions import get_membership


class TeamContextMixin:
    """所有业务视图共用：先反查成员关系，再允许碰数据。"""

    def get_team_context(self, request, required_roles=None):
        team_id = request.parser_context["kwargs"].get("team_id")
        membership = getattr(request, "team_membership", None)
        if membership is None:
            membership = get_membership(request.user, team_id)

        if membership is None:
            raise ApiError(
                403,
                "NOT_TEAM_MEMBER",
                "你不在该团队中",
                {"team_id": team_id},
            )
        if required_roles and membership.role not in required_roles:
            raise ApiError(403, "ROLE_NOT_ALLOWED", "当前角色不能执行该操作")
        return membership.team, membership

    def get_story(self, team_id, story_id):
        """不属于本团队的单视为不存在，避免泄露别团队的数据存在性。"""
        from apps.stories.models import Story

        story = Story.objects.filter(
            id=story_id, team_id=team_id, is_deleted=False
        ).first()
        if story is None:
            raise ApiError(404, "STORY_NOT_FOUND", "需求单不存在")
        return story
