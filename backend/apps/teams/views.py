from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import ApiError
from apps.common.mixins import TeamContextMixin
from apps.common.permissions import IsTeamMember
from apps.teams.models import TeamMember
from apps.teams.serializers import (
    MemberAddSerializer,
    MemberRoleUpdateSerializer,
    TeamCreateSerializer,
    TeamMemberSerializer,
    TeamSerializer,
    TeamUpdateSerializer,
)
from apps.teams.services import add_member, create_team, remove_member

MANAGER_ROLES = {TeamMember.ROLE_OWNER, TeamMember.ROLE_ADMIN}
OWNER_ROLES = {TeamMember.ROLE_OWNER}


class TeamListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            TeamMember.objects.filter(user=request.user)
            .select_related("team", "team__owner")
            .order_by("team_id")
        )
        by_team = {m.team_id: m for m in memberships}
        data = TeamSerializer(
            [m.team for m in memberships],
            many=True,
            context={"memberships": by_team},
        ).data
        return Response(data)

    def post(self, request):
        serializer = TeamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = create_team(
            request.user,
            serializer.validated_data["name"],
            serializer.validated_data["slug"],
            serializer.validated_data.get("git_repo_url", ""),
        )
        membership = TeamMember.objects.get(team=team, user=request.user)
        return Response(
            TeamSerializer(team, context={"memberships": {team.id: membership}}).data,
            status=201,
        )


class TeamDetailView(TeamContextMixin, APIView):
    permission_classes = [IsAuthenticated, IsTeamMember]

    def get(self, request, team_id):
        team, membership = self.get_team_context(request)
        return Response(
            TeamSerializer(team, context={"memberships": {team.id: membership}}).data
        )

    def patch(self, request, team_id):
        """管理员改团队名、绑定/解绑 Git 仓库；单号前缀不可改。"""
        team, membership = self.get_team_context(request, required_roles=MANAGER_ROLES)
        serializer = TeamUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data:
            for field, value in serializer.validated_data.items():
                setattr(team, field, value)
            team.save(update_fields=list(serializer.validated_data.keys()))
        return Response(
            TeamSerializer(team, context={"memberships": {team.id: membership}}).data
        )

    def delete(self, request, team_id):
        """只有创建者能删团队；成员、计数器、需求单随团队级联清理。"""
        team, _ = self.get_team_context(request, required_roles=OWNER_ROLES)
        team.delete()
        return Response(status=204)


class MemberListCreateView(TeamContextMixin, APIView):
    permission_classes = [IsAuthenticated, IsTeamMember]

    def get(self, request, team_id):
        team, _ = self.get_team_context(request)
        rows = TeamMember.objects.filter(team=team).select_related("user").order_by("id")
        return Response(TeamMemberSerializer(rows, many=True).data)

    def post(self, request, team_id):
        team, _ = self.get_team_context(request, required_roles=MANAGER_ROLES)
        serializer = MemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = add_member(
            team, serializer.validated_data["user_id"], serializer.validated_data["role"]
        )
        return Response(TeamMemberSerializer(membership).data, status=201)


class MemberDetailView(TeamContextMixin, APIView):
    permission_classes = [IsAuthenticated, IsTeamMember]

    def delete(self, request, team_id, user_id):
        team, _ = self.get_team_context(request, required_roles=MANAGER_ROLES)
        remove_member(team, user_id)
        return Response(status=204)

    def patch(self, request, team_id, user_id):
        """管理员调整成员角色，用于指定/取消团队验收负责人。"""
        team, _ = self.get_team_context(request, required_roles=MANAGER_ROLES)
        serializer = MemberRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = TeamMember.objects.filter(team=team, user_id=user_id).first()
        if membership is None:
            raise ApiError(404, "MEMBER_NOT_FOUND", "团队成员不存在")
        if membership.role == TeamMember.ROLE_OWNER:
            raise ApiError(403, "ROLE_NOT_ALLOWED", "创建者角色不可修改")
        membership.role = serializer.validated_data["role"]
        membership.save(update_fields=["role"])
        return Response(TeamMemberSerializer(membership).data)
