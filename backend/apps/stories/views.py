import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import ApiError
from apps.common.mixins import TeamContextMixin
from apps.common.pagination import StandardPagination
from apps.common.permissions import IsTeamMember
from apps.stories.models import BranchCommit, Project, Story, StoryTransition
from apps.stories.serializers import (
    BranchCommitSerializer,
    CommitImportSerializer,
    ProjectCreateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
    StoryCreateSerializer,
    StorySerializer,
    StoryTransitionSerializer,
    StoryUpdateSerializer,
    TransitionCreateSerializer,
)
from apps.stories.services import (
    build_branch_summary,
    build_dashboard_stats,
    build_repo_links,
    create_story,
    delete_story,
    import_commits,
    perform_transition,
    resolve_branch_fields,
    sync_branch_commits,
    update_story,
)
from apps.teams.models import TeamMember
from apps.teams.serializers import user_brief

MANAGER_ROLES = {TeamMember.ROLE_OWNER, TeamMember.ROLE_ADMIN}
ALLOWED_ORDERING = {"no_seq", "updated_at", "created_at"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
IMAGE_MAX_SIZE = 10 * 1024 * 1024
VIDEO_MAX_SIZE = 100 * 1024 * 1024


class StoryListCreateView(TeamContextMixin, APIView):
    permission_classes = [IsAuthenticated, IsTeamMember]

    def _context(self, membership, user):
        return {"role": membership.role, "user_id": user.id}

    def get(self, request, team_id):
        team, membership = self.get_team_context(request)
        params = request.query_params
        queryset = Story.objects.filter(
            team_id=team.id, is_deleted=False
        ).select_related("creator", "assignee", "project")

        for field in ("status", "type", "priority"):
            value = params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        if params.get("assignee_id"):
            queryset = queryset.filter(assignee_id=params["assignee_id"])
        if params.get("project_id"):
            queryset = queryset.filter(project_id=params["project_id"])
        keyword = (params.get("keyword") or "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) | Q(story_no__icontains=keyword)
            )

        ordering = params.get("ordering", "-no_seq")
        if ordering.lstrip("-") not in ALLOWED_ORDERING:
            ordering = "-no_seq"
        # 已发布统一置底：先按「是否完成」分组，再按用户选择的排序
        queryset = queryset.annotate(
            release_tail=Case(
                When(status=Story.STATUS_RELEASED, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by("release_tail", ordering, "-id")

        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = StorySerializer(
            page, many=True, context=self._context(membership, request.user)
        ).data
        return paginator.get_paginated_response(data)

    def post(self, request, team_id):
        team, membership = self.get_team_context(request)
        serializer = StoryCreateSerializer(
            data=request.data, context={"team_id": team.id}
        )
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        resolve_branch_fields(team, data)
        story = create_story(team, request.user, data)
        return Response(
            StorySerializer(
                story, context=self._context(membership, request.user)
            ).data,
            status=201,
        )


class StoryDetailView(TeamContextMixin, APIView):
    permission_classes = [IsAuthenticated, IsTeamMember]

    def get(self, request, team_id, story_id):
        team, membership = self.get_team_context(request)
        story = self.get_story(team.id, story_id)
        payload = dict(
            StorySerializer(
                story,
                context={"role": membership.role, "user_id": request.user.id},
            ).data
        )
        rows = StoryTransition.objects.filter(story=story).select_related("operator")
        payload["transitions"] = StoryTransitionSerializer(rows, many=True).data
        # 分支绑定、相对 main 的新增 commit 与总信息，一次返回给详情页
        payload["branch_summary"] = build_branch_summary(story)
        return Response(payload)

    def patch(self, request, team_id, story_id):
        team, membership = self.get_team_context(request)
        story = self.get_story(team.id, story_id)
        is_manager = membership.role in MANAGER_ROLES
        is_related = request.user.id in (story.creator_id, story.assignee_id)
        if not is_manager and not is_related:
            raise ApiError(403, "ROLE_NOT_ALLOWED", "只能编辑自己创建或负责的需求单")

        serializer = StoryUpdateSerializer(
            data=request.data, context={"team_id": team.id}
        )
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        resolve_branch_fields(team, data, story)
        story = update_story(story, data)
        return Response(
            StorySerializer(
                story,
                context={"role": membership.role, "user_id": request.user.id},
            ).data
        )

    def delete(self, request, team_id, story_id):
        team, membership = self.get_team_context(request)
        story = self.get_story(team.id, story_id)
        if membership.role not in MANAGER_ROLES:
            raise ApiError(403, "ROLE_NOT_ALLOWED", "只有创建者或管理员可删除需求单")
        delete_story(story, request.user)
        return Response(status=204)


class TransitionListCreateView(TeamContextMixin, APIView):
    permission_classes = [IsAuthenticated, IsTeamMember]

    def get(self, request, team_id, story_id):
        team, _ = self.get_team_context(request)
        story = self.get_story(team.id, story_id)
        rows = StoryTransition.objects.filter(story=story).select_related("operator")
        return Response(StoryTransitionSerializer(rows, many=True).data)

    def post(self, request, team_id, story_id):
        team, membership = self.get_team_context(request)
        story = self.get_story(team.id, story_id)
        serializer = TransitionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        story, from_status, to_status = perform_transition(
            story,
            request.user,
            membership.role,
            payload["action"],
            payload["version"],
            payload.get("remark", ""),
        )
        story_data = dict(
            StorySerializer(
                story,
                context={"role": membership.role, "user_id": request.user.id},
            ).data
        )
        rows = StoryTransition.objects.filter(story=story).select_related("operator")
        story_data["transitions"] = StoryTransitionSerializer(rows, many=True).data
        story_data["branch_summary"] = build_branch_summary(story)
        return Response(
            {
                "story_no": story.story_no,
                "from_status": from_status,
                "to_status": to_status,
                "version": story.version,
                "operator": user_brief(request.user),
                "story": story_data,
            },
            status=201,
        )


class StoryStatsView(TeamContextMixin, APIView):
    """首页大看板：按当前项目隔离的团队指标 + 当前用户个人指标。"""

    permission_classes = [IsAuthenticated, IsTeamMember]

    def get(self, request, team_id):
        team, _ = self.get_team_context(request)
        project_id = request.query_params.get("project_id")
        project = None
        if project_id:
            project = Project.objects.filter(id=project_id, team=team).first()
            if project is None:
                raise ApiError(400, "INVALID_PARAM", "项目不存在")
        return Response(build_dashboard_stats(team, request.user, project))


class StoryMediaUploadView(TeamContextMixin, APIView):
    """说明栏图片/视频上传：只认白名单扩展名，落本地 MEDIA_ROOT。"""

    permission_classes = [IsAuthenticated, IsTeamMember]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, team_id):
        team, _ = self.get_team_context(request)
        upload = request.FILES.get("file")
        if upload is None:
            raise ApiError(400, "INVALID_PARAM", "请选择要上传的图片或视频")

        suffix = Path(upload.name).suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            kind, limit = "image", IMAGE_MAX_SIZE
        elif suffix in VIDEO_EXTENSIONS:
            kind, limit = "video", VIDEO_MAX_SIZE
        else:
            raise ApiError(
                400,
                "INVALID_FILE_TYPE",
                "只支持 png/jpg/jpeg/gif/webp 图片与 mp4/webm/mov 视频",
            )
        if upload.size > limit:
            raise ApiError(400, "FILE_TOO_LARGE", f"文件不能超过 {limit // 1024 // 1024} MB")

        content_type = (upload.content_type or "").lower()
        if content_type and not content_type.startswith(kind + "/"):
            raise ApiError(400, "INVALID_FILE_TYPE", "文件内容类型与扩展名不一致")

        stored = default_storage.save(
            f"stories/{team.id}/{uuid.uuid4().hex}{suffix}", upload
        )
        return Response(
            {
                "url": settings.MEDIA_URL + stored,
                "kind": kind,
                "name": upload.name,
                "size": upload.size,
            },
            status=201,
        )


class ProjectListCreateView(TeamContextMixin, APIView):
    """团队下的多个项目，每个项目绑定自己的仓库与 main 基线。"""

    permission_classes = [IsAuthenticated, IsTeamMember]

    def get(self, request, team_id):
        team, _ = self.get_team_context(request)
        rows = Project.objects.filter(team=team).order_by("id")
        return Response(ProjectSerializer(rows, many=True).data)

    def post(self, request, team_id):
        team, _ = self.get_team_context(request, required_roles=MANAGER_ROLES)
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if Project.objects.filter(team=team, slug=data["slug"]).exists():
            raise ApiError(409, "PROJECT_SLUG_TAKEN", "项目标识已被占用")
        project = Project.objects.create(team=team, **data)
        return Response(ProjectSerializer(project).data, status=201)


class ProjectDetailView(TeamContextMixin, APIView):
    permission_classes = [IsAuthenticated, IsTeamMember]

    def _project(self, team, project_id):
        project = Project.objects.filter(id=project_id, team=team).first()
        if project is None:
            raise ApiError(404, "PROJECT_NOT_FOUND", "项目不存在")
        return project

    def get(self, request, team_id, project_id):
        team, _ = self.get_team_context(request)
        return Response(ProjectSerializer(self._project(team, project_id)).data)

    def patch(self, request, team_id, project_id):
        team, _ = self.get_team_context(request, required_roles=MANAGER_ROLES)
        project = self._project(team, project_id)
        serializer = ProjectUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(project, field, value)
        project.save(update_fields=list(serializer.validated_data.keys()) or None)
        return Response(ProjectSerializer(project).data)

    def delete(self, request, team_id, project_id):
        team, _ = self.get_team_context(request, required_roles=MANAGER_ROLES)
        project = self._project(team, project_id)
        project.delete()
        return Response(status=204)


class CommitListView(TeamContextMixin, APIView):
    """代码提交列表；POST 用于批量导入 main..branch 的新增 commit。"""

    permission_classes = [IsAuthenticated, IsTeamMember]

    def get(self, request, team_id):
        team, _ = self.get_team_context(request)
        params = request.query_params
        rows = BranchCommit.objects.filter(
            project__team=team
        ).select_related("project", "story")
        if params.get("project_id"):
            rows = rows.filter(project_id=params["project_id"])
        if params.get("story_id"):
            rows = rows.filter(story_id=params["story_id"])
        if params.get("branch"):
            rows = rows.filter(branch_name=params["branch"])
        keyword = (params.get("keyword") or "").strip()
        if keyword:
            rows = rows.filter(
                Q(title__icontains=keyword)
                | Q(sha__icontains=keyword)
                | Q(author__icontains=keyword)
            )
        data = BranchCommitSerializer(rows[:200], many=True).data
        return Response({
            "results": data,
            "summary": {
                "total": len(data),
                "additions": sum(row["additions"] for row in data),
                "deletions": sum(row["deletions"] for row in data),
                "files_changed": sum(row["files_changed"] for row in data),
                "authors": len({row["author"] for row in data if row["author"]}),
                "branches": len({row["branch_name"] for row in data}),
            },
        })

    def post(self, request, team_id):
        team, _ = self.get_team_context(request, required_roles=MANAGER_ROLES)
        serializer = CommitImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        project = Project.objects.filter(id=payload["project_id"], team=team).first()
        if project is None:
            raise ApiError(404, "PROJECT_NOT_FOUND", "项目不存在")
        story = None
        if payload.get("story_id"):
            story = Story.objects.filter(
                id=payload["story_id"], team=team, is_deleted=False
            ).first()
            if story is None:
                raise ApiError(404, "STORY_NOT_FOUND", "需求单不存在")
        result = import_commits(
            project,
            payload["branch_name"],
            payload.get("base_branch") or project.main_branch,
            payload["commits"],
            story,
        )
        return Response(result, status=201)


class CommitDetailView(TeamContextMixin, APIView):
    permission_classes = [IsAuthenticated, IsTeamMember]

    def get(self, request, team_id, sha):
        team, _ = self.get_team_context(request)
        rows = BranchCommit.objects.filter(
            project__team=team, sha=sha
        ).select_related("project", "story")
        project_id = request.query_params.get("project_id")
        if project_id:
            rows = rows.filter(project_id=project_id)
        row = rows.first()
        if row is None:
            raise ApiError(404, "COMMIT_NOT_FOUND", "commit 不存在")
        payload = dict(BranchCommitSerializer(row).data)
        links = build_repo_links(
            row.project.repo_url, row.branch_name, row.base_branch, row.sha
        )
        links["commit"] = row.url or links["commit"]
        payload["repo_links"] = links
        payload["story_brief"] = {
            "id": row.story_id,
            "story_no": row.story.story_no if row.story_id else "",
            "title": row.story.title if row.story_id else "",
        }
        return Response(payload)


class BranchSyncView(TeamContextMixin, APIView):
    """从项目配置的本地仓库读取 main..branch 的新增 commit。"""

    permission_classes = [IsAuthenticated, IsTeamMember]

    def post(self, request, team_id):
        team, _ = self.get_team_context(request, required_roles=MANAGER_ROLES)
        raw_id = request.data.get("story_id")
        try:
            story_id = int(raw_id)
        except (TypeError, ValueError):
            raise ApiError(400, "INVALID_PARAM", "请指定需求单")
        story = self.get_story(team.id, story_id)
        if story.project_id is None:
            raise ApiError(400, "PROJECT_NOT_FOUND", "需求单未归属项目")
        branch = (request.data.get("branch_name") or story.branch_name or "").strip()
        if not branch:
            raise ApiError(400, "INVALID_PARAM", "需求单未绑定开发分支")
        result = sync_branch_commits(story.project, story, branch)
        return Response(result, status=201)
