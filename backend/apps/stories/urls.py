from django.urls import path

from apps.stories.views import (
    StoryDetailView,
    StoryListCreateView,
    StoryMediaUploadView,
    StoryStatsView,
    TransitionListCreateView,
)

urlpatterns = [
    path("", StoryListCreateView.as_view(), name="story-list"),
    path("stats/", StoryStatsView.as_view(), name="story-stats"),
    path("media/", StoryMediaUploadView.as_view(), name="story-media"),
    path("<int:story_id>/", StoryDetailView.as_view(), name="story-detail"),
    path(
        "<int:story_id>/transitions/",
        TransitionListCreateView.as_view(),
        name="story-transitions",
    ),
]
