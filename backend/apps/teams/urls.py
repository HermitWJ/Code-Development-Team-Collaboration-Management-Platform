from django.urls import path

from apps.teams.views import (
    MemberDetailView,
    MemberListCreateView,
    TeamDetailView,
    TeamListCreateView,
)

urlpatterns = [
    path("", TeamListCreateView.as_view(), name="team-list"),
    path("<int:team_id>/", TeamDetailView.as_view(), name="team-detail"),
    path("<int:team_id>/members/", MemberListCreateView.as_view(), name="team-members"),
    path(
        "<int:team_id>/members/<int:user_id>/",
        MemberDetailView.as_view(),
        name="team-member-detail",
    ),
]
