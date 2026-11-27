from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from apps.accounts.views import UserSearchView
from apps.stories.views import (
    BranchSyncView,
    CommitDetailView,
    CommitListView,
    ProjectDetailView,
    ProjectListCreateView,
)

urlpatterns = [
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/users/search/", UserSearchView.as_view(), name="user-search"),
    # stories 放在 teams 之前，避免子路由被 teams 的前缀吞掉
    path("api/v1/teams/<int:team_id>/stories/", include("apps.stories.urls")),
    # 代码工程：项目仓库、commit 记录、分支同步
    path(
        "api/v1/teams/<int:team_id>/code/projects/",
        ProjectListCreateView.as_view(),
        name="project-list",
    ),
    path(
        "api/v1/teams/<int:team_id>/code/projects/<int:project_id>/",
        ProjectDetailView.as_view(),
        name="project-detail",
    ),
    path(
        "api/v1/teams/<int:team_id>/code/commits/",
        CommitListView.as_view(),
        name="commit-list",
    ),
    path(
        "api/v1/teams/<int:team_id>/code/commits/<str:sha>/",
        CommitDetailView.as_view(),
        name="commit-detail",
    ),
    path(
        "api/v1/teams/<int:team_id>/code/sync-branch/",
        BranchSyncView.as_view(),
        name="branch-sync",
    ),
    path("api/v1/teams/", include("apps.teams.urls")),
]

# 开发期由 Django 提供富文本上传的图片/视频；生产应由 Web 服务器托管 MEDIA_ROOT
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
