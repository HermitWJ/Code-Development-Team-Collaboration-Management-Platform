import re

from rest_framework import serializers

from apps.common.exceptions import ApiError
from apps.teams.models import Team, TeamMember

SLUG_PATTERN = re.compile(r"^[A-Z0-9]{2,16}$")
REPO_URL_PATTERN = re.compile(r"^(https?://|ssh://|git@)[\w.\-@:/~]+$", re.IGNORECASE)


def user_brief(user):
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.get_full_name() or user.username,
    }


def validate_repo_url(value):
    url = (value or "").strip()
    if url and not REPO_URL_PATTERN.fullmatch(url):
        raise serializers.ValidationError("仓库地址需为 http(s):// 、ssh:// 或 git@ 形式")
    return url


class TeamCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=64, trim_whitespace=True)
    slug = serializers.CharField(max_length=16, trim_whitespace=True)
    git_repo_url = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    def validate_name(self, value):
        if not value:
            raise serializers.ValidationError("团队名不能为空")
        return value

    def validate_slug(self, value):
        slug = value.upper()
        if not SLUG_PATTERN.fullmatch(slug):
            raise serializers.ValidationError("前缀只能是 2-16 位大写字母或数字")
        if Team.objects.filter(slug=slug).exists():
            raise ApiError(409, "SLUG_TAKEN", "该单号前缀已被占用", {"slug": slug})
        return slug

    def validate_git_repo_url(self, value):
        return validate_repo_url(value)


class TeamUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=64, required=False, trim_whitespace=True)
    git_repo_url = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("团队名不能为空")
        return value

    def validate_git_repo_url(self, value):
        return validate_repo_url(value)


class TeamSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id", "name", "slug", "owner", "my_role",
            "git_repo_url", "created_at",
        ]

    def get_owner(self, obj):
        return user_brief(obj.owner)

    def get_my_role(self, obj):
        membership = self.context.get("memberships", {}).get(obj.id)
        return membership.role if membership else None


class TeamMemberSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = TeamMember
        fields = ["id", "user", "role", "role_label", "joined_at"]

    def get_user(self, obj):
        return user_brief(obj.user)


class MemberRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            TeamMember.ROLE_ADMIN,
            TeamMember.ROLE_ACCEPTOR,
            TeamMember.ROLE_MEMBER,
        ]
    )


class MemberAddSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(
        choices=[
            TeamMember.ROLE_ADMIN,
            TeamMember.ROLE_ACCEPTOR,
            TeamMember.ROLE_MEMBER,
        ],
        default=TeamMember.ROLE_MEMBER,
    )
