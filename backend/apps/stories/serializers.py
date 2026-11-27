import re

import bleach
from rest_framework import serializers

from apps.common.exceptions import ApiError
from apps.stories.commit_title import STORY_TYPES, STORY_TYPE_VALUES, build_commit_title
from apps.stories.models import BranchCommit, Project, Story, StoryTransition
from apps.stories.state_machine import available_actions
from apps.teams.models import TeamMember
from apps.teams.serializers import user_brief, validate_repo_url

PRIORITY_VALUES = [value for value, _ in Story.PRIORITY_CHOICES]
STORY_TYPE_LABELS = dict(STORY_TYPES)
STATUS_LABELS = dict(Story.STATUS_CHOICES)
PROJECT_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,31}$")
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/\-]+$")

# 富文本白名单：脚本标签、on* 事件属性、javascript: 链接一律由 bleach 剔除
RICH_TAGS = [
    "p", "br", "div", "span", "h1", "h2", "h3", "h4", "strong", "b",
    "em", "i", "u", "s", "strike", "ul", "ol", "li", "blockquote",
    "code", "pre", "hr", "a", "img", "video", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td",
]
RICH_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height"],
    "video": ["src", "controls", "width", "poster"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}
RICH_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_rich_text(value):
    """说明栏落库前净化：前端 v-html 展示的永远是这份服务端权威结果。"""
    text = re.sub(
        r"<(script|style|iframe|object)\b[^>]*>.*?</\1\s*>",
        "",
        value or "",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return bleach.clean(
        text,
        tags=RICH_TAGS,
        attributes=RICH_ATTRIBUTES,
        protocols=RICH_PROTOCOLS,
        strip=True,
    )


class ProjectSerializer(serializers.ModelSerializer):
    story_count = serializers.SerializerMethodField()
    commit_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "name", "slug", "repo_url", "main_branch",
            "local_repo_path", "description", "story_count", "commit_count",
            "created_at", "updated_at",
        ]

    def get_story_count(self, obj):
        return Story.objects.filter(project=obj, is_deleted=False).count()

    def get_commit_count(self, obj):
        return BranchCommit.objects.filter(project=obj).count()


class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=64, trim_whitespace=True)
    slug = serializers.CharField(max_length=32, trim_whitespace=True)
    repo_url = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    main_branch = serializers.CharField(max_length=128, default="main")
    local_repo_path = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    description = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    def validate_slug(self, value):
        if not PROJECT_SLUG_PATTERN.fullmatch(value):
            raise serializers.ValidationError("项目标识只允许字母、数字、点、下划线与短横线")
        return value

    def validate_repo_url(self, value):
        return validate_repo_url(value)

    def validate_main_branch(self, value):
        branch = (value or "main").strip()
        if not BRANCH_PATTERN.fullmatch(branch):
            raise serializers.ValidationError("主分支名包含非法字符")
        return branch


class ProjectUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=64, required=False)
    repo_url = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    main_branch = serializers.CharField(
        max_length=128, required=False, allow_blank=True
    )
    local_repo_path = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    description = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )

    def validate_repo_url(self, value):
        return validate_repo_url(value)

    def validate_main_branch(self, value):
        branch = (value or "main").strip()
        if not BRANCH_PATTERN.fullmatch(branch):
            raise serializers.ValidationError("主分支名包含非法字符")
        return branch


class BranchCommitSerializer(serializers.ModelSerializer):
    short_sha = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    story_no = serializers.SerializerMethodField()

    class Meta:
        model = BranchCommit
        fields = [
            "id", "project", "project_name", "story", "story_no",
            "branch_name", "base_branch", "sha", "short_sha", "title",
            "message", "author", "committed_at", "url",
            "additions", "deletions", "files_changed", "created_at",
        ]

    def get_short_sha(self, obj):
        return obj.sha[:8]

    def get_project_name(self, obj):
        return obj.project.name if obj.project_id else ""

    def get_story_no(self, obj):
        return obj.story.story_no if obj.story_id else ""


class CommitItemSerializer(serializers.Serializer):
    sha = serializers.CharField(max_length=64)
    title = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    message = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=""
    )
    author = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )
    committed_at = serializers.DateTimeField(required=False, allow_null=True)
    url = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )
    additions = serializers.IntegerField(required=False, min_value=0, default=0)
    deletions = serializers.IntegerField(required=False, min_value=0, default=0)
    files_changed = serializers.IntegerField(required=False, min_value=0, default=0)


class CommitImportSerializer(serializers.Serializer):
    project_id = serializers.IntegerField(min_value=1)
    story_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True
    )
    branch_name = serializers.CharField(max_length=128)
    base_branch = serializers.CharField(
        max_length=128, required=False, allow_blank=True, default=""
    )
    commits = CommitItemSerializer(many=True)

    def validate_branch_name(self, value):
        if not BRANCH_PATTERN.fullmatch(value):
            raise serializers.ValidationError("分支名包含非法字符")
        return value

    def validate_base_branch(self, value):
        if value and not BRANCH_PATTERN.fullmatch(value):
            raise serializers.ValidationError("基线分支名包含非法字符")
        return value


class _AssigneeMixin:
    def validate_assignee_id(self, value):
        if value is None:
            return None
        team_id = self.context.get("team_id")
        if not TeamMember.objects.filter(team_id=team_id, user_id=value).exists():
            raise ApiError(400, "INVALID_PARAM", "负责人必须是本团队成员")
        return value


class _TypeMixin:
    def validate_type(self, value):
        if value not in STORY_TYPE_VALUES:
            raise ApiError(400, "INVALID_STORY_TYPE", "不支持的需求类型")
        return value


class _ProjectBranchMixin:
    def validate_project_id(self, value):
        if value is None:
            return None
        team_id = self.context.get("team_id")
        if not Project.objects.filter(id=value, team_id=team_id).exists():
            raise ApiError(400, "INVALID_PARAM", "项目不属于当前团队")
        return value

    def validate_branch_name(self, value):
        branch = (value or "").strip()
        if branch and not BRANCH_PATTERN.fullmatch(branch):
            raise serializers.ValidationError("分支名只允许字母、数字、点、下划线、短横线与斜杠")
        return branch


class StoryCreateSerializer(
    _AssigneeMixin, _TypeMixin, _ProjectBranchMixin, serializers.Serializer
):
    """字段白名单：单号、状态、版本、团队归属一律不接受客户端传入。"""

    type = serializers.CharField(max_length=16)
    title = serializers.CharField(max_length=200, trim_whitespace=True)
    description = serializers.CharField(
        required=False, allow_blank=True, default="", trim_whitespace=False
    )
    assignee_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    priority = serializers.ChoiceField(choices=PRIORITY_VALUES, default="medium")
    project_id = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    branch_name = serializers.CharField(
        max_length=128, required=False, allow_blank=True, default=""
    )

    def validate_title(self, value):
        if not value:
            raise serializers.ValidationError("标题不能为空")
        return value

    def validate_description(self, value):
        return sanitize_rich_text(value)


class StoryUpdateSerializer(
    _AssigneeMixin, _TypeMixin, _ProjectBranchMixin, serializers.Serializer
):
    version = serializers.IntegerField(min_value=1)
    type = serializers.CharField(max_length=16, required=False)
    title = serializers.CharField(max_length=200, required=False, trim_whitespace=True)
    description = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=False
    )
    assignee_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    priority = serializers.ChoiceField(choices=PRIORITY_VALUES, required=False)
    project_id = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    branch_name = serializers.CharField(
        max_length=128, required=False, allow_blank=True
    )

    def validate_description(self, value):
        return sanitize_rich_text(value)


class TransitionCreateSerializer(serializers.Serializer):
    action = serializers.CharField(max_length=32)
    version = serializers.IntegerField(min_value=1)
    remark = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


class StorySerializer(serializers.ModelSerializer):
    commit_title = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()
    assignee = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)
    type_label = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id",
            "story_no",
            "no_seq",
            "type",
            "type_label",
            "title",
            "description",
            "status",
            "status_label",
            "priority",
            "priority_label",
            "project",
            "branch_name",
            "base_branch",
            "creator",
            "assignee",
            "version",
            "commit_title",
            "available_actions",
            "created_at",
            "updated_at",
        ]

    def get_commit_title(self, obj):
        return build_commit_title(obj.type, obj.title, obj.no_seq)

    def get_creator(self, obj):
        return user_brief(obj.creator)

    def get_assignee(self, obj):
        return user_brief(obj.assignee)

    def get_type_label(self, obj):
        return STORY_TYPE_LABELS.get(obj.type, obj.type)

    def get_project(self, obj):
        if not obj.project_id:
            return None
        return {
            "id": obj.project.id,
            "name": obj.project.name,
            "slug": obj.project.slug,
            "repo_url": obj.project.repo_url,
            "main_branch": obj.project.main_branch,
        }

    def get_available_actions(self, obj):
        role = self.context.get("role")
        user_id = self.context.get("user_id")
        if not role:
            return []
        return available_actions(obj, role, user_id)


class StoryTransitionSerializer(serializers.ModelSerializer):
    operator = serializers.SerializerMethodField()
    from_status_label = serializers.SerializerMethodField()
    to_status_label = serializers.SerializerMethodField()

    class Meta:
        model = StoryTransition
        fields = [
            "id",
            "from_status",
            "from_status_label",
            "to_status",
            "to_status_label",
            "operator",
            "remark",
            "created_at",
        ]

    def get_operator(self, obj):
        return user_brief(obj.operator)

    def get_from_status_label(self, obj):
        return STATUS_LABELS.get(obj.from_status, obj.from_status)

    def get_to_status_label(self, obj):
        return STATUS_LABELS.get(obj.to_status, obj.to_status)
